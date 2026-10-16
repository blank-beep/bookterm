from datetime import date
from typing import Annotated, Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import Shelf
from app.types import UTCDatetimeJSON

MAX_TITLE = 500
MAX_AUTHORS = 20
MAX_AUTHOR = 200
MAX_TAGS = 30
MAX_TAG = 50
MAX_NOTE_BODY = 50_000
MAX_QUOTE_TEXT = 5_000
MAX_CHAPTER = 200

Title = Annotated[str, StringConstraints(min_length=1, max_length=MAX_TITLE)]
Author = Annotated[str, StringConstraints(min_length=1, max_length=MAX_AUTHOR)]
Tag = Annotated[str, StringConstraints(min_length=1, max_length=MAX_TAG)]
Authors = Annotated[list[Author], Field(max_length=MAX_AUTHORS)]
Tags = Annotated[list[Tag], Field(max_length=MAX_TAGS)]
NoteBody = Annotated[str, StringConstraints(min_length=1, max_length=MAX_NOTE_BODY)]
QuoteText = Annotated[str, StringConstraints(min_length=1, max_length=MAX_QUOTE_TEXT)]
Chapter = Annotated[str, StringConstraints(max_length=MAX_CHAPTER)]
PositiveInt = Annotated[int, Field(ge=1)]
Rating = Annotated[int, Field(ge=1, le=5)]


def check_dates(started_at: date | None, finished_at: date | None) -> None:
    if started_at is not None and finished_at is not None and finished_at < started_at:
        raise ValueError("finished_at must be on or after started_at")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Update(_Strict):
    """PATCH body: fields may be omitted, but fields listed in NON_NULLABLE may not be sent as null."""

    NON_NULLABLE: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="before")
    @classmethod
    def _reject_explicit_null(cls, data: Any) -> Any:
        if isinstance(data, dict):
            nulls = sorted(k for k in cls.NON_NULLABLE if k in data and data[k] is None)
            if nulls:
                raise ValueError(f"fields cannot be null: {', '.join(nulls)}")
        return data


class BookCreate(_Strict):
    title: Title
    authors: Authors = []
    open_library_id: Annotated[str, StringConstraints(max_length=50)] | None = None
    page_count: PositiveInt | None = None
    shelf: Shelf = Shelf.to_read
    rating: Rating | None = None
    tags: Tags = []
    started_at: date | None = None
    finished_at: date | None = None

    @model_validator(mode="after")
    def _dates(self) -> Self:
        check_dates(self.started_at, self.finished_at)
        return self


class BookUpdate(_Update):
    NON_NULLABLE: ClassVar[frozenset[str]] = frozenset({"title", "authors", "shelf", "tags"})

    title: Title | None = None
    authors: Authors | None = None
    open_library_id: Annotated[str, StringConstraints(max_length=50)] | None = None
    page_count: PositiveInt | None = None
    shelf: Shelf | None = None
    rating: Rating | None = None
    tags: Tags | None = None
    started_at: date | None = None
    finished_at: date | None = None


class BookRead(BookCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: UTCDatetimeJSON
    updated_at: UTCDatetimeJSON


class NoteCreate(_Strict):
    body: NoteBody
    page: PositiveInt | None = None
    chapter: Chapter | None = None


class NoteUpdate(_Update):
    NON_NULLABLE: ClassVar[frozenset[str]] = frozenset({"body"})

    body: NoteBody | None = None
    page: PositiveInt | None = None
    chapter: Chapter | None = None


class NoteRead(NoteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    created_at: UTCDatetimeJSON
    updated_at: UTCDatetimeJSON


class QuoteCreate(_Strict):
    text: QuoteText
    page: PositiveInt | None = None


class QuoteUpdate(_Update):
    NON_NULLABLE: ClassVar[frozenset[str]] = frozenset({"text"})

    text: QuoteText | None = None
    page: PositiveInt | None = None


class QuoteRead(QuoteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    created_at: UTCDatetimeJSON
