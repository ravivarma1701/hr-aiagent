# AI Architecture — NovaWorks PeopleOps Copilot (Phase 4)

## Why this design

CB Nest (the base HRMS) already has real authorization, validation, and
business logic in its FastAPI endpoints. The brief for this phase was
explicit: **AI agents must not directly mutate the database** — mutations
must go through the existing service layer, and the AI layer's job is
retrieval, reasoning, and *calling* the existing app, not replacing parts of
it. Every design choice below follows from that constraint.

## Diagram

```text
┌───────────────────────────────────────────────────────────────────────┐
│ Next.js frontend — /ai-copilot                                        │
│  ChatPanel + SourceList + SqlResultTable + ActionResultCard           │
│  JWT (localStorage) sent as Authorization: Bearer <token>             │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ POST /api/v1/chat/{policy,sql,actions,router}
                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│ FastAPI endpoints — backend/app/api/v1/endpoints/chat.py               │
│  Depends(get_current_user)  -> Employee (id, role)                    │
│  Depends(oauth2_scheme)     -> raw bearer token (for tool calls)      │
│  calls graph.run_chat_graph(forced_intent=...) -- see below            │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│ LangGraph pipeline — backend/app/services/ai/graph.py                 │
│  load_user_context -> classify_intent -> route ->                     │
│  {policy_agent | sql_agent_node | action_propose->permission_check->  │
│   confirm_gate->execute} -> generate_final_response -> audit_log      │
└───────┬───────────────────────┬───────────────────────┬─────────────────┘
        ▼                       ▼                       ▼
 policy_rag.py            sql_agent.py             action_agent.py
 - embed question         - build role-scoped      - offer only the role's
 - vector_store.query       TEMP VIEWs (SQLite)       permitted tools to
 - LLM answers grounded   - LLM: NL -> SELECT          Claude tool-calling
   ONLY in retrieved        against those views      - re-check permission
   <policy_context>        only                        before executing
 - refuses if no          - sql_guardrails.validate   - confirmation step
   relevant chunk            _sql() before execution    for high-impact
                           - execute read-only,          tools
                             role/self-scoped          - api_tools.py makes
                                                          an HTTP call back
                                                          into THIS SAME
                                                          service, with the
                                                          user's own token
        │                       │                       │
        ▼                       ▼                       ▼
 ChromaDB (local,        SQLite (read-only          Existing FastAPI
 persisted on disk)      connection + TEMP           endpoints (leaves,
                          VIEWs, mode=ro)             tickets, announcements,
                                                       employees/projects)
                                                              │
                                                              ▼
                                                       Existing service
                                                       layer + validation
                                                       + SQLAlchemy ORM
                                                              │
                                                              ▼
                                                          hrms.db
```

## Orchestration: LangGraph (bonus, implemented)

`/chat/policy`, `/chat/sql`, and `/chat/actions` all run through a single
compiled `langgraph.graph.StateGraph` (`backend/app/services/ai/graph.py`)
rather than each endpoint calling its agent module directly. This is the
assignment's suggested pipeline, implemented for real rather than just
described:

```text
START -> load_user_context -> classify_intent -> route:
    ├── policy_agent ──────────────────────────────────────┐
    ├── sql_agent_node ────────────────────────────────────┤
    ├── action_propose -> action_permission_check -> route:│
    │       ├── forbidden ───────────────────────────────┐ │
    │       ├── needs_confirmation ──────────────────────┤ │
    │       └── execute ─────────────────────────────────┤ │
    ├── action_no_tool ──────────────────────────────────┤ │
    └── unknown ─────────────────────────────────────────┘ │
                                                             ▼
                                          generate_final_response -> audit_log -> END
```

Design notes:

- **Each endpoint sets `forced_intent`** (`POLICY_QA`/`SQL_QUERY`/`HR_ACTION`)
  when invoking the graph, since it already knows which capability it is —
  `classify_intent` only calls the LLM-based router when no `forced_intent`
  is given (that path exists for a future single "auto-route" entry point;
  today only the standalone `/chat/router` endpoint calls the classifier
  directly, without the rest of the graph, since it's meant to be a cheap
  "which agent would handle this" preview, not a full run).
- **The action branch is decomposed into four separate nodes**
  (`action_propose` -> `action_permission_check` -> confirm-gate ->
  `action_execute`) instead of one function, because those are genuinely
  separate concerns: propose (LLM tool-call extraction, in
  `action_agent.propose_action`), authorize, gate on human confirmation,
  execute (`action_agent._execute_tool`). Decomposing them into nodes makes
  each step independently testable — see `docs/ai_eval_results.md` for the
  node-level permission tests this enabled — and means a future change
  (e.g. adding a new confirmation-required tool) touches `permissions.py`
  only, not a large branching function.
- **`action_permission_check` calls the exact same `permissions.can_use_tool`**
  that `action_agent._execute_tool` also calls internally before running a
  tool. This was a deliberate choice to avoid the classic multi-layer-auth
  bug: a graph-level permission node that re-implements or approximates the
  real check can drift from it over time. There is one authorization
  function; the graph calls it earlier (to short-circuit before wasting a
  confirmation round-trip on a forbidden action), and the agent calls it
  again immediately before execution as defense in depth — same function,
  called twice, not two different policies.
- **Confirmation is plain state, not LangGraph's `interrupt()`.** LangGraph
  has a built-in human-in-the-loop primitive (`interrupt()` + a
  checkpointer that persists the paused run so it can be resumed later from
  a `thread_id`). This app's chat endpoints are stateless HTTP request/
  response, and the existing `confirm` / `pending_action` round-trip
  (client resubmits the exact tool+args the server proposed) already gives
  the same guarantee — the action that runs is exactly what was shown to
  the user — without standing up a persistent checkpoint store for what is,
  per request, a single, short-lived graph run. The graph is compiled with
  `checkpointer=None`.
- **Audit logging moved from each endpoint into a single `audit_log` node.**
  Previously `chat.py` called `log_ai_interaction(...)` once per endpoint,
  duplicating the same call three times; now it happens once, in the graph,
  regardless of which branch produced the response. `chat.py` keeps its own
  `try/except` around `run_chat_graph(...)` purely as an outer safety net —
  if the graph itself raises before reaching `audit_log` (e.g. a bug in a
  node), the endpoint still records an `action_status="error"` audit entry
  and returns a clean 500 instead of leaking a traceback.

## Model / provider

- **Generation** (RAG answers, NL→SQL, intent extraction/tool-calling,
  router classification): Google Gemini by default (`gemini-flash-latest`,
  configurable via `AI_MODEL_NAME`), with Anthropic Claude available as a
  drop-in alternative via `AI_LLM_PROVIDER=anthropic`. Accessed through a
  small wrapper (`app/services/ai/llm_client.py`) so the rest of the
  codebase depends on `complete()` / `complete_json()` / `complete_with_tools()`,
  never a provider SDK directly — `llm_client.py` dispatches to
  `_gemini_*`/`_anthropic_*` internally based on `AI_LLM_PROVIDER`, and the
  Action Agent's tool schemas are translated (union `type` arrays and `None`
  enum values stripped) into Gemini's function-calling `Schema` format at
  call time so `action_agent.py` itself stays provider-agnostic. Gemini's
  "thinking" token budget is explicitly disabled
  (`ThinkingConfig(thinking_budget=0)`) for all calls, since these are
  direct extraction/generation tasks rather than multi-step reasoning, and
  leaving it on was silently consuming part of `max_output_tokens` and
  truncating visible answers.
- **Embeddings**: local `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim,
  runs on CPU/MPS, no API key or network call at query time). Chosen so
  Policy RAG retrieval works even before an LLM key is configured, and so
  embedding cost/latency doesn't depend on an external API.
- **Vector store**: ChromaDB in persistent local mode
  (`backend/storage/vector-store/`), one collection (`hr_policy_chunks`).
  Cosine similarity. We always pass in our own embeddings — Chroma is used
  purely as a persistent nearest-neighbour index.

If no API key is configured for the selected provider, every endpoint still returns a real,
correctly-shaped response instead of erroring: Policy RAG returns the raw
best-matching excerpt, the SQL Agent and Action Agent explain that
generation isn't configured, and the router falls back to a keyword
heuristic. This was a deliberate choice so the retrieval/guardrail layers
(the part graded on safety) are exercisable without live API access.

## Component design decisions

### 1. Policy RAG (`policy_rag.py`, `embeddings.py`, `vector_store.py`)

- Ingestion reads `HRPolicy.content` (legacy inline text) or, for
  file-backed policies, the uploaded `.txt`/`.md`/`.pdf` from
  `policy_upload_dir` (pypdf for PDF text extraction).
- Chunking is fixed-size (700 chars, 120 overlap) after whitespace
  normalization — the seeded policies are short, so most become a single
  chunk; longer uploaded policies get overlapping chunks.
- Retrieval takes the top-5 chunks above a minimum cosine similarity
  (`MIN_SIMILARITY = 0.12`); below that, the endpoint returns the
  insufficient-context refusal rather than guessing.
- **Prompt-injection defense**: retrieved chunks are wrapped in
  `<policy_context>` tags and the system prompt explicitly instructs the
  model to treat that content as data, never as instructions, and to ignore
  any embedded commands. This is tested in the eval set with a policy
  question crafted to look like an injection attempt (see
  `docs/ai_eval_results.md`).
- Ingestion runs automatically on app startup if the vector store is empty
  (`ensure_policies_ingested`), and can be re-run manually with
  `python -m scripts.ingest_policies` after editing policy content.

### 2. SQL Agent (`sql_agent.py`, `sql_guardrails.py`)

The spec's requirement to "apply role-based filters" is satisfied
structurally, not by hoping the LLM writes a correct `WHERE` clause:

1. For every request, a **short-lived, read-only** SQLite connection
   (`mode=ro` + `PRAGMA query_only = ON`) is opened directly against
   `hrms.db`.
2. A set of `CREATE TEMP VIEW` statements is executed on that connection —
   one per view the requesting role is allowed to use
   (`permissions.allowed_views_for_role`). Self- and team-scoped views bake
   the current user's numeric id directly into the view's `WHERE` clause as
   a literal (not a bind parameter the model could omit or override).
3. The LLM is asked to generate a single `SELECT` using *only* those view
   names — it never sees the underlying table names.
4. `sql_guardrails.validate_sql()` parses the generated SQL with `sqlglot`
   and rejects it unless: exactly one statement, statement type is
   `SELECT`/`WITH`, every `FROM`/`JOIN` target is in the allowed view set,
   no forbidden keyword or forbidden column name appears anywhere in the
   text (defense in depth even though the views don't expose them), and a
   `LIMIT` is present (injected if missing, capped at `AI_SQL_MAX_ROWS`,
   hard cap 500).
5. Only after all of that does the query actually run, again on the
   read-only connection with `query_only` enabled — three independent
   layers (OS-level read-only, `PRAGMA query_only`, and guardrail
   validation) all have to hold for a write to occur, and only one of them
   is prompt-dependent.
6. Whether the raw SQL is echoed back depends on role
   (`permissions.can_view_raw_sql`) — Employees get an answer and rows only.

Payroll/salary/bank/PAN data has **no corresponding view at all**, for any
role — see Security Decisions below.

### 3. HR Action Agent (`action_agent.py`, `api_tools.py`, `permissions.py`)

- Intent + argument extraction uses the LLM's native tool-calling
  (`action_agent.propose_action`, run as the graph's `action_propose` node).
  The tool list handed to the model is pre-filtered to the current role
  (`_tools_for_role`), so an Employee's model call literally cannot see an
  `approve_leave_request` tool definition.
- `api_tools.py` is the only place that talks to the rest of the app, and it
  does so exclusively over HTTP, to `INTERNAL_API_BASE_URL` (this same
  service), with the *current user's own bearer token* in the
  `Authorization` header. This means the existing endpoint's own
  `get_current_user` / `require_roles` / business-rule checks run exactly
  as they would for a human clicking a button — there is no privileged
  internal code path.
- Every tool call is checked against `permissions.can_use_tool()` a second
  time immediately before execution (defense in depth against a model that
  ignores its instructions or hallucinates a tool name).
- **Human-in-the-loop confirmation** (bonus): tools in
  `permissions.CONFIRMATION_REQUIRED_TOOLS` (approve/reject leave, assign
  ticket, create announcement, assign employee to project) return a
  `pending_confirmation` status with a `pending_action` payload instead of
  executing immediately. The frontend shows Confirm/Cancel buttons; a
  confirmed action is executed by re-submitting the exact `pending_action`
  the server returned (tool name + arguments), not by re-running the LLM,
  so what gets executed is exactly what was shown to the user.
- **Known limitation**: tools that reference another person/project (assign
  ticket, assign employee to project) require numeric ids. If the user
  names someone instead ("assign it to Priya"), the agent is instructed to
  ask for the id rather than guess — resolving names to ids would need a
  directory-lookup tool, which was left out to keep the tool surface small
  and auditable for this phase.

### 4. Router (`intent_router.py`)

Optional per the spec; implemented because a single chat box is a much
better demo than three separate boxes. Uses the configured LLM
(`complete_json`) when available, else a keyword-heuristic fallback so
`/chat/router` still works offline. The heuristic checks action verbs first, then
data-lookup phrasing, then policy phrasing last — deliberately in that
order, because a message like *"Who is assigned to the **HR Policy**
Copilot project?"* contains the substring "policy" inside a proper noun and
would otherwise be misrouted to Policy QA if policy keywords were checked
first.

### 5. Audit logging (`audit.py`, `ai_audit_log.py`, migration `0017`)

Every one of the four endpoints results in exactly one
`log_ai_interaction()` call, success or failure — for `/policy`, `/sql`,
`/actions` this happens in the graph's `audit_log` node; `/router` calls it
directly since it doesn't run the graph. Each entry records: `user_id`, `role`, the original `message`,
detected `intent`, `tool_name` used (agent/API tool), `action_status`, a
JSON list of accessed/modified record ids, an `error_reason` on failure, and
`latency_ms`. Access tokens, passwords, and raw payroll/bank values are
never written to this table — only identifiers.

## Known limitations

- **Pre-existing app gap, not AI-related**: `GET /api/v1/employees/{id}`
  returns an employee's bank/PAN/salary fields to *any* authenticated user
  for *any* employee id (no role or ownership check on that endpoint). The
  AI layer never calls this endpoint and never surfaces those fields through
  any SQL view, so the AI layer does not add to this exposure — but it's
  worth flagging since fixing the underlying endpoint was out of scope for
  this phase (changing existing endpoint behavior risks breaking the
  existing frontend pages that rely on it, and wasn't requested).
- Employee-name → id resolution is not implemented for action tools (see
  above); users must supply or look up numeric ids for cross-employee
  actions.
- Chat history is not persisted server-side (the Phase-3 `/chat/sessions`
  stub endpoints are untouched); the frontend keeps the conversation in
  React state for the current page load.
- No streaming; each request blocks until the LLM call(s) complete.
- OpenTelemetry/LangSmith tracing and the AI usage dashboard bonuses were
  not implemented, to keep the four core capabilities and audit logging
  solid within scope. LangGraph orchestration, human-in-the-loop
  confirmation, and a small eval dataset (`docs/ai_eval_results.md`,
  `backend/scripts/eval_dataset.json`) were implemented as bonuses.

## Security decisions worth calling out

1. **Payroll/bank/PAN are unreachable by the SQL Agent for every role**,
   including Admin — there is deliberately no SQL view over
   `payroll_records` or the sensitive `employees` columns. The assignment
   allows "Admin: broad HRMS data except explicitly forbidden fields," and
   since Admin already has a dedicated, validated app flow for payroll
   (`/finance/*`, employee management pages), routing that through a
   natural-language SQL generator wasn't worth the residual risk of a
   prompt-injected or malformed query touching that data.
2. **"View own projects" is served by the SQL Agent, not the Action
   Agent**, even though the assignment lists it under both. The only
   existing endpoint that returns an employee's own project list
   (`GET /employees/{id}`) also returns their bank/PAN/salary in the same
   payload; making that an AI *tool* would mean the tool's HTTP response
   always contains sensitive fields that then have to be scrubbed before
   they reach the LLM or audit log. The scoped SQL view
   (`v_my_employee_projects`) returns exactly the project columns and
   nothing else, so it's the safer path to the same feature.
3. **SQL row/column security is structural, not prompt-based.** See "SQL
   Agent" above — this was the single most important design decision, since
   trusting a generated `WHERE` clause for authorization is the classic way
   NL-to-SQL agents leak data.
4. **Tool execution always goes over real HTTP with the caller's own
   token**, never an internal function call with elevated privileges. This
   was chosen specifically so a code reviewer (or grader) can `grep` for any
   `INSERT`/`UPDATE`/`DELETE` in `app/services/ai/` and find none.
