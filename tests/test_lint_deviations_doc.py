"""Guard tests for ``docs/process/lint-deviations.md``.

The lint-deviations doc catalogues every standing lint-rule suppression in
the repo (ruff ``ignore`` / ``per-file-ignores`` and inline
``# pyright: ignore`` / ``# type: ignore`` / ``# noqa``). These tests keep
the doc honest: if a new suppression is added without documenting it, or a
documented file is renamed/removed, a test fails.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEVIATIONS_DOC = REPO_ROOT / "docs" / "process" / "lint-deviations.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Inline-suppression marker comments.
_INLINE_RE = re.compile(r"#\s*(pyright:\s*ignore|type:\s*ignore|noqa)")


def _doc_text() -> str:
    return DEVIATIONS_DOC.read_text(encoding="utf-8")


def test_deviations_doc_exists() -> None:
    """The catalogue file must exist at the conventional path."""
    assert DEVIATIONS_DOC.is_file(), f"missing {DEVIATIONS_DOC}"


def test_doc_documents_global_ignore_rules() -> None:
    """Every ruff global-ignore code is named somewhere in the doc."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    ignore_codes = pyproject["tool"]["ruff"]["lint"]["ignore"]
    text = _doc_text()
    missing = [code for code in ignore_codes if code not in text]
    assert not missing, f"global ignore codes absent from doc: {missing}"


def test_doc_documents_per_file_ignore_groups() -> None:
    """Every per-file-ignore code appears in the doc at least once."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    per_file = pyproject["tool"]["ruff"]["lint"]["per-file-ignores"]
    all_codes: set[str] = set()
    for codes in per_file.values():
        all_codes.update(codes)
    text = _doc_text()
    missing = sorted(code for code in all_codes if code not in text)
    assert not missing, f"per-file-ignore codes absent from doc: {missing}"


def test_doc_documents_basedpyright_overrides() -> None:
    """basedpyright rule-level overrides in pyproject are documented."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    bp = pyproject["tool"].get("basedpyright", {})
    text = _doc_text()
    # Any reportX key set to "none"/"warning" is a deviation from recommended.
    overrides = [
        key
        for key, val in bp.items()
        if key.startswith("report") and val in {"none", "warning", "information"}
    ]
    missing = [key for key in overrides if key not in text]
    assert not missing, f"basedpyright overrides absent from doc: {missing}"


def test_doc_lists_files_with_inline_suppressions() -> None:
    """Every src/ file carrying an inline suppression is named in the doc.

    Tests and scripts are blanket-covered by per-file-ignores, so only
    production ``src/`` files need individual mention.
    """
    text = _doc_text()
    src_dir = REPO_ROOT / "src"
    offenders: list[str] = []
    for py in sorted(src_dir.rglob("*.py")):
        content = py.read_text(encoding="utf-8")
        if not _INLINE_RE.search(content):
            continue
        # The doc may reference the file by basename or by package path.
        rel = py.relative_to(src_dir)
        if py.name not in text and str(rel) not in text:
            offenders.append(str(rel))
    assert not offenders, f"src files with undocumented inline suppressions: {offenders}"
