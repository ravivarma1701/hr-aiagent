"""Central RBAC map for the AI layer.

Mirrors the authorization rules already enforced by the existing FastAPI
endpoints (see docs/ai_permissions_matrix.md) rather than inventing a new
policy. This module is the single place the Action Agent and SQL Agent
consult before doing anything, so refusals are consistent everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import Role

GENERIC_REFUSAL = "You do not have permission to do that."


@dataclass(frozen=True)
class PermissionResult:
    allowed: bool
    reason: str = ""


# --- HR Action Agent: tool_name -> roles allowed to invoke it -------------
TOOL_PERMISSIONS: dict[str, set[Role]] = {
    "create_leave_request": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "get_my_leave_balances": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "get_my_leave_requests": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "get_pending_leave_requests": {Role.MANAGER, Role.ADMIN},
    "approve_leave_request": {Role.MANAGER, Role.ADMIN},
    "reject_leave_request": {Role.MANAGER, Role.ADMIN},
    "create_ticket": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "get_my_tickets": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "assign_ticket": {Role.MANAGER, Role.ADMIN},
    "update_ticket_status": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "create_announcement": {Role.MANAGER, Role.ADMIN},
    "list_announcements": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "assign_employee_to_project": {Role.MANAGER, Role.ADMIN},
    "list_projects_catalog": {Role.MANAGER, Role.ADMIN},
}

# Actions that mutate shared/other-people's state and should be confirmed
# before execution (bonus: human-in-the-loop).
CONFIRMATION_REQUIRED_TOOLS: set[str] = {
    "approve_leave_request",
    "reject_leave_request",
    "assign_ticket",
    "create_announcement",
    "assign_employee_to_project",
}

# --- SQL Agent: logical view -> roles allowed to select from it -----------
# Every view is created fresh per request as a role-scoped SQLite TEMP VIEW
# (see sql_agent.py) -- these names are the ONLY tables/views the generated
# SQL is allowed to reference. Raw tables (employees, leave_requests,
# tickets, payroll_records, ...) are never exposed directly.
SQL_VIEW_PERMISSIONS: dict[str, set[Role]] = {
    # Non-sensitive directory/catalog data, same for every role.
    "v_employees_directory": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "v_departments": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "v_projects": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "v_skills": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "v_employee_skills": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    # Self-scoped (hardcoded to the requesting user's employee id).
    "v_my_leave_requests": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "v_my_leave_balances": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "v_my_tickets": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "v_my_employee_projects": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    "v_my_job_history": {Role.EMPLOYEE, Role.MANAGER, Role.ADMIN},
    # Team-scoped (direct reports of the requesting manager/admin).
    "v_team_leave_requests": {Role.MANAGER, Role.ADMIN},
    "v_team_tickets": {Role.MANAGER, Role.ADMIN},
    "v_team_employee_projects": {Role.MANAGER, Role.ADMIN},
    # Org-wide (admin only).
    "v_all_leave_requests": {Role.ADMIN},
    "v_all_tickets": {Role.ADMIN},
    "v_all_employee_projects": {Role.ADMIN},
}

# Employee/Manager may see natural-language answers only; Admin (and
# optionally Manager) may also see the generated SQL itself.
ROLES_ALLOWED_RAW_SQL: set[Role] = {Role.MANAGER, Role.ADMIN}


def can_use_tool(role: Role, tool_name: str) -> PermissionResult:
    allowed_roles = TOOL_PERMISSIONS.get(tool_name)
    if allowed_roles is None:
        return PermissionResult(False, "Unknown action.")
    if role in allowed_roles:
        return PermissionResult(True)
    return PermissionResult(False, GENERIC_REFUSAL)


def can_query_view(role: Role, view_name: str) -> bool:
    allowed_roles = SQL_VIEW_PERMISSIONS.get(view_name)
    return bool(allowed_roles and role in allowed_roles)


def allowed_views_for_role(role: Role) -> list[str]:
    return [view for view, roles in SQL_VIEW_PERMISSIONS.items() if role in roles]


def requires_confirmation(tool_name: str) -> bool:
    return tool_name in CONFIRMATION_REQUIRED_TOOLS


def can_view_raw_sql(role: Role) -> bool:
    return role in ROLES_ALLOWED_RAW_SQL
