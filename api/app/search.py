from typing import Annotated, Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
_FIELDS = "key,title,author_name,number_of_pages_median,first_publish_year"
_USER_AGENT = "bookterm/0.1 (+https://github.com/blank-beep/bookterm)"

router = APIRouter(prefix="/api")


class SearchResult(BaseModel):
    title: str
    authors: list[str]
    open_library_id: str
    page_count: int | None
    first_publish_year: int | None


def normalize(doc: dict[str, Any]) -> SearchResult | None:
    key, title = doc.get("key"), doc.get("title")
    if not isinstance(key, str) or not isinstance(title, str):
        return None
    return SearchResult(
        title=title,
        authors=[a for a in doc.get("author_name") or [] if isinstance(a, str)],
        open_library_id=key.rsplit("/", 1)[-1],
        page_count=doc.get("number_of_pages_median"),
        first_publish_year=doc.get("first_publish_year"),
    )


@router.get("/search", response_model=list[SearchResult])
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[SearchResult]:
    client: httpx.AsyncClient = request.app.state.http
    try:
        resp = await client.get(OPEN_LIBRARY_SEARCH_URL, params={"q": q, "limit": limit, "fields": _FIELDS})
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Open Library search failed") from exc
    return [r for r in (normalize(d) for d in docs) if r is not None]


def make_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0, headers={"User-Agent": _USER_AGENT})
