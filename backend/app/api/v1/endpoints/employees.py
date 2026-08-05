import hashlib
import re
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.response import error_response, success_response
from app.core.security import hash_password
from app.db.session import get_db
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_document import EmployeeDocument
from app.models.employee_project import EmployeeProject
from app.models.enums import EmployeeStatus, LeaveType, ProjectStatus, Role
from app.models.job_history import JobHistory
from app.models.leave_balance import LeaveBalance
from app.models.payroll_record import PayrollRecord
from app.models.project import Project
from app.schemas.employee import (
    EmployeeAdminUpdate,
    EmployeeCreate,
    EmployeeJobTitleUpdate,
    EmployeeMeUpdate,
    EmployeeProjectAssign,
    ProjectCreate,
    ProjectStatusUpdate,
)
from app.services.auth import get_current_user, require_roles

router = APIRouter()
ALLOWED_PROFILE_PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".doc", ".docx"}
ALLOWED_DOCUMENT_TYPES = {"APPOINTMENT", "PAYSLIP", "TAX", "OTHER"}
PAYSLIP_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
DEFAULT_LEAVE_TOTALS: dict[LeaveType, float] = {
    LeaveType.CASUAL: 12.0,
    LeaveType.SICK: 10.0,
    LeaveType.EARNED: 15.0,
}


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


def _employee_directory_payload(e: Employee):
    return {
        "id": e.id,
        "name": e.name,
        "email": e.email,
        "department_id": e.department_id,
        "role": e.role.value,
        "status": e.status.value,
        "joining_date": e.joining_date,
    }


def _document_payload(doc: EmployeeDocument):
    return {
        "id": str(doc.id),
        "title": doc.title,
        "type": doc.document_type,
        "uploaded_by": doc.uploaded_by,
        "issued_on": (doc.created_at.date().isoformat() if doc.created_at else None),
        "original_filename": doc.original_filename,
        "mime_type": doc.mime_type,
        "size_bytes": doc.size_bytes,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


def _system_document_items(current_user: Employee) -> list[dict]:
    today = date.today()
    previous_month = today.replace(day=1) - timedelta(days=1)
    payslip_period = f"{previous_month.year}-{previous_month.month:02d}"
    items = [
        {
            "id": f"system-appointment-{current_user.id}",
            "title": "Appointment Letter",
            "type": "APPOINTMENT",
            "issued_on": current_user.joining_date.isoformat(),
            "original_filename": f"appointment_letter_{current_user.id}.txt",
            "mime_type": "text/plain",
            "size_bytes": None,
            "created_at": f"{current_user.joining_date.isoformat()}T00:00:00",
        },
        {
            "id": f"system-payslip-{current_user.id}-{payslip_period}",
            "title": f"Payslip - {payslip_period}",
            "type": "PAYSLIP",
            "issued_on": f"{payslip_period}-01",
            "original_filename": f"payslip_{current_user.id}_{payslip_period}.pdf",
            "mime_type": "application/pdf",
            "size_bytes": None,
            "created_at": f"{payslip_period}-01T00:00:00",
        },
        {
            "id": f"system-tax-{current_user.id}-{today.year}",
            "title": f"Tax Statement FY {today.year}-{str(today.year + 1)[2:]}",
            "type": "TAX",
            "issued_on": f"{today.year}-04-01",
            "original_filename": f"tax_statement_{current_user.id}_{today.year}.txt",
            "mime_type": "text/plain",
            "size_bytes": None,
            "created_at": f"{today.year}-04-01T00:00:00",
        },
    ]
    return items


def _build_system_document_file(
    current_user: Employee,
    document_id: str,
    payroll_data: dict | None = None,
) -> tuple[Path, str, str]:
    def dob_password(user: Employee) -> str:
        value = user.pan_dob or user.date_of_birth
        if value is None:
            return "01-01-90"
        return value.strftime("%d-%m-%y")

    def encrypt_pdf(raw_pdf: bytes, password: str) -> bytes:
        source = BytesIO(raw_pdf)
        reader = PdfReader(source)
        if reader.is_encrypted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF must not be encrypted before upload")
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)
        output = BytesIO()
        writer.write(output)
        return output.getvalue()

    def build_payslip_pdf(content_lines: list[str], password: str) -> bytes:
        raw_pdf = BytesIO()
        doc = canvas.Canvas(raw_pdf, pagesize=A4)
        _, page_height = A4
        y = page_height - 50
        for line in content_lines:
            doc.drawString(50, y, line)
            y -= 16
            if y <= 50:
                doc.showPage()
                y = page_height - 50
        doc.save()
        return encrypt_pdf(raw_pdf.getvalue(), password)

    base_dir = Path(settings.employee_document_upload_dir) / "system"
    base_dir.mkdir(parents=True, exist_ok=True)

    if document_id == f"system-appointment-{current_user.id}":
        filename = f"appointment_letter_{current_user.id}.txt"
        media_type = "text/plain"
        content = (
            f"Appointment Letter\n\n"
            f"Employee: {current_user.name}\n"
            f"Employee ID: {current_user.id}\n"
            f"Email: {current_user.email}\n"
            f"Joining Date: {current_user.joining_date.isoformat()}\n"
        )
    elif document_id.startswith(f"system-payslip-{current_user.id}-"):
        period = document_id.replace(f"system-payslip-{current_user.id}-", "", 1)
        filename = f"payslip_{current_user.id}_{period}.pdf"
        media_type = "application/pdf"
        gross = payroll_data.get("gross") if payroll_data else None
        net = payroll_data.get("net") if payroll_data else None
        deductions = payroll_data.get("deductions") if payroll_data else {}
        pan = payroll_data.get("pan") if payroll_data else None
        pf_uan = payroll_data.get("pf_uan") if payroll_data else None
        esi_no = payroll_data.get("esi_no") if payroll_data else None
        pf = float(deductions.get("pf", 0)) if isinstance(deductions, dict) else 0.0
        esi = float(deductions.get("esi", 0)) if isinstance(deductions, dict) else 0.0
        tax = float(deductions.get("tax", 0)) if isinstance(deductions, dict) else 0.0
        professional_tax = float(
            deductions.get("professional_tax", deductions.get("pt", deductions.get("pr", 0)))
        ) if isinstance(deductions, dict) else 0.0
        known_keys = {"pf", "esi", "tax", "professional_tax", "pt", "pr"}
        other_deductions_total = 0.0
        if isinstance(deductions, dict):
            for key, value in deductions.items():
                if key in known_keys:
                    continue
                try:
                    other_deductions_total += float(value)
                except (TypeError, ValueError):
                    continue
        credit_amount = net if net is not None else (
            (float(gross) - (pf + esi + tax + professional_tax + other_deductions_total))
            if gross is not None
            else None
        )
        content_lines = [
            "Payslip Statement",
            "",
            f"Employee: {current_user.name}",
            f"Employee ID: {current_user.id}",
            f"Email: {current_user.email}",
            f"Period: {period}",
            "",
            "Earnings",
            f"Gross Salary: {f'{float(gross):.2f}' if gross is not None else 'N/A'}",
            "",
            "Deductions",
            f"Tax Deduction: {tax:.2f}",
            f"PF Deduction: {pf:.2f}",
            f"ESI Deduction: {esi:.2f}",
            f"Professional Tax: {professional_tax:.2f}",
            f"Other Deductions: {other_deductions_total:.2f}",
            "",
            f"Net Credit: {f'{float(credit_amount):.2f}' if credit_amount is not None else 'N/A'}",
            "",
            "Statutory Details",
            f"PAN: {pan or current_user.pan_number or 'N/A'}",
            f"PF UAN: {pf_uan or 'N/A'}",
            f"ESI No: {esi_no or 'N/A'}",
            "",
            "PDF Password: Employee DOB (DD-MM-YY)",
        ]
        path = base_dir / filename
        path.write_bytes(build_payslip_pdf(content_lines, dob_password(current_user)))
        return path, filename, media_type
    elif document_id.startswith(f"system-tax-{current_user.id}-"):
        year = document_id.replace(f"system-tax-{current_user.id}-", "", 1)
        filename = f"tax_statement_{current_user.id}_{year}.txt"
        media_type = "text/plain"
        content = (
            f"Tax Statement\n\n"
            f"Employee: {current_user.name}\n"
            f"Employee ID: {current_user.id}\n"
            f"Financial Year: {year}-{str(int(year) + 1)[2:] if year.isdigit() else ''}\n"
            f"Note: This is a generated sample tax statement.\n"
        )
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    path = base_dir / filename
    if not path.exists():
        path.write_text(content, encoding="utf-8")
    return path, filename, media_type


@router.get("/departments")
async def list_departments(
    _: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Department).order_by(Department.name.asc()))).scalars().all()
    return success_response(
        [{"id": row.id, "name": row.name, "location": row.location} for row in rows]
    )


@router.post("")
async def create_employee(
    payload: EmployeeCreate,
    _: Employee = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    email = payload.email.strip().lower()
    existing = (
        await db.execute(select(Employee).where(func.lower(Employee.email) == email))
    ).scalar_one_or_none()
    if existing is not None and existing.status == EmployeeStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response("EMAIL_ALREADY_EXISTS", "An employee with this email already exists"),
        )

    if payload.department_id is not None:
        department = (
            await db.execute(select(Department).where(Department.id == payload.department_id))
        ).scalar_one_or_none()
        if department is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response("INVALID_DEPARTMENT", "Selected department does not exist"),
            )

    try:
        role = Role(payload.role.strip().upper())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_ROLE", "role must be ADMIN, MANAGER, or EMPLOYEE"),
        ) from exc

    if existing is not None and existing.status == EmployeeStatus.INACTIVE:
        employee = existing
        employee.name = payload.name.strip()
        employee.hashed_password = hash_password(payload.password)
        employee.department_id = payload.department_id
        employee.role = role
        employee.status = EmployeeStatus.ACTIVE
        employee.joining_date = payload.joining_date
        employee.date_of_birth = payload.date_of_birth
        employee.phone = payload.phone.strip() if payload.phone else None
        employee.address = payload.address.strip() if payload.address else None
        employee.blood_type = payload.blood_type.strip().upper() if payload.blood_type else None
        employee.occupancy = payload.occupancy.strip() if payload.occupancy else None
        employee.current_salary_usd = payload.current_salary_usd
        employee.bank_name = payload.bank_name.strip() if payload.bank_name else None
        employee.bank_account_number = payload.bank_account_number.strip() if payload.bank_account_number else None
        employee.bank_account_name = payload.bank_account_name.strip() if payload.bank_account_name else None
        employee.bank_branch = payload.bank_branch.strip() if payload.bank_branch else None
        employee.bank_ifsc = payload.bank_ifsc.strip().upper() if payload.bank_ifsc else None
        employee.pan_number = payload.pan_number.strip().upper() if payload.pan_number else None
        employee.pan_name = payload.pan_name.strip() if payload.pan_name else None
        employee.pan_dob = payload.pan_dob
    else:
        employee = Employee(
            name=payload.name.strip(),
            email=email,
            hashed_password=hash_password(payload.password),
            department_id=payload.department_id,
            role=role,
            status=EmployeeStatus.ACTIVE,
            joining_date=payload.joining_date,
            date_of_birth=payload.date_of_birth,
            phone=payload.phone.strip() if payload.phone else None,
            address=payload.address.strip() if payload.address else None,
            blood_type=payload.blood_type.strip().upper() if payload.blood_type else None,
            occupancy=payload.occupancy.strip() if payload.occupancy else None,
            current_salary_usd=payload.current_salary_usd,
            bank_name=payload.bank_name.strip() if payload.bank_name else None,
            bank_account_number=payload.bank_account_number.strip() if payload.bank_account_number else None,
            bank_account_name=payload.bank_account_name.strip() if payload.bank_account_name else None,
            bank_branch=payload.bank_branch.strip() if payload.bank_branch else None,
            bank_ifsc=payload.bank_ifsc.strip().upper() if payload.bank_ifsc else None,
            pan_number=payload.pan_number.strip().upper() if payload.pan_number else None,
            pan_name=payload.pan_name.strip() if payload.pan_name else None,
            pan_dob=payload.pan_dob,
        )
        db.add(employee)

    # Flush first so employee.id is available for statutory seeding.
    await db.flush()

    existing_balances = (
        await db.execute(select(LeaveBalance).where(LeaveBalance.employee_id == employee.id))
    ).scalars().all()
    existing_types = {row.leave_type for row in existing_balances}
    for leave_type, total in DEFAULT_LEAVE_TOTALS.items():
        if leave_type in existing_types:
            continue
        db.add(
            LeaveBalance(
                employee_id=employee.id,
                leave_type=leave_type,
                total=total,
                used=0.0,
                remaining=total,
            )
        )

    should_seed_statutory = bool(payload.pf_uan or payload.esi_no or payload.pan_number or payload.current_salary_usd is not None)
    if should_seed_statutory:
        join_month = payload.joining_date.replace(day=1)
        gross = float(payload.current_salary_usd) if payload.current_salary_usd is not None else 0.0
        existing_seed = (
            await db.execute(
                select(PayrollRecord).where(
                    PayrollRecord.employee_id == employee.id,
                    PayrollRecord.month == join_month,
                ).order_by(desc(PayrollRecord.id)).limit(1)
            )
        ).scalar_one_or_none()
        if existing_seed is not None:
            existing_seed.gross = gross
            existing_seed.deductions = existing_seed.deductions or {}
            existing_seed.net = gross
            existing_seed.pan = payload.pan_number.strip().upper() if payload.pan_number else _default_pan(employee.id)
            existing_seed.pf_uan = payload.pf_uan.strip() if payload.pf_uan else None
            existing_seed.esi_no = payload.esi_no.strip() if payload.esi_no else None
        else:
            db.add(
                PayrollRecord(
                    employee_id=employee.id,
                    month=join_month,
                    gross=gross,
                    deductions={},
                    net=gross,
                    pan=(payload.pan_number.strip().upper() if payload.pan_number else _default_pan(employee.id)),
                    pf_uan=payload.pf_uan.strip() if payload.pf_uan else None,
                    esi_no=payload.esi_no.strip() if payload.esi_no else None,
                )
            )

    if payload.job_title and payload.job_title.strip():
        current_job = (
            await db.execute(
                select(JobHistory)
                .where(JobHistory.employee_id == employee.id, JobHistory.is_current.is_(True))
                .order_by(desc(JobHistory.start_date), desc(JobHistory.id))
            )
        ).scalars().first()
        if current_job and current_job.is_current:
            current_job.is_current = False
            current_job.end_date = payload.joining_date

        dept_name = "Unassigned"
        if employee.department_id is not None:
            department = (
                await db.execute(select(Department).where(Department.id == employee.department_id))
            ).scalar_one_or_none()
            if department is not None:
                dept_name = department.name

        db.add(
            JobHistory(
                employee_id=employee.id,
                designation=payload.job_title.strip(),
                business_unit="General",
                department=dept_name,
                start_date=payload.joining_date,
                end_date=None,
                is_current=True,
            )
        )

    await db.commit()
    await db.refresh(employee)
    return success_response(_employee_directory_payload(employee))


@router.get("")
async def list_employees(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    department_id: int | None = None,
    location: str | None = None,
    q: str | None = None,
    _: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Employee).where(Employee.status == EmployeeStatus.ACTIVE)
    count_query = select(func.count(Employee.id)).where(Employee.status == EmployeeStatus.ACTIVE)

    if department_id is not None:
        query = query.where(Employee.department_id == department_id)
        count_query = count_query.where(Employee.department_id == department_id)

    if location:
        location_term = f"%{location.strip()}%"
        query = query.join(Department, Employee.department_id == Department.id).where(Department.location.ilike(location_term))
        count_query = count_query.join(Department, Employee.department_id == Department.id).where(Department.location.ilike(location_term))

    if q:
        raw = q.strip()
        if raw.isdigit():
            query = query.where(Employee.id == int(raw))
            count_query = count_query.where(Employee.id == int(raw))
        else:
            term = f"%{raw}%"
            query = query.where(or_(Employee.name.ilike(term), Employee.email.ilike(term)))
            count_query = count_query.where(or_(Employee.name.ilike(term), Employee.email.ilike(term)))

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.order_by(Employee.id).limit(limit).offset(offset))
    items = result.scalars().all()

    data = {
        "items": [_employee_directory_payload(e) for e in items],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }
    return success_response(data)


@router.get("/me")
async def my_profile(current_user: Employee = Depends(get_current_user)):
    return success_response(
        {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "department_id": current_user.department_id,
            "role": current_user.role.value,
            "status": current_user.status.value,
            "joining_date": current_user.joining_date,
            "date_of_birth": current_user.date_of_birth,
            "phone": current_user.phone,
            "address": current_user.address,
            "blood_type": current_user.blood_type,
            "occupancy": current_user.occupancy,
            "has_profile_photo": bool(current_user.profile_photo_path),
        }
    )


@router.put("/me")
async def update_my_profile(
    payload: EmployeeMeUpdate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if all(value is None for value in [payload.name, payload.phone, payload.address, payload.blood_type, payload.occupancy, payload.date_of_birth]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_PAYLOAD", "At least one editable field is required"),
        )

    if payload.name is not None:
        current_user.name = payload.name.strip()
        if len(current_user.name) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response("INVALID_NAME", "name must be at least 2 characters"),
            )
    if payload.phone is not None:
        current_user.phone = payload.phone.strip()
    if payload.address is not None:
        current_user.address = payload.address.strip()
    if payload.blood_type is not None:
        current_user.blood_type = payload.blood_type.strip().upper()
    if payload.occupancy is not None:
        current_user.occupancy = payload.occupancy.strip()
    if payload.date_of_birth is not None:
        current_user.date_of_birth = payload.date_of_birth

    await db.commit()
    await db.refresh(current_user)
    return success_response(
        {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "department_id": current_user.department_id,
            "role": current_user.role.value,
            "status": current_user.status.value,
            "joining_date": current_user.joining_date,
            "date_of_birth": current_user.date_of_birth,
            "phone": current_user.phone,
            "address": current_user.address,
            "blood_type": current_user.blood_type,
            "occupancy": current_user.occupancy,
            "has_profile_photo": bool(current_user.profile_photo_path),
        }
    )


@router.post("/me/profile-picture")
async def upload_my_profile_picture(
    file: UploadFile = File(...),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_PROFILE_PHOTO_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .png, .jpg, .jpeg, .webp are supported")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 2 MB)")

    upload_dir = Path(settings.profile_photo_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    if current_user.profile_photo_path:
        previous = Path(current_user.profile_photo_path)
        if previous.exists() and previous.is_file():
            previous.unlink(missing_ok=True)

    stored_name = f"user_{current_user.id}_{uuid4().hex}{extension}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(raw)

    mime_type = file.content_type or {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(extension, "application/octet-stream")
    current_user.profile_photo_path = str(stored_path)
    current_user.profile_photo_mime = mime_type
    await db.commit()
    await db.refresh(current_user)

    return success_response(
        {
            "message": "Profile picture uploaded",
            "has_profile_photo": True,
        }
    )


@router.get("/me/profile-picture")
async def get_my_profile_picture(current_user: Employee = Depends(get_current_user)):
    if not current_user.profile_photo_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile picture uploaded")

    base_dir = Path(settings.profile_photo_upload_dir).resolve()
    requested = Path(current_user.profile_photo_path).resolve()
    if base_dir not in requested.parents and requested != base_dir:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid profile picture path")
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile picture file missing")

    return FileResponse(
        path=str(requested),
        filename=requested.name,
        media_type=current_user.profile_photo_mime or "application/octet-stream",
    )


@router.get("/{employee_id}/profile-picture")
async def get_employee_profile_picture(
    employee_id: int,
    _: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    if not employee.profile_photo_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile picture uploaded")

    base_dir = Path(settings.profile_photo_upload_dir).resolve()
    requested = Path(employee.profile_photo_path).resolve()
    if base_dir not in requested.parents and requested != base_dir:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid profile picture path")
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile picture file missing")

    return FileResponse(
        path=str(requested),
        filename=requested.name,
        media_type=employee.profile_photo_mime or "application/octet-stream",
    )


@router.get("/me/job-history")
async def my_job_history(current_user: Employee = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(JobHistory).where(JobHistory.employee_id == current_user.id).order_by(JobHistory.start_date.desc(), JobHistory.id.desc())
    )
    rows = result.scalars().all()
    return success_response(
        [
            {
                "id": row.id,
                "designation": row.designation,
                "business_unit": row.business_unit,
                "department": row.department,
                "start_date": row.start_date,
                "end_date": row.end_date,
                "is_current": row.is_current,
            }
            for row in rows
        ]
    )


@router.get("/me/documents")
async def my_documents(current_user: Employee = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    uploaded_items: list[dict] = []
    try:
        rows = (
            await db.execute(
                select(EmployeeDocument)
                .where(EmployeeDocument.employee_id == current_user.id)
                .order_by(desc(EmployeeDocument.created_at), desc(EmployeeDocument.id))
            )
        ).scalars().all()
        uploaded_items = [_document_payload(row) for row in rows]
    except OperationalError:
        uploaded_items = []

    # My Documents should only list actual uploaded items for this employee.
    # System-generated docs remain available via their dedicated download route (used by Finance fallback).
    uploaded_items.sort(key=lambda item: item.get("issued_on") or "", reverse=True)
    return success_response(uploaded_items)


@router.post("/me/documents")
async def upload_my_document(
    title: str = Form(min_length=3, max_length=220),
    document_type: str = Form(default="OTHER"),
    file: UploadFile = File(...),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .pdf, .txt, .md, .doc, .docx are supported")

    normalized_type = document_type.strip().upper()
    if normalized_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document type")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 5 MB)")
    if extension in {".txt", ".md"}:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only UTF-8 text is supported for .txt/.md") from exc

    upload_dir = Path(settings.employee_document_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"user_{current_user.id}_{uuid4().hex}{extension}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(raw)

    mime_type = file.content_type or {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(extension, "application/octet-stream")

    doc = EmployeeDocument(
        employee_id=current_user.id,
        uploaded_by=current_user.id,
        title=title.strip(),
        document_type=normalized_type,
        original_filename=file.filename,
        file_path=str(stored_path),
        mime_type=mime_type,
        size_bytes=len(raw),
        checksum=hashlib.sha256(raw).hexdigest(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return success_response(_document_payload(doc))


@router.delete("/me/documents/{document_id}")
async def delete_my_document(
    document_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not document_id.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_DOCUMENT_ID", "Only uploaded documents can be deleted"),
        )

    numeric_id = int(document_id)
    doc = (
        await db.execute(
            select(EmployeeDocument).where(EmployeeDocument.id == numeric_id, EmployeeDocument.employee_id == current_user.id)
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("DOCUMENT_NOT_FOUND", "Document not found"),
        )
    if doc.document_type != "OTHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_response("DOCUMENT_DELETE_FORBIDDEN", "Only OTHER documents can be deleted"),
        )

    requested = Path(doc.file_path).resolve()
    base_dir = Path(settings.employee_document_upload_dir).resolve()
    if base_dir not in requested.parents and requested != base_dir:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid document path")

    await db.delete(doc)
    await db.commit()
    if requested.exists() and requested.is_file():
        requested.unlink(missing_ok=True)

    return success_response({"id": str(numeric_id), "deleted": True})


@router.post("/{employee_id}/documents")
async def upload_employee_document(
    employee_id: int,
    title: str = Form(min_length=3, max_length=220),
    document_type: str = Form(default="OTHER"),
    file: UploadFile = File(...),
    uploader: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("EMPLOYEE_NOT_FOUND", "Employee not found"),
        )

    normalized_type = document_type.strip().upper()
    allowed_non_payslip_types = {"APPOINTMENT", "TAX", "OTHER"}
    if normalized_type not in allowed_non_payslip_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_DOCUMENT_TYPE", "document_type must be APPOINTMENT, TAX, or OTHER"),
        )

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .pdf, .txt, .md, .doc, .docx are supported")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 5 MB)")
    if extension in {".txt", ".md"}:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only UTF-8 text is supported for .txt/.md") from exc

    upload_dir = Path(settings.employee_document_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"user_{employee.id}_{uuid4().hex}{extension}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(raw)

    mime_type = file.content_type or {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(extension, "application/octet-stream")

    doc = EmployeeDocument(
        employee_id=employee.id,
        uploaded_by=uploader.id,
        title=title.strip(),
        document_type=normalized_type,
        original_filename=file.filename,
        file_path=str(stored_path),
        mime_type=mime_type,
        size_bytes=len(raw),
        checksum=hashlib.sha256(raw).hexdigest(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return success_response(_document_payload(doc))


@router.post("/{employee_id}/documents/payslip")
async def upload_employee_payslip(
    employee_id: int,
    title: str = Form(min_length=3, max_length=220),
    period: str | None = Form(default=None),
    file: UploadFile = File(...),
    uploader: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("EMPLOYEE_NOT_FOUND", "Employee not found"),
        )

    normalized_period: str | None = None
    if period is not None and period.strip():
        candidate = period.strip()
        if not PAYSLIP_PERIOD_RE.match(candidate):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response("INVALID_PERIOD", "period must be in YYYY-MM format"),
            )
        year, month = candidate.split("-", 1)
        if int(month) < 1 or int(month) > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response("INVALID_PERIOD", "period month must be between 01 and 12"),
            )
        normalized_period = f"{year}-{month}"

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .pdf, .txt, .md, .doc, .docx are supported")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 5 MB)")
    if extension in {".txt", ".md"}:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only UTF-8 text is supported for .txt/.md") from exc

    upload_dir = Path(settings.employee_document_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"user_{employee.id}_{uuid4().hex}{extension}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(raw)

    mime_type = file.content_type or {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(extension, "application/octet-stream")

    doc = EmployeeDocument(
        employee_id=employee.id,
        uploaded_by=uploader.id,
        title=(f"[{normalized_period}] {title.strip()}" if normalized_period else title.strip()),
        document_type="PAYSLIP",
        original_filename=file.filename,
        file_path=str(stored_path),
        mime_type=mime_type,
        size_bytes=len(raw),
        checksum=hashlib.sha256(raw).hexdigest(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return success_response(_document_payload(doc))


@router.get("/me/documents/{document_id}/download")
async def download_my_document(
    document_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if document_id.startswith("system-"):
        payroll_data: dict | None = None
        if document_id.startswith(f"system-payslip-{current_user.id}-"):
            period = document_id.replace(f"system-payslip-{current_user.id}-", "", 1)
            try:
                year_str, month_str = period.split("-", 1)
                month_anchor = date(int(year_str), int(month_str), 1)
                joining_month_start = current_user.joining_date.replace(day=1)
                if month_anchor < joining_month_start:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=error_response("PAYSLIP_NOT_AVAILABLE", "Payslip is not available before joining month"),
                    )
                payroll_row = (
                    await db.execute(
                        select(PayrollRecord)
                        .where(PayrollRecord.employee_id == current_user.id, PayrollRecord.month == month_anchor)
                        .order_by(desc(PayrollRecord.id))
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if payroll_row is not None:
                    payroll_data = {
                        "gross": payroll_row.gross,
                        "deductions": payroll_row.deductions or {},
                        "net": payroll_row.net,
                        "pan": payroll_row.pan,
                        "pf_uan": payroll_row.pf_uan,
                        "esi_no": payroll_row.esi_no,
                    }
            except ValueError:
                payroll_data = None

        path, filename, media_type = _build_system_document_file(current_user, document_id, payroll_data)
        return FileResponse(path=str(path), filename=filename, media_type=media_type)

    if not document_id.isdigit():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    numeric_id = int(document_id)
    doc = (
        await db.execute(
            select(EmployeeDocument).where(EmployeeDocument.id == numeric_id, EmployeeDocument.employee_id == current_user.id)
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    base_dir = Path(settings.employee_document_upload_dir).resolve()
    requested = Path(doc.file_path).resolve()
    if base_dir not in requested.parents and requested != base_dir:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid document path")
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file missing")

    return FileResponse(
        path=str(requested),
        filename=doc.original_filename,
        media_type=doc.mime_type or "application/octet-stream",
    )


@router.delete("/{employee_id}")
async def deactivate_employee(
    employee_id: int,
    current_user: Employee = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("EMPLOYEE_NOT_FOUND", "Employee not found"),
        )
    if employee.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_OPERATION", "You cannot deactivate your own account"),
        )
    if employee.status == EmployeeStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("ALREADY_INACTIVE", "Employee is already inactive"),
        )

    employee.status = EmployeeStatus.INACTIVE
    await db.commit()
    await db.refresh(employee)
    return success_response({"id": employee.id, "status": employee.status.value})


@router.patch("/{employee_id}/reactivate")
async def reactivate_employee(
    employee_id: int,
    _: Employee = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("EMPLOYEE_NOT_FOUND", "Employee not found"),
        )
    if employee.status == EmployeeStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("ALREADY_ACTIVE", "Employee is already active"),
        )

    employee.status = EmployeeStatus.ACTIVE
    await db.commit()
    await db.refresh(employee)
    return success_response({"id": employee.id, "status": employee.status.value})


@router.get("/projects/catalog")
async def list_projects_catalog(
    _: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Project).order_by(Project.name.asc()))).scalars().all()
    return success_response(
        [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "status": row.status.value if hasattr(row.status, "value") else row.status,
            }
            for row in rows
        ]
    )


@router.post("/projects/catalog")
async def create_project_catalog_item(
    payload: ProjectCreate,
    _: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    normalized_name = payload.name.strip()
    duplicate = (
        await db.execute(select(Project).where(func.lower(Project.name) == normalized_name.lower()))
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response("PROJECT_ALREADY_EXISTS", "A project with this name already exists"),
        )

    try:
        project_status = ProjectStatus(payload.status.strip().upper()) if payload.status else ProjectStatus.ONGOING
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_PROJECT_STATUS", "status must be ONGOING, COMPLETED, ON_HOLD, or PLANNED"),
        ) from exc

    project = Project(
        name=normalized_name,
        description=payload.description.strip() if payload.description else None,
        status=project_status,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return success_response(
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status.value if hasattr(project.status, "value") else project.status,
        }
    )


@router.put("/projects/catalog/{project_id}/status")
async def update_project_catalog_status(
    project_id: int,
    payload: ProjectStatusUpdate,
    _: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("PROJECT_NOT_FOUND", "Project not found"),
        )
    try:
        project.status = ProjectStatus(payload.status.strip().upper())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_PROJECT_STATUS", "status must be ONGOING, COMPLETED, ON_HOLD, or PLANNED"),
        ) from exc

    await db.commit()
    await db.refresh(project)
    return success_response(
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status.value if hasattr(project.status, "value") else project.status,
        }
    )


@router.get("/{employee_id}/projects")
async def list_employee_projects(
    employee_id: int,
    _: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("EMPLOYEE_NOT_FOUND", "Employee not found"),
        )

    project_rows = (
        await db.execute(
            select(EmployeeProject, Project)
            .join(Project, EmployeeProject.project_id == Project.id)
            .where(EmployeeProject.employee_id == employee_id)
            .order_by(Project.name.asc())
        )
    ).all()
    return success_response(
        [
            {
                "project_id": project.id,
                "project_name": project.name,
                "project_description": project.description,
                "project_status": project.status.value if hasattr(project.status, "value") else project.status,
                "role_on_project": employee_project.role_on_project,
            }
            for employee_project, project in project_rows
        ]
    )


@router.post("/{employee_id}/projects")
async def assign_employee_project(
    employee_id: int,
    payload: EmployeeProjectAssign,
    _: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("EMPLOYEE_NOT_FOUND", "Employee not found"),
        )

    project = (await db.execute(select(Project).where(Project.id == payload.project_id))).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("PROJECT_NOT_FOUND", "Project not found"),
        )

    existing = (
        await db.execute(
            select(EmployeeProject).where(
                EmployeeProject.employee_id == employee_id,
                EmployeeProject.project_id == payload.project_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.role_on_project = payload.role_on_project.strip() if payload.role_on_project else existing.role_on_project
        await db.commit()
        await db.refresh(existing)
        return success_response(
            {
                "employee_id": employee_id,
                "project_id": payload.project_id,
                "role_on_project": existing.role_on_project,
            }
        )

    row = EmployeeProject(
        employee_id=employee_id,
        project_id=payload.project_id,
        role_on_project=payload.role_on_project.strip() if payload.role_on_project else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(
        {
            "employee_id": row.employee_id,
            "project_id": row.project_id,
            "role_on_project": row.role_on_project,
        }
    )


@router.delete("/{employee_id}/projects/{project_id}")
async def remove_employee_project(
    employee_id: int,
    project_id: int,
    _: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(EmployeeProject).where(
                EmployeeProject.employee_id == employee_id,
                EmployeeProject.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("ASSIGNMENT_NOT_FOUND", "Employee project assignment not found"),
        )

    await db.delete(row)
    await db.commit()
    return success_response({"employee_id": employee_id, "project_id": project_id})


@router.put("/{employee_id}/job-title")
async def update_employee_job_title(
    employee_id: int,
    payload: EmployeeJobTitleUpdate,
    _: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("EMPLOYEE_NOT_FOUND", "Employee not found"),
        )

    effective_date = payload.effective_date or date.today()
    current_job = (
        await db.execute(
            select(JobHistory)
            .where(JobHistory.employee_id == employee.id, JobHistory.is_current.is_(True))
            .order_by(desc(JobHistory.start_date), desc(JobHistory.id))
        )
    ).scalars().first()

    if current_job and effective_date < current_job.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_EFFECTIVE_DATE", "effective_date cannot be before current job start_date"),
        )

    department_name = None
    if payload.department:
        department_name = payload.department.strip()
    elif current_job:
        department_name = current_job.department
    elif employee.department_id is not None:
        department = (await db.execute(select(Department).where(Department.id == employee.department_id))).scalar_one_or_none()
        department_name = department.name if department else "Unassigned"
    else:
        department_name = "Unassigned"

    business_unit = (
        payload.business_unit.strip()
        if payload.business_unit
        else (current_job.business_unit if current_job else "General")
    )

    if current_job and current_job.is_current:
        current_job.is_current = False
        current_job.end_date = effective_date - timedelta(days=1) if effective_date > current_job.start_date else effective_date

    new_job = JobHistory(
        employee_id=employee.id,
        designation=payload.designation.strip(),
        business_unit=business_unit,
        department=department_name,
        start_date=effective_date,
        end_date=None,
        is_current=True,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    return success_response(
        {
            "id": new_job.id,
            "employee_id": employee.id,
            "designation": new_job.designation,
            "business_unit": new_job.business_unit,
            "department": new_job.department,
            "start_date": new_job.start_date,
            "end_date": new_job.end_date,
            "is_current": new_job.is_current,
        }
    )


@router.put("/{employee_id}")
async def update_employee(
    employee_id: int,
    payload: EmployeeAdminUpdate,
    _: Employee = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("EMPLOYEE_NOT_FOUND", "Employee not found"),
        )

    if payload.email is not None:
        normalized_email = payload.email.strip().lower()
        duplicate = (
            await db.execute(
                select(Employee).where(func.lower(Employee.email) == normalized_email, Employee.id != employee.id)
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_response("EMAIL_ALREADY_EXISTS", "An employee with this email already exists"),
            )
        employee.email = normalized_email

    if payload.department_id is not None:
        department = (
            await db.execute(select(Department).where(Department.id == payload.department_id))
        ).scalar_one_or_none()
        if department is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response("INVALID_DEPARTMENT", "Selected department does not exist"),
            )
        employee.department_id = payload.department_id

    if payload.role is not None:
        try:
            employee.role = Role(payload.role.strip().upper())
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response("INVALID_ROLE", "role must be ADMIN, MANAGER, or EMPLOYEE"),
            ) from exc

    if payload.name is not None:
        employee.name = payload.name.strip()
    if payload.password is not None and payload.password.strip():
        employee.hashed_password = hash_password(payload.password.strip())
    if payload.joining_date is not None:
        employee.joining_date = payload.joining_date
    if payload.date_of_birth is not None:
        employee.date_of_birth = payload.date_of_birth
    if payload.phone is not None:
        employee.phone = payload.phone.strip()
    if payload.occupancy is not None:
        employee.occupancy = payload.occupancy.strip()
    if payload.current_salary_usd is not None:
        employee.current_salary_usd = payload.current_salary_usd
    if payload.bank_name is not None:
        employee.bank_name = payload.bank_name.strip()
    if payload.bank_account_number is not None:
        employee.bank_account_number = payload.bank_account_number.strip()
    if payload.bank_account_name is not None:
        employee.bank_account_name = payload.bank_account_name.strip()
    if payload.bank_branch is not None:
        employee.bank_branch = payload.bank_branch.strip()
    if payload.bank_ifsc is not None:
        employee.bank_ifsc = payload.bank_ifsc.strip().upper()
    if payload.pan_number is not None:
        employee.pan_number = payload.pan_number.strip().upper()
    if payload.pan_name is not None:
        employee.pan_name = payload.pan_name.strip()
    if payload.pan_dob is not None:
        employee.pan_dob = payload.pan_dob

    if payload.job_title is not None and payload.job_title.strip():
        current_job = (
            await db.execute(
                select(JobHistory)
                .where(JobHistory.employee_id == employee.id, JobHistory.is_current.is_(True))
                .order_by(desc(JobHistory.start_date), desc(JobHistory.id))
            )
        ).scalars().first()

        next_designation = payload.job_title.strip()
        if current_job is None or current_job.designation != next_designation:
            if current_job and current_job.is_current:
                current_job.is_current = False
                current_job.end_date = date.today()

            department_name = "Unassigned"
            if employee.department_id is not None:
                department = (
                    await db.execute(select(Department).where(Department.id == employee.department_id))
                ).scalar_one_or_none()
                if department is not None:
                    department_name = department.name

            db.add(
                JobHistory(
                    employee_id=employee.id,
                    designation=next_designation,
                    business_unit="General",
                    department=department_name,
                    start_date=date.today(),
                    end_date=None,
                    is_current=True,
                )
            )

    should_upsert_statutory = any(
        value is not None
        for value in [payload.current_salary_usd, payload.pan_number, payload.pf_uan, payload.esi_no]
    )
    if should_upsert_statutory:
        month_anchor = date.today().replace(day=1)
        row = (
            await db.execute(
                select(PayrollRecord)
                .where(PayrollRecord.employee_id == employee.id, PayrollRecord.month == month_anchor)
                .order_by(desc(PayrollRecord.id))
                .limit(1)
            )
        ).scalar_one_or_none()
        gross = float(payload.current_salary_usd) if payload.current_salary_usd is not None else float(employee.current_salary_usd or 0.0)
        pan_value = payload.pan_number.strip().upper() if payload.pan_number else (employee.pan_number or _default_pan(employee.id))
        pf_value = payload.pf_uan.strip() if payload.pf_uan else None
        esi_value = payload.esi_no.strip() if payload.esi_no else None
        if row is not None:
            row.gross = gross
            row.net = gross
            row.deductions = row.deductions or {}
            row.pan = pan_value
            row.pf_uan = pf_value
            row.esi_no = esi_value
        else:
            db.add(
                PayrollRecord(
                    employee_id=employee.id,
                    month=month_anchor,
                    gross=gross,
                    deductions={},
                    net=gross,
                    pan=pan_value,
                    pf_uan=pf_value,
                    esi_no=esi_value,
                )
            )

    await db.commit()
    await db.refresh(employee)
    return success_response({"id": employee.id, "status": employee.status.value})


@router.get("/{employee_id}")
async def get_employee(employee_id: int, _: Employee = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if employee is None:
        return {"success": False, "data": None, "error": {"code": "EMPLOYEE_NOT_FOUND", "message": "Employee not found"}}

    department = None
    if employee.department_id is not None:
        department = (
            await db.execute(select(Department).where(Department.id == employee.department_id))
        ).scalar_one_or_none()

    job_history = (
        await db.execute(
            select(JobHistory)
            .where(JobHistory.employee_id == employee.id)
            .order_by(desc(JobHistory.is_current), desc(JobHistory.start_date), desc(JobHistory.id))
        )
    ).scalars().first()
    project_rows = (
        await db.execute(
            select(EmployeeProject, Project)
            .join(Project, EmployeeProject.project_id == Project.id)
            .where(EmployeeProject.employee_id == employee.id)
            .order_by(Project.name.asc())
        )
    ).all()
    latest_payroll = (
        await db.execute(
            select(PayrollRecord)
            .where(PayrollRecord.employee_id == employee.id)
            .order_by(desc(PayrollRecord.month), desc(PayrollRecord.id))
            .limit(1)
        )
    ).scalar_one_or_none()

    return success_response(
        {
            "id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "phone": employee.phone,
            "role": employee.role.value,
            "status": employee.status.value,
            "department_id": employee.department_id,
            "department": department.name if department else None,
            "location": department.location if department else None,
            "job_title": job_history.designation if job_history else None,
            "date_of_birth": employee.date_of_birth,
            "blood_type": employee.blood_type,
            "occupancy": employee.occupancy,
            "address": employee.address,
            "joining_date": employee.joining_date,
            "has_profile_photo": bool(employee.profile_photo_path),
            "current_salary_usd": float(employee.current_salary_usd) if employee.current_salary_usd is not None else None,
            "bank_name": employee.bank_name,
            "bank_account_number": employee.bank_account_number,
            "bank_account_name": employee.bank_account_name,
            "bank_branch": employee.bank_branch,
            "bank_ifsc": employee.bank_ifsc,
            "pan_number": employee.pan_number,
            "pan_name": employee.pan_name,
            "pan_dob": employee.pan_dob,
            "pf_uan": latest_payroll.pf_uan if latest_payroll else None,
            "esi_no": latest_payroll.esi_no if latest_payroll else None,
            "projects": [
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "role_on_project": employee_project.role_on_project,
                }
                for employee_project, project in project_rows
            ],
        }
    )
