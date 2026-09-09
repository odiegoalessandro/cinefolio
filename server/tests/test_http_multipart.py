"""Testes do parser multipart usado exclusivamente no envio de avatar."""

import io
import unittest

from server.http.multipart import read_multipart_file


PNG_BYTES = b"\x89PNG\r\n\x1a\nprofile-image"


class RequestHandler:
    """Handler mínimo que fornece um body multipart ao parser."""

    def __init__(self, content_type: str, body: bytes):
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }
        self.rfile = io.BytesIO(body)


def multipart_body(boundary: str, parts: list[tuple[str, str | None, str | None, bytes]]) -> bytes:
    """Monta um payload multipart real para validar a fronteira HTTP."""
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


class MultipartReaderTests(unittest.TestCase):
    """Garante que a rota de avatar aceite apenas um arquivo permitido."""

    def test_returns_the_only_avatar_file_part(self):
        """Falha se o conteúdo ou o tipo do arquivo válido não chegar ao controlador."""
        boundary = "avatar-boundary"
        handler = RequestHandler(
            f"multipart/form-data; boundary={boundary}",
            multipart_body(
                boundary,
                [("avatar", "perfil.png", "image/png", PNG_BYTES)],
            ),
        )

        uploaded = read_multipart_file(handler)

        self.assertEqual(uploaded.content, PNG_BYTES)
        self.assertEqual(uploaded.content_type, "image/png")

    def test_rejects_a_payload_with_an_identity_field(self):
        """Falha se um cliente puder associar o upload a uma identidade no multipart."""
        boundary = "avatar-boundary"
        handler = RequestHandler(
            f"multipart/form-data; boundary={boundary}",
            multipart_body(
                boundary,
                [
                    ("avatar", "perfil.png", "image/png", PNG_BYTES),
                    ("user_id", None, None, b"2"),
                ],
            ),
        )

        with self.assertRaisesRegex(ValueError, "somente o campo avatar"):
            read_multipart_file(handler)

    def test_rejects_an_empty_avatar_file(self):
        """Falha se um upload vazio alcançar a camada de armazenamento."""
        boundary = "avatar-boundary"
        handler = RequestHandler(
            f"multipart/form-data; boundary={boundary}",
            multipart_body(
                boundary,
                [("avatar", "perfil.png", "image/png", b"")],
            ),
        )

        with self.assertRaisesRegex(ValueError, "Selecione uma foto válida"):
            read_multipart_file(handler)

    def test_rejects_a_body_larger_than_the_upload_limit(self):
        """Falha se o parser ler mais que o teto de upload definido para avatar."""
        handler = RequestHandler(
            "multipart/form-data; boundary=avatar-boundary",
            b"x" * 17,
        )

        with self.assertRaisesRegex(ValueError, "tamanho da foto"):
            read_multipart_file(handler, max_body_bytes=16)


if __name__ == "__main__":
    unittest.main()
