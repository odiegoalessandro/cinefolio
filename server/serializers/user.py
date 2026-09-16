"""Serialização segura de usuários para respostas públicas."""


def sanitize_user(user: dict | None) -> dict | None:
    """Remove campos internos do registro de usuário.

    O registro que vem direto do banco (UserRepository) inclui o campo
    "password_hash". Essa função existe para garantir que esse campo (e
    qualquer outro campo sensível/interno) NUNCA seja enviado por engano
    numa resposta JSON para o cliente — só os campos da "allowed_keys"
    passam pelo filtro.
    """
    if not user:
        return None

    allowed_keys = (
        "id",
        "username",
        "display_name",
        "bio",
        "avatar_url",
        "banner_url",
        "created_at",
    )
    # user.keys() funciona porque "user" é um sqlite3.Row (não um dict comum),
    # que suporta acesso por chave mas precisa desse método para checar existência
    return {key: user[key] for key in allowed_keys if key in user.keys()}
