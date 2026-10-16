from datetime import date, datetime, timezone
from enum import StrEnum

from sqlalchemy import JSON, CheckConstraint, Column, ForeignKey, Integer
from sqlmodel import Field, SQLModel

from app.types import UTCDateTime


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Shelf(StrEnum):
    to_read = "to_read"
    reading = "reading"
    read = "read"
    dnf = "dnf"


class Book(SQLModel, table=True):
    __tablename__ = "books"
    __table_args__ = (CheckConstraint("rating IS NULL OR (rating BETWEEN 1 AND 5)", name="ck_books_rating"),)

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    open_library_id: str | None = Field(default=None, index=True)
    page_count: int | None = Field(default=None, ge=1)
    shelf: Shelf = Field(default=Shelf.to_read, index=True)
    rating: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    started_at: date | None = None
    finished_at: date | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)
    updated_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)


class Note(SQLModel, table=True):
    __tablename__ = "notes"

    id: int | None = Field(default=None, primary_key=True)
    book_id: int = Field(sa_column=Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True))
    body: str
    page: int | None = None
    chapter: str | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)
    updated_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)


class Quote(SQLModel, table=True):
    __tablename__ = "quotes"

    id: int | None = Field(default=None, primary_key=True)
    book_id: int = Field(sa_column=Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True))
    text: str
    page: int | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)
