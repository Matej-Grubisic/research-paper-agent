"""CLI entry point: python -m src.main "your request" """

import sys

from .agent import agent


def main() -> None:
    prompt = " ".join(sys.argv[1:]) or input("Research request: ")
    result = agent.run_sync(prompt)
    print(result.output.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
