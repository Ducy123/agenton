from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def paginate(query_count: int, page: int, page_size: int) -> tuple[int, int]:
    """Return (limit, offset) clamped to sane bounds."""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size
    return page_size, offset
