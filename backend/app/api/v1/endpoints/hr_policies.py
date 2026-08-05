import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.response import success_response
from app.db.session import get_db
from app.models.employee import Employee
from app.models.hr_policy import HRPolicy
from app.models.enums import Role
from app.services.auth import get_current_user, require_roles

router = APIRouter()
ALLOWED_POLICY_EXTENSIONS = {".txt", ".md", ".pdf"}


@router.get("")
async def list_policies(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    total = (await db.execute(select(func.count(HRPolicy.id)))).scalar_one()
    rows = (await db.execute(select(HRPolicy).order_by(HRPolicy.id.asc()).limit(limit).offset(offset))).scalars().all()
    return success_response(
        {
            "items": [
                {
                    "id": row.id,
                    "title": row.title,
                    "category": row.category,
                    "content": row.content,  # Legacy seeded rows may still use this.
                    "original_filename": row.original_filename,
                    "file_path": row.file_path,
                    "mime_type": row.mime_type,
                    "size_bytes": row.size_bytes,
                    "uploaded_by": row.uploaded_by,
                    "checksum": row.checksum,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ],
            "meta": {"total": total, "limit": limit, "offset": offset},
        }
    )


@router.post("/upload")
async def upload_policy_document(
    title: str = Form(min_length=3, max_length=220),
    category: str = Form(min_length=2, max_length=60),
    file: UploadFile = File(...),
    current_user: Employee = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    upload_dir = Path(settings.policy_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_POLICY_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .txt, .md, and .pdf are supported")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 2 MB)")

    if extension in {".txt", ".md"}:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only UTF-8 text is supported for .txt/.md") from exc

    stored_filename = f"{uuid4().hex}{extension}"
    stored_path = upload_dir / stored_filename
    stored_path.write_bytes(raw)

    checksum = hashlib.sha256(raw).hexdigest()
    mime_type = file.content_type or {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".pdf": "application/pdf",
    }.get(extension, "application/octet-stream")

    policy = HRPolicy(
        title=title.strip(),
        category=category.strip(),
        content=None,
        original_filename=file.filename,
        file_path=str(stored_path),
        mime_type=mime_type,
        size_bytes=len(raw),
        uploaded_by=current_user.id,
        checksum=checksum,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    return success_response(
        {
            "id": policy.id,
            "title": policy.title,
            "category": policy.category,
            "content": policy.content,
            "original_filename": policy.original_filename,
            "file_path": policy.file_path,
            "mime_type": policy.mime_type,
            "size_bytes": policy.size_bytes,
            "uploaded_by": policy.uploaded_by,
            "checksum": policy.checksum,
            "created_at": policy.created_at.isoformat() if policy.created_at else None,
        }
    )


@router.get("/{policy_id}/download")
async def download_policy_document(
    policy_id: int,
    _: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    policy = (await db.execute(select(HRPolicy).where(HRPolicy.id == policy_id))).scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    if not policy.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy file not available")

    base_dir = Path(settings.policy_upload_dir).resolve()
    requested = Path(policy.file_path).resolve()
    if base_dir not in requested.parents and requested != base_dir:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid file path")
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy file missing on server")

    return FileResponse(
        path=str(requested),
        filename=policy.original_filename or requested.name,
        media_type=policy.mime_type or "application/octet-stream",
    )
