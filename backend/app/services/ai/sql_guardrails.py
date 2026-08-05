"""SQL safety checks for the SQL Agent.

Defense in depth, in order:
1. Parse with sqlglot; reject anything that isn't exactly one SELECT (or
   WITH ... SELECT) statement.
2. Reject any statement containing a forbidden (mutating/DDL/pragma) keyword,
   as a textual backstop in case the parser is fooled by dialect quirks.
3. Reject any FROM/JOIN target that is not one of the caller-supplied
   allowed view names -- the SQL Agent only ever exposes pre-scoped SQL
   VIEWs (see sql_agent.py), never raw tables, so this is the real row/
   column-level security boundary, not just a keyword filter.
4. Reject any reference to a forbidden column name, even inside an alias or
   function call, as a final backstop.
5. Cap/enforce a row LIMIT.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "PRAGMA",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "GRANT",
    "REVOKE",
]

# Columns the AI layer must never surface, regardless of role. This backstops
# the view-based scoping in case a view is ever accidentally widened.
FORBIDDEN_COLUMNS = {
    "hashed_password",
    "bank_account_number",
    "bank_account_name",
    "bank_branch",
    "bank_ifsc",
    "bank_name",
    "pan_number",
    "pan_name",
    "pan_dob",
    "date_of_birth",
    "current_salary_usd",
    "profile_photo_path",
    "profile_photo_mime",
    "gross",
    "net",
    "deductions",
    "pf_uan",
    "esi_no",
    "pan",
}

MAX_ROWS_HARD_CAP = 500


@dataclass
class SqlValidationResult:
    is_valid: bool
    reason: str = ""
    safe_sql: str = ""
    referenced_tables: set[str] = field(default_factory=set)


def _contains_forbidden_keyword(sql: str) -> str | None:
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql, re.IGNORECASE):
            return keyword
    return None


def _contains_forbidden_column(sql: str) -> str | None:
    lowered = sql.lower()
    for column in FORBIDDEN_COLUMNS:
        if re.search(rf"\b{re.escape(column)}\b", lowered):
            return column
    return None


def validate_sql(sql: str, allowed_views: set[str], max_rows: int) -> SqlValidationResult:
    sql = sql.strip().rstrip(";")

    if not sql:
        return SqlValidationResult(False, "Empty query.")

    if ";" in sql:
        return SqlValidationResult(False, "Only a single SQL statement is allowed.")

    keyword_hit = _contains_forbidden_keyword(sql)
    if keyword_hit:
        return SqlValidationResult(False, f"Query contains a disallowed keyword: {keyword_hit}.")

    column_hit = _contains_forbidden_column(sql)
    if column_hit:
        return SqlValidationResult(False, "Query references a restricted field that cannot be exposed.")

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except Exception:
        return SqlValidationResult(False, "Could not parse the generated query.")

    if len(statements) != 1 or statements[0] is None:
        return SqlValidationResult(False, "Only a single SQL statement is allowed.")

    statement = statements[0]
    root_type = statement.key.upper()
    if root_type not in {"SELECT", "WITH", "UNION"}:
        return SqlValidationResult(False, "Only read-only SELECT queries are allowed.")

    # A WITH node's inner expression (or a UNION's branches) must ultimately
    # all be SELECTs -- reject anything else (e.g. a CTE wrapping a DML node,
    # which sqlglot would still parse as a distinct expression type).
    select_nodes = list(statement.find_all(exp.Select))
    if not select_nodes:
        return SqlValidationResult(False, "Only read-only SELECT queries are allowed.")
    for forbidden_node_type in (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Command):
        if list(statement.find_all(forbidden_node_type)):
            return SqlValidationResult(False, "Only read-only SELECT queries are allowed.")

    referenced_tables = {table.name.lower() for table in statement.find_all(exp.Table)}
    disallowed = {t for t in referenced_tables if t not in allowed_views}
    if disallowed:
        return SqlValidationResult(
            False,
            f"Query references tables/views that are not permitted for your role: {', '.join(sorted(disallowed))}.",
        )

    # Enforce a LIMIT clause so a broad SELECT can't dump an entire view.
    effective_limit = min(max_rows, MAX_ROWS_HARD_CAP)
    limit_node = statement.find(exp.Limit)
    if limit_node is None:
        safe_sql = f"{sql}\nLIMIT {effective_limit}"
    else:
        try:
            requested = int(limit_node.expression.this)
        except (AttributeError, ValueError, TypeError):
            requested = effective_limit
        if requested > effective_limit:
            safe_sql = re.sub(r"limit\s+\d+", f"LIMIT {effective_limit}", sql, flags=re.IGNORECASE)
        else:
            safe_sql = sql

    return SqlValidationResult(True, safe_sql=safe_sql, referenced_tables=referenced_tables)
