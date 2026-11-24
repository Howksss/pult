from fastapi import APIRouter, Response
from sqlalchemy import select

from app.api.access import CurrentUser, SessionDep
from app.api.paging import PageDep
from app.api.problems import not_found
from app.api.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from app.models import ApiKey
from app.services.api_keys import issue_key

router = APIRouter(prefix="/api/v1/api-keys", tags=["auth"])


def key_out(row: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=row.id,
        name=row.name,
        prefix=row.prefix,
        created_at=row.created_at,
        expires_at=row.expires_at,
        last_used_at=row.last_used_at,
    )


@router.get("", response_model=list[ApiKeyOut])
def list_keys(session: SessionDep, user: CurrentUser, page: PageDep) -> list[ApiKeyOut]:
    query = select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.id)
    return [key_out(row) for row in session.scalars(page.query(session, query))]


@router.post("", response_model=ApiKeyCreated, status_code=201)
def create_key(payload: ApiKeyCreate, session: SessionDep, user: CurrentUser) -> ApiKeyCreated:
    row, key = issue_key(session, user, payload.name.strip(), payload.expires_in_days)
    return ApiKeyCreated(**key_out(row).model_dump(), key=key)


@router.delete("/{key_id}", status_code=204)
def revoke_key(key_id: int, session: SessionDep, user: CurrentUser) -> Response:
    row = session.get(ApiKey, key_id)
    if row is None or row.user_id != user.id:
        raise not_found("api key", key_id)
    session.delete(row)
    session.commit()
    return Response(status_code=204)
