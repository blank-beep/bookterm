import os

DEFAULT_DATABASE_URL = "sqlite:///./bookterm.db"


class ConfigError(RuntimeError):
    pass


def database_url() -> str:
    return os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL


def owner_token() -> str:
    token = os.environ.get("OWNER_TOKEN", "").strip()
    if not token:
        raise ConfigError("OWNER_TOKEN is not set (or empty). Set it to a long random secret before starting the API.")
    return token
