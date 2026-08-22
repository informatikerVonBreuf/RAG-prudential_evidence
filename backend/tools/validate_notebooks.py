from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def validate_syntax(path: Path) -> None:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    if notebook.get("nbformat") != 4:
        raise ValueError(f"{path}: format notebook inattendu")
    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if "await " in source:
            continue
        ast.parse(source, filename=f"{path}:cell-{index}")


def execute(path: Path, *, save_outputs: bool = False) -> None:
    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError as exc:
        raise RuntimeError("Installer l'extra .[notebooks] pour exécuter les notebooks.") from exc
    notebook = nbformat.read(path, as_version=4)
    NotebookClient(notebook, timeout=600, kernel_name="python3").execute(cwd=Path.cwd())
    if save_outputs:
        nbformat.write(notebook, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--save-outputs",
        action="store_true",
        help="Persist fresh cell outputs in each notebook (implies --execute).",
    )
    args = parser.parse_args()
    paths = sorted(Path("notebooks").glob("*.ipynb"))
    for path in paths:
        validate_syntax(path)
        if args.execute or args.save_outputs:
            execute(path, save_outputs=args.save_outputs)
    print(f"Notebooks valides: {len(paths)}")


if __name__ == "__main__":
    main()
