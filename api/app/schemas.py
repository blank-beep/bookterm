from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Shelf


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BookCreate(_Strict):
    title: str = Field(min_length=1)
    authors: list[str] = []
    open_library_id: str | None = None
    page_count: int | None = Field(default=None, ge=1)
    shelf: Shelf = Shelf.to_read
    rating: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] = []
    started_at: date | None = None
    finished_at: date | None = None


class BookUpdate(_Strict):
    title: str | None = Field(default=None, min_length=1)
    authors: list[str] | None = None
    open_library_id: str | None = None
    page_count: int | None = Field(default=None, ge=1)
    shelf: Shelf | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] | None = None
    started_at: date | None = None
    finished_at: date | None = None


class BookRead(BookCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class NoteCreate(_Strict):
    body: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    chapter: str | None = None


class NoteUpdate(_Strict):
    body: str | None = Field(default=None, min_length=1)
    page: int | None = Field(default=None, ge=1)
    chapter: str | None = None


class NoteRead(NoteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    created_at: datetime
    updated_at: datetime


class QuoteCreate(_Strict):
    text: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)


class QuoteUpdate(_Strict):
    text: str | None = Field(default=None, min_length=1)
    page: int | None = Field(default=None, ge=1)


class QuoteRead(QuoteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    created_at: datetime
