from __future__ import annotations

import argparse
from pathlib import Path

from ingestion.chunking import contextualize
from ingestion.exporters import read_result, write_canonical_markdown, write_result
from ingestion.indexing import build_embedding_cache


def update_period(processed_directory: Path, period: str) -> None:
    result = read_result(processed_directory)
    chunks = [
        chunk.model_copy(
            update={
                "period": period,
                "contextualized_text": contextualize(
                    title=result.manifest.title,
                    entity=chunk.entity or result.manifest.entity,
                    period=period,
                    section_path=chunk.section_path,
                    text=chunk.raw_text,
                ),
            }
        )
        for chunk in result.chunks
    ]
    tables = [table.model_copy(update={"period": period}) for table in result.tables]
    updated = result.model_copy(
        update={
            "manifest": result.manifest.model_copy(update={"period": period}),
            "chunks": chunks,
            "tables": tables,
        }
    )
    write_result(updated)
    write_canonical_markdown(
        updated, (processed_directory / "docling.md").read_text(encoding="utf-8")
    )
    build_embedding_cache(updated.chunks, processed_directory / "indexes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update reviewed cached-document metadata")
    parser.add_argument("processed_directory", type=Path)
    parser.add_argument("--period", required=True)
    args = parser.parse_args()
    update_period(args.processed_directory, args.period)
    print({"processed_directory": str(args.processed_directory), "period": args.period})


if __name__ == "__main__":
    main()
