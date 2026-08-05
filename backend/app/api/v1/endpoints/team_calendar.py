from calendar import monthrange
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db
from app.models.attendance_log import AttendanceLog
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import LeaveRequestStatus, Role
from app.models.holiday import Holiday
from app.models.leave_request import LeaveRequest
from app.services.auth import get_current_user

router = APIRouter()


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _birthday_occurrence(dob: date, year: int) -> date:
    if dob.month == 2 and dob.day == 29:
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        return date(year, 2, 29 if is_leap else 28)
    return date(year, dob.month, dob.day)


@router.get("/team")
async def get_team_calendar(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start_date, end_date = _month_bounds(year, month)

    if current_user.role in {Role.ADMIN, Role.MANAGER}:
        employees_q = select(Employee).order_by(Employee.name.asc())
    else:
        if current_user.department_id is None:
            employees_q = select(Employee).where(Employee.id == current_user.id)
        else:
            employees_q = select(Employee).where(Employee.department_id == current_user.department_id).order_by(Employee.name.asc())

    employees = (await db.execute(employees_q)).scalars().all()
    employee_ids = [employee.id for employee in employees]
    markers_by_employee: dict[int, dict[str, str]] = {employee_id: {} for employee_id in employee_ids}

    if employee_ids:
        leaves_result = await db.execute(
            select(LeaveRequest).where(
                LeaveRequest.employee_id.in_(employee_ids),
                LeaveRequest.status == LeaveRequestStatus.APPROVED,
                and_(LeaveRequest.start_date <= end_date, LeaveRequest.end_date >= start_date),
            )
        )
        for leave in leaves_result.scalars().all():
            day = max(leave.start_date, start_date)
            while day <= min(leave.end_date, end_date):
                markers_by_employee[leave.employee_id][day.isoformat()] = "LEAVE"
                day += timedelta(days=1)

        wfh_result = await db.execute(
            select(AttendanceLog).where(
                AttendanceLog.employee_id.in_(employee_ids),
                AttendanceLog.work_mode == "WFH",
                AttendanceLog.date >= start_date,
                AttendanceLog.date <= end_date,
            )
        )
        for attendance in wfh_result.scalars().all():
            key = attendance.date.isoformat()
            if markers_by_employee[attendance.employee_id].get(key) is None:
                markers_by_employee[attendance.employee_id][key] = "WFH"

    days = []
    cursor = start_date
    while cursor <= end_date:
        days.append({"date": cursor.isoformat(), "day": cursor.day, "weekday": cursor.strftime("%a")})
        cursor += timedelta(days=1)

    items = [
        {
            "employee_id": employee.id,
            "employee_name": employee.name,
            "employee_role": employee.role.value,
            "markers": markers_by_employee.get(employee.id, {}),
        }
        for employee in employees
    ]

    return success_response({"year": year, "month": month, "days": days, "items": items})


@router.get("/holidays")
async def get_holidays(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    _ = current_user
    holidays_result = await db.execute(
        select(Holiday).order_by(Holiday.date.asc()).limit(limit)
    )
    holidays = holidays_result.scalars().all()
    return success_response([{"name": holiday.name, "date": holiday.date.isoformat()} for holiday in holidays])


@router.get("/birthdays")
async def get_birthdays(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=500),
):
    _ = current_user
    today = date.today()

    birthdays_result = await db.execute(
        select(Employee, Department.name)
        .outerjoin(Department, Department.id == Employee.department_id)
        .where(Employee.date_of_birth.is_not(None))
    )

    upcoming = []
    for employee, department_name in birthdays_result.all():
        dob = employee.date_of_birth
        if dob is None:
            continue

        next_occurrence = _birthday_occurrence(dob, today.year)
        if next_occurrence < today:
            next_occurrence = _birthday_occurrence(dob, today.year + 1)

        upcoming.append(
            {
                "name": employee.name,
                "team": department_name or "Unassigned",
                "date": next_occurrence.isoformat(),
            }
        )

    upcoming.sort(key=lambda item: item["date"])
    return success_response(upcoming[:limit])
