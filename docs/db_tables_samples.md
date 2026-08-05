# SQLite DB Snapshot

- Database file: `backend/storage/hrms.db`
- Tables found: **20**
- Sample rows per table: **3**

## Tables

- `alembic_version`
- `announcements`
- `attendance_logs`
- `departments`
- `employee_documents`
- `employee_projects`
- `employee_skills`
- `employees`
- `holidays`
- `hr_policies`
- `job_history`
- `leave_balances`
- `leave_requests`
- `onboarding_tasks`
- `payroll_records`
- `poll_responses`
- `polls`
- `projects`
- `skills`
- `tickets`

## `alembic_version`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `version_num` | `VARCHAR(32)` | 1 | 1 | `` |

### Sample Records (showing up to 3 of 1)

| version_num |
|---|
| 0013_employee_documents |

## `announcements`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `title` | `VARCHAR(180)` | 1 | 0 | `` |
| `body` | `TEXT` | 1 | 0 | `` |
| `author_id` | `INTEGER` | 1 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |

### Sample Records (showing up to 3 of 2)

| id | title | body | author_id | created_at |
|---|---|---|---|---|
| 1 | Quarterly Townhall - Friday 4 PM | Join the all-hands townhall this Friday at 4 PM in the main hall and via live... | 1 | 2026-03-06 03:44:23 |
| 2 | Platform Sprint Planning | Sprint planning starts Monday 10 AM. Please update your task estimates before... | 2 | 2026-03-06 03:44:23 |

## `attendance_logs`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `date` | `DATE` | 1 | 0 | `` |
| `clock_in` | `TIME` | 0 | 0 | `` |
| `clock_out` | `TIME` | 0 | 0 | `` |
| `status` | `VARCHAR(7)` | 1 | 0 | `` |
| `work_mode` | `VARCHAR(20)` | 0 | 0 | `` |
| `punctuality` | `VARCHAR(20)` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 22)

| id | employee_id | date | clock_in | clock_out | status | work_mode | punctuality |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 2026-03-05 | 09:00:00.000000 | 18:00:00.000000 | ON_TIME | PRESENT | ON_TIME |
| 2 | 1 | 2026-03-04 | 09:00:00.000000 | 18:00:00.000000 | ON_TIME | PRESENT | ON_TIME |
| 3 | 1 | 2026-03-03 | 09:10:00.000000 | 18:00:00.000000 | LATE | PRESENT | LATE |

## `departments`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(120)` | 1 | 0 | `` |
| `location` | `VARCHAR(120)` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 6)

| id | name | location |
|---|---|---|
| 1 | CEO | New York |
| 2 | Engineering | Bengaluru |
| 3 | Finance | London |

## `employee_documents`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `uploaded_by` | `INTEGER` | 0 | 0 | `` |
| `title` | `VARCHAR(220)` | 1 | 0 | `` |
| `document_type` | `VARCHAR(40)` | 1 | 0 | `` |
| `original_filename` | `VARCHAR(255)` | 1 | 0 | `` |
| `file_path` | `TEXT` | 1 | 0 | `` |
| `mime_type` | `VARCHAR(120)` | 1 | 0 | `` |
| `size_bytes` | `INTEGER` | 1 | 0 | `` |
| `checksum` | `VARCHAR(64)` | 1 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |

### Sample Records (showing up to 3 of 0)

_No rows_

## `employee_projects`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `project_id` | `INTEGER` | 1 | 0 | `` |
| `role_on_project` | `VARCHAR(120)` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 1254)

| id | employee_id | project_id | role_on_project |
|---|---|---|---|
| 1 | 1 | 1 | AI Engineer |
| 2 | 1 | 2 | ML Engineer |
| 3 | 2 | 2 | Backend Engineer |

## `employee_skills`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `skill_id` | `INTEGER` | 1 | 0 | `` |
| `level` | `VARCHAR(12)` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 2006)

| id | employee_id | skill_id | level |
|---|---|---|---|
| 1 | 1 | 1 | BEGINNER |
| 2 | 1 | 4 | INTERMEDIATE |
| 3 | 2 | 2 | INTERMEDIATE |

## `employees`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(120)` | 1 | 0 | `` |
| `email` | `VARCHAR(255)` | 1 | 0 | `` |
| `hashed_password` | `VARCHAR(255)` | 1 | 0 | `` |
| `department_id` | `INTEGER` | 0 | 0 | `` |
| `manager_id` | `INTEGER` | 0 | 0 | `` |
| `role` | `VARCHAR(8)` | 1 | 0 | `` |
| `status` | `VARCHAR(8)` | 1 | 0 | `` |
| `joining_date` | `DATE` | 1 | 0 | `` |
| `phone` | `VARCHAR(20)` | 0 | 0 | `` |
| `address` | `VARCHAR(255)` | 0 | 0 | `` |
| `blood_type` | `VARCHAR(8)` | 0 | 0 | `` |
| `occupancy` | `VARCHAR(60)` | 0 | 0 | `` |
| `date_of_birth` | `DATE` | 0 | 0 | `` |
| `profile_photo_path` | `VARCHAR(255)` | 0 | 0 | `` |
| `profile_photo_mime` | `VARCHAR(64)` | 0 | 0 | `` |
| `current_salary_usd` | `NUMERIC(12, 2)` | 0 | 0 | `` |
| `bank_name` | `VARCHAR(120)` | 0 | 0 | `` |
| `bank_account_number` | `VARCHAR(34)` | 0 | 0 | `` |
| `bank_account_name` | `VARCHAR(120)` | 0 | 0 | `` |
| `bank_branch` | `VARCHAR(120)` | 0 | 0 | `` |
| `bank_ifsc` | `VARCHAR(20)` | 0 | 0 | `` |
| `pan_number` | `VARCHAR(20)` | 0 | 0 | `` |
| `pan_name` | `VARCHAR(120)` | 0 | 0 | `` |
| `pan_dob` | `DATE` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 1003)

| id | name | email | hashed_password | department_id | manager_id | role | status | joining_date | phone | address | blood_type | occupancy | date_of_birth | profile_photo_path | profile_photo_mime | current_salary_usd | bank_name | bank_account_number | bank_account_name | bank_branch | bank_ifsc | pan_number | pan_name | pan_dob |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Admin User | admin@mock-hrms.dev | $2b$12$BrkPjdK1MtKhGLpuQlxSUeqRLH7rX2DsJ4nZUH7I4wqJsmcIfyqRq | 6 |  | ADMIN | ACTIVE | 2022-01-01 | 9876543210 | Bengaluru, India | O+ | Full-Time | 1980-01-01 | /app/storage/profile-photos/user_1_ea9ea618eca646479a14f29a35c64e65.jpg | image/jpeg | 60000 | DBS Bank | 00011000000000 | Admin User | Midtown | MOCK0000001 | ADHLP1000T | Admin User | 1980-01-01 |
| 2 | Manager User | manager@mock-hrms.dev | $2b$12$5M5cFFPmmJP/wsERME8SreNtniklamxf0npYuodI7yMVszf6pXBcm | 3 |  | MANAGER | ACTIVE | 2022-01-01 | 9876543210 | Bengaluru, India | O+ | Full-Time | 1981-02-04 |  |  | 64500 | Citibank | 00021000000001 | Manager User | Downtown | MOCK0000002 | BEIMQ1001U | Manager User | 1981-02-04 |
| 3 | Employee User | employee@mock-hrms.dev | $2b$12$ivSufsO/AgPSZI7McTpzf.eBrOuC.7NjQqm.R0t/U2PUyZ1ijaqmu | 2 | 2 | EMPLOYEE | ACTIVE | 2022-01-01 | 9876543210 | Bengaluru, India | O+ | Full-Time | 1982-03-07 | /app/storage/profile-photos/user_3_853e12a509274e83a33ad350957a8caa.jpg | image/jpeg | 69000 | JPMorgan Chase | 00031000000002 | Employee User | Midtown | MOCK0000003 | CFJNR1002V | Employee User | 1982-03-07 |

## `holidays`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(120)` | 1 | 0 | `` |
| `date` | `DATE` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 8)

| id | name | date |
|---|---|---|
| 1 | International Women's Day | 2026-03-08 |
| 2 | International Workers' Day | 2026-05-01 |
| 3 | United Nations Day | 2026-10-24 |

## `hr_policies`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `title` | `VARCHAR(220)` | 1 | 0 | `` |
| `content` | `TEXT` | 0 | 0 | `` |
| `category` | `VARCHAR(60)` | 1 | 0 | `` |
| `embedding` | `JSON` | 0 | 0 | `` |
| `original_filename` | `VARCHAR(255)` | 0 | 0 | `` |
| `file_path` | `TEXT` | 0 | 0 | `` |
| `mime_type` | `VARCHAR(100)` | 0 | 0 | `` |
| `size_bytes` | `INTEGER` | 0 | 0 | `` |
| `uploaded_by` | `INTEGER` | 0 | 0 | `` |
| `checksum` | `VARCHAR(64)` | 0 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |

### Sample Records (showing up to 3 of 22)

| id | title | content | category | embedding | original_filename | file_path | mime_type | size_bytes | uploaded_by | checksum | created_at |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Leave Policy |  | LEAVE | null | seed_policy_01.md | /app/storage/hr-policies/seed_policy_01.md | text/markdown | 94 | 1 | 94e7da2e5205a2ea272353937058c79222886b781ef6c9d7f81632b4d9a7a236 | 2026-03-06 03:44:28 |
| 2 | Attendance Policy |  | ATTENDANCE | null | seed_policy_02.md | /app/storage/hr-policies/seed_policy_02.md | text/markdown | 82 | 1 | 1847a5ab310e2f0a2c302e923ac134e8bf3538feb109f7182a56ac78f766d13b | 2026-03-06 03:44:28 |
| 3 | WFH Policy |  | WFH | null | seed_policy_03.md | /app/storage/hr-policies/seed_policy_03.md | text/markdown | 83 | 1 | a4085f25dc54a1247cab74ab204bb496114ba81641ce4a36bcf312cd9af13354 | 2026-03-06 03:44:28 |

## `job_history`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `designation` | `VARCHAR(120)` | 1 | 0 | `` |
| `business_unit` | `VARCHAR(120)` | 1 | 0 | `` |
| `department` | `VARCHAR(120)` | 1 | 0 | `` |
| `start_date` | `DATE` | 1 | 0 | `` |
| `end_date` | `DATE` | 0 | 0 | `` |
| `is_current` | `BOOLEAN` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 1005)

| id | employee_id | designation | business_unit | department | start_date | end_date | is_current |
|---|---|---|---|---|---|---|---|
| 1 | 1 | HR Director | Corporate | HR | 2022-01-01 |  | 1 |
| 2 | 2 | Finance Manager | Corporate | Finance | 2022-01-01 |  | 1 |
| 3 | 3 | Software Engineer II | Corporate | Engineering | 2022-01-01 |  | 1 |

## `leave_balances`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `leave_type` | `VARCHAR(6)` | 1 | 0 | `` |
| `total` | `INTEGER` | 1 | 0 | `` |
| `used` | `INTEGER` | 1 | 0 | `` |
| `remaining` | `INTEGER` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 3009)

| id | employee_id | leave_type | total | used | remaining |
|---|---|---|---|---|---|
| 1 | 1 | CASUAL | 12 | 2 | 10 |
| 2 | 1 | SICK | 10 | 1 | 9 |
| 3 | 1 | EARNED | 15 | 4 | 11 |

## `leave_requests`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `leave_type` | `VARCHAR(6)` | 1 | 0 | `` |
| `start_date` | `DATE` | 1 | 0 | `` |
| `end_date` | `DATE` | 1 | 0 | `` |
| `reason` | `VARCHAR(500)` | 1 | 0 | `` |
| `is_half_day` | `BOOLEAN` | 1 | 0 | `0` |
| `half_day_period` | `VARCHAR(11)` | 0 | 0 | `` |
| `status` | `VARCHAR(8)` | 1 | 0 | `` |
| `approver_id` | `INTEGER` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 2)

| id | employee_id | leave_type | start_date | end_date | reason | is_half_day | half_day_period | status | approver_id |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | CASUAL | 2026-03-08 | 2026-03-09 | Family function | 0 |  | PENDING |  |
| 2 | 3 | SICK | 2026-02-24 | 2026-02-25 | Recovery leave | 0 |  | APPROVED | 2 |

## `onboarding_tasks`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `ticket_id` | `INTEGER` | 1 | 0 | `` |
| `task_name` | `VARCHAR(200)` | 1 | 0 | `` |
| `is_completed` | `BOOLEAN` | 1 | 0 | `` |
| `due_date` | `DATE` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 2)

| id | ticket_id | task_name | is_completed | due_date |
|---|---|---|---|---|
| 1 | 2 | Issue laptop | 0 |  |
| 2 | 2 | Generate ID card | 0 | 2026-03-08 |

## `payroll_records`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `month` | `DATE` | 1 | 0 | `` |
| `gross` | `FLOAT` | 1 | 0 | `` |
| `deductions` | `JSON` | 1 | 0 | `` |
| `net` | `FLOAT` | 1 | 0 | `` |
| `pan` | `VARCHAR(20)` | 1 | 0 | `` |
| `pf_uan` | `VARCHAR(30)` | 0 | 0 | `` |
| `esi_no` | `VARCHAR(30)` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 6)

| id | employee_id | month | gross | deductions | net | pan | pf_uan | esi_no |
|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 2026-03-01 | 95000.0 | {"pf": 4200.0, "esi": 800.0, "tax": 9500.0} | 80500.0 | ABCDE1234F | 100200300400 | ESI100920 |
| 2 | 3 | 2026-01-01 | 95000.0 | {"pf": 4200.0, "esi": 800.0, "tax": 9500.0} | 80500.0 | ABCDE1234F | 100200300400 | ESI100920 |
| 3 | 3 | 2025-12-01 | 95000.0 | {"pf": 4200.0, "esi": 800.0, "tax": 9500.0} | 80500.0 | ABCDE1234F | 100200300400 | ESI100920 |

## `poll_responses`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `poll_id` | `INTEGER` | 1 | 0 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `option_index` | `INTEGER` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 2)

| id | poll_id | employee_id | option_index |
|---|---|---|---|
| 1 | 1 | 3 | 0 |
| 2 | 1 | 1 | 1 |

## `polls`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `question` | `VARCHAR(300)` | 1 | 0 | `` |
| `options` | `JSON` | 1 | 0 | `` |
| `created_by` | `INTEGER` | 1 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |

### Sample Records (showing up to 3 of 1)

| id | question | options | created_by | created_at |
|---|---|---|---|---|
| 1 | Which initiative should be prioritized next quarter? | ["Improve leave workflow", "Automate payroll FAQ", "Manager dashboard revamp"] | 2 | 2026-03-06 03:44:28 |

## `projects`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(180)` | 1 | 0 | `` |
| `description` | `TEXT` | 0 | 0 | `` |
| `status` | `VARCHAR(9)` | 1 | 0 | `ONGOING` |

### Sample Records (showing up to 3 of 4)

| id | name | description | status |
|---|---|---|---|
| 1 | Talent Intelligence Platform | Internal recommendation and skills intelligence platform. | ONGOING |
| 2 | HR Policy Copilot | Conversational assistant for HR policy answers. | ONGOING |
| 3 | Leave Automation Engine | Automated leave lifecycle and recommendation workflows. | ONGOING |

## `skills`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(120)` | 1 | 0 | `` |
| `normalized_name` | `VARCHAR(120)` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 8)

| id | name | normalized_name |
|---|---|---|
| 1 | Python | python |
| 2 | AI Engineer | ai engineer |
| 3 | FastAPI | fastapi |

## `tickets`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `assignee_id` | `INTEGER` | 0 | 0 | `` |
| `title` | `VARCHAR(180)` | 1 | 0 | `` |
| `description` | `TEXT` | 1 | 0 | `` |
| `category` | `VARCHAR(10)` | 1 | 0 | `` |
| `priority` | `VARCHAR(6)` | 1 | 0 | `` |
| `status` | `VARCHAR(11)` | 1 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |

### Sample Records (showing up to 3 of 4)

| id | employee_id | assignee_id | title | description | category | priority | status | created_at |
|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 2 | Laptop VPN access issue | Unable to connect to VPN from home network after update. | IT | HIGH | IN_PROGRESS | 2026-03-06 03:44:28 |
| 2 | 3 | 2 | New joiner onboarding setup | Complete laptop, ID card and workspace setup for onboarding. | ONBOARDING | MEDIUM | OPEN | 2026-03-06 03:44:28 |
| 3 | 3 | 2 | VPN issue | VPN issue in my laptop | IT | HIGH | RESOLVED | 2026-03-06 03:52:26 |
