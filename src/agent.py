"""PydanticAI agent definition. LLM = understanding + relevance; tools = data + filtering."""

import os
import json
import re

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic import ValidationError
from pydantic_ai.settings import ModelSettings

from .models import PaperAnswer, SearchConstraints
from .tools import filter_papers, search_openalex

load_dotenv()

MODEL = "groq:openai/gpt-oss-120b"

SYSTEM_PROMPT = f"""You are a research scout. Find ONE paper matching the user's request.
Rules:
- Always call the search_papers tool; never answer from memory.
- Call the search tool at most four times.
- Pass the user's full topic phrase as `topic` (e.g. "LLM agents for software engineering").
- Citation counts and years must come from tool results only. Never invent them.
- Base your explanation only on the title and abstract returned by the tool.
- If no paper satisfies the constraints, set found=false and explain why.
- If the request has no usable topic, set found=false and ask for a topic.

When you are done searching, reply with ONLY a JSON object matching this schema,
as plain text. Do NOT call any tool to deliver it (there is no "json" tool).
Schema: {json.dumps(PaperAnswer.model_json_schema())}
"""

agent = Agent(
    MODEL,
    output_type=str,
    system_prompt=SYSTEM_PROMPT,
    retries=3,
    model_settings=ModelSettings(max_tokens=1500),
)

#table formatting 
SEARCH_LOG: list[list[dict]] = []  # one entry per search_papers call

def verify_answer(out: PaperAnswer) -> tuple[PaperAnswer, bool]:
    """Check the LLM's pick against tool results. Returns (answer, hallucinated)."""
    if not out.found:
        return out, False
    for batch in SEARCH_LOG:
        for p in batch:
            if p["title"].strip().lower() == (out.title or "").strip().lower():
                # Overwrite with the tool's data so the LLM can't alter facts.
                out.authors = p["authors"]
                out.year = p["year"]
                out.citation_count = p["citation_count"]
                out.citation_source = p["citation_source"]
                out.url = p["url"]
                return out, False
    return PaperAnswer(
        found=False,
        explanation=f"Rejected: '{out.title}' was not in the tool results.",
    ), True
    
def run_agent(prompt: str, attempts: int = 3) -> PaperAnswer:
    """Run the agent and parse its text reply into a PaperAnswer (deterministic step)."""
    SEARCH_LOG.clear()
    text = prompt
    last_error = ""
    for _ in range(attempts):
        result = agent.run_sync(text)
        raw = result.output
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        try:
            if not match:
                raise ValueError("no JSON object found in reply")
            return PaperAnswer.model_validate_json(match.group(0))
        except (ValidationError, ValueError) as e:
            last_error = str(e)
            text = (f"{prompt}\n\nYour previous reply was not valid JSON for the "
                    f"schema ({last_error[:200]}). Reply again with only the JSON object.")
    return PaperAnswer(found=False, explanation=f"Agent failed to produce valid output: {last_error[:200]}")    


def print_table(results: list[dict]) -> None:
    """Print results as a simple ASCII table."""
    if not results:
        print("(no results)")
        return

    rows = [
        (
            str(i),
            (r.get("title") or "")[:60],
            str(r.get("year") or ""),
            str(r.get("citation_count") if r.get("citation_count") is not None else ""),
            ", ".join(r.get("authors") or [])[:30],
        )
        for i, r in enumerate(results, 1)
    ]
    headers = ("#", "Title", "Year", "Cites", "Authors")
    widths = [max(len(h), *(len(row[c]) for row in rows)) for c, h in enumerate(headers)]

    def fmt(cells):
        return " | ".join(cell.ljust(w) for cell, w in zip(cells, widths))

    print(fmt(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))

def slim(w: dict) -> dict:
    title = w.get("title") or w.get("display_name") or ""
    return {
        "title": title[:150],
        "year": w.get("publication_year"),
        "citations": w.get("cited_by_count"),
        "url": w.get("doi") or w.get("id"),
        "authors": [
            a["author"]["display_name"]
            for a in (w.get("authorships") or [])[:5]
            if a.get("author")
        ],
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
    candidates = search_openalex(constraints)
    matches = filter_papers(candidates, constraints)
    result = [p.model_dump() for p in matches[:5]]
    SEARCH_LOG.append(result)
    return result