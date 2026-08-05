from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import error_response, success_response
from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.employee import Employee
from app.models.enums import Role
from app.schemas.announcement import AnnouncementCreate
from app.services.auth import get_current_user

router = APIRouter()


@router.get("")
async def list_announcements(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    count_q = select(func.count(Announcement.id))
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        select(Announcement, Employee.name)
        .join(Employee, Employee.id == Announcement.author_id)
        .order_by(desc(Announcement.created_at), desc(Announcement.id))
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()

    return success_response(
        {
            "items": [
                {
                    "id": announcement.id,
                    "title": announcement.title,
                    "body": announcement.body,
                    "author_id": announcement.author_id,
                    "author_name": author_name,
                    "created_at": announcement.created_at,
                }
                for announcement, author_name in rows
            ],
            "meta": {"total": total, "limit": limit, "offset": offset},
        }
    )


@router.post("")
async def create_announcement(
    payload: AnnouncementCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {Role.ADMIN, Role.MANAGER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_response("FORBIDDEN", "Only manager/admin can create announcements"),
        )

    clean_title = payload.title.strip()
    clean_body = payload.body.strip()
    if len(clean_title) < 3 or len(clean_body) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_ANNOUNCEMENT", "title/body cannot be empty"),
        )

    announcement = Announcement(
        title=clean_title,
        body=clean_body,
        author_id=current_user.id,
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)

    return success_response(
        {
            "id": announcement.id,
            "title": announcement.title,
            "body": announcement.body,
            "author_id": announcement.author_id,
            "author_name": current_user.name,
            "created_at": announcement.created_at,
        }
    )
