"""Natural-language -> safe read-only SQL over a curated, role-scoped schema.

Row/column-level security is enforced structurally: for every request we
open a short-lived read-only SQLite connection and create a set of TEMP
VIEWs scoped to the current user (e.g. "WHERE employee_id = <me>" or
"WHERE manager_id = <me>" baked in as a literal, not a bind parameter the
LLM could omit). The LLM-generated SQL is only ever allowed to reference
those view names -- never the underlying tables -- so even a garbled or
adversarial generation can't reach another employee's row or a forbidden
column such as bank details or salary.
"""

from __future__ import annotations

import sqlite3

from app.core.config import settings
from app.models.employee import Employee
from app.models.enums import Role
from app.services.ai import sql_guardrails
from app.services.ai.llm_client import AIUnavailableError, LLMMessage, complete, complete_json, is_configured
from app.services.ai.permissions import allowed_views_for_role, can_view_raw_sql

VIEW_SQL_TEMPLATES: dict[str, str] = {
    "v_employees_directory": """
        CREATE TEMP VIEW v_employees_directory AS
        SELECT id, name, email, department_id, role, status, joining_date
        FROM employees WHERE status = 'ACTIVE'
    """,
    "v_departments": """
        CREATE TEMP VIEW v_departments AS
        SELECT id, name, location FROM departments
    """,
    "v_projects": """
        CREATE TEMP VIEW v_projects AS
        SELECT id, name, description, status FROM projects
    """,
    "v_skills": """
        CREATE TEMP VIEW v_skills AS
        SELECT id, name FROM skills
    """,
    "v_employee_skills": """
        CREATE TEMP VIEW v_employee_skills AS
        SELECT es.employee_id, e.name AS employee_name, s.name AS skill_name, es.level AS skill_level
        FROM employee_skills es
        JOIN employees e ON e.id = es.employee_id
        JOIN skills s ON s.id = es.skill_id
        WHERE e.status = 'ACTIVE'
    """,
    "v_my_leave_requests": """
        CREATE TEMP VIEW v_my_leave_requests AS
        SELECT id, employee_id, leave_type, start_date, end_date, is_half_day, half_day_period, reason, status, approver_id
        FROM leave_requests WHERE employee_id = {uid}
    """,
    "v_my_leave_balances": """
        CREATE TEMP VIEW v_my_leave_balances AS
        SELECT id, employee_id, leave_type, total, used, remaining
        FROM leave_balances WHERE employee_id = {uid}
    """,
    "v_my_tickets": """
        CREATE TEMP VIEW v_my_tickets AS
        SELECT id, employee_id, assignee_id, title, description, category, priority, status, created_at
        FROM tickets WHERE employee_id = {uid} OR assignee_id = {uid}
    """,
    "v_my_employee_projects": """
        CREATE TEMP VIEW v_my_employee_projects AS
        SELECT ep.employee_id, e.name AS employee_name, p.id AS project_id, p.name AS project_name,
               p.status AS project_status, ep.role_on_project
        FROM employee_projects ep
        JOIN employees e ON e.id = ep.employee_id
        JOIN projects p ON p.id = ep.project_id
        WHERE ep.employee_id = {uid}
    """,
    "v_my_job_history": """
        CREATE TEMP VIEW v_my_job_history AS
        SELECT id, employee_id, designation, business_unit, department, start_date, end_date, is_current
        FROM job_history WHERE employee_id = {uid}
    """,
    "v_team_leave_requests": """
        CREATE TEMP VIEW v_team_leave_requests AS
        SELECT lr.id, lr.employee_id, e.name AS employee_name, lr.leave_type, lr.start_date, lr.end_date,
               lr.is_half_day, lr.half_day_period, lr.reason, lr.status, lr.approver_id
        FROM leave_requests lr
        JOIN employees e ON e.id = lr.employee_id
        WHERE e.manager_id = {uid}
    """,
    "v_team_tickets": """
        CREATE TEMP VIEW v_team_tickets AS
        SELECT t.id, t.employee_id, e.name AS employee_name, t.assignee_id, t.title, t.description,
               t.category, t.priority, t.status, t.created_at
        FROM tickets t
        JOIN employees e ON e.id = t.employee_id
        WHERE e.manager_id = {uid} OR t.assignee_id = {uid}
    """,
    "v_team_employee_projects": """
        CREATE TEMP VIEW v_team_employee_projects AS
        SELECT ep.employee_id, e.name AS employee_name, p.id AS project_id, p.name AS project_name,
               p.status AS project_status, ep.role_on_project
        FROM employee_projects ep
        JOIN employees e ON e.id = ep.employee_id
        JOIN projects p ON p.id = ep.project_id
        WHERE e.manager_id = {uid}
    """,
    "v_all_leave_requests": """
        CREATE TEMP VIEW v_all_leave_requests AS
        SELECT lr.id, lr.employee_id, e.name AS employee_name, lr.leave_type, lr.start_date, lr.end_date,
               lr.is_half_day, lr.half_day_period, lr.reason, lr.status, lr.approver_id
        FROM leave_requests lr
        JOIN employees e ON e.id = lr.employee_id
    """,
    "v_all_tickets": """
        CREATE TEMP VIEW v_all_tickets AS
        SELECT t.id, t.employee_id, e.name AS employee_name, t.assignee_id, t.title, t.description,
               t.category, t.priority, t.status, t.created_at
        FROM tickets t
        JOIN employees e ON e.id = t.employee_id
    """,
    "v_all_employee_projects": """
        CREATE TEMP VIEW v_all_employee_projects AS
        SELECT ep.employee_id, e.name AS employee_name, p.id AS project_id, p.name AS project_name,
               p.status AS project_status, ep.role_on_project
        FROM employee_projects ep
        JOIN employees e ON e.id = ep.employee_id
        JOIN projects p ON p.id = ep.project_id
    """,
}

VIEW_SCHEMA_DESCRIPTIONS: dict[str, str] = {
    "v_employees_directory": "id, name, email, department_id, role, status, joining_date -- active employee directory",
    "v_departments": "id, name, location",
    "v_projects": "id, name, description, status (ONGOING/COMPLETED/ON_HOLD/PLANNED) -- project catalog",
    "v_skills": "id, name -- skill catalog",
    "v_employee_skills": "employee_id, employee_name, skill_name, skill_level -- who knows what skill",
    "v_my_leave_requests": "id, employee_id, leave_type, start_date, end_date, is_half_day, half_day_period, reason, status, approver_id -- ONLY the current user's own leave requests",
    "v_my_leave_balances": "id, employee_id, leave_type, total, used, remaining -- ONLY the current user's own leave balances",
    "v_my_tickets": "id, employee_id, assignee_id, title, description, category, priority, status, created_at -- tickets the current user raised or is assigned to",
    "v_my_employee_projects": "employee_id, employee_name, project_id, project_name, project_status, role_on_project -- ONLY the current user's own project assignments",
    "v_my_job_history": "id, employee_id, designation, business_unit, department, start_date, end_date, is_current -- ONLY the current user's own job history",
    "v_team_leave_requests": "id, employee_id, employee_name, leave_type, start_date, end_date, is_half_day, half_day_period, reason, status, approver_id -- leave requests of the current manager's direct reports",
    "v_team_tickets": "id, employee_id, employee_name, assignee_id, title, description, category, priority, status, created_at -- tickets of the current manager's direct reports, or assigned to them",
    "v_team_employee_projects": "employee_id, employee_name, project_id, project_name, project_status, role_on_project -- project assignments of the current manager's direct reports",
    "v_all_leave_requests": "id, employee_id, employee_name, leave_type, start_date, end_date, is_half_day, half_day_period, reason, status, approver_id -- ALL employees' leave requests (admin only)",
    "v_all_tickets": "id, employee_id, employee_name, assignee_id, title, description, category, priority, status, created_at -- ALL tickets (admin only)",
    "v_all_employee_projects": "employee_id, employee_name, project_id, project_name, project_status, role_on_project -- ALL project assignments (admin only)",
}


def _db_path() -> str:
    return settings.database_url.split("///", 1)[-1]


def _build_schema_context(role: Role) -> str:
    return "\n".join(f"- {view}({VIEW_SCHEMA_DESCRIPTIONS[view]})" for view in allowed_views_for_role(role))


_SQL_SYSTEM_PROMPT = """You are a careful, security-conscious SQL analyst for the NovaWorks HRMS.

Generate a single read-only SQLite SELECT statement that answers the user's
question, using ONLY the views listed below -- never reference any other
table or view, and never use INSERT/UPDATE/DELETE/DDL/PRAGMA. Always keep the
result to a reasonable number of rows (a LIMIT will be enforced automatically
if you omit one).

Available views for this user's role (they already encode who is allowed to
see what -- "v_my_*" and "v_team_*" are pre-filtered to the right rows, you
do not need to add your own permission filtering):
{schema}

If a view name contains "my", it is already scoped to the current user --
do not try to filter it by employee id yourself unless the question asks
about a specific field within their own data.

Respond as JSON only: {{"sql": "<the SELECT statement>"}}
If the question cannot be answered using only the views above (for example
it asks for payroll, bank details, PAN, salary, or another employee's private
data that isn't in any allowed view), respond with:
{{"sql": null, "reason": "<one short sentence explaining why, without confirming or denying that such data exists>"}}
"""

_SUMMARY_SYSTEM_PROMPT = """You summarize SQL query results for an HR chat assistant.
Given the user's original question and the resulting rows (as JSON), write a
concise 1-3 sentence natural-language answer. Do not mention SQL, tables, or
views. If there are zero rows, say so plainly. Never invent data not present
in the rows."""


async def _execute_readonly(sql: str, user_id: int, role: Role) -> list[dict]:
    import anyio

    def _run() -> list[dict]:
        path = _db_path()
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            conn.row_factory = sqlite3.Row
            # Views must be created before query_only is enabled: SQLite's
            # query_only pragma blocks writes to the TEMP database too (not
            # just the read-only main db file), so it has to be turned on
            # only once the role-scoped views already exist -- the main db
            # file itself is still protected throughout by the mode=ro URI.
            for view_name in allowed_views_for_role(role):
                conn.execute(VIEW_SQL_TEMPLATES[view_name].format(uid=user_id))
            conn.execute("PRAGMA query_only = ON;")
            cursor = conn.execute(sql)
            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    return await anyio.to_thread.run_sync(_run)


async def _summarize_rows(question: str, rows: list[dict]) -> str:
    if not rows:
        return "I didn't find any matching records."
    if not is_configured():
        return f"Found {len(rows)} matching record(s). (Set ANTHROPIC_API_KEY for a natural-language summary.)"
    try:
        import json

        preview = rows[:20]
        return (
            await complete(
                system=_SUMMARY_SYSTEM_PROMPT,
                messages=[
                    LLMMessage(
                        role="user",
                        content=f"Question: {question}\n\nRows ({len(rows)} total, showing up to 20):\n{json.dumps(preview, default=str)}",
                    )
                ],
                max_tokens=300,
            )
        ).strip()
    except AIUnavailableError:
        return f"Found {len(rows)} matching record(s)."


async def answer_sql_question(question: str, user: Employee) -> dict:
    role = user.role
    allowed_views = set(allowed_views_for_role(role))
    schema_context = _build_schema_context(role)

    if not is_configured():
        return {
            "answer": "AI SQL generation is not configured (no ANTHROPIC_API_KEY set). Please use the regular HRMS pages for this data, or ask an admin to configure the AI layer.",
            "sql": None,
            "rows": [],
        }

    try:
        generation = await complete_json(
            system=_SQL_SYSTEM_PROMPT.format(schema=schema_context),
            user_prompt=question,
        )
    except (AIUnavailableError, ValueError):
        return {
            "answer": "I couldn't turn that into a safe query. Please rephrase your question.",
            "sql": None,
            "rows": [],
        }

    raw_sql = generation.get("sql")
    if not raw_sql:
        reason = generation.get("reason") or "I don't have access to data that can answer that question."
        return {"answer": reason, "sql": None, "rows": []}

    validation = sql_guardrails.validate_sql(raw_sql, allowed_views=allowed_views, max_rows=settings.ai_sql_max_rows)
    if not validation.is_valid:
        return {
            "answer": f"I can't run that query safely: {validation.reason}",
            "sql": None,
            "rows": [],
        }

    try:
        rows = await _execute_readonly(validation.safe_sql, user.id, role)
    except Exception:
        return {
            "answer": "Something went wrong retrieving that data. Please try rephrasing your question.",
            "sql": None,
            "rows": [],
        }

    # Application-level backstop: cap rows regardless of whether the LIMIT
    # clause guardrail correctly parsed/rewrote the generated SQL's own
    # LIMIT value. This does not depend on sqlglot's Limit AST shape.
    effective_limit = min(settings.ai_sql_max_rows, sql_guardrails.MAX_ROWS_HARD_CAP)
    rows = rows[:effective_limit]

    answer_text = await _summarize_rows(question, rows)
    visible_sql = validation.safe_sql if can_view_raw_sql(role) else None
    return {"answer": answer_text, "sql": visible_sql, "rows": rows}
