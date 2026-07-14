"""Guard tests for ``docs/process/lint-deviations.md``.

The lint-deviations doc catalogues every standing lint-rule suppression in
the repo (ruff ``ignore`` / ``per-file-ignores`` and inline
``# pyright: ignore`` / ``# type: ignore`` / ``# noqa``). These tests keep
the doc honest: if a new suppression is added without documenting it, or a
documented file is renamed/removed, a test fails.
"""

from __future__ import annotations

import re
import tokenize
import tomllib
from io import BytesIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEVIATIONS_DOC = REPO_ROOT / "docs" / "process" / "lint-deviations.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Inline-suppression marker comments.
_INLINE_RE = re.compile(
    r"#\s*((?:pyright:\s*ignore|type:\s*ignore)(?:\[[^]]+\])?|noqa(?::\s*[^\s]+)?)"
)


def _inline_suppressions(path: Path) -> list[tuple[int, str, str]]:
    suppressions: list[tuple[int, str, str]] = []
    tokens = tokenize.tokenize(BytesIO(path.read_bytes()).readline)
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        match = _INLINE_RE.search(token.string)
        if match is not None:
            marker = " ".join(match.group(1).split())
            rationale = token.string[match.end() :].lstrip(" #-\u2014").strip()
            suppressions.append((token.start[0], marker, rationale))
    return suppressions


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


def test_doc_enumerates_every_inline_suppression() -> None:
    """Every inline suppression location and rule marker is catalogued."""
    text = _doc_text()
    missing: list[str] = []
    for root_name in ("src", "scripts", "tests"):
        for path in sorted((REPO_ROOT / root_name).rglob("*.py")):
            if path == Path(__file__):
                continue
            relative = path.relative_to(REPO_ROOT)
            for line, marker, rationale in _inline_suppressions(path):
                location = f"`{relative}:{line}`"
                documented_marker = f"`{marker}`"
                if location not in text or documented_marker not in text:
                    missing.append(f"{relative}:{line} ({marker})")
                if not rationale:
                    missing.append(f"{relative}:{line} ({marker}; missing rationale)")
    assert not missing, "inline suppressions absent from exact inventory: " + ", ".join(missing)
