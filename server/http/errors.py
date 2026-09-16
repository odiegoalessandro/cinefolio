"""Tradução de exceções da aplicação para respostas HTTP JSON."""

from http import HTTPStatus

from server.http.response_json import json_response


def write_exception_response(handler, error: Exception) -> None:
    """Envia a resposta HTTP correspondente a uma exceção da aplicação.

    Esta função centraliza a conversão "exceção Python -> status HTTP",
    evitando que cada controller precise decidir isso na mão. A ideia é:
    o tipo da exceção lançada em algum lugar do código (service, repository)
    já define automaticamente qual erro HTTP o cliente vai receber.
    """
    if isinstance(error, ValueError):
        # Erro de validação/entrada inválida do usuário -> 400 Bad Request
        json_response(
            handler,
            HTTPStatus.BAD_REQUEST,
            {"error": str(error)},
        )
        return

    if isinstance(error, PermissionError):
        # Usuário não autenticado ou sem permissão -> 401 Unauthorized
        json_response(
            handler,
            HTTPStatus.UNAUTHORIZED,
            {"error": str(error)},
        )
        return

    if isinstance(error, KeyError):
        # Recurso pedido não existe (ex: filme/usuário não encontrado) -> 404 Not Found
        message = error.args[0] if error.args else "Recurso não encontrado."
        json_response(
            handler,
            HTTPStatus.NOT_FOUND,
            {"error": message},
        )
        return

    # Qualquer outro tipo de exceção não prevista é tratada como erro interno.
    # Importante: a mensagem original do erro NÃO é exposta ao cliente aqui,
    # por segurança (evita vazar detalhes internos do sistema/stack trace).
    json_response(
        handler,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        {"error": "Ocorreu um erro interno no servidor."},
    )
