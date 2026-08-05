from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.response import error_response, success_response
from app.db.session import get_db
from app.models.attendance_log import AttendanceLog
from app.models.employee import Employee
from app.models.enums import AttendanceStatus
from app.schemas.attendance import ClockInRequest
from app.services.auth import get_current_user

router = APIRouter()
CLOCK_IN_CUTOFF = datetime.strptime("09:00:00", "%H:%M:%S").time()
HALF_DAY_MIN_SECONDS = int(4.5 * 60 * 60)
APP_TZ = ZoneInfo(settings.app_timezone)


def _derive_punctuality(clock_in_time):
    return "LATE" if clock_in_time > CLOCK_IN_CUTOFF else "ON_TIME"


def _local_now() -> datetime:
    return datetime.now(APP_TZ)


def _attendance_payload(item: AttendanceLog):
    status_value = item.punctuality or item.status.value
    return {
        "id": item.id,
        "date": item.date,
        "clock_in": item.clock_in,
        "clock_out": item.clock_out,
        "status": status_value,
        "work_mode": item.work_mode,
        "punctuality": item.punctuality,
    }


@router.get("/me")
async def my_attendance_logs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = (
        await db.execute(select(func.count(AttendanceLog.id)).where(AttendanceLog.employee_id == current_user.id))
    ).scalar_one()
    result = await db.execute(
        select(AttendanceLog)
        .where(AttendanceLog.employee_id == current_user.id)
        .order_by(AttendanceLog.date.desc(), AttendanceLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()

    return success_response(
        {
            "items": [_attendance_payload(item) for item in items],
            "meta": {"total": total, "limit": limit, "offset": offset},
        }
    )


@router.get("/today")
async def today_attendance(current_user: Employee = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = _local_now().date()
    result = await db.execute(
        select(AttendanceLog).where(AttendanceLog.employee_id == current_user.id, AttendanceLog.date == today)
    )
    record = result.scalar_one_or_none()

    if record is None:
        return success_response(None)

    return success_response(_attendance_payload(record))


@router.post("/clock-in")
async def clock_in(
    payload: ClockInRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now_local = _local_now()
    today = now_local.date()
    now = now_local.time().replace(microsecond=0)
    result = await db.execute(
        select(AttendanceLog).where(AttendanceLog.employee_id == current_user.id, AttendanceLog.date == today)
    )
    existing = result.scalar_one_or_none()
    if existing and existing.clock_in is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("ATTENDANCE_ALREADY_CLOCKED_IN", "Clock-in already exists for today"),
        )

    mode = payload.mode.upper()
    if mode not in {"PRESENT", "WFH"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_ATTENDANCE_MODE", "Mode must be PRESENT or WFH"),
        )

    punctuality = _derive_punctuality(now)
    status_value = AttendanceStatus.WFH if mode == "WFH" else AttendanceStatus(punctuality)

    if existing:
        existing.clock_in = now
        existing.status = status_value
        existing.work_mode = mode
        existing.punctuality = punctuality
        record = existing
    else:
        record = AttendanceLog(
            employee_id=current_user.id,
            date=today,
            clock_in=now,
            status=status_value,
            work_mode=mode,
            punctuality=punctuality,
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)

    return success_response(_attendance_payload(record))


@router.post("/clock-out")
async def clock_out(current_user: Employee = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    now_local = _local_now()
    today = now_local.date()
    now = now_local.time().replace(microsecond=0)
    result = await db.execute(
        select(AttendanceLog).where(AttendanceLog.employee_id == current_user.id, AttendanceLog.date == today)
    )
    record = result.scalar_one_or_none()

    if record is None or record.clock_in is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("ATTENDANCE_NOT_CLOCKED_IN", "Clock in first before clocking out"),
        )

    if record.clock_out is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("ATTENDANCE_ALREADY_CLOCKED_OUT", "Clock-out already exists for today"),
        )

    record.clock_out = now
    start_seconds = record.clock_in.hour * 3600 + record.clock_in.minute * 60 + record.clock_in.second
    end_seconds = now.hour * 3600 + now.minute * 60 + now.second
    worked_seconds = max(0, end_seconds - start_seconds)
    if worked_seconds < HALF_DAY_MIN_SECONDS:
        record.punctuality = "HALF_DAY"

    await db.commit()
    await db.refresh(record)
    return success_response(_attendance_payload(record))
