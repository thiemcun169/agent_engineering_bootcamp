"""Request and response bodies of the API (Pydantic). They also become the OpenAPI schema shown in /docs."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # no user_id here: the user comes from the token
    message: str = Field(min_length=1, max_length=4000, examples=["Brief on how well heat pumps work below 0°C."])


class ResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject"]
    message: str | None = Field(None, max_length=500, description="Reason sent to the agent when rejecting.")


class User(BaseModel):
    user_id: str
    name: str


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$", examples=["alice"])
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=60, examples=["Alice"])


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class Thread(BaseModel):
    thread_id: str
    title: str
    created_at: str
    status: Literal["idle", "busy", "interrupted"] = "idle"


class Message(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str
    name: str | None = None  # tool name for role="tool"
    tool_calls: list[dict] = []


class ThreadDetail(Thread):
    messages: list[Message]
    interrupt: dict | None = None
