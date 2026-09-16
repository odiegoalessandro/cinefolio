"""Leitura restrita de uploads multipart na fronteira HTTP."""

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser


@dataclass(frozen=True)
class UploadedFile:
    """Arquivo enviado pelo cliente, sem qualquer decisão de persistência.
    
        Esta classe só carrega os bytes crus e o tipo do arquivo — ela não decide
        onde/como salvar. Essa responsabilidade fica para outra camada (avatar_storage),
        seguindo o princípio de responsabilidade única.
        """

    content: bytes  # conteúdo binário do arquivo (ex: bytes da imagem)
    content_type: str   # tipo MIME informado (ex: "image/png")


def read_multipart_file(
    handler,
    field_name: str = "avatar",
    max_body_bytes: int = 2_162_688,    # ~2,06 MB: limite máximo de upload
) -> UploadedFile:
    """Lê exatamente um arquivo do campo multipart esperado.

    "multipart/form-data" é o formato usado por formulários HTML para enviar
    arquivos junto com outros dados. Aqui o servidor só aceita um único
    arquivo, no campo esperado (por padrão "avatar"), rejeitando qualquer
    outra coisa — isso simplifica e reduz a superfície de ataque.
    """
    content_type = handler.headers.get("Content-Type", "")
    content_length = _read_content_length(handler.headers.get("Content-Length", ""))

    if not 0 < content_length <= max_body_bytes:
        raise ValueError("O tamanho da foto excede o limite permitido.")

    message = _parse_multipart_message(content_type, handler.rfile.read(content_length))
    parts = list(message.iter_parts())
    # Recusa se não vier exatamente 1 parte, ou se essa parte não tiver
    # o nome de campo esperado (ex: alguém tentando mandar 2 arquivos, ou um campo errado)
    if len(parts) != 1 or _part_name(parts[0]) != field_name:
        raise ValueError("Envie somente o campo avatar.")

    part = parts[0]
    if part.get_filename() is None:
        # Sem nome de arquivo = não é um upload de arquivo de verdade
        raise ValueError("Envie somente o campo avatar.")

    content = part.get_payload(decode=True) or b""
    if not content:
        raise ValueError("Selecione uma foto válida.")

    return UploadedFile(content=content, content_type=part.get_content_type())


def _read_content_length(value: str) -> int:
    """Converte o cabeçalho Content-Length para um tamanho positivo."""
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("O tamanho da foto é inválido.") from error


def _parse_multipart_message(content_type: str, body: bytes):
    """Cria uma mensagem MIME completa para o parser padrão da biblioteca.

    O parser de e-mail da biblioteca padrão do Python (email.parser) sabe ler
    o formato multipart, mas espera uma mensagem completa com headers.
    Por isso aqui é "montada" uma mensagem MIME artificial: o header
    Content-Type real da requisição + o corpo bruto recebido.
    """
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode()
        + body,
    )
    if (
        message.get_content_maintype() != "multipart"
        or message.get_content_subtype() != "form-data"
        or not message.get_boundary()
    ):
        # boundary = delimitador que separa as partes dentro do multipart;
        # sem ele (ou com tipo errado), a requisição não é um upload válido
        raise ValueError("Envie a foto como multipart/form-data.")
    return message


def _part_name(part) -> str | None:
    """Obtém o atributo name do Content-Disposition da parte multipart."""
    # Ex: um header "Content-Disposition: form-data; name="avatar"" -> retorna "avatar"
    return part.get_param("name", header="content-disposition")
