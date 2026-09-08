# Annotation Vocabularies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the region role, page kind, and annotation provenance vocabularies into
`pdomain-book-contracts` so every repository shares one authority instead of three private lists.

**Architecture:** A new `annotation/` subpackage holds the vocabularies that describe what a human
or a model asserted about a page. Provenance enums move there from `typography/labels.py`, which
keeps re-exporting them so nothing downstream breaks. Region roles and page kinds are new. Mappings
translate PP-DocLayout's `RegionType` and `Block`'s twenty role strings into the new authority.

**Tech Stack:** Python 3.11+, `StrEnum`, frozen dataclasses, pytest, ruff, basedpyright.

**Spec:** [Annotation provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) and [Region
vocabulary](../specs/2026-09-07-region-vocabulary-design.md).

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-08
- **Last verified:** 2026-09-08
- **Provenance:** authored 2026-09-08 from the two design specs above and direct inspection of
  `pdomain-book-contracts` layout, typography, ocr, and text subpackages, its Makefile,
  `pyproject.toml`, and `tests/test_torch_free_import.py`
- **Disposition:** Active. Slice 1 of the labeling track. Blocks every other slice.
- **Read when:** implementing the shared region role or page kind enum, or moving the provenance
  vocabularies out of typography.
- **Search terms:** RegionRole, PageKind, LabelSource, KnowledgeState, ConfidenceTier, annotation
  subpackage, region vocabulary, additive only, torch-free import.

## Global Constraints

- Python floor is `>=3.11,<3.14`. Ruff targets `py311`; basedpyright pins `pythonVersion = "3.11"`.
- Runtime dependencies are exactly `pydantic`, `pydantic-core`, `regex`, `shapely`, and
  `typing-extensions`. Add none.
- The package must import with no imaging or ML stack. `tests/test_torch_free_import.py` blocks
  `torch`, `doctr`, `torchvision`, `cv2`, `pandas`, `matplotlib`, and `transformers`.
  **`test_every_subpackage_imports_without_heavy_stack` does not discover subpackages.** It runs a
  hardcoded list of `import` statements in a clean subprocess, so a new subpackage gets no coverage
  until it is added to that list by hand. Task 1 does exactly that.
- **Additive only.** No shipped role string is renamed. `route_sidenote_reading_order` matches the
  literal `"sidenote"`, and `dropcap._SKIP_ROLES` holds `"sidenote"` and `"page number"`.
- Canonical role strings use spaces, not underscores.
- Every subpackage `__init__.py` re-exports its public names and declares a sorted `__all__`, with
  `ALL_CAPS` constants first. Follow `pdomain_book_contracts/ocr/__init__.py`.
- Commands: `make test`, `make lint`, `make typecheck`, `make format`, `make ci`. There is no `AI=1`
  convention in this repository.
- Run `make ci` before every commit. It runs lint, typecheck, test, build, and
  `docgraph check --strict`.

---

## File Structure

| file | responsibility |
| --- | --- |
| `pdomain_book_contracts/annotation/__init__.py` | public exports for the annotation vocabularies |
| `pdomain_book_contracts/annotation/provenance.py` | `KnowledgeState`, `LabelSource`, `ConfidenceTier` |
| `pdomain_book_contracts/annotation/roles.py` | `RegionRole`, its alias map, its normalizer |
| `pdomain_book_contracts/annotation/page_kind.py` | `PageKind` and its normalizer |
| `pdomain_book_contracts/annotation/mappings.py` | `RegionType` and legacy block-role-string translation |
| `pdomain_book_contracts/typography/labels.py` | modified: re-exports the three moved enums |
| `pdomain_book_contracts/layout/types.py` | modified: adds `RegionType.page_number` |
| `pdomain_book_contracts/ocr/review.py` | modified: `ReviewMetadata` gains `source` and `state` |
| `tests/test_annotation_vocabularies.py` | covers roles, page kinds, aliases, normalizers |
| `tests/test_annotation_mappings.py` | covers both translation directions |
| `tests/test_review_metadata_provenance.py` | covers the new `ReviewMetadata` fields |

---

### Task 1: Move the provenance enums into `annotation/`

The three provenance enums are the strongest annotation model in the suite and they currently sit
inside `typography/`, where only style spans can reach them. Moving them makes them the shared
vocabulary for all five annotation levels. `typography/labels.py` re-exports so no downstream import
breaks.

**Files:**

- Create: `pdomain_book_contracts/annotation/__init__.py`
- Create: `pdomain_book_contracts/annotation/provenance.py`
- Modify: `pdomain_book_contracts/typography/labels.py`
- Test: `tests/test_annotation_vocabularies.py`

**Interfaces:**

- Consumes: nothing.
- Produces: `KnowledgeState`, `LabelSource`, `ConfidenceTier`, importable from
  `pdomain_book_contracts.annotation`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_annotation_vocabularies.py
from __future__ import annotations


def test_provenance_enums_import_from_annotation() -> None:
    from pdomain_book_contracts.annotation import (
        ConfidenceTier,
        KnowledgeState,
        LabelSource,
    )

    assert KnowledgeState.VERIFIED_NEGATIVE == "verified_negative"
    assert KnowledgeState.CONFLICT == "conflict"
    assert LabelSource.HUMAN == "human"
    assert ConfidenceTier.QUARANTINE == "quarantine"


def test_a_model_can_be_named_as_the_source() -> None:
    """The five shipped values are document sources and a person.

    Nothing among them can say a model proposed something, which is the claim
    the labeling track exists to record.
    """
    from pdomain_book_contracts.annotation import LabelSource

    assert LabelSource.MODEL == "model"


def test_the_f2_parser_s_source_is_unchanged() -> None:
    from pdomain_book_contracts.annotation import LabelSource

    # Additive only: the one existing consumer must keep working.
    assert LabelSource.F2 == "f2"


def test_typography_labels_still_re_export_them() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState as Moved
    from pdomain_book_contracts.typography.labels import KnowledgeState as ReExported

    assert Moved is ReExported
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_annotation_vocabularies.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pdomain_book_contracts.annotation'`

- [ ] **Step 3: Create the module and move the enums**

Create `pdomain_book_contracts/annotation/provenance.py` holding the three enum classes exactly as
they appear in `typography/labels.py` today, unchanged in members and values:

```python
"""Provenance vocabularies shared by every annotation level.

These describe how one assertion about a page got there: which source made it,
how much is known about it, and how far it is trusted. They apply to page kinds,
regions, style spans, words, and glyph annotations alike.
"""

from __future__ import annotations

from enum import StrEnum


class KnowledgeState(StrEnum):
    """How much is known about one label assignment."""

    POSITIVE = "positive"
    VERIFIED_NEGATIVE = "verified_negative"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class LabelSource(StrEnum):
    """Evidence sources that can assign a canonical label."""

    F2 = "f2"
    GUTENBERG_HTML = "gutenberg_html"
    SE_COMPUTED_CSS = "se_computed_css"
    HUMAN = "human"
    SYNTHETIC = "synthetic"
    # New. The five values above are four document sources and a person, because
    # this enum was built to record which transcription asserted a style. None of
    # them can say that a model proposed something, which is the claim the whole
    # labeling track exists to record. The model's identity and version live on
    # the proposal run record, so this member only names the category.
    MODEL = "model"


class ConfidenceTier(StrEnum):
    """Reviewed confidence tiers for label evidence."""

    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    QUARANTINE = "quarantine"
```

**This adds one member to a shipped enum.** It is additive, so the F2 parser at
`pdomain_book_contracts/sources/pgdp/f2/parser.py:143,291` — the only place `LabelSource` is
referenced today — is unaffected.

Create `pdomain_book_contracts/annotation/__init__.py`:

```python
"""Vocabularies describing what a human or a model asserted about a page.

This subpackage owns the words. It knows nothing about geometry, imaging, or the
page model, so every repository can depend on it without pulling either in.
"""

from __future__ import annotations

from pdomain_book_contracts.annotation.provenance import (
    ConfidenceTier,
    KnowledgeState,
    LabelSource,
)

__all__ = [
    "ConfidenceTier",
    "KnowledgeState",
    "LabelSource",
]
```

Then delete the three classes from `typography/labels.py` and re-export them there instead, keeping
`StyleLabel` where it is:

```python
from pdomain_book_contracts.annotation.provenance import (
    ConfidenceTier,
    KnowledgeState,
    LabelSource,
)

__all__ = [
    "ConfidenceTier",
    "KnowledgeState",
    "LabelSource",
    "StyleLabel",
]
```

- [ ] **Step 4: Add the new subpackage to the torch-free test**

`test_every_subpackage_imports_without_heavy_stack` runs a hardcoded list of imports, so the new
subpackage is invisible to it until added. In `tests/test_torch_free_import.py`, add one line to
that list, after `import pdomain_book_contracts.layout`:

```python
        import pdomain_book_contracts.annotation
```

Check `test_package_imports_without_heavy_stack` and `test_numpy_loads_only_via_shapely` in the same
file for any other hardcoded module list, and add the same line wherever subpackages are enumerated.

- [ ] **Step 5: Run the full suite to verify nothing downstream broke**

Run: `make test`
Expected: PASS, including `tests/test_torch_free_import.py`, which now covers `annotation`.

- [ ] **Step 6: Commit**

```bash
git add pdomain_book_contracts/annotation \
  pdomain_book_contracts/typography/labels.py \
  tests/test_annotation_vocabularies.py tests/test_torch_free_import.py
git commit -m "refactor(annotation): share the provenance enums beyond typography"
```

---

### Task 2: Add `RegionRole` with its 34 roles

Twenty roles ship on `Block` today and are carried over unchanged. Fourteen are new. The additive
rule is what keeps `route_sidenote_reading_order` and `dropcap._SKIP_ROLES` working, both of which
match role strings literally.

**Files:**

- Create: `pdomain_book_contracts/annotation/roles.py`
- Modify: `pdomain_book_contracts/annotation/__init__.py`
- Test: `tests/test_annotation_vocabularies.py`

**Interfaces:**

- Consumes: nothing from Task 1.
- Produces: `RegionRole`, `ALLOWED_REGION_ROLES: frozenset[str]`,
  `REGION_ROLE_ALIASES: dict[str, str]`, `normalize_region_role(label: str) -> str`.

- [ ] **Step 1: Write the failing test**

```python
def test_the_twenty_shipped_roles_are_unchanged() -> None:
    from pdomain_book_contracts.annotation import ALLOWED_REGION_ROLES

    shipped = {
        "paragraph", "sidenote", "page header", "page footer", "page number",
        "printers mark", "blockquote", "poetry", "recovered", "illustration",
        "decoration", "caption", "figure", "table", "footnote", "title",
        "section", "list", "formula", "artefact",
    }
    assert shipped <= ALLOWED_REGION_ROLES


def test_the_fourteen_additions_are_present() -> None:
    from pdomain_book_contracts.annotation import ALLOWED_REGION_ROLES

    additions = {
        "signature mark", "catchword", "press figure", "rule", "brace",
        "bracket", "group label", "plate", "speaker label", "stage direction",
        "interlinear gloss", "abandoned", "decorated initial", "unknown",
    }
    assert additions <= ALLOWED_REGION_ROLES
    assert len(ALLOWED_REGION_ROLES) == 34


def test_aliases_fold_to_canonical_roles() -> None:
    from pdomain_book_contracts.annotation import normalize_region_role

    assert normalize_region_role("frontispiece") == "plate"
    assert normalize_region_role("signaturemark") == "signature mark"
    assert normalize_region_role("pressfigure") == "press figure"
    assert normalize_region_role("stagedirection") == "stage direction"
    assert normalize_region_role("speakerlabel") == "speaker label"


def test_normalizer_accepts_case_and_separator_variants() -> None:
    from pdomain_book_contracts.annotation import normalize_region_role

    assert normalize_region_role("Page_Header") == "page header"
    assert normalize_region_role("  PAGE-NUMBER  ") == "page number"


def test_unknown_role_raises() -> None:
    import pytest

    from pdomain_book_contracts.annotation import normalize_region_role

    with pytest.raises(ValueError, match="Invalid region role"):
        normalize_region_role("marginalia")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_annotation_vocabularies.py -v`
Expected: FAIL with `ImportError: cannot import name 'ALLOWED_REGION_ROLES'`

- [ ] **Step 3: Write the implementation**

Create `pdomain_book_contracts/annotation/roles.py`:

```python
"""Region roles: what a block of a page means.

Structure lives on the block category. Meaning lives here. Sub-word features
live on word components. The rule governing this list is additive only: no
shipped role string is ever renamed, because several call sites match them
literally.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class RegionRole(StrEnum):
    """The meaning a page region carries."""

    # The twenty that ship on Block today, unchanged.
    PARAGRAPH = "paragraph"
    SIDENOTE = "sidenote"
    PAGE_HEADER = "page header"
    PAGE_FOOTER = "page footer"
    PAGE_NUMBER = "page number"
    PRINTERS_MARK = "printers mark"
    BLOCKQUOTE = "blockquote"
    POETRY = "poetry"
    RECOVERED = "recovered"
    ILLUSTRATION = "illustration"
    DECORATION = "decoration"
    CAPTION = "caption"
    FIGURE = "figure"
    TABLE = "table"
    FOOTNOTE = "footnote"
    TITLE = "title"  # pyright: ignore[reportAssignmentType]
    SECTION = "section"
    LIST = "list"
    FORMULA = "formula"
    ARTEFACT = "artefact"

    # The fourteen additions.
    SIGNATURE_MARK = "signature mark"
    CATCHWORD = "catchword"
    PRESS_FIGURE = "press figure"
    RULE = "rule"
    BRACE = "brace"
    BRACKET = "bracket"
    GROUP_LABEL = "group label"
    PLATE = "plate"
    SPEAKER_LABEL = "speaker label"
    STAGE_DIRECTION = "stage direction"
    INTERLINEAR_GLOSS = "interlinear gloss"
    ABANDONED = "abandoned"
    DECORATED_INITIAL = "decorated initial"
    UNKNOWN = "unknown"


ALLOWED_REGION_ROLES: Final[frozenset[str]] = frozenset(
    member.value for member in RegionRole
)

REGION_ROLE_ALIASES: Final[dict[str, str]] = {
    "frontispiece": "plate",
    "signaturemark": "signature mark",
    "pressfigure": "press figure",
    "stagedirection": "stage direction",
    "speakerlabel": "speaker label",
    "grouplabel": "group label",
    "interlineargloss": "interlinear gloss",
    "decoratedinitial": "decorated initial",
}


def _normalize_token(label: str) -> str:
    return " ".join(label.strip().lower().replace("_", " ").replace("-", " ").split())


def normalize_region_role(label: str) -> str:
    """Normalise one region role to a canonical allowed value.

    Accepts case, underscore, and hyphen variants, the compact no-space form of
    any canonical role, and every alias in ``REGION_ROLE_ALIASES``.
    """
    normalized = _normalize_token(label)
    compact = normalized.replace(" ", "")

    if normalized in ALLOWED_REGION_ROLES:
        return normalized

    if compact in REGION_ROLE_ALIASES:
        return REGION_ROLE_ALIASES[compact]

    for allowed in ALLOWED_REGION_ROLES:
        if compact == allowed.replace(" ", ""):
            return allowed

    allowed_list = ", ".join(sorted(ALLOWED_REGION_ROLES))
    raise ValueError(f"Invalid region role '{label}'. Allowed roles: {allowed_list}")
```

Add to `annotation/__init__.py`, keeping `__all__` sorted with constants first:

```python
from pdomain_book_contracts.annotation.roles import (
    ALLOWED_REGION_ROLES,
    REGION_ROLE_ALIASES,
    RegionRole,
    normalize_region_role,
)

__all__ = [
    "ALLOWED_REGION_ROLES",
    "REGION_ROLE_ALIASES",
    "ConfidenceTier",
    "KnowledgeState",
    "LabelSource",
    "RegionRole",
    "normalize_region_role",
]
```

- [ ] **Step 4: Run the tests**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_annotation_vocabularies.py -v`
Expected: PASS, all eight tests.

- [ ] **Step 5: Run the gate and commit**

```bash
make ci
git add pdomain_book_contracts/annotation tests/test_annotation_vocabularies.py
git commit -m "feat(annotation): add RegionRole with its 34 roles"
```

---

### Task 3: Add `PageKind`

Named `PageKind` and not `PageType`, because `pdomain-prep-for-pgdp` ships a seven-value `PageType`
deciding what is written to the submission zip. This enum answers what the page is, which is a
different question from what the packager does with it and from which template its text block
matches.

**Files:**

- Create: `pdomain_book_contracts/annotation/page_kind.py`
- Modify: `pdomain_book_contracts/annotation/__init__.py`
- Test: `tests/test_annotation_vocabularies.py`

**Interfaces:**

- Consumes: nothing.
- Produces: `PageKind`, `ALLOWED_PAGE_KINDS: frozenset[str]`,
  `normalize_page_kind(label: str) -> str`.

- [ ] **Step 1: Write the failing test**

```python
def test_page_kind_covers_the_body_and_front_matter_cases() -> None:
    from pdomain_book_contracts.annotation import ALLOWED_PAGE_KINDS

    expected = {
        "body", "chapter opening", "title page", "half title", "contents",
        "index", "dedication", "preface", "errata", "plate", "blank",
        "advertisement", "colophon", "unknown",
    }
    assert expected == ALLOWED_PAGE_KINDS


def test_page_kind_has_an_explicit_unknown() -> None:
    from pdomain_book_contracts.annotation import PageKind

    assert PageKind.UNKNOWN == "unknown"


def test_page_kind_normalizer_folds_variants() -> None:
    from pdomain_book_contracts.annotation import normalize_page_kind

    assert normalize_page_kind("Chapter_Opening") == "chapter opening"
    assert normalize_page_kind("titlepage") == "title page"


def test_page_kind_rejects_a_packaging_value() -> None:
    import pytest

    from pdomain_book_contracts.annotation import normalize_page_kind

    # "skip" and "cover" belong to prep-for-pgdp's PageType, not here.
    with pytest.raises(ValueError, match="Invalid page kind"):
        normalize_page_kind("skip")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_annotation_vocabularies.py -v`
Expected: FAIL with `ImportError: cannot import name 'ALLOWED_PAGE_KINDS'`

- [ ] **Step 3: Write the implementation**

Create `pdomain_book_contracts/annotation/page_kind.py`:

```python
"""Page kinds: what a page is.

Distinct from two vocabularies that already ship and are not merged with this
one. ``PageClass`` in pdomain-pgdp-measure records which fitted template a
page's text block matches, and is a measured signal that feeds a page kind
proposal. ``PageType`` in pdomain-prep-for-pgdp records what the packager does
with a leaf, and is derived from page kind plus policy.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class PageKind(StrEnum):
    """What a page is."""

    BODY = "body"
    CHAPTER_OPENING = "chapter opening"
    TITLE_PAGE = "title page"
    HALF_TITLE = "half title"
    CONTENTS = "contents"
    INDEX = "index"
    DEDICATION = "dedication"
    PREFACE = "preface"
    ERRATA = "errata"
    PLATE = "plate"
    BLANK = "blank"
    ADVERTISEMENT = "advertisement"
    COLOPHON = "colophon"
    UNKNOWN = "unknown"


ALLOWED_PAGE_KINDS: Final[frozenset[str]] = frozenset(
    member.value for member in PageKind
)


def _normalize_token(label: str) -> str:
    return " ".join(label.strip().lower().replace("_", " ").replace("-", " ").split())


def normalize_page_kind(label: str) -> str:
    """Normalise one page kind to a canonical allowed value."""
    normalized = _normalize_token(label)
    if normalized in ALLOWED_PAGE_KINDS:
        return normalized

    compact = normalized.replace(" ", "")
    for allowed in ALLOWED_PAGE_KINDS:
        if compact == allowed.replace(" ", ""):
            return allowed

    allowed_list = ", ".join(sorted(ALLOWED_PAGE_KINDS))
    raise ValueError(f"Invalid page kind '{label}'. Allowed kinds: {allowed_list}")
```

Add `ALLOWED_PAGE_KINDS`, `PageKind`, and `normalize_page_kind` to `annotation/__init__.py`,
keeping `__all__` sorted with constants first.

- [ ] **Step 4: Run the tests**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_annotation_vocabularies.py -v`
Expected: PASS.

- [ ] **Step 5: Run the gate and commit**

```bash
make ci
git add pdomain_book_contracts/annotation tests/test_annotation_vocabularies.py
git commit -m "feat(annotation): add PageKind, named apart from prep's PageType"
```

---

### Task 4: Add `RegionType.page_number` and the translation mappings

PP-DocLayout emits a native page-number label and the downstream mapping currently discards it into
`footer`, so nothing can propose a folio automatically for that reason alone. This task adds the
missing `RegionType` member and the two mappings that make `RegionRole` the authority rather than a
third list. The matching change in `pdomain-book-tools` is the second plan.

**Files:**

- Modify: `pdomain_book_contracts/layout/types.py`
- Create: `pdomain_book_contracts/annotation/mappings.py`
- Modify: `pdomain_book_contracts/annotation/__init__.py`
- Test: `tests/test_annotation_mappings.py`

**Interfaces:**

- Consumes: `RegionRole` from Task 2, `RegionType` from `layout/types.py`.
- Produces: `REGION_TYPE_TO_ROLE: dict[RegionType, RegionRole]`,
  `region_role_for_region_type(region_type: RegionType) -> RegionRole`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_annotation_mappings.py
from __future__ import annotations


def test_every_region_type_maps_to_a_role() -> None:
    from pdomain_book_contracts.annotation import REGION_TYPE_TO_ROLE
    from pdomain_book_contracts.layout import RegionType

    assert set(REGION_TYPE_TO_ROLE) == set(RegionType)


def test_page_number_survives_instead_of_becoming_a_footer() -> None:
    from pdomain_book_contracts.annotation import (
        RegionRole,
        region_role_for_region_type,
    )
    from pdomain_book_contracts.layout import RegionType

    assert region_role_for_region_type(RegionType.page_number) == RegionRole.PAGE_NUMBER
    assert region_role_for_region_type(RegionType.footer) == RegionRole.PAGE_FOOTER


def test_header_and_footer_do_not_collapse_the_folio_distinction() -> None:
    from pdomain_book_contracts.annotation import (
        RegionRole,
        region_role_for_region_type,
    )
    from pdomain_book_contracts.layout import RegionType

    assert region_role_for_region_type(RegionType.header) == RegionRole.PAGE_HEADER
    assert region_role_for_region_type(RegionType.abandoned) == RegionRole.ABANDONED


def test_figure_and_illustration_stay_distinct() -> None:
    from pdomain_book_contracts.annotation import (
        RegionRole,
        region_role_for_region_type,
    )
    from pdomain_book_contracts.layout import RegionType

    # A figure region carrying OCR text is a figure. The empty-placeholder
    # illustration role is stamped elsewhere and is not a RegionType target.
    assert region_role_for_region_type(RegionType.figure) == RegionRole.FIGURE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_annotation_mappings.py -v`
Expected: FAIL with `AttributeError: page_number` on `RegionType`.

- [ ] **Step 3: Add the enum member**

In `pdomain_book_contracts/layout/types.py`, append one member to `RegionType`, after `sidenote`:

```python
    page_number = "page_number"
```

- [ ] **Step 4: Write the mapping module**

Create `pdomain_book_contracts/annotation/mappings.py`:

```python
"""Translation from detector and legacy vocabularies into RegionRole.

RegionType stays as it is. It records what a detector proposed, which is a
different question from what a person meant, and merging them would erase the
distinction. This module is the one-way bridge.
"""

from __future__ import annotations

from typing import Final

from pdomain_book_contracts.annotation.roles import RegionRole
from pdomain_book_contracts.layout.types import RegionType

REGION_TYPE_TO_ROLE: Final[dict[RegionType, RegionRole]] = {
    RegionType.text: RegionRole.PARAGRAPH,
    RegionType.title: RegionRole.TITLE,
    RegionType.section: RegionRole.SECTION,
    RegionType.list: RegionRole.LIST,
    RegionType.table: RegionRole.TABLE,
    RegionType.figure: RegionRole.FIGURE,
    RegionType.decoration: RegionRole.DECORATION,
    RegionType.caption: RegionRole.CAPTION,
    RegionType.header: RegionRole.PAGE_HEADER,
    RegionType.footer: RegionRole.PAGE_FOOTER,
    RegionType.footnote: RegionRole.FOOTNOTE,
    RegionType.formula: RegionRole.FORMULA,
    RegionType.abandoned: RegionRole.ABANDONED,
    RegionType.sidenote: RegionRole.SIDENOTE,
    RegionType.page_number: RegionRole.PAGE_NUMBER,
}


def region_role_for_region_type(region_type: RegionType) -> RegionRole:
    """Return the role a detector's region type proposes."""
    return REGION_TYPE_TO_ROLE[region_type]
```

Add `REGION_TYPE_TO_ROLE` and `region_role_for_region_type` to `annotation/__init__.py`.

- [ ] **Step 5: Run the tests**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_annotation_mappings.py -v`
Expected: PASS, all four tests.

- [ ] **Step 6: Run the gate and commit**

```bash
make ci
git add pdomain_book_contracts tests/test_annotation_mappings.py
git commit -m "feat(annotation): map RegionType to RegionRole, keeping the folio"
```

---

### Task 5: Give `ReviewMetadata` provenance

`ReviewMetadata` today holds only `validated`, `reviewer_note`, and `flagged_for_attention`. It can
express neither a rejection nor a conflict, and it cannot say which source produced the answer it
guards. Four different writers fill `ground_truth_text` and nothing records which. Adding `source`
and `state` closes that at word level with no new store.

Both fields default so every existing construction and every stored record keeps working.

**Files:**

- Modify: `pdomain_book_contracts/ocr/review.py`
- Test: `tests/test_review_metadata_provenance.py`

**Interfaces:**

- Consumes: `LabelSource` and `KnowledgeState` from Task 1.
- Produces: `ReviewMetadata.source: LabelSource | None` and
  `ReviewMetadata.state: KnowledgeState`, both round-tripping through `to_dict` and `from_dict`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_review_metadata_provenance.py
from __future__ import annotations


def test_defaults_keep_existing_records_valid() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState
    from pdomain_book_contracts.ocr import ReviewMetadata

    review = ReviewMetadata()
    assert review.source is None
    assert review.state == KnowledgeState.UNKNOWN


def test_source_and_state_round_trip() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource
    from pdomain_book_contracts.ocr import ReviewMetadata

    review = ReviewMetadata(
        validated=True,
        source=LabelSource.HUMAN,
        state=KnowledgeState.POSITIVE,
    )
    restored = ReviewMetadata.from_dict(review.to_dict())
    assert restored == review
    assert restored.source == LabelSource.HUMAN
    assert restored.state == KnowledgeState.POSITIVE


def test_a_rejection_is_expressible() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource
    from pdomain_book_contracts.ocr import ReviewMetadata

    rejected = ReviewMetadata(source=LabelSource.HUMAN, state=KnowledgeState.VERIFIED_NEGATIVE)
    assert ReviewMetadata.from_dict(rejected.to_dict()).state == KnowledgeState.VERIFIED_NEGATIVE


def test_an_f2_supplied_answer_is_distinguishable_from_a_typed_one() -> None:
    from pdomain_book_contracts.annotation import LabelSource
    from pdomain_book_contracts.ocr import ReviewMetadata

    aligned = ReviewMetadata(source=LabelSource.F2)
    typed = ReviewMetadata(source=LabelSource.HUMAN)
    assert aligned.source != typed.source


def test_a_legacy_dict_without_the_new_keys_still_loads() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState
    from pdomain_book_contracts.ocr import ReviewMetadata

    legacy = {"validated": True, "reviewer_note": None, "flagged_for_attention": False}
    restored = ReviewMetadata.from_dict(legacy)
    assert restored.validated is True
    assert restored.source is None
    assert restored.state == KnowledgeState.UNKNOWN
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_review_metadata_provenance.py -v`
Expected: FAIL with `TypeError: ReviewMetadata.__init__() got an unexpected keyword argument 'source'`

- [ ] **Step 3: Write the implementation**

Replace the body of `ReviewMetadata` in `pdomain_book_contracts/ocr/review.py`:

```python
from pdomain_book_contracts.annotation.provenance import KnowledgeState, LabelSource


@dataclass
class ReviewMetadata:
    """Human-review state on a Word, Block (line), or Page.

    Fields:
        validated:            A reviewer has confirmed this item is correct.
        reviewer_note:        Optional free-text note left by the reviewer.
        flagged_for_attention: Flagged for follow-up review by a different
                               reviewer or for an automated pass.
        source:               Which source produced the answer this guards.
                              ``None`` means nothing has been recorded, which is
                              distinct from a recorded machine or human origin.
        state:                How much is known. Defaults to ``UNKNOWN`` so an
                              untouched record does not claim to be positive.
    """

    validated: bool = False
    reviewer_note: str | None = None
    flagged_for_attention: bool = False
    source: LabelSource | None = None
    state: KnowledgeState = KnowledgeState.UNKNOWN

    def to_dict(self) -> dict[str, bool | str | None]:
        return {
            "validated": self.validated,
            "reviewer_note": self.reviewer_note,
            "flagged_for_attention": self.flagged_for_attention,
            "source": self.source.value if self.source is not None else None,
            "state": self.state.value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> ReviewMetadata:
        raw_source = d.get("source")
        raw_state = d.get("state")
        return cls(
            validated=bool(d.get("validated", False)),
            reviewer_note=str(d["reviewer_note"])
            if d.get("reviewer_note") is not None
            else None,
            flagged_for_attention=bool(d.get("flagged_for_attention", False)),
            source=LabelSource(str(raw_source)) if raw_source is not None else None,
            state=KnowledgeState(str(raw_state))
            if raw_state is not None
            else KnowledgeState.UNKNOWN,
        )
```

- [ ] **Step 4: Run the tests**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_review_metadata_provenance.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Run the full gate**

Run: `make ci`
Expected: lint, typecheck, test, build, and `docgraph check --strict` all pass.

- [ ] **Step 6: Commit**

```bash
git add pdomain_book_contracts/ocr/review.py tests/test_review_metadata_provenance.py
git commit -m "feat(ocr): give ReviewMetadata a source and a knowledge state"
```

---

## What this plan does not do

- It does not change `Block`. Widening `ALLOWED_BLOCK_ROLE_LABELS` to the same 34 values is Task 4
  of the [preconditions plan](2026-09-08-annotation-preconditions-in-book-tools-and-measure.md),
  because a downstream repository cannot be changed from here. **Until that lands, `Block` rejects
  the fourteen additions**, so the two plans must ship together for the vocabulary to be usable.
- It does not add the `_REGION_TO_BLOCK_ROLE` entry for `page_number`. That mapping lives in
  `pdomain-book-tools` and is the second plan's work.
- It does not add `BlockCategory.TABLE`, `CELL`, or `GROUP`. Those depend on the table structure
  spec's data model, which is an open question the design records.
- It adds no proposal store, decision store, or route. Those are the third plan.
- **It defines `PageKind` and nothing consumes it.** No plan yet adds a typed page-kind field to
  `Page`, a classifier proposal store, or the per-page reviewed marker the design calls for. `Page`
  keeps its free-form `page_labels` list. The enum ships first because everything else depends on
  it, but a page-kind plan is still owed.
- It does not populate `ReviewMetadata.source`. The field lands here; the four writers that fill
  `ground_truth_text` in `pdomain-book-tools` and the labeler are not touched by any plan yet, so
  the field ships empty until one covers them.

## Related

- [Annotation provenance and
  persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) — the design.
- [Region vocabulary](../specs/2026-09-07-region-vocabulary-design.md) — the 34 roles and the
  additive-only rule.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — slice 1 of seven.
