"""PydanticAI agent definition. LLM = understanding + relevance; tools = data + filtering."""

import os
import json

from dotenv import load_dotenv
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.settings import ModelSettings

from .models import PaperAnswer, SearchConstraints
from .tools import filter_papers, search_openalex

load_dotenv()

MODEL = "groq:openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are a research scout. Find ONE paper matching the user's request.
Rules:
- Always call the search tool; never answer from memory.
- Citation counts and years must come from tool results only. Never invent them.
- If no paper satisfies the constraints, return found=False and explain why.
After the search tool returns, you must give your final answer as a PaperAnswer.
Never reply with an empty message.
"""

agent = Agent(
    MODEL,
    output_type=PromptedOutput(PaperAnswer),
    system_prompt=SYSTEM_PROMPT,
    retries=3,
    model_settings=ModelSettings(max_tokens=1500),
)

def slim(w: dict) -> dict:
    title = w.get("title") or w.get("display_name") or ""
    return {
        "title": title[:150],
        "year": w.get("publication_year"),
        "citations": w.get("cited_by_count"),
        "url": w.get("doi") or w.get("id"),
    }


@agent.tool_plain
def search_papers(
    topic: str,
    year: int | None = None,
    year_operator: str | None = None,
    citations: int | None = None,
    citation_operator: str | None = None,
) -> list[dict]:
    """Search OpenAlex for papers on a topic and filter by year/citation constraints.

    year_operator: 'before' | 'after' | 'in'. citation_operator: 'min' | 'max' | 'approx'.
    """
    constraints = SearchConstraints(
        topic=topic,
        year=year,
        year_operator=year_operator,
        citations=citations,
        citation_operator=citation_operator,
    )
    candidates = search_openalex(topic)
    matches = filter_papers(candidates, constraints)
    result = [slim(w) for w in matches[:5]]
    print(f"[search_papers] {len(candidates)} candidates, {len(matches)} matches, "f"~{len(json.dumps(result))} chars returned")
    return result