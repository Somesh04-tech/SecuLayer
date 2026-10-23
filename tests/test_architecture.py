"""src/seculayer is the reusable library: it never imports the demo, the web framework or OpenAI."""

from __future__ import annotations

import ast
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[1] / "src" / "seculayer"
FORBIDDEN = {"seculayer_demo", "fastapi", "starlette", "uvicorn", "openai"}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            roots.add(node.args[0].value.split(".")[0])
    return roots


def test_library_exists() -> None:
    assert (LIBRARY / "__init__.py").is_file()


def test_library_does_not_import_demo_web_or_openai() -> None:
    offenders = {
        str(path.relative_to(LIBRARY)): sorted(imported_roots(path) & FORBIDDEN)
        for path in LIBRARY.rglob("*.py")
    }
    offenders = {name: found for name, found in offenders.items() if found}
    assert offenders == {}


def test_checker_catches_forbidden_imports(tmp_path: Path) -> None:
    sample = tmp_path / "bad.py"
    sample.write_text(
        "import openai\nfrom fastapi import FastAPI\nimport seculayer_demo.cli\n"
        "x = __import__('starlette')\nfrom . import sibling\n",
        encoding="utf-8",
    )
    assert imported_roots(sample) & FORBIDDEN == {
        "openai",
        "fastapi",
        "seculayer_demo",
        "starlette",
    }
