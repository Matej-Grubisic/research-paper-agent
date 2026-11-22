# Research Scout Agent

AI agent (PydanticAI) that finds a research paper matching a topic plus year and citation constraints, using the OpenAlex API for real metadata. Compulsory Assignment #2, Machine Learning (E2026).

## Setup

Requires Python 3.10+.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure the API key
cp .env.example .env             # Windows: copy .env.example .env
# Edit .env: set MODEL and the matching API key (never commit .env)
```

## Run

```bash
python -m src.main "Find a paper about LLM agents for software engineering published after 2022 with at least 100 citations"
```

The CLI prints progress for Groq requests, OpenAlex searches, and rate-limit
waits. Requests have a 30-second network timeout; each agent attempt has a
120-second run timeout. Groq transport retries are disabled so errors surface
promptly. Invalid JSON can still trigger up to three agent attempts.

## Project structure

```
src/
  models.py   Pydantic models (constraints, Paper, structured answer)
  tools.py    OpenAlex search + deterministic filtering (no LLM)
  agent.py    PydanticAI agent, system prompt, tool registration
  main.py     CLI entry point
eval/
  prompts.py  Evaluation prompts (>= 10 required)
```

## Agent workflow

| Step | Handled by |
|------|-----------|
| Parse request, extract constraints | LLM |
| Search OpenAlex | Deterministic tool |
| Filter by year / citations | Deterministic code |
| Judge relevance, pick best paper | LLM |
| Return structured answer + uncertainty | LLM (validated by Pydantic) |

## LLM choice

We used **GPT-OSS 120B through Groq** (`groq:openai/gpt-oss-120b`, not xAI's Grok)
because it supports tool calling, works with PydanticAI, and can interpret search
constraints and judge paper relevance.

## Evaluation

We ran **12 prompts**, covering broad and narrow topics,
different year and citation constraints, difficult searches, and vague requests.
The agent was left unchanged during the run.

Following [Pydantic Evals](https://ai.pydantic.dev/evals/) and
[OpenAI's evaluation guidance](https://platform.openai.com/docs/guides/evaluation-best-practices),
we checked both answers and tool calls. Each case was assessed for relevance,
year, citations, valid sources, grounded claims, and a useful explanation.
Numeric checks used the original request, including strict comparisons such as
"fewer than 100". Qualitative scores were reviewed by the coding assistant,
**not an independent human reviewer**.

### Results

| # | Request | Result | Search calls |
|---|---------|--------|--------------|
| 1 | LLM software-engineering agents after 2022 | Pass | 1 |
| 2 | RAG before 2021, more than 500 citations | Pass | 1 |
| 3 | Deep learning in 2015 | Unsupported description | 1 |
| 4 | Recent tool-using AI agents | Did not explain "recent" | 1 |
| 5 | Transformers before 2018, at least 50,000 citations | Pass | 1 |
| 6 | Software agents after 2025, at least 5,000 citations | Pass: explained no match found | 4 |
| 7 | Quantum error correction for knitting | Execution error | 2 |
| 8 | Highly cited attention paper | Unsupported description | 1 |
| 9 | GNNs in 2020, fewer than 100 citations | Pass | 1 |
| 10 | Vision transformers, around 3,000 citations | Pass | 1 |
| 11 | Prompt injection after 2022 | Execution error | 1 |
| 12 | "Find me a good paper" | Execution error | 0 |

**6/12 passed all applicable checks.** Nine produced final answers: eight papers
and one explained rejection. All eight selected papers matched independent
OpenAlex checks of their title, year, citation count, and DOI/URL.

Among completed answers, relevance passed 8/8, explicit year checks 5/5,
citation checks 6/6, sources 8/8, grounding 7/9, and explanation usefulness 8/9.
These counts exclude errors and inapplicable checks; the overall result does not.
A rejection only passes if it is grounded and useful, not merely because the
search returned nothing.

The full prompts, outputs, tool evidence, citation snapshots, and scores are in
[`eval/`](eval). See [`scored_results.json`](eval/scored_results.json) for all six
scores per case and [`reviews.json`](eval/reviews.json) for the reasoning.
This was one small run, so results may vary and citation counts will change.

### Run the evaluation

```powershell
# Save a new run without overwriting the recorded evidence.
python -m eval.run --output eval/new_run.json --delay 65

# Recalculate scores for the original run and its saved reviews.
python -m eval.score
```

New runs need their own source checks and qualitative reviews. The recorded
environment and dependency versions are saved in `eval/recorded_run.json`.

## Reflection

The strongest part was finding real papers with correct metadata. All eight
paper answers needed just one search, and the agent rejected a general LLM
survey when it did not clearly match the software-agent request.

The main weakness was output reliability. Three cases failed because the model
tried to call a nonexistent `JSON` tool, including the request that should have
asked for a topic. It also sometimes changed search constraints: one year range
became narrower, and "more than 500" became "at least 500". Those selected papers
still qualified, but the extraction was not fully reliable.

We found no invented selected papers or incorrect citation counts. However, two
answers added descriptions that were not supported by the supplied evidence
because their abstracts were missing. That is a grounding failure, even if the
claims happen to be true.

There were **15 searches in total: 1.25 per case, with a maximum of four**.
The four-search rejection kept retrieving the same survey, so those extra calls
were not especially useful. Search calls are not the same as model API requests.

Deterministic filtering, Pydantic validation, and checking the selected title
helped protect the answers, but did not catch unsupported explanations or
misread constraints. With more time, we would fix the output protocol, verify
the original constraints independently, enforce search limits in code, and
handle missing abstracts and vague requests more carefully. We would also repeat
the evaluation and get a human review of the qualitative scores.
