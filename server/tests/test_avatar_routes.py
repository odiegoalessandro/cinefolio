"""Testes HTTP das rotas autenticadas de avatar."""

import json
import tempfile
import threading
import unittest
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server.config import ServerConfig
from server.database.connection import get_connection, initialize_database
from server.main import create_server
from server.repositories.user_repository import UserRepository


PNG_BYTES = b"\x89PNG\r\n\x1a\nprofile-image"


def multipart_body(boundary: str, parts: list[tuple[str, str | None, str | None, bytes]]) -> bytes:
    """Monta um body multipart real para exercitar o parser pelo servidor HTTP."""
    body = bytearray()
    for field_name, filename, content_type, content in parts:
        body.extend(f"--{boundary}\r\n".encode())
        disposition = f'Content-Disposition: form-data; name="{field_name}"'
        if filename is not None:
            disposition += f'; filename="{filename}"'
        body.extend(f"{disposition}\r\n".encode())
        if content_type is not None:
            body.extend(f"Content-Type: {content_type}\r\n".encode())
        body.extend(b"\r\n")
        body.extend(content)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    return bytes(body)


@dataclass(frozen=True)
class HttpResponse:
    """Resposta HTTP já consumida, sem manter sockets abertos durante o teste.

    urlopen devolve um objeto "ao vivo" ligado à conexão de rede — se ele
    ficasse aberto até o final do teste, poderia causar vazamento de
    recursos. Por isso a resposta é lida e guardada numa dataclass simples
    (status/headers/body) logo depois de receber, e a conexão original é fechada.
    """

    status: int
    headers: dict[str, str]
    body: bytes


class AvatarRouteTests(unittest.TestCase):
    """Garante que o upload use somente a identidade da sessão atual.

    Este arquivo é um teste de INTEGRAÇÃO: em vez de chamar as classes
    Python diretamente, ele sobe um servidor HTTP real (numa thread) e faz
    requisições de verdade contra ele — testando o sistema "de fora para
    dentro", como um cliente real faria.
    """

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        root = Path(self.temp_directory.name)
        self.database_path = root / "cinefolio.sqlite3"
        self.upload_directory = root / "avatars"
        initialize_database(self.database_path)
        self.connection = get_connection(self.database_path)
        self.users = UserRepository(self.connection)

        self.server = create_server(
            ServerConfig(host="127.0.0.1", port=0),
            database_path=self.database_path,
            avatar_upload_directory=self.upload_directory,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

        # Cria dois usuários de teste: "owner" (dono das operações testadas)
        # e "other" (uma segunda conta, usada para confirmar que as ações
        # de um usuário NUNCA afetam o outro)
        self.owner = self._register("owner")
        self.other = self._register("other")
        self.owner_cookie = self._login("owner")
        self.other_cookie = self._login("other")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.connection.close()
        self.temp_directory.cleanup()

    def test_upload_requires_an_authenticated_session(self):
        """Falha se qualquer visitante puder criar um arquivo de avatar."""
        # cookie=None simula um visitante não logado tentando fazer upload
        response = self._put_avatar(cookie=None, parts=[self._avatar_part()])

        self.assertEqual(response.status, 401)
        # Confirma que NENHUM arquivo foi criado no disco, mesmo tendo
        # enviado uma imagem válida — a rejeição acontece ANTES da escrita
        self.assertEqual(list(self.upload_directory.glob("*")), [])

    def test_upload_rejects_an_identity_part_and_preserves_the_other_user(self):
        """Falha se o multipart puder escolher qual usuário terá a foto alterada."""
        # Tenta "forjar" o dono do upload enviando um campo extra "user_id"
        # apontando para OUTRO usuário — a identidade real deve vir só do cookie
        response = self._put_avatar(
            cookie=self.owner_cookie,
            parts=[
                self._avatar_part(),
                ("user_id", None, None, str(self.other["id"]).encode()),
            ],
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(self.users.get_by_id(self.other["id"])["avatar_url"], "")
        self.assertEqual(list(self.upload_directory.glob("*")), [])

    def test_delete_avatar_uses_the_session_owner_and_restores_the_default(self):
        """Falha se remover a foto não se limitar ao usuário autenticado."""
        uploaded = self._put_avatar(self.owner_cookie, [self._avatar_part()])
        avatar_url = self._json(uploaded)["user"]["avatar_url"]

        removed = self._request(
            "DELETE",
            "/api/profile/avatar",
            cookie=self.owner_cookie,
        )

        self.assertEqual(removed.status, 200)
        self.assertEqual(self._json(removed)["user"]["avatar_url"], "")
        self.assertEqual(self.users.get_by_id(self.owner["id"])["avatar_url"], "")
        # Confirma que remover a foto do "owner" não afetou o "other" de forma alguma
        self.assertEqual(self.users.get_by_id(self.other["id"])["avatar_url"], "")
        # Confirma que o arquivo físico da foto do owner foi realmente apagado do disco
        self.assertFalse((self.upload_directory / avatar_url.rsplit("/", 1)[1]).exists())

    def test_uploaded_avatar_is_served_as_a_static_file(self):
        """Falha se uma URL retornada pelo upload não for acessível pelo frontend."""
        uploaded = self._put_avatar(self.owner_cookie, [self._avatar_part()])
        avatar_url = self._json(uploaded)["user"]["avatar_url"]

        # Confirma que a URL retornada pela API realmente funciona como
        # endereço público de imagem (sem precisar de autenticação para ver)
        with urlopen(f"{self.base_url}{avatar_url}", timeout=2) as response:
            body = response.read()

        self.assertEqual(response.status, 200)
        self.assertEqual(body, PNG_BYTES)

    def test_avatar_upload_directory_is_not_browsable(self):
        """Falha se a URL do diretório expuser uma lista de arquivos enviados por usuários."""
        self._put_avatar(self.owner_cookie, [self._avatar_part()])

        # Tenta acessar a PASTA de uploads diretamente (sem nome de
        # arquivo): não deve listar o conteúdo do diretório (o que
        # exporia os avatares de todos os usuários)
        with self.assertRaises(HTTPError) as raised:
            urlopen(f"{self.base_url}/uploads/avatars/", timeout=2)

        self.assertEqual(raised.exception.code, 404)

    def test_profile_update_rejects_an_avatar_url_and_preserves_another_users_file(self):
        """Falha se o endpoint textual puder apontar ou apagar o avatar de outra conta."""
        victim_upload = self._put_avatar(self.other_cookie, [self._avatar_part()])
        victim_avatar_url = self._json(victim_upload)["user"]["avatar_url"]

        # Tenta usar o endpoint de atualização de PERFIL (texto) para se
        # apropriar da URL de avatar de outro usuário
        response = self._request(
            "PUT",
            "/api/profile",
            body=json.dumps(
                {
                    "display_name": self.owner["display_name"],
                    "bio": "",
                    "avatar_url": victim_avatar_url,
                    "banner_url": "",
                }
            ).encode(),
            cookie=self.owner_cookie,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status, 400)
        # A foto da vítima continua intacta, tanto no disco quanto no banco
        self.assertTrue(
            (self.upload_directory / victim_avatar_url.rsplit("/", 1)[1]).exists()
        )
        self.assertEqual(
            self.users.get_by_id(self.other["id"])["avatar_url"],
            victim_avatar_url,
        )

    def test_avatar_removal_preserves_a_file_shared_by_a_legacy_record(self):
        """Falha se uma referência legada compartilhada permitir apagar a foto de outra conta."""
        victim_upload = self._put_avatar(self.other_cookie, [self._avatar_part()])
        victim_avatar_url = self._json(victim_upload)["user"]["avatar_url"]
        # Simula um cenário "legado"/anômalo: o owner passa a ter a MESMA
        # URL de avatar que a vítima (algo que não deveria acontecer no
        # fluxo normal, mas testa a defesa da camada de exclusividade)
        self.users.update_avatar_url(self.owner["id"], victim_avatar_url)

        response = self._request(
            "DELETE",
            "/api/profile/avatar",
            cookie=self.owner_cookie,
        )

        self.assertEqual(response.status, 200)
        # Mesmo removendo o avatar do owner, o arquivo físico NÃO pode ser
        # apagado, porque ainda está associado à vítima também
        # (ver avatar_url_is_exclusive_to_user em user_repository.py)
        self.assertTrue(
            (self.upload_directory / victim_avatar_url.rsplit("/", 1)[1]).exists()
        )
        self.assertEqual(
            self.users.get_by_id(self.other["id"])["avatar_url"],
            victim_avatar_url,
        )

    def _register(self, username: str) -> dict:
        """Cria um usuário pelo endpoint público de cadastro."""
        response = self._request(
            "POST",
            "/api/auth/register",
            body=json.dumps(
                {
                    "username": username,
                    "display_name": username.title(),
                    "password": "senhasegura123",
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        return self._json(response)["user"]

    def _login(self, username: str) -> str:
        """Autentica um usuário e retorna apenas o par de cookie necessário ao request."""
        response = self._request(
            "POST",
            "/api/auth/login",
            body=json.dumps({"username": username, "password": "senhasegura123"}).encode(),
            headers={"Content-Type": "application/json"},
        )

        # O header Set-Cookie pode vir com atributos extras (ex: "; HttpOnly; ...");
        # aqui só o par "session=valor" é extraído, que é o que precisa ser
        # reenviado no header Cookie das próximas requisições
        return response.headers["Set-Cookie"].split(";", 1)[0]

    def _put_avatar(self, cookie: str | None, parts) -> object:
        """Envia partes multipart para a rota de avatar."""
        boundary = "avatar-boundary"
        return self._request(
            "PUT",
            "/api/profile/avatar",
            body=multipart_body(boundary, parts),
            cookie=cookie,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )

    @staticmethod
    def _avatar_part():
        """Retorna a parte de arquivo esperada pela API."""
        return ("avatar", "perfil.png", "image/png", PNG_BYTES)

    def _request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        cookie: str | None = None,
        headers: dict | None = None,
    ):
        """Executa uma chamada HTTP e preserva respostas de erro para asserções."""
        request_headers = dict(headers or {})
        if cookie:
            request_headers["Cookie"] = cookie

        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=2) as response:
                return self._read_response(response)
        except HTTPError as error:
            # urlopen lança exceção para respostas de erro (4xx/5xx) em vez
            # de devolvê-las normalmente; aqui a exceção é capturada e
            # tratada como uma resposta comum, para os testes conseguirem
            # inspecionar o status/corpo do erro
            with error:
                return self._read_response(error)

    @staticmethod
    def _json(response) -> dict:
        """Decodifica uma resposta JSON consumindo seu body uma única vez."""
        return json.loads(response.body.decode("utf-8"))

    @staticmethod
    def _read_response(response) -> HttpResponse:
        """Fecha a resposta HTTP após reter os dados necessários à asserção."""
        return HttpResponse(
            status=response.status,
            headers=dict(response.headers.items()),
            body=response.read(),
        )


if __name__ == "__main__":
    unittest.main()
