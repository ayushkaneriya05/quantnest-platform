from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=6000)
    run_token: str = Field(min_length=1, max_length=1000)
    as_of: str
    context: dict[str, Any]
    builder_schema: dict[str, Any]
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=6)


class ResearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1, max_length=12000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=8)
    draft_evidence_id: str | None = None
    next_steps: list[str] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=8)
    clarification_questions: list[str] = Field(default_factory=list, max_length=8)
    artifact_refs: list[str] = Field(default_factory=list, max_length=8)
    proposed_actions: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
