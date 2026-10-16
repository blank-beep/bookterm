from datetime import date

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import Book, Note, Quote, Shelf


def test_book_crud_roundtrip(engine: Engine) -> None:
    with Session(engine) as s:
        book = Book(
            title="Dune",
            authors=["Frank Herbert"],
            open_library_id="OL893415W",
            page_count=412,
            shelf=Shelf.reading,
            rating=5,
            tags=["sci-fi", "classic"],
            started_at=date(2026, 10, 1),
        )
        s.add(book)
        s.commit()
        book_id = book.id

    with Session(engine) as s:
        got = s.get(Book, book_id)
        assert got is not None
        assert got.authors == ["Frank Herbert"]
        assert got.tags == ["sci-fi", "classic"]
        assert got.shelf is Shelf.reading
        assert got.started_at == date(2026, 10, 1)
        got.shelf = Shelf.read
        got.finished_at = date(2026, 10, 14)
        s.add(got)
        s.commit()

    with Session(engine) as s:
        got = s.get(Book, book_id)
        assert got is not None and got.shelf is Shelf.read
        s.delete(got)
        s.commit()
        assert s.get(Book, book_id) is None


def test_notes_and_quotes_attach_to_book_and_cascade(engine: Engine) -> None:
    with Session(engine) as s:
        book = Book(title="Neuromancer", authors=["William Gibson"])
        s.add(book)
        s.commit()
        assert book.id is not None
        s.add(Note(book_id=book.id, body="# Ch1\nThe sky above the port...", page=1, chapter="1"))
        s.add(Quote(book_id=book.id, text="The sky above the port was the color of television.", page=3))
        s.commit()
        assert len(s.exec(select(Note).where(Note.book_id == book.id)).all()) == 1
        assert len(s.exec(select(Quote).where(Quote.book_id == book.id)).all()) == 1
        s.delete(book)
        s.commit()
        assert s.exec(select(Note)).all() == []
        assert s.exec(select(Quote)).all() == []


def test_rating_out_of_range_rejected_by_db(engine: Engine) -> None:
    with Session(engine) as s:
        s.add(Book(title="Bad", rating=6))  # table models skip pydantic validation; the DB constraint must catch it
        with pytest.raises(IntegrityError):
            s.commit()


def test_note_for_missing_book_rejected(engine: Engine) -> None:
    with Session(engine) as s:
        s.add(Note(book_id=9999, body="orphan"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_datetimes_roundtrip_as_aware_utc(engine: Engine) -> None:
    from datetime import datetime, timedelta, timezone

    from app.types import iso_z

    pacific = timezone(timedelta(hours=-7))
    written = datetime(2026, 10, 15, 21, 42, 7, 123456, tzinfo=pacific)
    with Session(engine) as s:
        book = Book(title="Clock", created_at=written, updated_at=written)
        s.add(book)
        s.commit()
        book_id = book.id

    with Session(engine) as s:
        got = s.get(Book, book_id)
        assert got is not None
        assert got.created_at.tzinfo == timezone.utc
        assert got.created_at == written
        assert got.created_at.utcoffset() == timedelta(0)
        assert iso_z(got.created_at) == "2026-10-16T04:42:07.123456Z"


def test_naive_datetime_rejected(engine: Engine) -> None:
    from datetime import datetime

    with Session(engine) as s:
        s.add(Book(title="Naive", created_at=datetime(2026, 1, 1)))
        with pytest.raises(Exception, match="naive datetime"):
            s.commit()
