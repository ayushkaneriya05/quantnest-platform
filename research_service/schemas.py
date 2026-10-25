from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    parameters: dict[str, Any]


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=6000)
    run_token: str = Field(min_length=1, max_length=1000)
    as_of: str
    context: dict[str, Any]
    tools: list[ToolDefinition] = Field(default_factory=list)
    deadline: float
    max_tool_calls: int = Field(ge=0, le=8)
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=6)


ShortText = Annotated[str, Field(max_length=2000)]


class ResearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1, max_length=12000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=8)
    draft_evidence_id: str | None = None
    next_steps: list[ShortText] = Field(default_factory=list, max_length=8)
    limitations: list[ShortText] = Field(default_factory=list, max_length=8)
    clarification_questions: list[ShortText] = Field(default_factory=list, max_length=8)
    artifact_refs: list[str] = Field(default_factory=list, max_length=8)
    proposed_actions: list[dict[str, Any]] = Field(default_factory=list, max_length=3)

    @field_validator("answer")
    @classmethod
    def nonempty_answer(cls, value):
        if not value.strip():
            raise ValueError("Provide a nonempty answer.")
        return value

    @field_validator("proposed_actions", mode="before")
    @classmethod
    def optional_actions(cls, value):
        # Action proposals are optional. Django independently validates their
        # meaning; malformed proposals must not discard a well-formed answer.
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)][:3]
