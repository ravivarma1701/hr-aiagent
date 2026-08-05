from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import error_response, success_response
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.auth import LoginRequest

router = APIRouter()


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee).where(Employee.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("INVALID_CREDENTIALS", "Invalid email or password"),
        )

    tokens = {
        "access_token": create_access_token(subject=str(user.id), role=user.role.value),
        "refresh_token": create_refresh_token(subject=str(user.id)),
        "token_type": "bearer",
    }
    return success_response(tokens)


@router.post("/token")
async def token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee).where(Employee.email == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("INVALID_CREDENTIALS", "Invalid email or password"),
        )

    return {
        "access_token": create_access_token(subject=str(user.id), role=user.role.value),
        "token_type": "bearer",
    }
