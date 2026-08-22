from pathlib import Path

from backend.tools.validate_notebooks import validate_syntax


def test_notebook_sources_are_syntactically_valid() -> None:
    notebooks = sorted(Path("notebooks").glob("*.ipynb"))
    assert len(notebooks) == 11
    for notebook in notebooks:
        validate_syntax(notebook)
