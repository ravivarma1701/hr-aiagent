from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import error_response, success_response
from app.db.session import get_db
from app.models.employee import Employee
from app.models.enums import Role
from app.models.poll import Poll
from app.models.poll_response import PollResponse
from app.schemas.poll import PollCreate, PollVote
from app.services.auth import get_current_user

router = APIRouter()


@router.get("")
async def list_polls(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    total = (await db.execute(select(func.count(Poll.id)))).scalar_one()
    polls = (await db.execute(select(Poll).order_by(desc(Poll.created_at), desc(Poll.id)).limit(limit).offset(offset))).scalars().all()
    if not polls:
        return success_response({"items": [], "meta": {"total": total, "limit": limit, "offset": offset}})

    poll_ids = [poll.id for poll in polls]
    my_votes = (
        await db.execute(select(PollResponse).where(PollResponse.employee_id == current_user.id, PollResponse.poll_id.in_(poll_ids)))
    ).scalars().all()
    my_votes_by_poll = {row.poll_id: row.option_index for row in my_votes}

    return success_response(
        {
            "items": [
                {
                    "id": poll.id,
                    "question": poll.question,
                    "options": poll.options,
                    "created_by": poll.created_by,
                    "created_at": poll.created_at,
                    "my_vote": my_votes_by_poll.get(poll.id),
                }
                for poll in polls
            ],
            "meta": {"total": total, "limit": limit, "offset": offset},
        }
    )


@router.post("")
async def create_poll(
    payload: PollCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {Role.ADMIN, Role.MANAGER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_response("FORBIDDEN", "Only manager/admin can create polls"),
        )

    cleaned_options = [option.strip() for option in payload.options if option.strip()]
    if len(cleaned_options) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_POLL_OPTIONS", "At least 2 options are required"),
        )

    poll = Poll(question=payload.question.strip(), options=cleaned_options, created_by=current_user.id)
    db.add(poll)
    await db.commit()
    await db.refresh(poll)
    return success_response({"id": poll.id, "question": poll.question, "options": poll.options, "created_by": poll.created_by, "created_at": poll.created_at})


@router.post("/{poll_id}/vote")
async def vote_poll(
    poll_id: int,
    payload: PollVote,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    poll = (await db.execute(select(Poll).where(Poll.id == poll_id))).scalar_one_or_none()
    if poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_response("POLL_NOT_FOUND", "Poll not found"))

    if payload.option_index >= len(poll.options):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_response("INVALID_OPTION_INDEX", "option_index out of range"))

    existing = (
        await db.execute(select(PollResponse).where(PollResponse.poll_id == poll_id, PollResponse.employee_id == current_user.id))
    ).scalar_one_or_none()
    if existing:
        existing.option_index = payload.option_index
    else:
        db.add(PollResponse(poll_id=poll_id, employee_id=current_user.id, option_index=payload.option_index))
    await db.commit()
    return success_response({"poll_id": poll_id, "employee_id": current_user.id, "option_index": payload.option_index})


@router.get("/{poll_id}/results")
async def poll_results(
    poll_id: int,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    poll = (await db.execute(select(Poll).where(Poll.id == poll_id))).scalar_one_or_none()
    if poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_response("POLL_NOT_FOUND", "Poll not found"))

    rows = (
        await db.execute(
            select(PollResponse.option_index, func.count(PollResponse.id))
            .where(PollResponse.poll_id == poll_id)
            .group_by(PollResponse.option_index)
        )
    ).all()
    counts = {option_idx: count for option_idx, count in rows}
    total_votes = sum(counts.values())
    items = []
    for idx, option in enumerate(poll.options):
        votes = counts.get(idx, 0)
        percentage = round((votes / total_votes) * 100, 2) if total_votes else 0.0
        items.append({"option_index": idx, "option": option, "votes": votes, "percentage": percentage})

    return success_response({"poll_id": poll_id, "question": poll.question, "total_votes": total_votes, "items": items})
