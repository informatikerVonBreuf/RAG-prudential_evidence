from pathlib import Path
from zipfile import ZipFile

from tools.validate_wheel import validate


def test_wheel_validator_rejects_missing_runtime_artifacts(tmp_path: Path) -> None:
    wheel = tmp_path / "prudential_evidence_lab-0.1.0-py3-none-any.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("app/__init__.py", "")

    try:
        validate(tmp_path)
    except SystemExit as exc:
        assert "corpus.json" in str(exc)
    else:
        raise AssertionError("A wheel without the corpus must be rejected.")
