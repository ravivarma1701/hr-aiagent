# AI Permissions Matrix

The AI layer does not define its own authorization model — it mirrors the
authorization already enforced by the existing FastAPI endpoints, and adds
one additional layer of its own (role-scoped SQL views) for the one place
where the AI has more reach than any single existing endpoint: ad-hoc data
lookups.

Single source of truth in code: `backend/app/services/ai/permissions.py`.

## Capability matrix

| AI Capability | Employee | Manager | Admin | Enforced by |
|---|---|---|---|---|
| Ask HR policy questions | Yes | Yes | Yes | No restriction (policy Q&A is public to all logged-in users, matching `GET /hr-policies`) |
| Ask own leave balance | Yes | Yes | Yes | SQL view `v_my_leave_balances` (hardcoded `employee_id = <self>`) |
| Ask another employee's leave balance | No | Team only | Yes | Manager: `v_team_leave_requests`/balances scoped to `manager_id = <self>`. Admin: `v_all_leave_requests`. No view ever exposes another employee's balance to an Employee. |
| View own project assignments | Yes | Yes | Yes | SQL view `v_my_employee_projects` |
| View all project assignments | No | Limited (team) | Yes | Manager: `v_team_employee_projects` (direct reports only). Admin: `v_all_employee_projects`. Employee has no unscoped project view. |
| Search employees by skill | Limited (directory-only) | Yes | Yes | `v_employee_skills`/`v_employees_directory` contain no sensitive columns, so this is safe for every role; "limited" for Employee just means the same non-sensitive columns everyone gets, no elevated fields. |
| Generate SQL over HR data | Limited (self-scoped views only) | Limited (self+team views) | Broad (org-wide views, still no forbidden columns) | `permissions.allowed_views_for_role()` — the *set* of views offered to the NL→SQL generator differs per role; the LLM cannot query outside that set (`sql_guardrails.validate_sql` rejects unknown table/view names). |
| View raw SQL | No | Yes | Yes | `permissions.can_view_raw_sql()`; Employee responses never include the `sql` field (only `answer`/`rows`). |
| Create own leave request | Yes | Yes | Yes | `create_leave_request` tool → `POST /leaves/requests` (existing endpoint takes leave for the authenticated user only) |
| Approve/reject leave | No | Yes | Yes | `approve_leave_request`/`reject_leave_request` tools, gated by `TOOL_PERMISSIONS`; existing endpoint re-checks role independently |
| Create ticket | Yes | Yes | Yes | `create_ticket` tool |
| Assign/update ticket | No (assign) / Yes (own status) | Yes | Yes | `assign_ticket` gated to Manager/Admin; `update_ticket_status` is open to all roles because the *existing* endpoint already restricts it to the ticket's owner/assignee/manager/admin |
| Create announcement | No | Yes | Yes | `create_announcement` tool, gated + requires confirmation |
| Assign employee to project | No | Yes | Yes | `assign_employee_to_project` tool, gated + requires confirmation |
| Access payroll data | Own only (via existing app, not via AI) or blocked | Restricted | Admin only (still not via AI) | The SQL Agent has **no view at all** over `payroll_records` or salary/bank/PAN columns, for any role — see Security Decisions in `ai_architecture.md` |
| Access bank/PAN/password fields | No | No | No | Hard-blocked in `sql_guardrails.FORBIDDEN_COLUMNS` (defense in depth) and structurally absent from every SQL view (primary control) |

## HR Action Agent tool → role map

Source: `permissions.TOOL_PERMISSIONS` in `backend/app/services/ai/permissions.py`.

| Tool | Employee | Manager | Admin | Confirmation required |
|---|---|---|---|---|
| `create_leave_request` | ✅ | ✅ | ✅ | No |
| `get_my_leave_balances` | ✅ | ✅ | ✅ | No |
| `get_my_leave_requests` | ✅ | ✅ | ✅ | No |
| `get_pending_leave_requests` | ❌ | ✅ | ✅ | No |
| `approve_leave_request` | ❌ | ✅ | ✅ | **Yes** |
| `reject_leave_request` | ❌ | ✅ | ✅ | **Yes** |
| `create_ticket` | ✅ | ✅ | ✅ | No |
| `get_my_tickets` | ✅ | ✅ | ✅ | No |
| `assign_ticket` | ❌ | ✅ | ✅ | **Yes** |
| `update_ticket_status` | ✅ | ✅ | ✅ | No (existing endpoint scopes to owner/assignee/manager/admin) |
| `create_announcement` | ❌ | ✅ | ✅ | **Yes** |
| `list_announcements` | ✅ | ✅ | ✅ | No |
| `assign_employee_to_project` | ❌ | ✅ | ✅ | **Yes** |
| `list_projects_catalog` | ❌ | ✅ | ✅ | No |

Two independent checks gate every tool call: (1) the tool list offered to the
LLM is pre-filtered by role, and (2) `permissions.can_use_tool()` is checked
again right before execution, so a hallucinated or out-of-list tool name
from the model is refused rather than executed.

## SQL Agent view → role map

Source: `permissions.SQL_VIEW_PERMISSIONS`. Full view SQL lives in
`backend/app/services/ai/sql_agent.py::VIEW_SQL_TEMPLATES`.

| View | Employee | Manager | Admin | Scope |
|---|---|---|---|---|
| `v_employees_directory` | ✅ | ✅ | ✅ | active employees, non-sensitive columns |
| `v_departments` | ✅ | ✅ | ✅ | all |
| `v_projects` | ✅ | ✅ | ✅ | project catalog |
| `v_skills` | ✅ | ✅ | ✅ | skill catalog |
| `v_employee_skills` | ✅ | ✅ | ✅ | who knows what skill |
| `v_my_leave_requests` / `v_my_leave_balances` / `v_my_tickets` / `v_my_employee_projects` / `v_my_job_history` | ✅ (self only) | ✅ (self only) | ✅ (self only) | hardcoded `= <requesting user's id>` |
| `v_team_leave_requests` / `v_team_tickets` / `v_team_employee_projects` | ❌ | ✅ (direct reports only) | ✅ (direct reports only) | hardcoded `manager_id = <requesting user's id>` |
| `v_all_leave_requests` / `v_all_tickets` / `v_all_employee_projects` | ❌ | ❌ | ✅ | unscoped |

No view — at any role — ever selects `hashed_password`, `bank_*`, `pan_*`,
`current_salary_usd`, `date_of_birth`, `profile_photo_*`, or any
`payroll_records` column. This is why payroll/bank/PAN questions are refused
regardless of role: the data is not reachable through the SQL Agent at all,
not merely filtered at the LLM-prompt level.

## Refusal style

Per the assignment's refusal requirement, refusals never confirm or deny
that a specific restricted record exists:

- Good: *"You do not have permission to do that."*
- Avoided: *"I found Rahul's leave request, but I can't show it to you."*

`permissions.GENERIC_REFUSAL` is the single refusal string used across the
Action Agent and SQL Agent for permission failures.
