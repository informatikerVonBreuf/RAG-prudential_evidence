from __future__ import annotations

import argparse
from pathlib import Path

from ingestion.promote import compile_runtime_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote several reviewed document caches")
    parser.add_argument("processed_directories", nargs="+", type=Path)
    parser.add_argument("--base", type=Path, default=Path("backend/app/data/corpus.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.base
    for processed in args.processed_directories:
        compile_runtime_corpus(base, processed, args.output)
        base = args.output
    print({"promoted_documents": len(args.processed_directories), "output": str(args.output)})


if __name__ == "__main__":
    main()
