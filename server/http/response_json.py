"""Serialização de respostas JSON HTTP."""

import json


def json_response(
    handler,
    status: int,
    body: dict,
    headers: dict | None = None,
) -> None:
    """Envia uma resposta JSON com headers e encoding padronizados."""
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))

    if headers:
        for name, value in headers.items():
            handler.send_header(name, value)

    handler.end_headers()
    handler.wfile.write(payload)
