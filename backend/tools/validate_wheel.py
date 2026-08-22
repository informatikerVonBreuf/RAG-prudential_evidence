from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def validate(dist_directory: Path = Path("dist")) -> None:
    wheels = sorted(dist_directory.glob("prudential_evidence_lab-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected exactly one project wheel in {dist_directory}, got {wheels}")
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
    required = {
        "app/data/corpus.json",
        "app/data/indexes/foyer_group_qrt_2025_gemini/embedding_manifest.json",
        "app/data/indexes/foyer_group_qrt_2025_gemini/embeddings.json",
        "app/data/indexes/foyer_group_qrt_2025_gemini/query_embeddings.json",
    }
    missing = sorted(required - names)
    if missing:
        raise SystemExit(f"Wheel is missing runtime artifacts: {', '.join(missing)}")
    print(f"Wheel valid: {wheels[0].name}, {len(required)} runtime artifacts present")


if __name__ == "__main__":
    validate(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist"))
