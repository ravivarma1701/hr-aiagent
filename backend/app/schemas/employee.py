from datetime import date

from pydantic import BaseModel, EmailStr, Field


class EmployeeOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    department_id: int | None
    role: str
    status: str
    joining_date: date
    date_of_birth: date | None = None
    phone: str | None = None
    address: str | None = None
    blood_type: str | None = None
    occupancy: str | None = None


class EmployeeListOut(BaseModel):
    items: list[EmployeeOut]
    meta: dict


class EmployeeMeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    address: str | None = Field(default=None, min_length=5, max_length=255)
    blood_type: str | None = Field(default=None, min_length=2, max_length=8)
    occupancy: str | None = Field(default=None, min_length=2, max_length=60)
    date_of_birth: date | None = None


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    department_id: int | None = None
    role: str = Field(default="EMPLOYEE")
    joining_date: date
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    address: str | None = Field(default=None, min_length=5, max_length=255)
    blood_type: str | None = Field(default=None, min_length=2, max_length=8)
    occupancy: str | None = Field(default=None, min_length=2, max_length=60)
    job_title: str | None = Field(default=None, min_length=2, max_length=120)
    current_salary_usd: float | None = Field(default=None, ge=0)
    bank_name: str | None = Field(default=None, min_length=2, max_length=120)
    bank_account_number: str | None = Field(default=None, min_length=6, max_length=34)
    bank_account_name: str | None = Field(default=None, min_length=2, max_length=120)
    bank_branch: str | None = Field(default=None, min_length=2, max_length=120)
    bank_ifsc: str | None = Field(default=None, min_length=4, max_length=20)
    pan_number: str | None = Field(default=None, min_length=8, max_length=20)
    pan_name: str | None = Field(default=None, min_length=2, max_length=120)
    pan_dob: date | None = None
    pf_uan: str | None = Field(default=None, min_length=6, max_length=30)
    esi_no: str | None = Field(default=None, min_length=6, max_length=30)


class EmployeeJobTitleUpdate(BaseModel):
    designation: str = Field(min_length=2, max_length=120)
    effective_date: date | None = None
    business_unit: str | None = Field(default=None, min_length=2, max_length=120)
    department: str | None = Field(default=None, min_length=2, max_length=120)


class EmployeeProjectAssign(BaseModel):
    project_id: int
    role_on_project: str | None = Field(default=None, min_length=2, max_length=120)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=1000)
    status: str = Field(default="ONGOING")


class ProjectStatusUpdate(BaseModel):
    status: str


class EmployeeAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    department_id: int | None = None
    role: str | None = None
    joining_date: date | None = None
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, min_length=6, max_length=20)
    occupancy: str | None = Field(default=None, min_length=2, max_length=60)
    current_salary_usd: float | None = Field(default=None, ge=0)
    bank_name: str | None = Field(default=None, min_length=2, max_length=120)
    bank_account_number: str | None = Field(default=None, min_length=6, max_length=34)
    bank_account_name: str | None = Field(default=None, min_length=2, max_length=120)
    bank_branch: str | None = Field(default=None, min_length=2, max_length=120)
    bank_ifsc: str | None = Field(default=None, min_length=4, max_length=20)
    pan_number: str | None = Field(default=None, min_length=8, max_length=20)
    pan_name: str | None = Field(default=None, min_length=2, max_length=120)
    pan_dob: date | None = None
    pf_uan: str | None = Field(default=None, min_length=6, max_length=30)
    esi_no: str | None = Field(default=None, min_length=6, max_length=30)
    job_title: str | None = Field(default=None, min_length=2, max_length=120)
