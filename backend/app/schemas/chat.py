from pydantic import BaseModel, Field, field_validator


class ChatHistoryMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str = Field(max_length=4000)

    @field_validator("role")
    @classmethod
    def _validate_role(cls, value: str) -> str:
        if value not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        return value


class ChatSessionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)


class ChatMessageCreate(BaseModel):
    role: str = Field(min_length=3, max_length=20)
    content: str = Field(min_length=1, max_length=4000)


# --- Phase 4: AI copilot chat endpoints ------------------------------------


class ChatPolicyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class PolicySource(BaseModel):
    title: str
    category: str
    filename: str


class ChatPolicyResponse(BaseModel):
    answer: str
    sources: list[PolicySource]


class ChatSQLRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatSQLResponse(BaseModel):
    answer: str
    sql: str | None = None
    rows: list[dict]


class PendingAction(BaseModel):
    tool_name: str
    arguments: dict


class ChatActionRequest(BaseModel):
    message: str = Field(default="", max_length=2000)
    confirm: bool = False
    pending_action: PendingAction | None = None
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=20)


class ChatActionResponse(BaseModel):
    answer: str
    action: str | None = None
    status: str
    result: dict | list | None = None
    pending_action: PendingAction | None = None


class ChatRouterRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=20)


class ChatRouterResponse(BaseModel):
    intent: str
    confidence: float
    reason: str
