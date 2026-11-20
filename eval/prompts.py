"""Fixed manual evaluation cases, matching the numbering in prompts.txt."""

PROMPTS = [
    {
        "id": 1,
        "prompt": "Find a paper about LLM agents for software engineering published after 2022 with at least 100 citations.",
        "year_min": 2023, "citations_min": 100,
    },
    {
        "id": 2,
        "prompt": "Find a paper about retrieval-augmented generation published before 2021 with more than 500 citations.",
        "year_max": 2020, "citations_min": 501,
    },
    {
        "id": 3,
        "prompt": "Find a paper about deep learning published in 2015 with at least 1000 citations.",
        "year_min": 2015, "year_max": 2015, "citations_min": 1000,
    },
    {
        "id": 4,
        "prompt": "Find a recent paper about AI agents using tools.",
    },
    {
        "id": 5,
        "prompt": "Find a paper about transformers published before 2018 with at least 50000 citations.",
        "year_max": 2017, "citations_min": 50000,
    },
    {
        "id": 6,
        "prompt": "Find a paper about LLM agents for software engineering published after 2025 with at least 5000 citations.",
        "year_min": 2026, "citations_min": 5000,
    },
    {
        "id": 7,
        "prompt": "Find a paper about quantum error correction for knitting patterns published in 2019 with at least 200 citations.",
        "year_min": 2019, "year_max": 2019, "citations_min": 200,
    },
    {
        "id": 8,
        "prompt": "Find a highly cited paper about attention.",
    },
    {
        "id": 9,
        "prompt": "Find a paper about graph neural networks published in 2020 with fewer than 100 citations.",
        "year_min": 2020, "year_max": 2020, "citations_max": 99,
    },
    {
        "id": 10,
        "prompt": "Find a paper about vision transformers with around 3000 citations.",
        "citations_min": 2400, "citations_max": 3600,
    },
    {
        "id": 11,
        "prompt": "Find a paper on prompt injection attacks in LLM applications published after 2022.",
        "year_min": 2023,
    },
    {
        "id": 12,
        "prompt": "Find me a good paper.",
    },
]
