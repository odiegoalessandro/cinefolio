"""Serialização segura de usuários para respostas públicas."""


def sanitize_user(user: dict | None) -> dict | None:
    """Remove campos internos do registro de usuário."""
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
    return {key: user[key] for key in allowed_keys if key in user.keys()}
