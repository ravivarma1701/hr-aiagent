from datetime import date, time

from pydantic import BaseModel


class AttendanceLogOut(BaseModel):
    id: int
    date: date
    clock_in: time | None
    clock_out: time | None
    status: str
    work_mode: str | None = None
    punctuality: str | None = None


class ClockInRequest(BaseModel):
    mode: str = "PRESENT"
