import json
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from app.search import OPEN_LIBRARY_SEARCH_URL

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "openlibrary_search_dune.json").read_text())


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:  # context manager runs lifespan (creates the httpx client)
        yield c


@respx.mock
def test_search_returns_normalized_results(client: TestClient) -> None:
    route = respx.get(OPEN_LIBRARY_SEARCH_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    r = client.get("/api/search", params={"q": "dune"})
    assert r.status_code == 200
    results = r.json()
    assert len(results) == len(FIXTURE["docs"])
    assert results[0] == {
        "title": "Dune",
        "authors": ["Frank Herbert"],
        "open_library_id": "OL893414W",
        "page_count": 608,
        "first_publish_year": 1965,
    }
    assert route.calls.last.request.url.params["q"] == "dune"


@respx.mock
def test_search_tolerates_missing_fields(client: TestClient) -> None:
    respx.get(OPEN_LIBRARY_SEARCH_URL).mock(return_value=httpx.Response(200, json={"docs": [
        {"key": "/works/OL1W", "title": "Anon"},
        {"title": "no key"},
    ]}))
    assert client.get("/api/search", params={"q": "x"}).json() == [
        {"title": "Anon", "authors": [], "open_library_id": "OL1W", "page_count": None, "first_publish_year": None}
    ]


@respx.mock
@pytest.mark.parametrize("upstream", [httpx.Response(503), httpx.ConnectTimeout("boom")])
def test_upstream_failure_is_502(client: TestClient, upstream: httpx.Response | Exception) -> None:
    respx.get(OPEN_LIBRARY_SEARCH_URL).mock(side_effect=[upstream])
    assert client.get("/api/search", params={"q": "dune"}).status_code == 502


def test_empty_query_rejected(client: TestClient) -> None:
    assert client.get("/api/search", params={"q": ""}).status_code == 422


def _limited_client(monkeypatch: pytest.MonkeyPatch, limit: int, trust: bool) -> TestClient:
    monkeypatch.setenv("SEARCH_RATE_LIMIT_PER_MIN", str(limit))
    if trust:
        monkeypatch.setenv("TRUST_PROXY", "1")
    else:
        monkeypatch.delenv("TRUST_PROXY", raising=False)
    return TestClient(create_app())


@respx.mock
def test_search_rate_limited_per_client(monkeypatch: pytest.MonkeyPatch) -> None:
    respx.get(OPEN_LIBRARY_SEARCH_URL).mock(return_value=httpx.Response(200, json={"docs": []}))
    with _limited_client(monkeypatch, 3, trust=False) as c:
        codes = [c.get("/api/search", params={"q": "x"}).status_code for _ in range(4)]
        assert codes == [200, 200, 200, 429]
        assert c.get("/api/search", params={"q": "x"}).headers["retry-after"] == "60"


@respx.mock
def test_spoofed_fly_client_ip_ignored_without_trust_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    respx.get(OPEN_LIBRARY_SEARCH_URL).mock(return_value=httpx.Response(200, json={"docs": []}))
    with _limited_client(monkeypatch, 2, trust=False) as c:
        codes = [c.get("/api/search", params={"q": "x"}, headers={"Fly-Client-IP": f"10.0.0.{i}"}).status_code
                 for i in range(3)]
        assert codes == [200, 200, 429]


@respx.mock
def test_fly_client_ip_keys_limit_with_trust_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    respx.get(OPEN_LIBRARY_SEARCH_URL).mock(return_value=httpx.Response(200, json={"docs": []}))
    with _limited_client(monkeypatch, 2, trust=True) as c:
        def hit(ip: str) -> int:
            return c.get("/api/search", params={"q": "x"}, headers={"Fly-Client-IP": ip}).status_code

        assert [hit("1.1.1.1") for _ in range(3)] == [200, 200, 429]
        assert [hit("2.2.2.2") for _ in range(2)] == [200, 200]


def test_limiter_window_expires() -> None:
    from app.ratelimit import SlidingWindowLimiter

    lim = SlidingWindowLimiter(limit=1, window=60)
    assert lim.allow("a", now=0) and not lim.allow("a", now=59.9) and lim.allow("a", now=60)
