"""Leitura e validação de corpos JSON HTTP."""

import json


def read_json(handler) -> dict:
    """Lê e decodifica um corpo JSON com limite de tamanho."""
    content_length_header = handler.headers.get("Content-Length", "0")
    try:
        size = int(content_length_header)
    except ValueError:
        # Header ausente ou corrompido: trata como se não houvesse corpo
        size = 0

    # Limite de 30KB evita que um cliente malicioso envie um corpo gigante
    # e sobrecarregue o servidor (proteção básica contra ataque de negação de serviço)
    if size > 30_000:
        raise ValueError("O tamanho da requisição excede o limite permitido (30KB).")

    if size == 0:
        return {}   # requisição sem corpo é tratada como objeto vazio

    try:
        # rfile.read(size) lê exatamente "size" bytes do corpo da requisição
        raw_body = handler.rfile.read(size).decode("utf-8")
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise ValueError("Formato JSON inválido.") from error

    if not isinstance(payload, dict):
        # Recusa arrays, strings, números soltos etc. — só objetos JSON ({...}) são aceitos
        raise ValueError("O corpo da requisição deve ser um objeto JSON.")

    return payload
