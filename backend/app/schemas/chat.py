from pydantic import BaseModel, Field


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


class ChatActionResponse(BaseModel):
    answer: str
    action: str | None = None
    status: str
    result: dict | list | None = None
    pending_action: PendingAction | None = None


class ChatRouterRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatRouterResponse(BaseModel):
    intent: str
    confidence: float
    reason: str
