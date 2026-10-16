from fastapi import FastAPI

from app.config import owner_token
from app.db import make_engine
from app.routes import router


def create_app() -> FastAPI:
    """App factory. Raises ConfigError immediately if OWNER_TOKEN is unset, so the server never starts unprotected."""
    token = owner_token()
    app = FastAPI(title="bookterm")
    app.state.owner_token = token
    app.state.engine = make_engine()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app
