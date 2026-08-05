from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return success_response({"status": "ok", "db": "connected"})
