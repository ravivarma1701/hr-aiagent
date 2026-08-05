from datetime import date

from pydantic import BaseModel, Field


class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    is_half_day: bool = False
    half_day_period: str | None = None
    reason: str = Field(min_length=3, max_length=500)


class LeaveActionRequest(BaseModel):
    comment: str | None = None
