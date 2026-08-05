from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import error_response, success_response
from app.db.session import get_db
from app.models.employee import Employee
from app.models.enums import HalfDayPeriod, LeaveRequestStatus, LeaveType, Role
from app.models.leave_balance import LeaveBalance
from app.models.leave_request import LeaveRequest
from app.schemas.leave import LeaveRequestCreate
from app.services.auth import get_current_user

router = APIRouter()


DEFAULT_LEAVE_TOTALS: dict[LeaveType, float] = {
    LeaveType.CASUAL: 12.0,
    LeaveType.SICK: 10.0,
    LeaveType.EARNED: 15.0,
}


def _days_between(start_date: date, end_date: date) -> int:
    return (end_date - start_date).days + 1


def _leave_units(start_date: date, end_date: date, is_half_day: bool) -> float:
    if is_half_day:
        return 0.5
    return float(_days_between(start_date, end_date))


async def _get_or_create_leave_balance(
    db: AsyncSession,
    employee_id: int,
    leave_type: LeaveType,
) -> LeaveBalance:
    rows = (
        await db.execute(
            select(LeaveBalance).where(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_type == leave_type,
            ).order_by(LeaveBalance.id.asc())
        )
    ).scalars().all()
    if rows:
        # Self-heal historical duplicates by retaining one row and removing extras.
        balance = rows[0]
        if len(rows) > 1:
            max_total = max(float(row.total or 0.0) for row in rows)
            max_used = max(float(row.used or 0.0) for row in rows)
            balance.total = max_total
            balance.used = max_used
            balance.remaining = max(0.0, max_total - max_used)
            for duplicate in rows[1:]:
                await db.delete(duplicate)
            await db.flush()
        return balance

    total = DEFAULT_LEAVE_TOTALS[leave_type]
    balance = LeaveBalance(
        employee_id=employee_id,
        leave_type=leave_type,
        total=total,
        used=0.0,
        remaining=total,
    )
    db.add(balance)
    await db.flush()
    return balance


@router.get("/balances/me")
async def my_leave_balances(current_user: Employee = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    balances: list[LeaveBalance] = []
    for leave_type in (LeaveType.CASUAL, LeaveType.SICK, LeaveType.EARNED):
        balances.append(await _get_or_create_leave_balance(db, current_user.id, leave_type))
    await db.commit()
    return success_response(
        [
            {
                "id": row.id,
                "leave_type": row.leave_type.value,
                "total": row.total,
                "used": row.used,
                "remaining": row.remaining,
            }
            for row in balances
        ]
    )


@router.get("/requests/me")
async def my_leave_requests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count_q = select(func.count(LeaveRequest.id)).where(LeaveRequest.employee_id == current_user.id)
    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        select(LeaveRequest)
        .where(LeaveRequest.employee_id == current_user.id)
        .order_by(LeaveRequest.id.desc())
        .limit(limit)
        .offset(offset)
    )
    requests = result.scalars().all()
    return success_response(
        {
            "items": [
                {
                    "id": req.id,
                    "employee_id": req.employee_id,
                    "leave_type": req.leave_type.value,
                    "start_date": req.start_date,
                    "end_date": req.end_date,
                    "is_half_day": req.is_half_day,
                    "half_day_period": req.half_day_period.value if req.half_day_period else None,
                    "reason": req.reason,
                    "status": req.status.value,
                    "approver_id": req.approver_id,
                }
                for req in requests
            ],
            "meta": {"total": total, "limit": limit, "offset": offset},
        }
    )


@router.post("/requests")
async def submit_leave_request(
    payload: LeaveRequestCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_DATE_RANGE", "end_date must be on or after start_date"),
        )

    leave_type = payload.leave_type.upper()
    if leave_type not in {LeaveType.CASUAL.value, LeaveType.SICK.value, LeaveType.EARNED.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_LEAVE_TYPE", "leave_type must be CASUAL, SICK, or EARNED"),
        )

    if payload.is_half_day and payload.start_date != payload.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_HALF_DAY_RANGE", "Half-day leave must have same start_date and end_date"),
        )

    normalized_half_day_period = payload.half_day_period.strip().upper() if payload.half_day_period else None
    if payload.is_half_day:
        if normalized_half_day_period not in {HalfDayPeriod.FIRST_HALF.value, HalfDayPeriod.SECOND_HALF.value}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response(
                    "INVALID_HALF_DAY_PERIOD",
                    "half_day_period must be FIRST_HALF or SECOND_HALF for half-day leave",
                ),
            )
    elif normalized_half_day_period is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_HALF_DAY_PERIOD", "half_day_period is only allowed when is_half_day is true"),
        )

    overlap_q = select(LeaveRequest).where(
        LeaveRequest.employee_id == current_user.id,
        LeaveRequest.status.in_([LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED]),
        and_(LeaveRequest.start_date <= payload.end_date, LeaveRequest.end_date >= payload.start_date),
    )
    overlap = (await db.execute(overlap_q)).scalar_one_or_none()
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response("LEAVE_OVERLAP", "A leave request already exists for overlapping dates"),
        )

    leave = LeaveRequest(
        employee_id=current_user.id,
        leave_type=LeaveType(leave_type),
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        is_half_day=payload.is_half_day,
        half_day_period=(HalfDayPeriod(normalized_half_day_period) if normalized_half_day_period else None),
        status=LeaveRequestStatus.PENDING,
    )

    # Admin self-service leave is auto-approved and balance is reduced immediately.
    if current_user.role == Role.ADMIN:
        days = _leave_units(payload.start_date, payload.end_date, payload.is_half_day)
        balance = await _get_or_create_leave_balance(db, current_user.id, LeaveType(leave_type))
        if balance.remaining < days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response("LEAVE_INSUFFICIENT_BALANCE", "Not enough leave balance"),
            )

        leave.status = LeaveRequestStatus.APPROVED
        leave.approver_id = current_user.id
        balance.used += days
        balance.remaining -= days

    db.add(leave)
    await db.commit()
    await db.refresh(leave)

    return success_response(
        {
            "id": leave.id,
            "employee_id": leave.employee_id,
            "leave_type": leave.leave_type.value,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "is_half_day": leave.is_half_day,
            "half_day_period": leave.half_day_period.value if leave.half_day_period else None,
            "reason": leave.reason,
            "status": leave.status.value,
            "approver_id": leave.approver_id,
        }
    )


@router.get("/requests/pending")
async def pending_leave_requests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {Role.ADMIN, Role.MANAGER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_response("FORBIDDEN", "Only manager/admin can view pending leave approvals"),
        )

    count_q = select(func.count(LeaveRequest.id)).where(LeaveRequest.status == LeaveRequestStatus.PENDING)
    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        select(LeaveRequest).where(LeaveRequest.status == LeaveRequestStatus.PENDING).order_by(LeaveRequest.id.desc()).limit(limit).offset(offset)
    )
    requests = result.scalars().all()

    return success_response(
        {
            "items": [
                {
                    "id": req.id,
                    "employee_id": req.employee_id,
                    "leave_type": req.leave_type.value,
                    "start_date": req.start_date,
                    "end_date": req.end_date,
                    "is_half_day": req.is_half_day,
                    "half_day_period": req.half_day_period.value if req.half_day_period else None,
                    "reason": req.reason,
                    "status": req.status.value,
                    "approver_id": req.approver_id,
                }
                for req in requests
            ],
            "meta": {"total": total, "limit": limit, "offset": offset},
        }
    )


@router.post("/requests/{request_id}/approve")
async def approve_leave_request(
    request_id: int,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {Role.ADMIN, Role.MANAGER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_response("FORBIDDEN", "Only manager/admin can approve leave"),
        )

    result = await db.execute(select(LeaveRequest).where(LeaveRequest.id == request_id))
    leave = result.scalar_one_or_none()
    if leave is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_response("LEAVE_NOT_FOUND", "Leave request not found"))
    if leave.status != LeaveRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("LEAVE_NOT_PENDING", "Only pending leave request can be approved"),
        )

    days = _leave_units(leave.start_date, leave.end_date, leave.is_half_day)
    balance = await _get_or_create_leave_balance(db, leave.employee_id, leave.leave_type)
    if balance.remaining < days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("LEAVE_INSUFFICIENT_BALANCE", "Not enough leave balance to approve this request"),
        )

    leave.status = LeaveRequestStatus.APPROVED
    leave.approver_id = current_user.id
    balance.used += days
    balance.remaining -= days

    await db.commit()
    await db.refresh(leave)

    return success_response(
        {
            "id": leave.id,
            "employee_id": leave.employee_id,
            "leave_type": leave.leave_type.value,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "is_half_day": leave.is_half_day,
            "half_day_period": leave.half_day_period.value if leave.half_day_period else None,
            "reason": leave.reason,
            "status": leave.status.value,
            "approver_id": leave.approver_id,
        }
    )


@router.post("/requests/{request_id}/reject")
async def reject_leave_request(
    request_id: int,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {Role.ADMIN, Role.MANAGER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_response("FORBIDDEN", "Only manager/admin can reject leave"),
        )

    result = await db.execute(select(LeaveRequest).where(LeaveRequest.id == request_id))
    leave = result.scalar_one_or_none()
    if leave is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_response("LEAVE_NOT_FOUND", "Leave request not found"))
    if leave.status != LeaveRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("LEAVE_NOT_PENDING", "Only pending leave request can be rejected"),
        )

    leave.status = LeaveRequestStatus.REJECTED
    leave.approver_id = current_user.id
    await db.commit()
    await db.refresh(leave)

    return success_response(
        {
            "id": leave.id,
            "employee_id": leave.employee_id,
            "leave_type": leave.leave_type.value,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "is_half_day": leave.is_half_day,
            "half_day_period": leave.half_day_period.value if leave.half_day_period else None,
            "reason": leave.reason,
            "status": leave.status.value,
            "approver_id": leave.approver_id,
        }
    )
