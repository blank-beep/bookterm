import os

DEFAULT_DATABASE_URL = "sqlite:///./bookterm.db"


def database_url() -> str:
    return os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL
