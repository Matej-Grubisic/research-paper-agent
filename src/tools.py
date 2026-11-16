"""Deterministic tool code: OpenAlex search and constraint filtering. No LLM here."""

import os

import httpx
import time

from .models import Paper, SearchConstraints

OPENALEX_URL = "https://api.openalex.org/works"


def _rebuild_abstract(inverted_index: dict | None) -> str | None:
    """OpenAlex stores abstracts as an inverted index; turn it back into text."""
    if not inverted_index:
        return None
    positions = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


def get_with_retry(url, params=None, max_tries=5):
    for attempt in range(max_tries):
        resp = httpx.get(url, params=params, timeout=30)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        wait = float(resp.headers.get("Retry-After", 2 ** attempt))
        time.sleep(wait)
    raise RuntimeError("OpenAlex still rate-limiting after retries")

def search_openalex(topic: str):
    params = {
        "search": topic,
        "filter": "from_publication_date:2023-01-01,cited_by_count:>99",
        "sort": "cited_by_count:desc",
        "per_page": 10,
        "api_key": os.environ["OPENALEX_API_KEY"],
    }
    resp = get_with_retry("https://api.openalex.org/works", params=params)
    return resp.json()["results"]


def filter_papers(papers: list[Paper], c: SearchConstraints) -> list[Paper]:
    """Deterministically drop papers that violate year / citation constraints."""
    # TODO: implement year and citation filtering (before/after/in, min/max/approx)
    return papers
