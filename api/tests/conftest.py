from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from app.db import make_engine

API_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _owner_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OWNER_TOKEN", "test-owner-token")


@pytest.fixture
def db_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def engine(db_url: str) -> Iterator[Engine]:
    eng = make_engine(db_url)
    yield eng
    eng.dispose()
