from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.core.response import error_response
from app.models.employee import Employee
from app.schemas.chat import ChatMessageCreate, ChatSessionCreate
from app.services.auth import get_current_user

router = APIRouter()


@router.post("/sessions")
async def create_chat_session(
    payload: ChatSessionCreate,
    current_user: Employee = Depends(get_current_user),
):
    _ = payload
    _ = current_user
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=error_response("CHAT_NOT_IMPLEMENTED", "Chat session creation is a Phase-3 stub and not implemented yet"),
    )


@router.post("/sessions/{session_id}/messages")
async def post_chat_message(
    session_id: str,
    payload: ChatMessageCreate,
    current_user: Employee = Depends(get_current_user),
):
    _ = session_id
    _ = payload
    _ = current_user
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=error_response("CHAT_NOT_IMPLEMENTED", "Chat messaging is a Phase-3 stub and not implemented yet"),
    )
