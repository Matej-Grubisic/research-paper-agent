"""Pydantic models: parsed constraints, tool results and the final structured answer."""

from typing import Literal

from pydantic import BaseModel, Field


class SearchConstraints(BaseModel):
    """Constraints extracted from the user's request (LLM step)."""

    topic: str
    year: int | None = None
    year_operator: Literal["before", "after", "in"] | None = None
    citations: int | None = None
    citation_operator: Literal["min", "max", "approx"] | None = None


class Paper(BaseModel):
    """One candidate paper as returned by the search tool."""

    title: str
    authors: list[str]
    year: int | None
    citation_count: int | None
    citation_source: str = "OpenAlex"
    url: str | None
    abstract: str | None = None


class PaperAnswer(BaseModel):
    """Final structured answer returned by the agent."""

    found: bool = Field(description="False if no paper satisfies the constraints")
    title: str | None = None
    authors: list[str] = []
    year: int | None = None
    citation_count: int | None = None
    citation_source: str | None = None
    url: str | None = None
    explanation: str = Field(description="Why the paper matches, or why nothing was found")
