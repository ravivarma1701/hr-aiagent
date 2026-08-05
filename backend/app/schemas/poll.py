from pydantic import BaseModel, Field


class PollCreate(BaseModel):
    question: str = Field(min_length=5, max_length=300)
    options: list[str] = Field(min_length=2, max_length=6)


class PollVote(BaseModel):
    option_index: int = Field(ge=0)
