"""HR Task Automation Agent.

Intent/argument extraction is done via LLM tool-calling: the model is only
ever offered the subset of tools the current user's role is permitted to
use (permissions.py), and every tool call is re-checked against the same
permission map before execution as a second, non-bypassable line of defense.
Execution never touches the database directly -- see api_tools.py.

This module exposes small, independently-callable pieces
(``propose_action``, ``_execute_tool``, ``_describe_proposed_action``)
rather than one monolithic entry point, because they're used as separate
nodes in the LangGraph pipeline (graph.py) -- propose, permission-check,
confirm-gate, and execute are distinct steps in that graph, not one
function call.
"""

from __future__ import annotations

from datetime import date

from app.models.enums import Role
from app.services.ai import api_tools
from app.services.ai.api_tools import ApiToolError
from app.services.ai.llm_client import AIUnavailableError, LLMMessage, complete_with_tools, is_configured
from app.services.ai.permissions import GENERIC_REFUSAL, can_use_tool, TOOL_PERMISSIONS

TOOL_SCHEMAS: dict[str, dict] = {
    "create_leave_request": {
        "name": "create_leave_request",
        "description": "Submit a new leave request for the current user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "leave_type": {"type": "string", "enum": ["CASUAL", "SICK", "EARNED"]},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "reason": {"type": "string"},
                "is_half_day": {"type": "boolean", "default": False},
                "half_day_period": {"type": ["string", "null"], "enum": ["FIRST_HALF", "SECOND_HALF", None]},
            },
            "required": ["leave_type", "start_date", "end_date", "reason"],
        },
    },
    "get_my_leave_balances": {
        "name": "get_my_leave_balances",
        "description": "Get the current user's own leave balances (casual/sick/earned).",
        "input_schema": {"type": "object", "properties": {}},
    },
    "get_my_leave_requests": {
        "name": "get_my_leave_requests",
        "description": "List the current user's own leave requests and their status.",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
    },
    "get_pending_leave_requests": {
        "name": "get_pending_leave_requests",
        "description": "List leave requests awaiting approval (manager/admin only).",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
    },
    "approve_leave_request": {
        "name": "approve_leave_request",
        "description": "Approve a specific pending leave request by its numeric id (manager/admin only).",
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "integer"}},
            "required": ["request_id"],
        },
    },
    "reject_leave_request": {
        "name": "reject_leave_request",
        "description": "Reject a specific pending leave request by its numeric id (manager/admin only).",
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "integer"}},
            "required": ["request_id"],
        },
    },
    "create_ticket": {
        "name": "create_ticket",
        "description": "Create a new support ticket raised by the current user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "category": {"type": "string", "enum": ["IT", "HR", "ONBOARDING"]},
                "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
            },
            "required": ["title", "description", "category", "priority"],
        },
    },
    "get_my_tickets": {
        "name": "get_my_tickets",
        "description": "List tickets the current user raised or is assigned to.",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
    },
    "assign_ticket": {
        "name": "assign_ticket",
        "description": "Assign a ticket to an employee by numeric employee id (manager/admin only). If the user only gave a name, ask them for the numeric id or suggest they look it up first.",
        "input_schema": {
            "type": "object",
            "properties": {"ticket_id": {"type": "integer"}, "assignee_id": {"type": "integer"}},
            "required": ["ticket_id", "assignee_id"],
        },
    },
    "update_ticket_status": {
        "name": "update_ticket_status",
        "description": "Update a ticket's status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["OPEN", "IN_PROGRESS", "RESOLVED"]},
            },
            "required": ["ticket_id", "status"],
        },
    },
    "create_announcement": {
        "name": "create_announcement",
        "description": "Post a company/team announcement (manager/admin only).",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            "required": ["title", "body"],
        },
    },
    "list_announcements": {
        "name": "list_announcements",
        "description": "List recent announcements.",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}},
    },
    "assign_employee_to_project": {
        "name": "assign_employee_to_project",
        "description": "Assign an employee (by numeric id) to a project (by numeric id) (manager/admin only). If the user only gave names, ask for the numeric ids or suggest looking them up first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer"},
                "project_id": {"type": "integer"},
                "role_on_project": {"type": ["string", "null"]},
            },
            "required": ["employee_id", "project_id"],
        },
    },
    "list_projects_catalog": {
        "name": "list_projects_catalog",
        "description": "List the project catalog (manager/admin only).",
        "input_schema": {"type": "object", "properties": {}},
    },
}


EXECUTORS = {
    "create_leave_request": lambda token, args: api_tools.create_leave_request(token, payload=args),
    "get_my_leave_balances": lambda token, args: api_tools.get_my_leave_balances(token),
    "get_my_leave_requests": lambda token, args: api_tools.get_my_leave_requests(token, **args),
    "get_pending_leave_requests": lambda token, args: api_tools.get_pending_leave_requests(token, **args),
    "approve_leave_request": lambda token, args: api_tools.approve_leave_request(token, **args),
    "reject_leave_request": lambda token, args: api_tools.reject_leave_request(token, **args),
    "create_ticket": lambda token, args: api_tools.create_ticket(token, payload=args),
    "get_my_tickets": lambda token, args: api_tools.get_my_tickets(token, **args),
    "assign_ticket": lambda token, args: api_tools.assign_ticket(token, **args),
    "update_ticket_status": lambda token, args: api_tools.update_ticket_status(token, **args),
    "create_announcement": lambda token, args: api_tools.create_announcement(token, **args),
    "list_announcements": lambda token, args: api_tools.list_announcements(token, **args),
    "assign_employee_to_project": lambda token, args: api_tools.assign_employee_to_project(token, **args),
    "list_projects_catalog": lambda token, args: api_tools.list_projects_catalog(token),
}


_SYSTEM_PROMPT = """You are the NovaWorks HR Task Automation Agent, acting on
behalf of a logged-in {role} user. Today's date is {today}.

You may call at most one tool per message, chosen from the tools provided to
you -- that list has already been filtered to what this user's role is
allowed to do, so if the right tool isn't offered, the user is not permitted
to do that action. In that case, reply with plain text explaining you cannot
do that (do not apologize excessively, do not explain the underlying
permission system, do not confirm or deny whether the target record exists).

Rules:
- Resolve relative dates ("tomorrow", "next Monday") into YYYY-MM-DD using today's date.
- If required details are missing or ambiguous, ask a short clarifying
  question in plain text instead of guessing or calling a tool with made-up
  values.
- Never invent employee ids, ticket ids, or project ids. If the user names a
  person or project instead of giving a numeric id, ask them for the id or
  suggest they look it up first.
- If the user's message clearly asks for one specific action (e.g. approve,
  reject, assign) but you are missing a required id for THAT action, do not
  call a different tool as a substitute -- especially not a lookup/list
  tool. Reply in plain text instead: say which id you need, and if it would
  help, offer to look up the relevant records first so the user can tell
  you which one they mean. Only call the lookup tool after the user agrees
  to that -- never as a silent substitute for the action they actually asked for.
- If the user's message is not an HR action at all, reply in plain text
  that you handle HR task automation and suggest they rephrase.
"""


def _tools_for_role(role: Role) -> list[dict]:
    allowed = [name for name, roles in TOOL_PERMISSIONS.items() if role in roles]
    return [TOOL_SCHEMAS[name] for name in allowed if name in TOOL_SCHEMAS]


def _describe_proposed_action(tool_name: str, args: dict) -> str:
    descriptions = {
        "approve_leave_request": f"I found pending leave request #{args.get('request_id')}. Confirm approval?",
        "reject_leave_request": f"I found pending leave request #{args.get('request_id')}. Confirm rejection?",
        "assign_ticket": f"This will assign ticket #{args.get('ticket_id')} to employee #{args.get('assignee_id')}. Confirm?",
        "create_announcement": f"This will post an announcement titled \"{args.get('title')}\" visible to everyone. Confirm?",
        "assign_employee_to_project": f"This will assign employee #{args.get('employee_id')} to project #{args.get('project_id')}. Confirm?",
    }
    return descriptions.get(tool_name, "This action needs your confirmation before I proceed. Confirm?")


def _summarize_result(tool_name: str, args: dict, result) -> str:
    if tool_name == "create_leave_request" and isinstance(result, dict):
        return (
            f"Your {result.get('leave_type', '').title()} leave request for "
            f"{result.get('start_date')} to {result.get('end_date')} has been submitted. "
            f"Status: {result.get('status', 'PENDING').title()}."
        )
    if tool_name == "approve_leave_request" and isinstance(result, dict):
        return f"Leave request #{result.get('id')} has been approved."
    if tool_name == "reject_leave_request" and isinstance(result, dict):
        return f"Leave request #{result.get('id')} has been rejected."
    if tool_name == "create_ticket" and isinstance(result, dict):
        return f"Ticket #{result.get('id')} \"{result.get('title')}\" has been created (status: {result.get('status')})."
    if tool_name == "assign_ticket" and isinstance(result, dict):
        return f"Ticket #{result.get('id')} has been assigned to employee #{result.get('assignee_id')}."
    if tool_name == "update_ticket_status" and isinstance(result, dict):
        return f"Ticket #{result.get('id')} status updated to {result.get('status')}."
    if tool_name == "create_announcement" and isinstance(result, dict):
        return f"Announcement \"{result.get('title')}\" has been posted."
    if tool_name == "assign_employee_to_project" and isinstance(result, dict):
        return f"Employee #{result.get('employee_id')} has been assigned to project #{result.get('project_id')}."
    if tool_name in {"get_my_leave_balances", "get_my_leave_requests", "get_pending_leave_requests", "get_my_tickets", "list_announcements", "list_projects_catalog"}:
        if isinstance(result, list):
            return f"Found {len(result)} matching record(s)." if result else "I didn't find any matching records."
        return "Here's what I found."
    return "Done."


async def _execute_tool(tool_name: str, args: dict, role: Role, access_token: str) -> dict:
    permission = can_use_tool(role, tool_name)
    if not permission.allowed:
        return {"answer": permission.reason or GENERIC_REFUSAL, "action": tool_name, "status": "forbidden", "result": None, "pending_action": None}

    executor = EXECUTORS.get(tool_name)
    if executor is None:
        return {"answer": "That action isn't available yet.", "action": tool_name, "status": "failed", "result": None, "pending_action": None}

    try:
        result = await executor(access_token, args)
    except ApiToolError as exc:
        return {"answer": f"That didn't go through: {exc.message}", "action": tool_name, "status": "failed", "result": None, "pending_action": None}
    except TypeError:
        return {
            "answer": "I didn't have enough information to complete that action. Could you provide more details?",
            "action": tool_name,
            "status": "failed",
            "result": None,
            "pending_action": None,
        }

    return {"answer": _summarize_result(tool_name, args, result), "action": tool_name, "status": "completed", "result": result, "pending_action": None}


async def propose_action(message: str, role: Role, history: list[LLMMessage] | None = None) -> dict:
    """LLM tool-call extraction only -- no permission check, no execution.

    `history` is the prior conversation turns (if any), oldest first, NOT
    including `message` itself. It's what lets a reply like "its a casual
    leave" resolve an earlier clarifying question ("which leave type?")
    instead of being interpreted as a brand new, context-free message.

    Returns {"text": str, "tool_name": str | None, "args": dict}. The
    caller (graph.py) is responsible for the permission check, the
    confirmation gate, and execution -- each is a distinct node in the
    LangGraph pipeline so they can be tested and audited independently.
    """
    if not is_configured():
        return {
            "text": "AI task automation is not configured (no LLM API key set). Please use the regular HRMS pages for this action, or ask an admin to configure the AI layer.",
            "tool_name": None,
            "args": {},
        }

    tools = _tools_for_role(role)
    system = _SYSTEM_PROMPT.format(role=role.value, today=date.today().isoformat())
    messages = [*(history or []), LLMMessage(role="user", content=message)]

    try:
        generation = await complete_with_tools(system=system, messages=messages, tools=tools)
    except AIUnavailableError:
        return {"text": "AI task automation is currently unavailable.", "tool_name": None, "args": {}}

    if not generation["tool_calls"]:
        return {"text": generation["text"] or "I'm not sure how to help with that.", "tool_name": None, "args": {}}

    call = generation["tool_calls"][0]
    return {"text": generation["text"], "tool_name": call["name"], "args": call["input"] or {}}
