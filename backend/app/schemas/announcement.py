from datetime import datetime

from pydantic import BaseModel, Field


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    body: str = Field(min_length=5, max_length=5000)


class AnnouncementRead(BaseModel):
    id: int
    title: str
    body: str
    author_id: int
    author_name: str
    created_at: datetime
