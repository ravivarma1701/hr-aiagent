from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db
from app.models.employee import Employee
from app.models.payroll_record import PayrollRecord
from app.services.auth import get_current_user

router = APIRouter()


def _default_pan(employee_id: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    i = employee_id % 26
    return (
        f"{letters[i]}"
        f"{letters[(i + 3) % 26]}"
        f"{letters[(i + 7) % 26]}"
        f"{letters[(i + 11) % 26]}"
        f"{letters[(i + 15) % 26]}"
        f"{1000 + (employee_id % 9000)}"
        f"{letters[(i + 19) % 26]}"
    )


def _default_bank_account_number(employee_id: int) -> str:
    return f"{employee_id:04d}{(1000000000 + employee_id):010d}"


def _default_ifsc(employee_id: int) -> str:
    return f"MOCK0{employee_id:06d}"[:11]


def _fallback_dob(current_user: Employee) -> date | None:
    if current_user.pan_dob is not None:
        return current_user.pan_dob
    if current_user.date_of_birth is not None:
        return current_user.date_of_birth
    return None


@router.get("/payroll/me")
async def my_payroll(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PayrollRecord)
        .where(PayrollRecord.employee_id == current_user.id)
        .order_by(desc(PayrollRecord.month), desc(PayrollRecord.id))
        .limit(12)
    )
    rows = result.scalars().all()
    return success_response(
        [
            {
                "id": row.id,
                "month": row.month,
                "gross": row.gross,
                "deductions": row.deductions,
                "net": row.net,
                "pan": row.pan,
                "pf_uan": row.pf_uan,
                "esi_no": row.esi_no,
            }
            for row in rows
        ]
    )


@router.get("/statutory/me")
async def my_statutory(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    latest = (
        await db.execute(
            select(PayrollRecord)
            .where(PayrollRecord.employee_id == current_user.id)
            .order_by(desc(PayrollRecord.month), desc(PayrollRecord.id))
            .limit(1)
        )
    ).scalar_one_or_none()

    return success_response(
        {
            "employee_id": current_user.id,
            "pan": latest.pan if latest else (current_user.pan_number or _default_pan(current_user.id)),
            "pf_uan": latest.pf_uan if latest else f"{100200300000 + current_user.id}",
            "esi_no": latest.esi_no if latest else f"ESI{100000 + current_user.id}",
        }
    )


@router.get("/profile/me")
async def my_finance_profile(
    current_user: Employee = Depends(get_current_user),
):
    return success_response(
        {
            "employee_id": current_user.id,
            "current_salary_usd": float(current_user.current_salary_usd) if current_user.current_salary_usd is not None else 60000.0,
            "bank_name": current_user.bank_name or "DBS Bank",
            "bank_account_number": current_user.bank_account_number or _default_bank_account_number(current_user.id),
            "bank_account_name": current_user.bank_account_name or current_user.name,
            "bank_branch": current_user.bank_branch or "City Center",
            "bank_ifsc": current_user.bank_ifsc or _default_ifsc(current_user.id),
            "pan_number": current_user.pan_number or _default_pan(current_user.id),
            "pan_name": current_user.pan_name or current_user.name,
            "pan_dob": _fallback_dob(current_user),
        }
    )
