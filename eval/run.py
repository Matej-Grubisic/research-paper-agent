"""Record live, unmodified-agent runs for subsequent criterion-based review."""

import argparse
import copy
import importlib.metadata
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from src import agent as agent_module
from src import tools

from .prompts import PROMPTS


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=65, help="Seconds between cases")
    parser.add_argument("--output", type=Path, default=Path("eval") / "recorded_run.json")
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.output.exists():
        parser.error("Output already exists; choose a different --output to preserve evidence")

    report = {
        "started_at": timestamp(),
        "model": agent_module.MODEL,
        "python": platform.python_version(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("pydantic-ai-slim", "pydantic", "groq", "httpx")
        },
        "delay_seconds": args.delay,
        "cases": [],
    }
    original_search = agent_module.search_openalex
    original_get = tools.get_with_retry
    original_run = agent_module.agent.run_sync
    args.output.parent.mkdir(parents=True, exist_ok=True)

    for index, case in enumerate(PROMPTS):
        if index:
            time.sleep(args.delay)
        record = {
            "id": case["id"],
            "prompt": case["prompt"],
            "expected_bounds": {key: value for key, value in case.items() if key not in ("id", "prompt")},
            "started_at": timestamp(),
            "searches": [],
            "model_runs": [],
        }

        def capture_get(*positional, **kwargs):
            response = original_get(*positional, **kwargs)
            record["searches"][-1]["source_records"] = [
                {
                    "id": work.get("id"),
                    "doi": work.get("doi"),
                    "title": work.get("title"),
                    "year": work.get("publication_year"),
                    "citation_count": work.get("cited_by_count"),
                }
                for work in response.json()["results"]
            ]
            return response

        def capture_search(constraints):
            search = {"requested_at": timestamp(), "constraints": constraints.model_dump()}
            record["searches"].append(search)
            papers = original_search(constraints)
            search["candidates"] = [paper.model_dump() for paper in papers]
            return papers

        def capture_run(*positional, **kwargs):
            result = original_run(*positional, **kwargs)
            record["model_runs"].append({
                "raw_output": result.output,
                "messages": json.loads(result.all_messages_json()),
            })
            return result

        started = time.monotonic()
        try:
            with (
                patch.object(tools, "get_with_retry", capture_get),
                patch.object(agent_module, "search_openalex", capture_search),
                patch.object(agent_module.agent, "run_sync", capture_run),
            ):
                answer = agent_module.run_agent(case["prompt"])
            record["unverified_answer"] = copy.deepcopy(answer.model_dump())
            answer, rejected = agent_module.verify_answer(answer)
            record["answer"] = answer.model_dump()
            record["invented_title_rejected"] = rejected
            record["status"] = (
                "invalid_output"
                if answer.explanation.startswith("Agent failed to produce valid output:")
                else "completed"
            )
        except Exception as error:
            # Keep failures as explicit evaluation outcomes, not successful rejections.
            message = str(error)
            for name in ("GROQ_API_KEY", "OPENALEX_API_KEY"):
                secret = os.environ.get(name)
                if secret:
                    message = message.replace(secret, "[REDACTED]")
            record["status"] = "execution_error"
            record["error"] = {"type": type(error).__name__, "message": message}
        record["duration_seconds"] = round(time.monotonic() - started, 3)
        record["completed_search_calls"] = len(agent_module.SEARCH_LOG)
        record["attempted_search_calls"] = len(record["searches"])
        record["tool_results"] = copy.deepcopy(agent_module.SEARCH_LOG)
        report["cases"].append(record)
        report["updated_at"] = timestamp()
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        print(
            f"Case {case['id']}: {record['status']}; "
            f"searches={record['attempted_search_calls']}; "
            f"found={record.get('answer', {}).get('found')}",
            flush=True,
        )
    report["finished_at"] = timestamp()
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
