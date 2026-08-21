from __future__ import annotations

import argparse
import json
from pathlib import Path

from ingestion.pipeline import ingest_pdf


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Ingestion documentaire hors ligne")
    command.add_argument("path", type=Path)
    command.add_argument("--document-id", required=True)
    command.add_argument("--title", required=True)
    command.add_argument("--entity", required=True)
    command.add_argument("--period", required=True)
    command.add_argument("--source-url", required=True)
    command.add_argument("--output-root", type=Path, default=Path("data/processed"))
    return command


def main() -> None:
    args = parser().parse_args()
    result = ingest_pdf(
        path=args.path,
        document_id=args.document_id,
        title=args.title,
        entity=args.entity,
        period=args.period,
        source_url=args.source_url,
        output_root=args.output_root,
    )
    print(json.dumps({
        "manifest": result.manifest.model_dump(mode="json"),
        "pages": len(result.pages),
        "tables": len(result.tables),
        "facts": sum(len(table.cells) for table in result.tables),
        "chunks": len(result.chunks),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
