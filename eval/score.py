"""Combine recorded qualitative reviews with independent numeric/source checks."""

import json
from pathlib import Path
from statistics import mean


CRITERIA = ("relevant", "year", "citations", "source", "grounded", "useful")


def check_bounds(value: int | None, bounds: dict, prefix: str) -> str:
    low, high = bounds.get(f"{prefix}_min"), bounds.get(f"{prefix}_max")
    if low is None and high is None:
        return "n/a"
    if value is None:
        return "fail"
    return "pass" if (low is None or value >= low) and (high is None or value <= high) else "fail"


def main() -> None:
    directory = Path(__file__).parent
    run = json.loads((directory / "recorded_run.json").read_text(encoding="utf-8"))
    reviews = json.loads((directory / "reviews.json").read_text(encoding="utf-8"))
    sources = json.loads((directory / "source_checks.json").read_text(encoding="utf-8"))
    if reviews["run_started_at"] != run["started_at"]:
        raise ValueError("Qualitative reviews belong to a different run; review the new evidence first")
    by_id = {review["id"]: review for review in reviews["cases"]}
    source_by_id = {source["case_id"]: source for source in sources}
    if set(by_id) != {case["id"] for case in run["cases"]}:
        raise ValueError("Every recorded case must have exactly one qualitative review")
    results = []
    for case in run["cases"]:
        review = by_id[case["id"]]
        if case["status"] != "completed":
            scores = {criterion: "error" for criterion in CRITERIA}
        else:
            answer = case["answer"]
            scores = {criterion: review[criterion] for criterion in ("relevant", "grounded", "useful")}
            if answer["found"]:
                scores["year"] = check_bounds(answer["year"], case["expected_bounds"], "year")
                scores["citations"] = check_bounds(answer["citation_count"], case["expected_bounds"], "citations")
                source = source_by_id.get(case["id"], {})
                scores["source"] = "pass" if source.get("http_status") == 200 and source.get("matches_answer") else "fail"
            else:
                scores.update(year="n/a", citations="n/a", source="n/a")
        results.append({
            "id": case["id"],
            "scores": scores,
            "overall": "pass" if all(value in ("pass", "n/a") for value in scores.values()) else "fail",
            "notes": review["notes"],
        })
    summary = {
        "cases": len(results),
        "completed": sum(case["status"] == "completed" for case in run["cases"]),
        "execution_errors": sum(case["status"] == "execution_error" for case in run["cases"]),
        "paper_answers": sum(case.get("answer", {}).get("found", False) for case in run["cases"]),
        "passed": sum(result["overall"] == "pass" for result in results),
        "attempted_search_calls": sum(case["attempted_search_calls"] for case in run["cases"]),
        "completed_search_calls": sum(case["completed_search_calls"] for case in run["cases"]),
        "mean_search_calls_all_cases": mean(case["attempted_search_calls"] for case in run["cases"]),
        "mean_search_calls_completed_cases": mean(
            case["attempted_search_calls"] for case in run["cases"] if case["status"] == "completed"
        ),
        "max_search_calls": max(case["attempted_search_calls"] for case in run["cases"]),
        "invented_title_rejections": sum(case.get("invented_title_rejected", False) for case in run["cases"]),
        "criteria": {
            criterion: {
                status: sum(result["scores"][criterion] == status for result in results)
                for status in ("pass", "fail", "n/a", "error")
            }
            for criterion in CRITERIA
        },
    }
    report = {
        "run_started_at": run["started_at"],
        "review_method": reviews["review_method"],
        "summary": summary,
        "cases": results,
    }
    (directory / "scored_results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
