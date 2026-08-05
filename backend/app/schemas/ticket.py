from datetime import date, datetime

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=5, max_length=5000)
    category: str
    priority: str


class TicketAssign(BaseModel):
    assignee_id: int


class TicketStatusUpdate(BaseModel):
    status: str


class OnboardingTaskCreate(BaseModel):
    task_name: str = Field(min_length=3, max_length=200)
    due_date: date | None = None


class TicketOut(BaseModel):
    id: int
    employee_id: int
    assignee_id: int | None
    title: str
    description: str
    category: str
    priority: str
    status: str
    created_at: datetime
