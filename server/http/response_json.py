"""Serialização de respostas JSON HTTP."""

import json


def json_response(
    handler,
    status: int,
    body: dict,
    headers: dict | None = None,
) -> None:
    """Envia uma resposta JSON com headers e encoding padronizados."""
    # ensure_ascii=False preserva acentos/caracteres especiais (ex: "ç", "ã")
    # em vez de convertê-los em sequências \uXXXX, deixando o JSON mais legível.
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")

    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    # Content-Length é obrigatório para o cliente saber onde a resposta termina
    handler.send_header("Content-Length", str(len(payload)))

    # Permite anexar headers extras (ex: Set-Cookie de login/logout)
    if headers:
        for name, value in headers.items():
            handler.send_header(name, value)

    handler.end_headers()   # finaliza os headers, a partir daqui só vem o corpo
    handler.wfile.write(payload)    # escreve o corpo da resposta (bytes) na conexão
