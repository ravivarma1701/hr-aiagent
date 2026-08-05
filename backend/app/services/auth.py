from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import error_response
from app.core.security import decode_token
from app.db.session import get_db
from app.models.employee import Employee
from app.models.enums import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    try:
        payload = decode_token(token)
        subject = payload.get("sub")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_response("INVALID_TOKEN", "Token is invalid"))

    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_response("INVALID_TOKEN", "Token missing subject"))

    result = await db.execute(select(Employee).where(Employee.id == int(subject)))
    employee = result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_response("USER_NOT_FOUND", "User not found"))
    return employee


def require_roles(*allowed: Role):
    async def _checker(current_user: Employee = Depends(get_current_user)) -> Employee:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_response("FORBIDDEN", "You do not have required permissions"),
            )
        return current_user

    return _checker
