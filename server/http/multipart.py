"""Leitura restrita de uploads multipart na fronteira HTTP."""

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser


@dataclass(frozen=True)
class UploadedFile:
    """Arquivo enviado pelo cliente, sem qualquer decisão de persistência."""

    content: bytes
    content_type: str


def read_multipart_file(
    handler,
    field_name: str = "avatar",
    max_body_bytes: int = 2_162_688,
) -> UploadedFile:
    """Lê exatamente um arquivo do campo multipart esperado."""
    content_type = handler.headers.get("Content-Type", "")
    content_length = _read_content_length(handler.headers.get("Content-Length", ""))

    if not 0 < content_length <= max_body_bytes:
        raise ValueError("O tamanho da foto excede o limite permitido.")

    message = _parse_multipart_message(content_type, handler.rfile.read(content_length))
    parts = list(message.iter_parts())
    if len(parts) != 1 or _part_name(parts[0]) != field_name:
        raise ValueError("Envie somente o campo avatar.")

    part = parts[0]
    if part.get_filename() is None:
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
    """Cria uma mensagem MIME completa para o parser padrão da biblioteca."""
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode()
        + body,
    )
    if (
        message.get_content_maintype() != "multipart"
        or message.get_content_subtype() != "form-data"
        or not message.get_boundary()
    ):
        raise ValueError("Envie a foto como multipart/form-data.")
    return message


def _part_name(part) -> str | None:
    """Obtém o atributo name do Content-Disposition da parte multipart."""
    return part.get_param("name", header="content-disposition")
