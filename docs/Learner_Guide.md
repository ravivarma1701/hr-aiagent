# CB Nest — Project Guide for Learners

> **CB Nest** is a full-stack HR operations platform built with modern technologies.
> This guide walks you through everything you need to understand, run, and extend it.

---

## 1. What Is CB Nest?

CB Nest is an **HR Management System (HRMS)** that handles:

- Employee lifecycle (onboarding → active → deactivation/reactivation)
- Attendance tracking (clock in/out, work mode, punctuality)
- Leave management (apply, approve/reject, half-day support, balance tracking)
- Finance & payroll (salary, bank details, statutory info, payslips with DOB-password-protected PDFs)
- Document management (My Documents upload/search/view/download/delete, admin/manager document uploads)
- Project management (project catalog, employee-project assignments)
- Engagement (announcements, polls, notifications)
- Ticketing & task management (IT, HR, and onboarding tickets with task checklists)
- HR policy library (upload, search, view/download)
- Organization chart (tree visualisation based on reporting lines)
- My Profile (edit personal details, profile photo upload, job history)

It is also designed with **AI-ready API stubs** (`/api/v1/chat/*`) so you can later plug in RAG assistants, policy copilots, and intelligent agents.

---

## 2. Tech Stack

| Layer           | Technology                                              |
| --------------- | ------------------------------------------------------- |
| **Frontend**    | Next.js 15, React 19, Tailwind CSS, shadcn/ui, lucide-react |
| **Backend**     | FastAPI (Python), SQLAlchemy 2.0 (async), Pydantic v2   |
| **Database**    | SQLite (via `aiosqlite`)                                |
| **Migrations**  | Alembic                                                 |
| **Auth**        | JWT (JSON Web Tokens)                                   |
| **Deployment**  | Docker Compose (two containers: `api` + `web`)          |

### Why these choices?

- **Next.js 15** — File-based routing, server components, and a rich React ecosystem.
- **FastAPI** — Async-first Python framework with automatic OpenAPI docs.
- **SQLite** — Zero-config database perfect for learning and prototyping.
- **Docker Compose** — One command to spin up the entire stack.
- **shadcn/ui** — Pre-built, accessible UI components that integrate with Tailwind CSS.

---

## 3. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     BROWSER (:3000)                      │
│               Next.js Frontend (React)                   │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Pages: Dashboard, Employees, Attendance, Leaves │    │
│  │  Finance, Tickets, Polls, Announcements,         │    │
│  │  Team Calendar, HR Policies, Organization, etc.  │    │
│  └────────────────────┬─────────────────────────────┘    │
└───────────────────────┼──────────────────────────────────┘
                        │  HTTP (REST API calls)
                        ▼
┌──────────────────────────────────────────────────────────┐
│                  FastAPI Backend (:8000)                  │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐   │
│  │  Endpoints │  │  Services  │  │  Core (Auth,     │   │
│  │  (Routes)  │→ │  (Logic)   │→ │  Config, Security│   │
│  └────────────┘  └────────────┘  └──────────────────┘   │
│                        │                                 │
│                        ▼                                 │
│  ┌─────────────────────────────────────────────────┐     │
│  │  SQLAlchemy Models → SQLite Database            │     │
│  │  (hrms.db via Alembic migrations)               │     │
│  └─────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

### How a request flows (example: Employee applies for leave)

1. **Frontend** — User fills the leave request form and clicks Submit.
2. **Middleware** — Next.js middleware checks that the user has a valid `hrms_auth` cookie; if not, redirects to `/login`.
3. **API Call** — The frontend sends `POST /api/v1/leaves/requests` with leave details + JWT token in the header.
4. **Backend Endpoint** — `leaves.py` receives the request and validates it via Pydantic schemas.
5. **Auth Check** — The JWT is decoded, the user is identified, and role-based access is enforced.
6. **Database** — A new `leave_requests` row is inserted with `status = PENDING`, and leave balances are checked.
7. **Response** — The backend returns a standard envelope: `{ "success": true, "data": {...}, "error": null }`.
8. **UI Update** — The frontend reflects the new pending leave request.

---

## 4. User Roles & Permissions

CB Nest uses three roles with a clear permission hierarchy:

| Action                           | ADMIN | MANAGER | EMPLOYEE |
| -------------------------------- | :---: | :-----: | :------: |
| View own profile                 |  ✅   |   ✅    |    ✅    |
| Clock in/out attendance          |  ✅   |   ✅    |    ✅    |
| Apply for leave                  |  ✅   |   ✅    |    ✅    |
| Submit tickets                   |  ✅   |   ✅    |    ✅    |
| Vote in polls                    |  ✅   |   ✅    |    ✅    |
| View own finance details         |  ✅   |   ✅    |    ✅    |
| Upload own documents             |  ✅   |   ✅    |    ✅    |
| View/download own documents      |  ✅   |   ✅    |    ✅    |
| Delete own `OTHER` documents     |  ✅   |   ✅    |    ✅    |
| View HR policies                 |  ✅   |   ✅    |    ✅    |
| Approve/reject leaves            |  ✅   |   ✅    |    ❌    |
| Manage projects                  |  ✅   |   ✅    |    ❌    |
| Assign employees to projects     |  ✅   |   ✅    |    ❌    |
| Assign/update tickets            |  ✅   |   ✅    |    ❌    |
| Create announcements             |  ✅   |   ✅    |    ❌    |
| Upload employee documents        |  ✅   |   ✅    |    ❌    |
| Upload employee payslips         |  ✅   |   ✅    |    ❌    |
| Upload HR policies               |  ✅   |   ✅    |    ❌    |
| Add/edit employees               |  ✅   |   ❌    |    ❌    |
| Deactivate/reactivate users      |  ✅   |   ❌    |    ❌    |

---

## 5. Project Structure

```
HRMS/
├── backend/                      # FastAPI Application
│   ├── app/
│   │   ├── api/v1/endpoints/     # Route handlers (14 files)
│   │   │   ├── auth.py           #   Login / JWT token issue
│   │   │   ├── employees.py      #   CRUD, lifecycle, directory, documents, projects
│   │   │   ├── attendance.py     #   Clock in/out, history
│   │   │   ├── leaves.py         #   Requests, approvals, balances
│   │   │   ├── finance.py        #   Salary, payroll, payslips
│   │   │   ├── tickets.py        #   Ticket CRUD, assignment, onboarding tasks
│   │   │   ├── announcements.py  #   Company announcements
│   │   │   ├── polls.py          #   Polls with voting
│   │   │   ├── hr_policies.py    #   Policy upload/download
│   │   │   ├── team_calendar.py  #   Calendar (leaves, WFH, holidays, birthdays)
│   │   │   ├── org.py            #   Organization structure
│   │   │   ├── chat.py           #   AI stubs (501 – not yet implemented)
│   │   │   └── health.py         #   Health check endpoint
│   │   ├── core/                 # App config, security, logging, response helpers
│   │   ├── db/                   # Database session & connection
│   │   ├── models/               # SQLAlchemy ORM models (19 models + enums)
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   └── services/             # Business logic (auth service, etc.)
│   ├── alembic/                  # Database migration scripts
│   ├── scripts/
│   │   ├── seed.py               #   Seeds demo data (1000+ employees)
│   │   └── migrate_payslips_to_encrypted_pdf.py  # One-time payslip migration
│   ├── storage/                  # File storage (photos, policies, documents)
│   │   ├── profile-photos/
│   │   └── hr-policies/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                     # Next.js Application
│   ├── app/                      # File-based routing (13 page modules)
│   │   ├── login/                #   Login page
│   │   ├── dashboard/            #   Main dashboard
│   │   ├── employees/            #   Directory, onboarding, edit
│   │   │   ├── new/              #     New employee form
│   │   │   ├── payslips/         #     Payslip upload management
│   │   │   └── projects/         #     Project assignment management
│   │   ├── attendance/           #   Attendance tracking
│   │   ├── leaves/               #   Leave management
│   │   ├── finance/              #   Finance & payroll view
│   │   ├── tickets/              #   Ticket system
│   │   ├── announcements/        #   Company announcements
│   │   ├── polls/                #   Polls & surveys
│   │   ├── team-calendar/        #   Team calendar
│   │   ├── hr-policies/          #   HR policy library
│   │   ├── me/                   #   My Profile
│   │   │   └── documents/        #     My Documents page
│   │   └── organization/         #   Org chart
│   ├── components/               # Reusable React components
│   │   ├── layout/               #   Sidebar, topbar, notification bell
│   │   └── ui/                   #   Shared UI (button, card, input, label, badge, etc.)
│   ├── lib/api.ts                # Centralized API client (typed functions for every endpoint)
│   ├── middleware.ts             # Route protection (auth cookie check)
│   ├── Dockerfile
│   └── package.json
│
├── docs/                         # Documentation
│   ├── api/                      #   AI chat endpoint contract examples
│   ├── Learner_Guide.md          #   This guide
│   ├── PRD.md                    #   Product Requirements Document
│   └── db_tables_samples.md      #   Database schema reference with sample data
│
├── docker-compose.yml            # Orchestrates api + web containers
├── owasp_top10_security_scan.md  # OWASP Top 10 security review
├── permissions_audit_report.md   # Role-based permissions audit
└── README.md                     # Developer setup guide
```

---

## 6. Database Schema (20 Tables)

The database uses SQLite and contains 20 tables. Here is a categorized overview:

### Core
| Table          | Purpose                                      |
| -------------- | -------------------------------------------- |
| `employees`    | All employee records (name, email, role, DOB, salary, bank, PAN, etc.) |
| `departments`  | Department master data (name + location)     |

### Attendance & Leaves
| Table             | Purpose                                    |
| ----------------- | ------------------------------------------ |
| `attendance_logs` | Daily clock in/out records with status, work mode, punctuality |
| `leave_balances`  | Per-employee leave quotas (Casual, Sick, Earned) |
| `leave_requests`  | Leave applications with half-day support and approval workflow |

### Finance & Payroll
| Table             | Purpose                                    |
| ----------------- | ------------------------------------------ |
| `payroll_records` | Monthly payroll with deductions (PF, ESI, Tax) and statutory details |

### Career & Skills
| Table               | Purpose                                  |
| ------------------- | ---------------------------------------- |
| `job_history`        | Employee designation/department timeline |
| `skills`             | Skill master list (with normalized names) |
| `employee_skills`    | Employee-skill mapping with proficiency level (Beginner/Intermediate/Expert) |
| `projects`           | Project catalog with status (Ongoing/Completed/On Hold/Planned) |
| `employee_projects`  | Employee-project assignments with role on project |

### Documents & Policies
| Table                | Purpose                                  |
| -------------------- | ---------------------------------------- |
| `employee_documents` | Personal documents per employee (with uploaded_by tracking) |
| `hr_policies`        | HR policy files with metadata + embeddings field for AI |

### Engagement
| Table            | Purpose                                     |
| ---------------- | ------------------------------------------- |
| `announcements`  | Company-wide announcements                  |
| `polls`          | Poll questions with JSON options array      |
| `poll_responses`  | Individual employee votes                  |

### Operations
| Table              | Purpose                                    |
| ------------------ | ------------------------------------------ |
| `tickets`          | Support/IT/onboarding tickets with priority and status |
| `onboarding_tasks` | Checklist items linked to tickets          |
| `holidays`         | Holiday calendar                           |

### System
| Table              | Purpose                                    |
| ------------------ | ------------------------------------------ |
| `alembic_version`  | Tracks current migration version           |

> 📖 **Full column-level schema with sample data:** See [`db_tables_samples.md`](db_tables_samples.md)

---

## 7. API Endpoints

All APIs are prefixed with `/api/v1/` and return a consistent envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

| Module          | Prefix                | Key Operations                            |
| --------------- | --------------------- | ----------------------------------------- |
| Auth            | `/auth`               | Login (returns JWT)                       |
| Employees       | `/employees`          | CRUD, search, filters, lifecycle actions (deactivate/reactivate) |
| Profile         | `/employees/me`       | View/edit own profile, profile photo upload/download |
| My Documents    | `/employees/me/documents` | Upload, list, download, delete (OTHER only) |
| Employee Docs   | `/employees/{id}/documents` | Admin/Manager upload (APPOINTMENT, TAX, OTHER) |
| Payslip Upload  | `/employees/{id}/documents/payslip` | Admin/Manager payslip upload with period  |
| Job History     | `/employees/me/job-history` | View own job history timeline             |
| Job Title       | `/employees/{id}/job-title` | Update employee designation (Admin/Manager) |
| Projects        | `/employees/projects/catalog` | List, create, update status (Admin/Manager) |
| Project Assign  | `/employees/{id}/projects` | Assign/remove employee-project mapping    |
| Departments     | `/employees/departments` | List all departments                     |
| Attendance      | `/attendance`         | Clock in/out, history                     |
| Leaves          | `/leaves`             | Request, approve/reject, balance queries  |
| Announcements   | `/announcements`      | Create, list                              |
| Polls           | `/polls`              | Create, vote, results                     |
| Tickets         | `/tickets`            | Create, assign, status update, onboarding tasks |
| Finance         | `/finance`            | Salary, payroll, statutory details, payslip download |
| HR Policies     | `/hr-policies`        | Upload, download, list, search            |
| Team Calendar   | `/calendar`           | Leaves, WFH, holidays, birthdays         |
| Organization    | `/org`                | Org structure data                        |
| Chat (AI stub)  | `/chat`               | Returns 501 — ready for AI integration   |
| Health          | `/health`             | Service health check                      |

> 💡 **Tip:** With the backend running, visit `http://localhost:8000/docs` for the **interactive Swagger UI** and `http://localhost:8000/redoc` for **ReDoc** — both auto-generated by FastAPI.

---

## 8. Key Concepts & Patterns Used

### 🔐 Authentication & Authorization

- **JWT tokens** are issued on login and sent via HTTP headers for every API call.
- The **frontend middleware** (`middleware.ts`) checks for an `hrms_auth` cookie and redirects unauthenticated users to `/login`.
- The **backend** decodes the JWT, identifies the user, and enforces role-based access on each endpoint.

### 📦 Layered Backend Architecture

```
Endpoints (Routes) → Services (Business Logic) → Models (Database)
```

- **Endpoints** handle HTTP request/response — validation, auth checks, response formatting.
- **Services** contain reusable business logic (e.g., password hashing, token generation).
- **Models** define the database schema using SQLAlchemy ORM.
- **Schemas** (Pydantic) validate incoming data and shape outgoing responses.

### 🗃️ Database Migrations with Alembic

Instead of manually creating tables, this project uses **Alembic** to track and apply database changes incrementally:

```bash
# Apply all pending migrations
docker-compose exec api alembic -c alembic.ini upgrade head
```

Each migration file in `backend/alembic/versions/` represents a schema change (add column, create table, etc.).

### 🐳 Docker Compose Orchestration

The `docker-compose.yml` defines two services:

| Service | Container      | Port  | Role          |
| ------- | -------------- | ----- | ------------- |
| `api`   | `hrms-api`     | 8000  | FastAPI backend |
| `web`   | `hrms-web`     | 3000  | Next.js frontend |

Both use **volume mounts** so your code changes reflect instantly without rebuilding containers.

### 📄 Document Management

- Employees can upload personal documents (`.pdf`, `.txt`, `.md`, `.doc`, `.docx`) up to 5 MB.
- Admin/Manager can upload documents for any employee, including dedicated payslip uploads with period tagging.
- Documents track `uploaded_by` to distinguish self-uploads from admin uploads (used by the notification system).
- Only `OTHER` type documents can be deleted by the employee.
- Payslip PDFs are **password-protected** using the employee's date of birth in `DD-MM-YY` format.

### 🔔 Notification System

The notification bell in the topbar aggregates events from multiple APIs:
- New announcements
- New polls
- Ticket assignment and status changes
- Leave approval/rejection decisions
- Document uploads by others (self-uploads are excluded)

Read/dismiss state is persisted in browser **localStorage**.

### 🤖 AI-Ready Hooks

The `/api/v1/chat/*` endpoints currently return `501 Not Implemented`. This is intentional — they serve as **contract stubs** for future AI features:

- Policy RAG assistant (ask questions about HR policies)
- Payroll explanation helper
- Leave policy reasoning agent

The `hr_policies` table includes an `embedding` field (JSON) ready for vector storage.

---

## 9. Getting Started (Setup)

### Prerequisites

- **Docker Desktop** (or Docker Engine + Compose v2)
  - On **Windows**: install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and ensure the **WSL 2 backend** is enabled
- **Git**

### Step-by-step

```bash
# 1. Clone the repository
git clone <repo-url>
cd HRMS

# 2. Copy environment file
cp backend/.env.example backend/.env
# On Windows PowerShell:
# Copy-Item backend/.env.example backend/.env

# 3. Build and start containers
docker-compose up -d --build

# 4. Run database migrations
docker-compose exec api alembic -c alembic.ini upgrade head

# 5. Seed demo data
docker-compose exec api python scripts/seed.py

# 6. Open the app
# Frontend:  http://localhost:3000
# API Docs:  http://localhost:8000/docs
```

### Login Credentials

| Role       | Email                      | Password      |
| ---------- | -------------------------- | ------------- |
| Admin      | `admin@mock-hrms.dev`      | `password123` |
| Manager    | `manager@mock-hrms.dev`    | `password123` |
| Employee   | `employee@mock-hrms.dev`   | `password123` |

> 💡 Log in with **each role** to see how the UI and permissions change.

---

## 10. Common Tasks

### Start / Stop the app

```bash
docker-compose up -d       # Start
docker-compose down        # Stop
docker-compose ps          # Check status
```

### Restart after code changes

```bash
docker compose restart api web
```

### Reset the database

```bash
docker-compose down
# macOS/Linux:
rm -f backend/storage/hrms.db
# Windows PowerShell:
# Remove-Item backend\storage\hrms.db -Force -ErrorAction SilentlyContinue

docker-compose up -d --build
docker-compose exec api alembic -c alembic.ini upgrade head
docker-compose exec api python scripts/seed.py
```

### View API documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 11. How to Explore & Learn

Here is a suggested learning path:

### Level 1: Understand the App
1. Run the app and log in as all three roles (Admin, Manager, Employee).
2. Explore each module: Dashboard, Employees, Attendance, Leaves, Finance, Tickets, Polls, Team Calendar, HR Policies, Organization.
3. Perform key workflows: add an employee, apply for leave, approve it, clock in/out, upload a document, create a project, assign an employee to it.

### Level 2: Read the Code
1. Start with `backend/app/main.py` — the entry point that sets up FastAPI.
2. Pick one API module (e.g., `leaves.py`) and trace the full flow: endpoint → schema → model → database.
3. In the frontend, explore `frontend/app/leaves/` to see how the UI calls the API and renders data.
4. Read `frontend/middleware.ts` to understand route protection.
5. Explore `frontend/lib/api.ts` to see how the centralized API client is structured with TypeScript types.
6. Look at `frontend/components/layout/notification-bell.tsx` to understand how multi-source notifications are aggregated.

### Level 3: Modify & Extend
1. **Add a new field** to the employee model and create an Alembic migration.
2. **Build a new API endpoint** (e.g., employee search by skills).
3. **Create a new frontend page** under `frontend/app/`.
4. **Implement the AI chat stub** — connect a real LLM to the `/api/v1/chat/*` endpoint.
5. **Add a Skills management UI** — the `skills` and `employee_skills` tables are seeded but have no dedicated UI yet.

### Level 4: Production Thinking
1. What would you change to support **1000+ employees** in production?
2. How would you replace SQLite with **PostgreSQL**?
3. What **security improvements** would you add? (Hint: review `owasp_top10_security_scan.md` and `permissions_audit_report.md` in the repo.)
4. How would you add **automated tests**?

---

## 12. Glossary

| Term                | Meaning                                                   |
| ------------------- | --------------------------------------------------------- |
| **JWT**             | JSON Web Token — a secure, stateless auth token           |
| **ORM**             | Object-Relational Mapping — Python classes ↔ DB tables    |
| **Alembic**         | Database migration tool for SQLAlchemy                    |
| **Pydantic**        | Data validation library using Python type hints           |
| **FastAPI**         | Async Python web framework with auto-generated API docs   |
| **Next.js**         | React framework with file-based routing & SSR             |
| **Tailwind CSS**    | Utility-first CSS framework                               |
| **shadcn/ui**       | Accessible React component library built on Radix UI      |
| **Docker Compose**  | Tool to define and run multi-container applications       |
| **CORS**            | Cross-Origin Resource Sharing — browser security policy   |
| **RAG**             | Retrieval-Augmented Generation — AI pattern for Q&A       |
| **DOB**             | Date of Birth — used as payslip PDF password (`DD-MM-YY`) |

---

*Built with ❤️ by Codebasics — Enabling Careers.*
