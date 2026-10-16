from collections.abc import Iterator
from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, SQLModel, select

from app.auth import OwnerOnly
from app.models import Book, Note, Quote, Shelf, utcnow
from app.schemas import (
    check_dates,
    BookCreate, BookRead, BookUpdate, NoteCreate, NoteRead, NoteUpdate, QuoteCreate, QuoteRead, QuoteUpdate,
)

router = APIRouter(prefix="/api")
M = TypeVar("M", bound=SQLModel)


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


DB = Annotated[Session, Depends(get_session)]


def _get_or_404(db: Session, model: type[M], obj_id: int) -> M:
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__.lower()} {obj_id} not found")
    return obj


def _save(db: Session, obj: M) -> M:
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# Books
@router.get("/books", response_model=list[BookRead])
def list_books(db: DB, shelf: Shelf | None = None) -> list[Book]:
    query = select(Book).order_by(Book.id)
    if shelf is not None:
        query = query.where(Book.shelf == shelf)
    return list(db.exec(query).all())


@router.get("/books/{book_id}", response_model=BookRead)
def get_book(book_id: int, db: DB) -> Book:
    return _get_or_404(db, Book, book_id)


@router.post("/books", response_model=BookRead, status_code=201, dependencies=[OwnerOnly])
def create_book(payload: BookCreate, db: DB) -> Book:
    return _save(db, Book(**payload.model_dump()))


@router.patch("/books/{book_id}", response_model=BookRead, dependencies=[OwnerOnly])
def update_book(book_id: int, payload: BookUpdate, db: DB) -> Book:
    book = _get_or_404(db, Book, book_id)
    changes = payload.model_dump(exclude_unset=True)
    try:
        check_dates(changes.get("started_at", book.started_at), changes.get("finished_at", book.finished_at))
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    book.sqlmodel_update(changes)
    book.updated_at = utcnow()
    return _save(db, book)


@router.delete("/books/{book_id}", status_code=204, dependencies=[OwnerOnly])
def delete_book(book_id: int, db: DB) -> Response:
    db.delete(_get_or_404(db, Book, book_id))
    db.commit()
    return Response(status_code=204)


# Notes
@router.get("/books/{book_id}/notes", response_model=list[NoteRead])
def list_notes(book_id: int, db: DB) -> list[Note]:
    _get_or_404(db, Book, book_id)
    return list(db.exec(select(Note).where(Note.book_id == book_id).order_by(Note.id)).all())


@router.post("/books/{book_id}/notes", response_model=NoteRead, status_code=201, dependencies=[OwnerOnly])
def create_note(book_id: int, payload: NoteCreate, db: DB) -> Note:
    _get_or_404(db, Book, book_id)
    return _save(db, Note(book_id=book_id, **payload.model_dump()))


@router.get("/notes/{note_id}", response_model=NoteRead)
def get_note(note_id: int, db: DB) -> Note:
    return _get_or_404(db, Note, note_id)


@router.patch("/notes/{note_id}", response_model=NoteRead, dependencies=[OwnerOnly])
def update_note(note_id: int, payload: NoteUpdate, db: DB) -> Note:
    note = _get_or_404(db, Note, note_id)
    note.sqlmodel_update(payload.model_dump(exclude_unset=True))
    note.updated_at = utcnow()
    return _save(db, note)


@router.delete("/notes/{note_id}", status_code=204, dependencies=[OwnerOnly])
def delete_note(note_id: int, db: DB) -> Response:
    db.delete(_get_or_404(db, Note, note_id))
    db.commit()
    return Response(status_code=204)


# Quotes
@router.get("/books/{book_id}/quotes", response_model=list[QuoteRead])
def list_quotes(book_id: int, db: DB) -> list[Quote]:
    _get_or_404(db, Book, book_id)
    return list(db.exec(select(Quote).where(Quote.book_id == book_id).order_by(Quote.id)).all())


@router.post("/books/{book_id}/quotes", response_model=QuoteRead, status_code=201, dependencies=[OwnerOnly])
def create_quote(book_id: int, payload: QuoteCreate, db: DB) -> Quote:
    _get_or_404(db, Book, book_id)
    return _save(db, Quote(book_id=book_id, **payload.model_dump()))


@router.get("/quotes/{quote_id}", response_model=QuoteRead)
def get_quote(quote_id: int, db: DB) -> Quote:
    return _get_or_404(db, Quote, quote_id)


@router.patch("/quotes/{quote_id}", response_model=QuoteRead, dependencies=[OwnerOnly])
def update_quote(quote_id: int, payload: QuoteUpdate, db: DB) -> Quote:
    quote = _get_or_404(db, Quote, quote_id)
    quote.sqlmodel_update(payload.model_dump(exclude_unset=True))
    return _save(db, quote)


@router.delete("/quotes/{quote_id}", status_code=204, dependencies=[OwnerOnly])
def delete_quote(quote_id: int, db: DB) -> Response:
    db.delete(_get_or_404(db, Quote, quote_id))
    db.commit()
    return Response(status_code=204)
