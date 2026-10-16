from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import owner_token
from app.db import make_engine
from app.routes import router
from app.search import make_http_client
from app.search import router as search_router


def create_app() -> FastAPI:
    """App factory. Raises ConfigError immediately if OWNER_TOKEN is unset, so the server never starts unprotected."""
    token = owner_token()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with make_http_client() as http:
            app.state.http = http
            yield

    app = FastAPI(title="bookterm", lifespan=lifespan)
    app.state.owner_token = token
    app.state.engine = make_engine()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    app.include_router(search_router)
    return app
