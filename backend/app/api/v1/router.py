from fastapi import APIRouter

from app.api.v1.endpoints import (
    announcements,
    attendance,
    auth,
    chat,
    employees,
    finance,
    health,
    hr_policies,
    leaves,
    org,
    polls,
    team_calendar,
    tickets,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(leaves.router, prefix="/leaves", tags=["leaves"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(team_calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
api_router.include_router(polls.router, prefix="/polls", tags=["polls"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(hr_policies.router, prefix="/hr-policies", tags=["hr-policies"])
api_router.include_router(org.router, prefix="/org", tags=["org"])
api_router.include_router(health.router, tags=["health"])
