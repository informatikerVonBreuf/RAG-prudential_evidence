from __future__ import annotations

import importlib.util
import os
import platform
import sys
from pathlib import Path
from typing import Any


def locate_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "backend").is_dir():
            return candidate
    raise RuntimeError("Impossible de localiser le projet : ouvrir Jupyter depuis sa racine.")


def bootstrap() -> Path:
    root = locate_project_root()
    backend_path = str(root / "backend")
    notebook_path = str(root / "notebooks")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    if notebook_path not in sys.path:
        sys.path.insert(0, notebook_path)

    if module_available("dotenv"):
        from dotenv import load_dotenv

        load_dotenv(root / ".env", override=False)
    return root


def module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def environment_report() -> dict[str, Any]:
    packages = [
        "fastapi", "pydantic", "pytest", "ipykernel", "pandas", "matplotlib",
        "pymupdf", "pdfplumber", "camelot", "docling", "sentence_transformers", "torch",
    ]
    report: dict[str, Any] = {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "project_root": str(locate_project_root()),
        "packages": {name: module_available(name) for name in packages},
        "gemini_key_configured": bool(os.getenv("GEMINI_API_KEY")),
        "local_model_path_configured": bool(os.getenv("LOCAL_EMBEDDING_MODEL_PATH")),
    }
    if module_available("torch"):
        import torch

        report["accelerator"] = {
            "cuda_available": torch.cuda.is_available(),
            "mps_available": bool(
                getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
            ),
        }
    else:
        report["accelerator"] = {"cuda_available": False, "mps_available": False}
    return report


def display_table(rows: list[dict[str, Any]]) -> Any:
    if module_available("pandas"):
        import pandas as pd

        return pd.DataFrame(rows)
    return rows


def safe_model_summary() -> dict[str, Any]:
    local_path = os.getenv("LOCAL_EMBEDDING_MODEL_PATH", "").strip()
    return {
        "baseline": "hash embeddings déterministes 384 dimensions",
        "local_embedding_model": os.getenv("LOCAL_EMBEDDING_MODEL", "non configuré"),
        "local_model_path_exists": bool(local_path and Path(local_path).expanduser().exists()),
        "sentence_transformers_installed": module_available("sentence_transformers"),
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "gemini_sdk_installed": module_available("google.genai"),
        "ollama_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    }

