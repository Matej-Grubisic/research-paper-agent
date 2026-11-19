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

_TODO: which provider/model, current free-tier limits, why it was chosen._

## Evaluation

_TODO: how agents can be evaluated (research + justification), method, results table for the 10+ prompts._

## Reflection

_TODO: what worked, what failed, tool call frequency, hallucinations, safeguards, improvements._

## Group contributions


