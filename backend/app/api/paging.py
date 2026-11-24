from collections.abc import Sequence
from typing import Annotated, Any, TypeVar

from fastapi import Depends, Query, Response
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")
TOTAL_HEADER = "X-Total-Count"


class Page:
    def __init__(
        self,
        response: Response,
        limit: Annotated[int, Query(ge=1, le=500, description="Сколько элементов вернуть")] = 100,
        offset: Annotated[int, Query(ge=0, description="Сколько элементов пропустить")] = 0,
    ) -> None:
        self.response = response
        self.limit = limit
        self.offset = offset

    def query(self, session: Session, query: Select[Any]) -> Select[Any]:
        total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        self.response.headers[TOTAL_HEADER] = str(total or 0)
        return query.limit(self.limit).offset(self.offset)

    def items(self, items: Sequence[T]) -> list[T]:
        self.response.headers[TOTAL_HEADER] = str(len(items))
        return list(items[self.offset : self.offset + self.limit])


PageDep = Annotated[Page, Depends()]
