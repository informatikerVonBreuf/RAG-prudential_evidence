from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.store.artifacts import ArtifactStore  # noqa: E402


def validate() -> None:
    store = ArtifactStore()
    document_ids = {document.id for document in store.documents}
    chunk_ids: set[str] = set()
    errors: list[str] = []
    for chunk in store.chunks:
        if chunk.id in chunk_ids:
            errors.append(f"chunk dupliqué: {chunk.id}")
        chunk_ids.add(chunk.id)
        if chunk.document_id not in document_ids:
            errors.append(f"document inconnu pour {chunk.id}: {chunk.document_id}")
        if chunk.locator.document_id != chunk.document_id:
            errors.append(f"locator incohérent pour {chunk.id}")
        if not chunk.locator.section_path:
            errors.append(f"section absente pour {chunk.id}")
        for fact in chunk.facts:
            if not fact.entity or not fact.formatted_value:
                errors.append(f"fait incomplet dans {chunk.id}: {fact.field_id}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"Corpus valide: {len(store.documents)} documents, {len(store.chunks)} chunks, "
        f"version {store.corpus_version}"
    )


if __name__ == "__main__":
    validate()

