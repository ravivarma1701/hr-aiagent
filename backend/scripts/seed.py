import asyncio
import hashlib
from datetime import date, time, timedelta
from pathlib import Path

from faker import Faker
from sqlalchemy import select, text

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.attendance_log import AttendanceLog
from app.models.announcement import Announcement
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_project import EmployeeProject
from app.models.employee_skill import EmployeeSkill
from app.models.enums import AttendanceStatus, LeaveRequestStatus, LeaveType, Role, SkillLevel, TicketCategory, TicketPriority, TicketStatus
from app.models.leave_balance import LeaveBalance
from app.models.leave_request import LeaveRequest
from app.models.onboarding_task import OnboardingTask
from app.models.hr_policy import HRPolicy
from app.models.holiday import Holiday
from app.models.job_history import JobHistory
from app.models.payroll_record import PayrollRecord
from app.models.poll import Poll
from app.models.poll_response import PollResponse
from app.models.project import Project
from app.models.skill import Skill
from app.models.ticket import Ticket

fake = Faker()


def month_start_n_months_ago(base_month_start: date, months_ago: int) -> date:
    year = base_month_start.year
    month = base_month_start.month - months_ago
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


async def seed():
    async with SessionLocal() as session:
        tables = [
            "poll_responses",
            "polls",
            "payroll_records",
            "job_history",
            "holidays",
            "employee_projects",
            "employee_skills",
            "hr_policies",
            "onboarding_tasks",
            "tickets",
            "announcements",
            "attendance_logs",
            "leave_requests",
            "leave_balances",
            "projects",
            "skills",
            "employees",
            "departments",
        ]
        for table in tables:
            await session.execute(text(f"DELETE FROM {table}"))
        if session.bind and session.bind.dialect.name == "sqlite":
            seq_table_exists = (
                await session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
                )
            ).scalar_one_or_none()
            if seq_table_exists:
                await session.execute(text("DELETE FROM sqlite_sequence"))

        department_specs = [
            ("CEO", "New York"),
            ("Engineering", "Bengaluru"),
            ("Finance", "London"),
            ("Freelancer", "Remote"),
            ("Marketing", "Singapore"),
            ("HR", "Dubai"),
        ]
        departments: dict[str, Department] = {}
        for dept_name, dept_location in department_specs:
            dept = Department(name=dept_name, location=dept_location)
            session.add(dept)
            departments[dept_name] = dept
        await session.flush()

        fixed_users = [
            ("Admin User", "admin@mock-hrms.dev", Role.ADMIN, "HR"),
            ("Manager User", "manager@mock-hrms.dev", Role.MANAGER, "Finance"),
            ("Employee User", "employee@mock-hrms.dev", Role.EMPLOYEE, "Engineering"),
        ]

        fixed_employee_ids: list[int] = []
        for name, email, role, dept_name in fixed_users:
            employee = Employee(
                name=name,
                email=email,
                hashed_password=hash_password("password123"),
                department_id=departments[dept_name].id,
                role=role,
                joining_date=date(2022, 1, 1),
                phone="9876543210",
                address="Bengaluru, India",
                blood_type="O+",
                occupancy="Full-Time",
            )
            session.add(employee)
            await session.flush()
            fixed_employee_ids.append(employee.id)

        manager_user_id = fixed_employee_ids[1]
        employee_user_id = fixed_employee_ids[2]
        employee_user = (await session.execute(select(Employee).where(Employee.id == employee_user_id))).scalar_one()
        employee_user.manager_id = manager_user_id

        cycle_departments = ["Engineering", "Finance", "Marketing", "Freelancer", "Engineering"]
        for index in range(1000):
            dept_name = cycle_departments[index % len(cycle_departments)]
            session.add(
                Employee(
                    name=fake.name(),
                    email=fake.unique.email(),
                    hashed_password=hash_password("password123"),
                    department_id=departments[dept_name].id,
                    manager_id=manager_user_id,
                    role=Role.EMPLOYEE,
                    joining_date=fake.date_between(start_date="-5y", end_date="today"),
                    phone="9" + str(fake.random_int(min=100000000, max=999999999)),
                    address=fake.address().replace("\n", ", "),
                    blood_type=fake.random_element(elements=("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")),
                    occupancy=fake.random_element(elements=("Full-Time", "Contract", "Intern")),
                )
            )

        for employee_id in fixed_employee_ids:
            for day_offset in range(1, 8):
                log_date = date.today() - timedelta(days=day_offset)
                session.add(
                    AttendanceLog(
                        employee_id=employee_id,
                        date=log_date,
                        clock_in=time(9, 10 if day_offset % 3 == 0 else 0),
                        clock_out=time(18, 0),
                        status=AttendanceStatus.LATE if day_offset % 3 == 0 else AttendanceStatus.ON_TIME,
                        work_mode="PRESENT",
                        punctuality=AttendanceStatus.LATE.value if day_offset % 3 == 0 else AttendanceStatus.ON_TIME.value,
                    )
                )

        all_employees_result = await session.execute(select(Employee.id))
        all_employee_ids = [row[0] for row in all_employees_result.all()]
        all_employees = (await session.execute(select(Employee).order_by(Employee.id.asc()))).scalars().all()
        dept_name_by_id = {value.id: key for key, value in departments.items()}

        # Distribute DOBs across different months/days (deterministic spread, no clustering).
        for index, employee in enumerate(all_employees):
            birth_year = 1980 + (index % 22)  # 1980..2001
            birth_month = (index % 12) + 1  # 1..12
            birth_day = ((index * 3) % 28) + 1  # 1..28 to avoid invalid month dates
            employee.date_of_birth = date(birth_year, birth_month, birth_day)
            employee.current_salary_usd = 60000 + ((index % 15) * 4500)
            employee.bank_name = fake.random_element(elements=("JPMorgan Chase", "HSBC", "Citibank", "DBS Bank", "Barclays"))
            employee.bank_account_number = f"{employee.id:04d}{(1000000000 + index):010d}"
            employee.bank_account_name = employee.name
            employee.bank_branch = fake.random_element(elements=("Downtown", "Central", "Midtown", "Main Branch", "City Center"))
            employee.bank_ifsc = f"MOCK0{employee.id:06d}"[:11]
            employee.pan_number = f"{chr(65 + (index % 26))}{chr(65 + ((index + 3) % 26))}{chr(65 + ((index + 7) % 26))}{chr(65 + ((index + 11) % 26))}{chr(65 + ((index + 15) % 26))}{1000 + (index % 9000)}{chr(65 + ((index + 19) % 26))}"
            employee.pan_name = employee.name
            employee.pan_dob = employee.date_of_birth

        # International holidays: keep only upcoming dates from today onward.
        today = date.today()
        base_holidays = [
            ("International Women's Day", 3, 8),
            ("International Workers' Day", 5, 1),
            ("United Nations Day", 10, 24),
            ("Christmas Day", 12, 25),
            ("New Year's Day", 1, 1),
            ("World Health Day", 4, 7),
            ("International Day of Peace", 9, 21),
            ("Human Rights Day", 12, 10),
        ]
        for holiday_name, month, day in base_holidays:
            holiday_date = date(today.year, month, day)
            if holiday_date < today:
                holiday_date = date(today.year + 1, month, day)
            session.add(Holiday(name=holiday_name, date=holiday_date))

        titles_by_department = {
            "CEO": ["Chief Executive Officer", "Executive Assistant", "Chief of Staff"],
            "Engineering": [
                "Software Engineer",
                "Senior Software Engineer",
                "Backend Engineer",
                "Frontend Engineer",
                "DevOps Engineer",
                "Data Engineer",
                "QA Engineer",
                "Technical Lead",
            ],
            "Finance": ["Financial Analyst", "Accountant", "Payroll Specialist", "Finance Manager", "Controller"],
            "Freelancer": ["Freelance Consultant", "Independent Contractor", "External Specialist"],
            "Marketing": ["Marketing Specialist", "Content Strategist", "SEO Analyst", "Brand Manager", "Growth Marketer"],
            "HR": ["HR Executive", "HR Manager", "HR Business Partner", "Talent Acquisition Specialist"],
        }
        for index, employee in enumerate(all_employees):
            dept_name = dept_name_by_id.get(employee.department_id, "Engineering")
            if employee.id == fixed_employee_ids[0]:
                title = "HR Director"
            elif employee.id == fixed_employee_ids[1]:
                title = "Finance Manager"
            elif employee.id == fixed_employee_ids[2]:
                title = "Software Engineer II"
            else:
                title_options = titles_by_department.get(dept_name, ["Associate"])
                title = title_options[index % len(title_options)]
            session.add(
                JobHistory(
                    employee_id=employee.id,
                    designation=title,
                    business_unit="Corporate",
                    department=dept_name,
                    start_date=employee.joining_date,
                    end_date=None,
                    is_current=True,
                )
            )

        skills = [
            ("Python", "python"),
            ("AI Engineer", "ai engineer"),
            ("FastAPI", "fastapi"),
            ("Machine Learning", "machine learning"),
            ("NLP", "nlp"),
            ("Data Analysis", "data analysis"),
            ("SQL", "sql"),
            ("React", "react"),
        ]
        skill_models: list[Skill] = []
        for name, normalized in skills:
            skill = Skill(name=name, normalized_name=normalized)
            session.add(skill)
            skill_models.append(skill)
        await session.flush()

        projects = [
            ("Talent Intelligence Platform", "Internal skills intelligence and capability planning platform."),
            ("Engineering Reliability Hub", "Service quality, SLO tracking, and incident intelligence workflows."),
            ("Data Platform Modernization", "Warehouse optimization, ETL reliability, and data contract governance."),
            ("Developer Experience Portal", "Productivity tooling and internal engineering workflows."),
            ("HR Policy Copilot", "Conversational assistant for HR policy answers and governance workflows."),
            ("Leave Automation Engine", "Automated leave lifecycle and compliance workflows."),
            ("Onboarding Journey Studio", "Standardized onboarding plans and task workflows."),
            ("Workforce Insights Dashboard", "Data-driven workforce analytics and reporting."),
            ("Finance Forecast Workbench", "Scenario planning and financial forecast automation."),
            ("Expense Compliance Monitor", "Policy validation and expense anomaly detection."),
            ("Revenue Assurance Console", "Revenue leakage analysis and audit tracking."),
            ("Compensation Planning Suite", "Salary benchmarking and compensation planning."),
            ("Campaign Performance Hub", "Campaign analytics and attribution workflows."),
            ("Content Operations Studio", "Editorial workflow planning and content governance."),
            ("Brand Sentiment Radar", "Brand monitoring and sentiment trend analysis."),
            ("Digital Growth Experiments", "Experiment pipeline for acquisition and conversion."),
            ("Executive KPI Cockpit", "Board-level KPI and strategic performance dashboard."),
            ("Enterprise Risk Compass", "Cross-functional risk registry and control tracking."),
            ("Client Delivery Marketplace", "Freelancer assignment and delivery orchestration."),
            ("Independent Consultant Toolkit", "Freelancer engagement and reporting workflows."),
        ]
        project_models: list[Project] = []
        for name, description in projects:
            project = Project(name=name, description=description)
            session.add(project)
            project_models.append(project)
        await session.flush()

        level_cycle = [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE, SkillLevel.EXPERT]
        project_id_by_name = {project.name: project.id for project in project_models}
        project_assignments_by_department = {
            "CEO": [
                ("Executive KPI Cockpit", "Executive Sponsor"),
                ("Enterprise Risk Compass", "Steering Committee"),
                ("Workforce Insights Dashboard", "Strategic Reviewer"),
                ("Revenue Assurance Console", "Portfolio Sponsor"),
            ],
            "Engineering": [
                ("Talent Intelligence Platform", "Platform Engineer"),
                ("Engineering Reliability Hub", "Reliability Engineer"),
                ("Data Platform Modernization", "Data Engineer"),
                ("Developer Experience Portal", "Backend Engineer"),
            ],
            "Finance": [
                ("Finance Forecast Workbench", "Finance Analyst"),
                ("Expense Compliance Monitor", "Compliance Reviewer"),
                ("Revenue Assurance Console", "Revenue Controller"),
                ("Compensation Planning Suite", "Payroll Reviewer"),
            ],
            "Freelancer": [
                ("Client Delivery Marketplace", "Delivery Consultant"),
                ("Independent Consultant Toolkit", "External Specialist"),
                ("Digital Growth Experiments", "Contract Contributor"),
                ("Content Operations Studio", "Independent Consultant"),
            ],
            "Marketing": [
                ("Campaign Performance Hub", "Campaign Analyst"),
                ("Content Operations Studio", "Content Strategist"),
                ("Brand Sentiment Radar", "Brand Analyst"),
                ("Digital Growth Experiments", "Growth Marketer"),
            ],
            "HR": [
                ("HR Policy Copilot", "Policy Specialist"),
                ("Leave Automation Engine", "HR Operations"),
                ("Onboarding Journey Studio", "Talent Specialist"),
                ("Compensation Planning Suite", "People Operations"),
            ],
        }
        for index, employee_id in enumerate(all_employee_ids):
            primary_skill = skill_models[index % len(skill_models)]
            secondary_skill = skill_models[(index + 3) % len(skill_models)]
            session.add(EmployeeSkill(employee_id=employee_id, skill_id=primary_skill.id, level=level_cycle[index % len(level_cycle)]))
            if secondary_skill.id != primary_skill.id:
                session.add(
                    EmployeeSkill(
                        employee_id=employee_id,
                        skill_id=secondary_skill.id,
                        level=level_cycle[(index + 1) % len(level_cycle)],
                    )
                )
            employee = all_employees[index]
            dept_name = dept_name_by_id.get(employee.department_id, "Freelancer")
            assignments = project_assignments_by_department.get(
                dept_name,
                [("Workforce Insights Dashboard", "Contributor"), ("Enterprise Risk Compass", "Collaborator")],
            )
            start_index = employee.id % len(assignments)
            assignments_per_employee = 2 + (1 if employee.id % 5 == 0 and len(assignments) >= 3 else 0)
            chosen: list[tuple[str, str]] = []
            for offset in range(assignments_per_employee):
                candidate = assignments[(start_index + offset) % len(assignments)]
                if candidate not in chosen:
                    chosen.append(candidate)
            for project_name, role_on_project in chosen:
                project_id = project_id_by_name.get(project_name)
                if project_id is None:
                    continue
                session.add(
                    EmployeeProject(
                        employee_id=employee_id,
                        project_id=project_id,
                        role_on_project=role_on_project,
                    )
                )

        for employee_id in all_employee_ids:
            session.add(LeaveBalance(employee_id=employee_id, leave_type=LeaveType.CASUAL, total=12, used=2, remaining=10))
            session.add(LeaveBalance(employee_id=employee_id, leave_type=LeaveType.SICK, total=10, used=1, remaining=9))
            session.add(LeaveBalance(employee_id=employee_id, leave_type=LeaveType.EARNED, total=15, used=4, remaining=11))

        # Seed one pending and one approved request for demo accounts
        session.add(
            LeaveRequest(
                employee_id=employee_user_id,
                leave_type=LeaveType.CASUAL,
                start_date=date.today() + timedelta(days=2),
                end_date=date.today() + timedelta(days=3),
                reason="Family function",
                status=LeaveRequestStatus.PENDING,
                approver_id=None,
            )
        )
        session.add(
            LeaveRequest(
                employee_id=employee_user_id,
                leave_type=LeaveType.SICK,
                start_date=date.today() - timedelta(days=10),
                end_date=date.today() - timedelta(days=9),
                reason="Recovery leave",
                status=LeaveRequestStatus.APPROVED,
                approver_id=manager_user_id,
            )
        )

        admin_user_id = fixed_employee_ids[0]
        session.add(
            Announcement(
                title="Quarterly Townhall - Friday 4 PM",
                body="Join the all-hands townhall this Friday at 4 PM in the main hall and via livestream.",
                author_id=admin_user_id,
            )
        )
        session.add(
            Announcement(
                title="Platform Sprint Planning",
                body="Sprint planning starts Monday 10 AM. Please update your task estimates before EOD Friday.",
                author_id=manager_user_id,
            )
        )

        ticket_it = Ticket(
            employee_id=employee_user_id,
            assignee_id=manager_user_id,
            title="Laptop VPN access issue",
            description="Unable to connect to VPN from home network after update.",
            category=TicketCategory.IT,
            priority=TicketPriority.HIGH,
            status=TicketStatus.IN_PROGRESS,
        )
        session.add(ticket_it)
        await session.flush()

        onboarding_ticket = Ticket(
            employee_id=employee_user_id,
            assignee_id=manager_user_id,
            title="New joiner onboarding setup",
            description="Complete laptop, ID card and workspace setup for onboarding.",
            category=TicketCategory.ONBOARDING,
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
        )
        session.add(onboarding_ticket)
        await session.flush()

        session.add(OnboardingTask(ticket_id=onboarding_ticket.id, task_name="Issue laptop", is_completed=False))
        session.add(
            OnboardingTask(
                ticket_id=onboarding_ticket.id,
                task_name="Generate ID card",
                is_completed=False,
                due_date=date.today() + timedelta(days=2),
            )
        )

        for employee in all_employees:
            base_salary = float(employee.current_salary_usd) if employee.current_salary_usd is not None else 60000.0
            pan = employee.pan_number or f"PAN{employee.id:06d}"
            pf_uan = f"{100200300000 + employee.id}"
            esi_no = f"ESI{100000 + employee.id}"
            joining_month_start = employee.joining_date.replace(day=1)
            for month_offset in range(0, 6):
                month_start = month_start_n_months_ago(date.today().replace(day=1), month_offset)
                if month_start < joining_month_start:
                    continue
                # Keep slight month-to-month variance for realistic payroll history.
                gross = round(base_salary * (1 + ((employee.id + month_offset) % 3) * 0.005), 2)
                deductions = {
                    "pf": round(gross * 0.045, 2),
                    "esi": round(gross * 0.008, 2),
                    "tax": round(gross * 0.1, 2),
                }
                session.add(
                    PayrollRecord(
                        employee_id=employee.id,
                        month=month_start,
                        gross=gross,
                        deductions=deductions,
                        net=round(gross - sum(deductions.values()), 2),
                        pan=pan,
                        pf_uan=pf_uan,
                        esi_no=esi_no,
                    )
                )

        session.add(
            JobHistory(
                employee_id=employee_user_id,
                designation="Software Engineer I",
                business_unit="Engineering",
                department="Platform",
                start_date=date(2022, 1, 1),
                end_date=date(2023, 6, 30),
                is_current=False,
            )
        )
        session.add(
            JobHistory(
                employee_id=employee_user_id,
                designation="Software Engineer II",
                business_unit="Engineering",
                department="Platform",
                start_date=date(2023, 7, 1),
                end_date=None,
                is_current=True,
            )
        )

        poll = Poll(
            question="Which initiative should be prioritized next quarter?",
            options=["Improve leave workflow", "Automate payroll FAQ", "Manager dashboard revamp"],
            created_by=manager_user_id,
        )
        session.add(poll)
        await session.flush()
        session.add(PollResponse(poll_id=poll.id, employee_id=employee_user_id, option_index=0))
        session.add(PollResponse(poll_id=poll.id, employee_id=admin_user_id, option_index=1))

        policies = [
            ("Leave Policy", "Employees can avail casual, sick, and earned leave as per allocated balances."),
            ("Attendance Policy", "Clock-in should be completed before 9:30 AM on working days."),
            ("WFH Policy", "Work from home requests require manager approval for planned leaves."),
            ("Code of Conduct", "All employees must follow professional communication standards."),
            ("Travel Reimbursement", "Travel claims must be submitted within 15 days of return."),
            ("Data Security", "Sensitive company data must be accessed only on approved devices."),
            ("Laptop Usage", "Company laptops should not be shared with unauthorized users."),
            ("Information Classification", "Documents must be tagged based on internal classification guidelines."),
            ("Incident Reporting", "Security incidents should be reported to IT within 1 hour."),
            ("Onboarding SLA", "New joiners should receive system access within two business days."),
            ("ID Card Policy", "Employees must carry ID cards inside office premises."),
            ("Performance Review", "Mid-year and annual reviews are mandatory for all full-time staff."),
            ("Probation Policy", "Probation period is six months unless explicitly waived."),
            ("Grievance Policy", "Employees may raise grievances through HR ticket workflow."),
            ("Expense Policy", "Business expenses require valid invoices and manager approval."),
            ("Dress Code", "Employees should maintain business-casual attire in office."),
            ("Holiday Policy", "National holidays are predefined in annual HR calendar."),
            ("Comp Off Policy", "Comp-off requests are valid for 60 days from earning date."),
            ("Overtime Policy", "Overtime requires prior manager acknowledgement."),
            ("Separation Policy", "Exit clearance must complete before final settlement is processed."),
            ("Background Verification", "All hires are subject to background verification checks."),
            ("Communication Policy", "Official communication should use company-approved channels."),
        ]
        upload_dir = Path(settings.policy_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        for index, (title, content) in enumerate(policies, start=1):
            stored_name = f"seed_policy_{index:02d}.md"
            stored_path = upload_dir / stored_name
            body = f"# {title}\n\n{content}\n"
            raw = body.encode("utf-8")
            stored_path.write_bytes(raw)
            session.add(
                HRPolicy(
                    title=title,
                    category=title.split()[0].upper(),
                    content=None,
                    original_filename=stored_name,
                    file_path=str(stored_path),
                    mime_type="text/markdown",
                    size_bytes=len(raw),
                    uploaded_by=admin_user_id,
                    checksum=hashlib.sha256(raw).hexdigest(),
                    embedding=None,
                )
            )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
