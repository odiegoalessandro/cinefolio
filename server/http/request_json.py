"""Leitura e validação de corpos JSON HTTP."""

import json


def read_json(handler) -> dict:
    """Lê e decodifica um corpo JSON com limite de tamanho."""
    content_length_header = handler.headers.get("Content-Length", "0")
    try:
        size = int(content_length_header)
    except ValueError:
        size = 0

    if size > 30_000:
        raise ValueError("O tamanho da requisição excede o limite permitido (30KB).")

    if size == 0:
        return {}

    try:
        raw_body = handler.rfile.read(size).decode("utf-8")
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise ValueError("Formato JSON inválido.") from error

    if not isinstance(payload, dict):
        raise ValueError("O corpo da requisição deve ser um objeto JSON.")

    return payload
