"""CLI entry point: python -m src.main "your request" """

import sys

from .agent import SEARCH_LOG, print_table, run_agent, verify_answer


def main() -> None:
    prompt = " ".join(sys.argv[1:]) or input("Research request: ")
    out, hallucinated = verify_answer(run_agent(prompt))

    print(f"\nTool calls: {len(SEARCH_LOG)}")

    if SEARCH_LOG:
        print("\nTop candidates (last search):")
        print_table(SEARCH_LOG[-1])

    if hallucinated:
        print("\n[!] The model picked a paper that was not in the tool results.")

    if not out.found:
        print(f"\nNo matching paper found.\n{out.explanation}")
        return

    print("\nSelected paper:")
    print_table([{
        "title": out.title,
        "year": out.year,
        "citation_count": out.citation_count,
        "authors": out.authors,
    }])
    print(f"\nCitation source: {out.citation_source}")
    print(f"URL: {out.url}")
    print(f"\nWhy it matches: {out.explanation}")


if __name__ == "__main__":
    main()