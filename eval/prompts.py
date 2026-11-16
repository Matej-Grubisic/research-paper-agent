"""Evaluation prompts (need >= 10). Fill in expectations as you build the evaluator."""

PROMPTS = [
    # broad topic
    {"id": 1, "prompt": "Find a paper about machine learning published after 2020 with at least 1000 citations."},
    # narrow topic
    {"id": 2, "prompt": "Find a paper about LLM agents for software engineering published after 2022 with at least 100 citations."},
    # before-year constraint
    {"id": 3, "prompt": "Find a paper about retrieval-augmented generation published before 2021 with more than 500 citations."},
    # exact year
    {"id": 4, "prompt": "Find a paper about diffusion models published in 2021."},
    # no constraints on citations
    {"id": 5, "prompt": "Find a recent paper about AI agents using tools and say whether it helps someone building autonomous software agents."},
    # TODO: add 5+ more covering: max citations, approximate citations,
    # no-good-paper-exists cases, and ambiguous requests.
]
