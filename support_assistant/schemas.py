"""Pydantic models for the /ask request and the structured answer response."""
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str


class AskResponse(BaseModel):
    answer: str = Field(..., description="The final natural-language answer.")
    sources: list[str] = Field(
        default_factory=list,
        description="Chunk/document IDs used to ground the answer. Empty for general_question answers.",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1.")
