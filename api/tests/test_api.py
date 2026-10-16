from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigError
from app.main import create_app

TOKEN = "test-owner-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client(db_url: str) -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def book_id(client: TestClient) -> int:
    r = client.post("/api/books", json={"title": "Dune", "authors": ["Frank Herbert"]}, headers=AUTH)
    assert r.status_code == 201
    return int(r.json()["id"])


@pytest.mark.parametrize("value", [None, "", "   "])
def test_startup_fails_without_owner_token(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv("OWNER_TOKEN", raising=False)
    else:
        monkeypatch.setenv("OWNER_TOKEN", value)
    with pytest.raises(ConfigError, match="OWNER_TOKEN"):
        create_app()


BAD_HEADERS = {
    "missing": {},
    "empty bearer": {"Authorization": "Bearer "},
    "wrong token": {"Authorization": "Bearer nope"},
    "token prefix": {"Authorization": f"Bearer {TOKEN[:-1]}"},
    "wrong scheme": {"Authorization": f"Basic {TOKEN}"},
}


def _writes(book_id: int) -> list[tuple[str, str, dict[str, object] | None]]:
    return [
        ("POST", "/api/books", {"title": "X"}),
        ("PATCH", f"/api/books/{book_id}", {"shelf": "read"}),
        ("DELETE", f"/api/books/{book_id}", None),
        ("POST", f"/api/books/{book_id}/notes", {"body": "n"}),
        ("POST", f"/api/books/{book_id}/quotes", {"text": "q"}),
    ]


@pytest.mark.parametrize("case", list(BAD_HEADERS))
def test_writes_rejected_without_valid_token(client: TestClient, book_id: int, case: str) -> None:
    for method, url, body in _writes(book_id):
        r = client.request(method, url, json=body, headers=BAD_HEADERS[case])
        assert r.status_code == 401, (method, url, case)
        assert r.headers["www-authenticate"] == "Bearer"
    assert client.get(f"/api/books/{book_id}").json()["shelf"] == "to_read"


def test_note_and_quote_writes_rejected_without_token(client: TestClient, book_id: int) -> None:
    note = client.post(f"/api/books/{book_id}/notes", json={"body": "n"}, headers=AUTH).json()
    quote = client.post(f"/api/books/{book_id}/quotes", json={"text": "q"}, headers=AUTH).json()
    for method, url in [("PATCH", f"/api/notes/{note['id']}"), ("DELETE", f"/api/notes/{note['id']}"),
                        ("PATCH", f"/api/quotes/{quote['id']}"), ("DELETE", f"/api/quotes/{quote['id']}")]:
        assert client.request(method, url, json={} if method == "PATCH" else None).status_code == 401


def test_reads_are_public(client: TestClient, book_id: int) -> None:
    assert client.get("/api/books").status_code == 200
    assert client.get(f"/api/books/{book_id}").status_code == 200
    assert client.get(f"/api/books/{book_id}/notes").json() == []
    assert client.get(f"/api/books/{book_id}/quotes").json() == []


def test_book_crud_with_token(client: TestClient) -> None:
    r = client.post("/api/books", headers=AUTH, json={
        "title": "Neuromancer", "authors": ["William Gibson"], "shelf": "reading", "tags": ["cyberpunk"], "rating": 4,
    })
    assert r.status_code == 201
    book = r.json()
    assert client.get("/api/books", params={"shelf": "reading"}).json()[0]["id"] == book["id"]
    assert client.get("/api/books", params={"shelf": "read"}).json() == []

    r = client.patch(f"/api/books/{book['id']}", headers=AUTH, json={"shelf": "read", "finished_at": "2026-10-14"})
    assert r.status_code == 200
    assert r.json()["shelf"] == "read" and r.json()["title"] == "Neuromancer"

    assert client.delete(f"/api/books/{book['id']}", headers=AUTH).status_code == 204
    assert client.get(f"/api/books/{book['id']}").status_code == 404


def test_notes_and_quotes_crud_with_token(client: TestClient, book_id: int) -> None:
    note = client.post(f"/api/books/{book_id}/notes", headers=AUTH, json={"body": "**bold**", "page": 10}).json()
    assert client.patch(f"/api/notes/{note['id']}", headers=AUTH, json={"chapter": "2"}).json()["chapter"] == "2"
    assert [n["id"] for n in client.get(f"/api/books/{book_id}/notes").json()] == [note["id"]]
    assert client.delete(f"/api/notes/{note['id']}", headers=AUTH).status_code == 204
    assert client.get(f"/api/notes/{note['id']}").status_code == 404

    quote = client.post(f"/api/books/{book_id}/quotes", headers=AUTH, json={"text": "Fear is the mind-killer."}).json()
    assert client.patch(f"/api/quotes/{quote['id']}", headers=AUTH, json={"page": 8}).json()["page"] == 8
    assert client.delete(f"/api/quotes/{quote['id']}", headers=AUTH).status_code == 204


@pytest.mark.parametrize("body", [{"title": ""}, {"title": "x", "rating": 6}, {"title": "x", "shelf": "lost"},
                                  {"title": "x", "bogus": 1}])
def test_invalid_book_payloads_rejected(client: TestClient, body: dict[str, object]) -> None:
    assert client.post("/api/books", headers=AUTH, json=body).status_code == 422


def test_note_on_missing_book_is_404(client: TestClient) -> None:
    assert client.post("/api/books/999/notes", headers=AUTH, json={"body": "x"}).status_code == 404
