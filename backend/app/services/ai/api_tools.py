"""HTTP wrappers around the EXISTING backend APIs, used as the HR Action
Agent's tools.

This is the enforcement of the architecture rule "agents must not directly
mutate the database": every one of these functions is a plain authenticated
HTTP call to this same FastAPI service, carrying the *current user's own*
access token. All validation, role checks, and business rules therefore run
exactly once, in the existing endpoint code -- the AI layer has no
special-cased write path at all.
"""

from __future__ import annotations

import httpx

from app.core.config import settings


class ApiToolError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


async def _request(method: str, path: str, token: str, **kwargs) -> dict:
    url = f"{settings.internal_api_base_url}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.request(method, url, headers=headers, **kwargs)

    try:
        body = response.json()
    except ValueError:
        raise ApiToolError(response.status_code, "BAD_RESPONSE", "Backend returned a non-JSON response.")

    if response.status_code >= 400 or not body.get("success", True):
        error = body.get("error") or {}
        raise ApiToolError(
            response.status_code,
            error.get("code", "REQUEST_FAILED"),
            error.get("message", "The request could not be completed."),
        )
    return body.get("data")


# --- Leaves -----------------------------------------------------------------


async def create_leave_request(token: str, payload: dict) -> dict:
    return await _request("POST", "/api/v1/leaves/requests", token, json=payload)


async def get_my_leave_balances(token: str) -> dict:
    return await _request("GET", "/api/v1/leaves/balances/me", token)


async def get_my_leave_requests(token: str, limit: int = 20) -> dict:
    return await _request("GET", "/api/v1/leaves/requests/me", token, params={"limit": limit})


async def get_pending_leave_requests(token: str, limit: int = 20) -> dict:
    return await _request("GET", "/api/v1/leaves/requests/pending", token, params={"limit": limit})


async def approve_leave_request(token: str, request_id: int) -> dict:
    return await _request("POST", f"/api/v1/leaves/requests/{request_id}/approve", token)


async def reject_leave_request(token: str, request_id: int) -> dict:
    return await _request("POST", f"/api/v1/leaves/requests/{request_id}/reject", token)


# --- Tickets ------------------------------------------------------------------


async def create_ticket(token: str, payload: dict) -> dict:
    return await _request("POST", "/api/v1/tickets", token, json=payload)


async def get_my_tickets(token: str, limit: int = 20) -> dict:
    return await _request("GET", "/api/v1/tickets", token, params={"limit": limit, "mine": True})


async def assign_ticket(token: str, ticket_id: int, assignee_id: int) -> dict:
    return await _request("POST", f"/api/v1/tickets/{ticket_id}/assign", token, json={"assignee_id": assignee_id})


async def update_ticket_status(token: str, ticket_id: int, status: str) -> dict:
    return await _request("POST", f"/api/v1/tickets/{ticket_id}/status", token, json={"status": status})


# --- Announcements --------------------------------------------------------


async def create_announcement(token: str, title: str, body: str) -> dict:
    return await _request("POST", "/api/v1/announcements", token, json={"title": title, "body": body})


async def list_announcements(token: str, limit: int = 10) -> dict:
    return await _request("GET", "/api/v1/announcements", token, params={"limit": limit})


# --- Projects -----------------------------------------------------------------


async def assign_employee_to_project(token: str, employee_id: int, project_id: int, role_on_project: str | None) -> dict:
    payload = {"project_id": project_id}
    if role_on_project:
        payload["role_on_project"] = role_on_project
    return await _request("POST", f"/api/v1/employees/{employee_id}/projects", token, json=payload)


async def list_projects_catalog(token: str) -> dict:
    return await _request("GET", "/api/v1/employees/projects/catalog", token)
