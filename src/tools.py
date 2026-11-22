"""Deterministic tool code: OpenAlex search and constraint filtering. No LLM here."""

import os
import time
import logging

import httpx

from .models import Paper, SearchConstraints

OPENALEX_URL = "https://api.openalex.org/works"
APPROX_TOLERANCE = 0.2  # "approx N" citations means within +/-20% of N
FETCH_SIZE = 50
logger = logging.getLogger(__name__)


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
        logger.info("OpenAlex: sending request %s/%s (30s request timeout).", attempt + 1, max_tries)
        started = time.monotonic()
        try:
            resp = httpx.get(url, params=params, timeout=30)
        except httpx.RequestError as error:
            logger.error("OpenAlex: request failed (%s).", type(error).__name__)
            raise
        logger.info("OpenAlex: HTTP %s after %.1fs.", resp.status_code, time.monotonic() - started)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        if attempt == max_tries - 1:
            break
        wait = float(resp.headers.get("Retry-After", 2**attempt))
        logger.warning("OpenAlex: rate limited; waiting %.1fs before retry.", wait)
        time.sleep(wait)
    raise RuntimeError("OpenAlex still rate-limiting after retries")


def _bounds(c: SearchConstraints):
    """Turn constraints into inclusive (year_lo, year_hi, cite_lo, cite_hi).
    Used by BOTH the API query and the code filter, so they always agree."""
    y_lo = y_hi = c_lo = c_hi = None
    if c.year is not None:
        op = c.year_operator or "in"
        if op == "after":
            y_lo = c.year + 1          # "after 2022" -> 2023+
        elif op == "before":
            y_hi = c.year - 1          # "before 2021" -> 2020 and earlier
        else:
            y_lo = y_hi = c.year
    if c.citations is not None:
        op = c.citation_operator or "min"
        if op == "min":
            c_lo = c.citations         # "at least N" -> >= N
        elif op == "max":
            c_hi = c.citations
        else:
            c_lo = int(c.citations * (1 - APPROX_TOLERANCE))
            c_hi = int(c.citations * (1 + APPROX_TOLERANCE))
    return y_lo, y_hi, c_lo, c_hi


def _api_filter(c: SearchConstraints) -> str:
    """Best-effort pre-filter sent to OpenAlex. Code re-checks everything afterwards."""
    y_lo, y_hi, c_lo, c_hi = _bounds(c)
    parts = []
    if y_lo is not None and y_lo == y_hi:
        parts.append(f"publication_year:{y_lo}")
    elif y_lo is not None:
        parts.append(f"publication_year:>{y_lo - 1}")
    elif y_hi is not None:
        parts.append(f"publication_year:<{y_hi + 1}")
    # Only one side of the citation range goes to the API; code enforces the other.
    if c_lo is not None:
        parts.append(f"cited_by_count:>{c_lo - 1}")
    elif c_hi is not None:
        parts.append(f"cited_by_count:<{c_hi + 1}")
    return ",".join(parts)


def _to_paper(w: dict) -> Paper:
    abstract = _rebuild_abstract(w.get("abstract_inverted_index"))
    return Paper(
        title=w.get("title") or w.get("display_name") or "",
        authors=[
            a["author"]["display_name"]
            for a in (w.get("authorships") or [])[:5]
            if a.get("author")
        ],
        year=w.get("publication_year"),
        citation_count=w.get("cited_by_count"),
        url=w.get("doi") or w.get("id"),
        abstract=abstract[:300] if abstract else None,
    )


def search_openalex(c: SearchConstraints) -> list[Paper]:
    params = {
        "search": c.topic,
        "per_page": FETCH_SIZE,  # default sort = relevance
        "select": "id,doi,title,display_name,publication_year,cited_by_count,"
                  "authorships,abstract_inverted_index",
    }
    api_filter = _api_filter(c)
    if api_filter:
        params["filter"] = api_filter
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    resp = get_with_retry(OPENALEX_URL, params=params)
    return [_to_paper(w) for w in resp.json()["results"]]


def filter_papers(papers: list[Paper], c: SearchConstraints) -> list[Paper]:
    """Deterministically drop papers that violate year / citation constraints."""
    y_lo, y_hi, c_lo, c_hi = _bounds(c)
    keep = []
    for p in papers:
        if (y_lo is not None or y_hi is not None) and p.year is None:
            continue
        if (c_lo is not None or c_hi is not None) and p.citation_count is None:
            continue
        if y_lo is not None and p.year < y_lo:
            continue
        if y_hi is not None and p.year > y_hi:
            continue
        if c_lo is not None and p.citation_count < c_lo:
            continue
        if c_hi is not None and p.citation_count > c_hi:
            continue
        keep.append(p)
    return keep