import asyncio
import hashlib
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.models.employee_document import EmployeeDocument


def resolve_container_path(raw_path: str) -> Path:
    normalized = raw_path.replace("\\", "/")
    candidate = Path(normalized)
    if candidate.exists():
        return candidate
    if normalized.startswith("backend/storage/"):
        return Path("/app/storage") / normalized.removeprefix("backend/storage/")
    if normalized.startswith("./storage/"):
        return Path("/app/storage") / normalized.removeprefix("./storage/")
    if normalized.startswith("storage/"):
        return Path("/app/storage") / normalized.removeprefix("storage/")
    return candidate


def dob_password(employee: Employee) -> str:
    source = employee.pan_dob or employee.date_of_birth
    if source is None:
        return "01-01-90"
    return source.strftime("%d-%m-%y")


def encrypt_pdf(raw_pdf: bytes, password: str) -> bytes:
    reader = PdfReader(BytesIO(raw_pdf))
    if reader.is_encrypted:
        return raw_pdf
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def text_to_pdf(text: str, password: str) -> bytes:
    raw_pdf = BytesIO()
    doc = canvas.Canvas(raw_pdf, pagesize=A4)
    _, height = A4
    y = height - 50
    for line in text.splitlines() or [""]:
        doc.drawString(40, y, line[:1500])
        y -= 16
        if y <= 50:
            doc.showPage()
            y = height - 50
    doc.save()
    return encrypt_pdf(raw_pdf.getvalue(), password)


async def run() -> None:
    converted = 0
    skipped = 0
    failed = 0

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(EmployeeDocument, Employee)
                .join(Employee, Employee.id == EmployeeDocument.employee_id)
                .where(EmployeeDocument.document_type == "PAYSLIP")
            )
        ).all()

        for doc, employee in rows:
            path = resolve_container_path(doc.file_path)
            if not path.exists() or not path.is_file():
                print(f"[skip] id={doc.id} file missing: {path}")
                skipped += 1
                continue

            ext = path.suffix.lower()
            password = dob_password(employee)

            try:
                new_bytes: bytes
                target_path = path

                if ext == ".pdf":
                    original = path.read_bytes()
                    new_bytes = encrypt_pdf(original, password)
                elif ext in {".txt", ".md"}:
                    text = path.read_text(encoding="utf-8")
                    new_bytes = text_to_pdf(text, password)
                    target_path = path.with_suffix(".pdf")
                else:
                    print(f"[skip] id={doc.id} unsupported extension: {ext}")
                    skipped += 1
                    continue

                target_path.write_bytes(new_bytes)
                if target_path != path:
                    path.unlink(missing_ok=True)

                if doc.original_filename.lower().endswith(ext):
                    doc.original_filename = f"{Path(doc.original_filename).stem}.pdf"
                elif not doc.original_filename.lower().endswith(".pdf"):
                    doc.original_filename = f"{doc.original_filename}.pdf"
                doc.file_path = str(target_path)
                doc.mime_type = "application/pdf"
                doc.size_bytes = len(new_bytes)
                doc.checksum = hashlib.sha256(new_bytes).hexdigest()
                converted += 1
                print(f"[ok] id={doc.id} -> {target_path.name}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"[fail] id={doc.id}: {exc}")

        await session.commit()

    print(f"Done. converted={converted} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    asyncio.run(run())
