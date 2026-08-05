# CB Nest Product Requirement Document

## 1. Business Context

CB Nest is a high-fidelity HRMS learning platform designed for engineers who want to build AI features on top of realistic enterprise workflows without creating base HR modules from scratch.

The system intentionally includes end-to-end operational complexity: employee lifecycle, attendance, leave approvals, payroll visibility, employee documents, HR policies, tickets, announcements, polls, and notifications.

The current product is Docker-first and learner-friendly, with stable REST contracts and AI-stub endpoints under `/api/v1/chat/*`.

## 2. Target User Persona

### Primary Persona: The Engineer

- Mid-to-senior software engineer with full-stack background (Next.js/React + Python/FastAPI).
- Transitioning into AI engineering (RAG, copilots, workflow agents).
- Wants to prototype AI features quickly on top of working business flows.
- Comfortable with APIs, SQL, Docker, and local development.

### Product End Users (Role Model)

| Role | Product Usage |
|---|---|
| `ADMIN` | Full control: employee lifecycle, payroll/docs upload, approvals, policy management |
| `MANAGER` | Team operations: approvals, ticket handling, employee doc uploads, policy uploads |
| `EMPLOYEE` | Self-service: profile, attendance, leaves, my documents, finance, tickets, engagement |

## 3. Success Metrics (KPIs)

| KPI | Target | Measurement |
|---|---|---|
| Onboarding Time | App running in <= 15 minutes | Fresh clone setup timing |
| Workflow Completeness | Employee create/edit/reactivate works end-to-end | Manual test checklist |
| Leave Accuracy | Balances and request states remain consistent | Approve/reject scenario validation |
| Document Usability | Search + view/download flows work in My Docs and HR Policies | UI and API checks |
| Payroll Security | Payslips are password-protected PDF using DOB | Download and open verification |
| API Stability | Standard response envelope across modules | API contract review |

## 4. Feature Sets

Features are organized around implemented modules and available API contracts.

### 4.1 Core Employee Management

- Employee Directory with search, department/location filters, pagination, and detail panel.
- Add/Edit employee using dedicated onboarding screen (`/employees/new`).
- Employee reactivation by email when an inactive record exists.
- Role and status lifecycle controls (`ACTIVE`/`INACTIVE`).
- Profile management with editable fields and profile photo upload.
- Job history timeline support via `job_history`.

### 4.2 Time, Attendance, and Leave

- Attendance logs with clock in/out, status, and work mode.
- Leave balances (`CASUAL`, `SICK`, `EARNED`) with defaults for new users.
- Leave request types:
  - Full day
  - First half
  - Second half
- Leave approval/rejection by `ADMIN`/`MANAGER`.

### 4.3 Finance and Payroll

- Finance profile view (salary, bank, PAN/PF/ESI context).
- Payroll history by month from `payroll_records`.
- Payslip month selection in `MM-YY` UX format.
- Payslip view/download from Finance and My Documents.
- Payslip PDFs are password-protected using employee DOB (`DD-MM-YY`).

### 4.4 Documents and Policies

- My Documents:
  - User upload (`.pdf`, `.txt`, `.md`, `.doc`, `.docx`)
  - Search with suggestions
  - View/download
  - Delete control only for eligible uploaded `OTHER` docs
  - Newest-first ordering
- System-generated virtual docs in My Documents:
  - Appointment Letter
  - Monthly Payslip
  - Tax Statement
- Employee document upload by `ADMIN`/`MANAGER`:
  - `APPOINTMENT`, `TAX`, `OTHER` via generic endpoint
  - `PAYSLIP` via dedicated payslip endpoint
- HR Policies:
  - Upload by `ADMIN`/`MANAGER`
  - Search suggestions
  - View/download
  - Newest-first listing

### 4.5 Projects and Assignments

- Project catalog management:
  - Create project
  - Update project status (`ONGOING`, `PLANNED`, `ON_HOLD`, `COMPLETED`)
  - List projects with status filters
- Employee-project assignment management:
  - Assign project
  - Update role on project
  - Remove assignment
- Dedicated frontend page for project assignment workflows (`/employees/projects`).

### 4.6 Organization and Directory Intelligence

- Organization tree endpoint and UI (`/organization`) based on reporting lines.
- Global employee search in topbar.
- Employee details include active project assignments.

### 4.7 Engagement and Ticketing

- Announcements creation and feed.
- Poll creation, voting, and results.
- Tickets with assignment and status updates.
- Onboarding tasks linked to tickets (`onboarding_tasks` table + APIs).

### 4.8 Notifications (Client Aggregated)

- Notification bell composes events from multiple APIs:
  - Announcements
  - Polls
  - Ticket assignment and status changes
  - Leave decision updates
  - Document uploads by others
- Read/dismiss state persisted in browser local storage.
- Self-uploaded documents are excluded from "new document" notifications.

### 4.9 Skills Data Layer

- `skills` and `employee_skills` are present in schema and seed data.
- Seed creates multiple normalized skills and employee-skill mappings with levels.
- Current release: no dedicated skills CRUD endpoints/UI yet; available for future module expansion.

### 4.10 AI Readiness

- Chat endpoints exposed as contract stubs:
  - `POST /api/v1/chat/sessions`
  - `POST /api/v1/chat/sessions/{id}/messages`
- Both currently return `501` with structured error response.

## 5. Technical Architecture

### 5.1 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, Tailwind CSS, shadcn/ui, lucide-react |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | SQLite (`backend/storage/hrms.db`) |
| Migration | Alembic |
| Auth | JWT with role-based authorization |
| Dev Setup | Docker Compose |

### 5.2 Data Flow

1. Frontend sends JWT-authenticated REST calls to FastAPI (`/api/v1/*`).
2. FastAPI validates with Pydantic schemas.
3. SQLAlchemy async layer persists/fetches from SQLite.
4. API returns standard success/error envelope.

Standard response envelope:

- Success: `{ "success": true, "data": ..., "error": null }`
- Error: `{ "success": false, "data": null, "error": { "code": "...", "message": "..." } }`

### 5.3 Core Data Model (Current)

Full schema snapshot: `db_tables_samples.md`

| Entity/Table | Key Notes |
|---|---|
| `employees` | Master profile, role, status, finance/statutory fields |
| `departments` | Department and office location |
| `job_history` | Designation history and current role tracking |
| `skills` | Skill dictionary with normalized names |
| `employee_skills` | Employee-to-skill mapping with proficiency level |
| `projects` | Project catalog with status lifecycle |
| `employee_projects` | Employee-to-project assignment + role on project |
| `attendance_logs` | Daily attendance with status/work mode |
| `leave_balances` | Leave counters by type |
| `leave_requests` | Leave workflow state and approver linkage |
| `payroll_records` | Payroll month-level gross/net/deduction records |
| `employee_documents` | Employee document metadata and storage reference |
| `hr_policies` | Policy metadata/content/storage reference |
| `tickets` | Ticket lifecycle and assignment |
| `onboarding_tasks` | Task checklist records linked to tickets |
| `announcements` | Broadcast communication records |
| `polls` | Poll questions and options |
| `poll_responses` | Poll voting records |
| `holidays` | Organization holiday calendar entries |
| `alembic_version` | Migration version state |

#### 5.3.1 Table Columns (Reference)

Full column-level definition (types + constraints): `db_tables_samples.md`

| Table | Columns |
|---|---|
| `employees` | `id`, `name`, `email`, `hashed_password`, `department_id`, `manager_id`, `role`, `status`, `joining_date`, `phone`, `address`, `blood_type`, `occupancy`, `date_of_birth`, `profile_photo_path`, `profile_photo_mime`, `current_salary_usd`, `bank_name`, `bank_account_number`, `bank_account_name`, `bank_branch`, `bank_ifsc`, `pan_number`, `pan_name`, `pan_dob` |
| `departments` | `id`, `name`, `location` |
| `job_history` | `id`, `employee_id`, `designation`, `business_unit`, `department`, `start_date`, `end_date`, `is_current` |
| `skills` | `id`, `name`, `normalized_name` |
| `employee_skills` | `id`, `employee_id`, `skill_id`, `level` |
| `projects` | `id`, `name`, `description`, `status` |
| `employee_projects` | `id`, `employee_id`, `project_id`, `role_on_project` |
| `attendance_logs` | `id`, `employee_id`, `date`, `clock_in`, `clock_out`, `status`, `work_mode`, `punctuality` |
| `leave_balances` | `id`, `employee_id`, `leave_type`, `total`, `used`, `remaining` |
| `leave_requests` | `id`, `employee_id`, `leave_type`, `start_date`, `end_date`, `reason`, `is_half_day`, `half_day_period`, `status`, `approver_id` |
| `payroll_records` | `id`, `employee_id`, `month`, `gross`, `deductions`, `net`, `pan`, `pf_uan`, `esi_no` |
| `employee_documents` | `id`, `employee_id`, `uploaded_by`, `title`, `document_type`, `original_filename`, `file_path`, `mime_type`, `size_bytes`, `checksum`, `created_at` |
| `hr_policies` | `id`, `title`, `content`, `category`, `embedding`, `original_filename`, `file_path`, `mime_type`, `size_bytes`, `uploaded_by`, `checksum`, `created_at` |
| `tickets` | `id`, `employee_id`, `assignee_id`, `title`, `description`, `category`, `priority`, `status`, `created_at` |
| `onboarding_tasks` | `id`, `ticket_id`, `task_name`, `is_completed`, `due_date` |
| `announcements` | `id`, `title`, `body`, `author_id`, `created_at` |
| `polls` | `id`, `question`, `options`, `created_by`, `created_at` |
| `poll_responses` | `id`, `poll_id`, `employee_id`, `option_index` |
| `holidays` | `id`, `name`, `date` |
| `alembic_version` | `version_num` |

### 5.4 API Standards

- Versioned paths: `/api/v1/*`
- OpenAPI docs: `/docs`, `/redoc`
- Resource-based route naming
- Pagination for list APIs
- Semantic error codes and HTTP status mapping

## 6. Local Development Setup

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Git

### Quick Start

1. Clone and configure env:

   `git clone <repo-url> && cd HRMS`

   `cp backend/.env.example backend/.env` (or PowerShell equivalent)

2. Build and start:

   `docker-compose up -d --build`

3. Run migrations:

   `docker-compose exec api alembic -c alembic.ini upgrade head`

4. Seed data:

   `docker-compose exec api python scripts/seed.py`

5. Open app:

   `http://localhost:3000`

### Default Users

- Admin: `admin@mock-hrms.dev` / `password123`
- Manager: `manager@mock-hrms.dev` / `password123`
- Employee: `employee@mock-hrms.dev` / `password123`

Optional one-time utility:

- `docker compose exec api python scripts/migrate_payslips_to_encrypted_pdf.py`

## 7. Phased Implementation Plan

### Phase 1: Foundation (Completed)

- Core scaffold: FastAPI + Next.js + Docker + migrations
- JWT auth and role-aware navigation/access
- Employee directory, profile baseline, attendance baseline
- README/setup and seed workflows

### Phase 2: Core HR Workflows (Completed)

- Leave request and approval flow with balances
- Tickets, announcements, polls, team calendar
- Employee lifecycle improvements (active/deactivate/reactivate)

### Phase 3: Finance, Documents, UX Hardening (Completed)

- Finance payroll summary and statutory details
- Password-protected PDF payslips by DOB
- Employee document management (self + admin/manager upload paths)
- HR policy library improvements (search suggestions, newest-first, view/download)
- Notification behavior refinement (sender/receiver correctness)

### Phase 4: AI Feature Integration (Planned)

- HR policy RAG assistant
- Payroll explanation assistant
- Leave compliance reasoning assistant
- Multi-agent conversational workflows
- AI action auditability

## 8. Non-Functional Requirements

### 8.1 Security

- JWT-based protected API access
- Role-based access enforcement for privileged actions
- Validation through Pydantic and safe ORM-based DB access

### 8.2 Performance

- Pagination on list endpoints
- Efficient client-side filtering for document/policy search
- Avoid unbounded large payload flows in core modules

### 8.3 Scalability

- Containerized services via Docker Compose
- Versioned API paths for safe contract evolution
- Schema migration path via Alembic

### 8.4 Observability and Reliability

- Health endpoints: `/health`, `/api/v1/health`
- Consistent API envelope for frontend error handling
- Migration + seed repeatability for learner environments

## 9. Engineering Task Breakdown (Current)

| ID | Task | Area | Priority | Status |
|---|---|---|---|---|
| HRMS-001 | Platform scaffold (Next.js + FastAPI + Docker) | Core | P0 | Completed |
| HRMS-002 | Auth + RBAC route protection | Auth | P0 | Completed |
| HRMS-003 | Employee directory, onboarding edit flow, lifecycle controls | Employee | P1 | Completed |
| HRMS-004 | Attendance + leave balances + leave approval workflow | Attendance/Leave | P1 | Completed |
| HRMS-005 | Finance profile + payroll summary endpoints and UI | Finance | P1 | Completed |
| HRMS-006 | Payslip PDF generation/encryption and monthly retrieval logic | Finance | P1 | Completed |
| HRMS-007 | My Documents upload/search/view/download/delete rules | Documents | P1 | Completed |
| HRMS-008 | Admin/Manager employee document upload (incl. payslip path) | Documents | P1 | Completed |
| HRMS-009 | HR policies upload/search/view/download with ordering | Policies | P2 | Completed |
| HRMS-010 | Project catalog + employee project assignment workflows | Projects | P1 | Completed |
| HRMS-011 | Announcements, polls, tickets, onboarding tasks | Engagement | P2 | Completed |
| HRMS-012 | Org tree endpoint + frontend visualization | Org | P2 | Completed |
| HRMS-013 | Notification bell aggregation and persistence behavior | Notifications | P1 | Completed |
| HRMS-014 | Skills and employee_skills seeded data foundation | Data Model | P3 | Completed |
| HRMS-015 | Skills management APIs/UI | Skills Feature | P3 | Planned |
| HRMS-016 | AI chat contract stubs (`501`) and schema placeholders | AI Readiness | P3 | Completed |

## 10. Open Items and Decisions Required

- Finalize notification policy matrix for each event type (who gets notified, who does not).
- Finalize document deletion governance for admin-uploaded employee documents.
- Decide whether payslip generation should be fully server-generated PDF template or upload-only.
- Define rollout plan for skills CRUD APIs/UI (currently data-model-only).
- Define minimum automated test threshold for CI (API + critical UI paths).
- Confirm Phase 4 AI stack details (provider, vector DB strategy, async orchestration).
