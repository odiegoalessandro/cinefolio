"""Tradução de exceções da aplicação para respostas HTTP JSON."""

from http import HTTPStatus

from server.http.response_json import json_response


def write_exception_response(handler, error: Exception) -> None:
    """Envia a resposta HTTP correspondente a uma exceção da aplicação."""
    if isinstance(error, ValueError):
        json_response(
            handler,
            HTTPStatus.BAD_REQUEST,
            {"error": str(error)},
        )
        return

    if isinstance(error, PermissionError):
        json_response(
            handler,
            HTTPStatus.UNAUTHORIZED,
            {"error": str(error)},
        )
        return

    if isinstance(error, KeyError):
        message = error.args[0] if error.args else "Recurso não encontrado."
        json_response(
            handler,
            HTTPStatus.NOT_FOUND,
            {"error": message},
        )
        return

    json_response(
        handler,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        {"error": "Ocorreu um erro interno no servidor."},
    )
