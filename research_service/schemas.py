from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    parameters: dict[str, Any]


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1)
    run_token: str = Field(min_length=1, max_length=1000)
    as_of: str
    context: dict[str, Any]
    tools: list[ToolDefinition] = Field(default_factory=list)
    deadline: float
    history: list[dict[str, Any]] = Field(default_factory=list)


class ResearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    draft_evidence_id: str | None = None
    next_steps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    proposed_actions: list[dict[str, Any]] = Field(default_factory=list)

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
        return [item for item in value if isinstance(item, dict)]


class WebResearchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1)
    urls: list[str] = Field(default_factory=list)

    @field_validator('urls')
    @classmethod
    def public_urls(cls, values):
        from urllib.parse import urlparse
        if any(urlparse(value).scheme not in ('http', 'https') or not urlparse(value).hostname for value in values):
            raise ValueError('Use public HTTP or HTTPS URLs for provider retrieval.')
        return values
