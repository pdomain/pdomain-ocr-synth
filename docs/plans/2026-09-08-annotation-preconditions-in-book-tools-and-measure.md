# Annotation Preconditions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gaps that block region annotation and page-kind confidence: nothing detects a
word duplicated across regions, no template records the spread a residual must be scaled against,
the folio signal is discarded into the footer, and `Block` rejects fourteen of the thirty-four
region roles.

**Architecture:** Two independent changes in two repositories. In `pdomain-book-tools`, a new
validator reports words the reorganize pipeline duplicated, wired into the existing reconcile step
behind the strict-mode flag that already governs dropped words. In `pdomain-pgdp-measure`, each
fitted page template records the spread of the group it was fitted from, so a per-page-class
normalizer becomes possible.

**Tech Stack:** Python 3.11+ in book-tools and 3.13 in pgdp-measure, frozen dataclasses, pytest,
ruff, basedpyright.

**Spec:** [Annotation provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md).

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-08
- **Last verified:** 2026-09-08
- **Provenance:** authored 2026-09-08 from the design above and direct inspection of
  `pdomain-book-tools/pdomain_book_tools/ocr/reorganize_page_utils.py`, `ocr/layout_aware_reorg.py`,
  `ocr/block.py`, its Makefile and `pyproject.toml`, and
  `pdomain-pgdp-measure/src/pdomain_pgdp_measure/page_templates.py`, `profiling.py`,
  `profile_models.py`, and `tests/test_pgdp_page_templates.py`
- **Disposition:** Active. Preconditions for slices 2 and 4 of the labeling track. Tasks 1 and 3
  are independent and may ship alone. Tasks 2 and 4 both need the vocabularies plan first.
- **Read when:** implementing the word duplication check, or adding per-class spread to page
  templates so `template_residual_px` can become a confidence.
- **Search terms:** word duplication, validate_word_preservation, reconcile_dropped_words,
  PD_OCR_REORGANIZE_STRICT, PageTemplate spread, template_residual_px, confidence normalization,
  page_number region type.

## Global Constraints

- **book-tools:** Python `>=3.11,<3.14`. Warnings are errors (`filterwarnings = ["error"]`), and
  `--strict-markers` plus `--strict-config` are set. Branch coverage is on. Run targets with
  `AI=1` to capture verbose output to `.ci-ai.log`. Run `make ci AI=1` before committing.
- **pgdp-measure:** Python `>=3.13,<3.14`. There is no Makefile, no `AGENTS.md`, and no
  `CONVENTIONS.md`. Commands run through `uv` directly. Warnings are errors. `pythonpath = ["src"]`
  is required by the src layout and must not be removed.
- **Additive only.** Do not change the signature or return contract of `validate_word_preservation`.
  Existing callers and five existing tests depend on it reporting missing words and permitting
  extras.
- Any new field on a serialized dataclass must default, so stored profiles keep loading.
- **`make ci` in book-tools needs `CI=1` in this sandbox.** The Makefile's `GPU_EXTRA` auto-detect
  runs `nvidia-smi` when `$CI` is empty and installs cupy. A device is reported, but CUDA memory
  allocation fails, so the GPU tests error with `CURAND_STATUS_INITIALIZATION_FAILED` and
  `CUDA_ERROR_OUT_OF_MEMORY`. Measured on pristine master: 2910 passed, 24 failed, every failure in
  one of five GPU-specific test files and every underlying cause a driver or allocation fault rather
  than an assertion. `CI=1` disables only that auto-detect, which is what real CI sets, so the gate
  is the same one CI runs.
- **Re-sync `.venv` after any merge that changes `uv.lock`.** `basedpyright` reads `venvPath`/`venv`
  from `pyproject.toml` pointing at `.venv`, while everything else uses `.venv-container` via
  `UV_PROJECT_ENVIRONMENT`. A `.venv` left behind by an older lock resolves the old
  `pdomain-book-contracts` and reports every new enum member as a missing attribute. Fix with
  `UV_PROJECT_ENVIRONMENT=.venv uv sync --all-groups`; the errors are not real.
- **Adding a defaulted field to `ReviewMetadata` breaks tests that assert exact serialization.**
  Six book-tools tests compare `to_dict()` output against literal dicts, so `source` and `state`
  appearing with their defaults fails them. The updates are mechanical and additive, but they must
  happen in the same change or the suite goes red.

---

## File Structure

| file | responsibility |
| --- | --- |
| `pdomain_book_tools/ocr/reorganize_page_utils.py` | modified: adds `find_duplicated_words` and its reconcile wiring |
| `pdomain_book_tools/layout/_mappings.py` | modified: stops mapping the native `page_number` label to `footer` |
| `pdomain_book_tools/ocr/layout_aware_reorg.py` | modified: `_REGION_TO_BLOCK_ROLE` gains the folio role |
| `pdomain-book-tools/tests/ocr/test_word_duplication.py` | covers the new validator and its strict-mode path |
| `pdomain-book-tools/tests/layout/test_page_number_mapping.py` | covers both halves of the folio fix |
| `pdomain-book-tools/tests/layout/test_mappings.py` | modified: an existing test locks the old behaviour |
| `pdomain-book-tools/docs/architecture/page-serialization.md` | modified: two drift gates require listing new values |
| `src/pdomain_pgdp_measure/page_templates.py` | modified: `PageTemplate` gains `first_band_spread_px` |
| `src/pdomain_pgdp_measure/profile_models.py` | modified: the record and the wire model both carry it |
| `src/pdomain_pgdp_measure/profiling.py` | modified: copies the new field into the record |
| `schemas/pgdp-profile-v2.schema.json` | modified: documents the new property |
| `pdomain_book_tools/ocr/block.py` | modified: `ALLOWED_BLOCK_ROLE_LABELS` widens to 34 roles |
| `pdomain-book-tools/tests/ocr/test_block_role_vocabulary.py` | covers all 34 roles and the new aliases |
| `pdomain-book-tools/docs/architecture/page-serialization.md` | modified: the drift gate requires listing every role |
| `pdomain-pgdp-measure/tests/test_pgdp_page_templates.py` | modified: covers the spread and its round trip |

---

### Task 1: Detect words the pipeline duplicated

`validate_word_preservation` compares word signatures before and after reorganization and reports
only the ones that went missing. Its docstring states that extra words are allowed. That was correct
while a word could belong to several regions at once. Once sibling regions are disjoint, one word
appearing twice is a violation, and today nothing would catch it.

The new function is separate rather than a change to the existing one, so the existing contract and
its five tests stay untouched. It compares counts in the opposite direction: a signature whose count
after exceeds its count before was duplicated by the pipeline. Comparing against the before-count
rather than against one means a page that legitimately starts with two identical signatures is not
falsely flagged.

**Files:**

- Modify: `pdomain_book_tools/ocr/reorganize_page_utils.py`
- Test: `pdomain-book-tools/tests/ocr/test_word_duplication.py`

**Interfaces:**

- Consumes: `collect_word_signatures(words: list[Word]) -> list[tuple[str, float, float, float, float]]`
  and `reorganize_strict_mode_enabled() -> bool`, both already in this module.
- Produces: `find_duplicated_words(pre_words: list[Word], post_words: list[Word]) -> list[str]`,
  and `ReorganizeDuplicatedWordsError`.

- [ ] **Step 1: Write the failing test**

```python
# tests/ocr/test_word_duplication.py
from __future__ import annotations

import pytest

from pdomain_book_tools.geometry.bounding_box import BoundingBox
from pdomain_book_tools.geometry.point import Point
from pdomain_book_tools.ocr.word import Word


def _bbox(left: float, top: float, right: float, bottom: float) -> BoundingBox:
    return BoundingBox(
        top_left=Point(left, top, is_normalized=True),
        bottom_right=Point(right, bottom, is_normalized=True),
        is_normalized=True,
    )


def _word(text: str, left: float, top: float, right: float, bottom: float) -> Word:
    return Word(text=text, bounding_box=_bbox(left, top, right, bottom), ocr_confidence=0.95)


def test_no_duplication_reports_nothing() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import find_duplicated_words

    pre = [_word("alpha", 0.1, 0.1, 0.2, 0.2), _word("beta", 0.3, 0.1, 0.4, 0.2)]
    post = list(pre)
    assert find_duplicated_words(pre, post) == []


def test_a_word_appearing_twice_after_is_reported() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import find_duplicated_words

    alpha = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    pre = [alpha]
    post = [alpha, alpha]
    errors = find_duplicated_words(pre, post)
    assert len(errors) == 1
    assert "alpha" in errors[0]
    assert "duplicated" in errors[0]


def test_a_pre_existing_duplicate_is_not_flagged() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import find_duplicated_words

    alpha = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    pre = [alpha, alpha]
    post = [alpha, alpha]
    assert find_duplicated_words(pre, post) == []


def test_a_dropped_word_is_not_reported_as_duplication() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import find_duplicated_words

    alpha = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    beta = _word("beta", 0.3, 0.1, 0.4, 0.2)
    assert find_duplicated_words([alpha, beta], [alpha]) == []


def test_a_brand_new_word_absent_from_pre_is_not_flagged() -> None:
    """Creation is not duplication.

    The cursive drop-cap recovery synthesizes a Word for a glyph the recognizer
    missed. It exists nowhere in pre_words and must not be reported.
    """
    from pdomain_book_tools.ocr.reorganize_page_utils import find_duplicated_words

    alpha = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    recovered = _word("O", 0.05, 0.1, 0.09, 0.2)
    assert find_duplicated_words([alpha], [alpha, recovered]) == []


def test_empty_text_words_are_ignored_like_the_drop_validator() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import find_duplicated_words

    blank = _word("", 0.1, 0.1, 0.2, 0.2)
    assert find_duplicated_words([blank], [blank, blank]) == []


def test_strict_mode_raises_on_duplication() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import (
        ReorganizeDuplicatedWordsError,
        raise_if_words_duplicated,
    )

    alpha = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    with pytest.raises(ReorganizeDuplicatedWordsError, match="duplicated 1 word"):
        raise_if_words_duplicated([alpha], [alpha, alpha], strict=True)


def test_non_strict_mode_returns_the_errors_without_raising() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import raise_if_words_duplicated

    alpha = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    errors = raise_if_words_duplicated([alpha], [alpha, alpha], strict=False)
    assert len(errors) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-single TEST='tests/ocr/test_word_duplication.py'`
Expected: FAIL with `ImportError: cannot import name 'find_duplicated_words'`

- [ ] **Step 3: Write the implementation**

Add to `pdomain_book_tools/ocr/reorganize_page_utils.py`, directly after
`validate_word_preservation`:

```python
def find_duplicated_words(
    pre_words: list[Word],
    post_words: list[Word],
) -> list[str]:
    """Report words the reorganize pipeline duplicated.

    ``validate_word_preservation`` is the mirror of this and permits extras,
    which was correct while a word could belong to several regions at once.
    Sibling regions are disjoint in membership, so one word appearing in two of
    them is a defect rather than a nesting.

    Counts are compared against the pre-multiset rather than against one, so a
    page that already held two identical signatures is not falsely flagged.
    Empty-text and bbox-less words are filtered by ``collect_word_signatures``,
    matching the drop validator exactly.

    A signature absent from ``pre_words`` is **created**, not duplicated, and is
    never flagged. The pipeline legitimately synthesizes words: the cursive
    drop-cap recovery in ``dropcap.detect_and_stitch_cursive_dropcaps`` builds a
    ``Word`` for a glyph the recognizer missed entirely, so a page whose OCR read
    only "NCE" of "ONCE" gains a real "O" that exists nowhere in ``pre_words``.
    Flagging that would break the corpus on its first run.
    """
    pre_counts = Counter(collect_word_signatures(pre_words))
    post_counts = Counter(collect_word_signatures(post_words))
    errors: list[str] = []
    for sig, post_n in post_counts.items():
        pre_n = pre_counts.get(sig, 0)
        if pre_n == 0:
            # Created, not duplicated.
            continue
        extra = post_n - pre_n
        if extra <= 0:
            continue
        text, x0, y0, x1, y1 = sig
        for _ in range(extra):
            errors.append(
                f"reorganize duplicated word: text={text!r} "
                f"bbox=({x0:.4f},{y0:.4f})-({x1:.4f},{y1:.4f})"
            )
    return errors


class ReorganizeDuplicatedWordsError(RuntimeError):
    """Raised in strict mode when reorganize_page duplicates one or more words."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__(
            f"reorganize_page duplicated {len(errors)} word(s); "
            + f"first: {errors[0] if errors else '(none)'}"
        )
        self.errors: list[str] = errors


def raise_if_words_duplicated(
    pre_words: list[Word],
    post_words: list[Word],
    *,
    strict: bool,
) -> list[str]:
    """Return duplication errors, raising instead when ``strict`` is set.

    Mirrors the dropped-word policy: loud in CI and tests, recoverable in
    ordinary use so a person still sees the page.
    """
    errors = find_duplicated_words(pre_words, post_words)
    if errors and strict:
        raise ReorganizeDuplicatedWordsError(errors)
    return errors
```

- [ ] **Step 4: Run the tests**

Run: `make test-single TEST='tests/ocr/test_word_duplication.py'`
Expected: PASS, all seven tests.

- [ ] **Step 5: Wire it into the reconcile step**

In `reconcile_dropped_words`, immediately after the existing
`errors = validate_word_preservation(pre_words, post_words)` call at line 975, add the duplication
check so both defects are caught in the same pass:

The module logger in this file is named `logger`, declared at `reorganize_page_utils.py:46` as
`logger = getLogger(__name__)`. There is no `log` name in this module, so writing `log.warning`
raises `NameError` on exactly the pages that have something to report.

```python
    duplication_errors = raise_if_words_duplicated(
        pre_words, post_words, strict=reorganize_strict_mode_enabled()
    )
    for message in duplication_errors:
        logger.warning(message)
```

- [ ] **Step 6: Run the full suite to confirm no existing test regressed**

Run: `make test AI=1`
Expected: PASS. Pay particular attention to
`tests/ocr/test_reconcile_dropped_words.py`, `tests/ocr/test_reorganize_early_return_and_soft_recover.py`,
and `tests/ocr/test_reorganize_page_utils_grouping.py`, which exercise the reconcile path.

- [ ] **Step 7: Run the gate and commit**

```bash
make ci AI=1
git add pdomain_book_tools/ocr/reorganize_page_utils.py tests/ocr/test_word_duplication.py
git commit -m "feat(ocr): detect words the reorganize pipeline duplicated"
```

---

### Task 2: Stop discarding the folio signal

PP-DocLayout emits a native page-number label and the mapping in this repository routes it into
`footer`, so a folio cannot be proposed automatically for that reason alone. The first plan adds
`RegionType.page_number` in `pdomain-book-contracts`. This task consumes it.

Do this task only after the first plan's Task 4 has landed and the new contracts version is
resolvable, since `RegionType.page_number` does not exist until then.

**The two dictionaries live in different modules and hold different value types.** Read both before
editing:

- `PP_DOCLAYOUT_TO_PGDP: dict[str, str | None]` is in `pdomain_book_tools/layout/_mappings.py:11`.
  It maps PP-DocLayout's native label strings to plain strings, not to `RegionType` members. Its
  `"page_number": "footer"` entry at line 34 is the discard, and the comment above it at line 30
  documents the collapse.
- `_REGION_TO_BLOCK_ROLE: dict[RegionType, str]` is in `pdomain_book_tools/ocr/layout_aware_reorg.py:101`.
  It maps `RegionType` members to block role strings, and it is read by the dominance pass at
  `layout_aware_reorg.py:683`. Editing `_mappings.py` alone would compile and change nothing.

**Files:**

- Modify: `pdomain_book_tools/layout/_mappings.py`
- Modify: `pdomain_book_tools/ocr/layout_aware_reorg.py`
- Test: `pdomain-book-tools/tests/layout/test_page_number_mapping.py`

**Interfaces:**

- Consumes: `RegionType.page_number` from the first plan.
- Produces: no new public symbol. `PP_DOCLAYOUT_TO_PGDP` and `_REGION_TO_BLOCK_ROLE` gain entries.

- [ ] **Step 1: Read both mapping sites first**

Run: `sed -n '1,60p' pdomain_book_tools/layout/_mappings.py`
Run: `sed -n '95,125p' pdomain_book_tools/ocr/layout_aware_reorg.py`
The entry style you add must match the surrounding entries in each file.

- [ ] **Step 2: Write the failing test**

```python
# tests/layout/test_page_number_mapping.py
from __future__ import annotations

from pdomain_book_contracts.layout.types import RegionType

from pdomain_book_tools.layout._mappings import PP_DOCLAYOUT_TO_PGDP
from pdomain_book_tools.ocr.layout_aware_reorg import _REGION_TO_BLOCK_ROLE


def test_pp_doclayout_page_number_no_longer_becomes_a_footer() -> None:
    # This dict holds plain strings, not RegionType members.
    assert PP_DOCLAYOUT_TO_PGDP["page_number"] == "page_number"


def test_the_new_value_names_a_real_region_type() -> None:
    assert RegionType(PP_DOCLAYOUT_TO_PGDP["page_number"]) is RegionType.page_number


def test_the_page_number_region_carries_the_folio_role() -> None:
    assert _REGION_TO_BLOCK_ROLE[RegionType.page_number] == "page number"


def test_the_footer_role_is_unchanged() -> None:
    assert _REGION_TO_BLOCK_ROLE[RegionType.footer] == "page footer"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `make test-single TEST='tests/layout/test_page_number_mapping.py'`
Expected: FAIL, because `PP_DOCLAYOUT_TO_PGDP["page_number"]` is currently `"footer"` and
`_REGION_TO_BLOCK_ROLE` has no `page_number` key.

- [ ] **Step 4: Add the two entries**

In `pdomain_book_tools/layout/_mappings.py`, change line 34 from `"page_number": "footer",` to:

```python
    "page_number": "page_number",
```

Update the comment above it, which currently states that page_number collapses into footer. It no
longer does.

In `pdomain_book_tools/ocr/layout_aware_reorg.py`, add one entry to `_REGION_TO_BLOCK_ROLE`:

```python
    RegionType.page_number: "page number",
```

The role string is `"page number"` with a space. It is one of the twenty that ship on `Block`
today, and `dropcap._SKIP_ROLES` matches it literally, so it must not be written with an
underscore.

- [ ] **Step 5: Run the tests**

Run: `make test-single TEST='tests/layout/test_page_number_mapping.py'`
Expected: PASS, all three tests.

- [ ] **Step 6: Run the full suite**

Run: `make test AI=1`
Expected: FAIL on two existing tests, then PASS once both are updated.

`tests/layout/test_mappings.py::test_page_chrome_labels_are_preserved_not_dropped` asserts
`page_number` maps to `RegionType.footer`, which is exactly what this task reverses. Update it to
expect `RegionType.page_number`.

`tests/test_page_model_doc.py::test_doc_lists_every_layout_region_type` requires every `RegionType`
member to appear backtick-quoted in `docs/architecture/page-serialization.md`. Add `page_number`
there. This is the `RegionType` analogue of the block-role drift gate Task 4 hits.

The 120-case layout regression fixture needs no regeneration: no case carries a `page_number`
region, verified by grep across `tests/fixtures/layout_regression`.

- [ ] **Step 7: Run the gate and commit**

```bash
make ci AI=1
git add pdomain_book_tools/layout/_mappings.py tests/layout/test_page_number_mapping.py
git commit -m "fix(layout): keep the folio instead of folding it into the footer"
```

---

### Task 3: Record the spread each page template was fitted from

`template_residual_px` is a raw pixel distance from a page to its fitted template. It is unbounded
and lower is better, so it cannot be compared to a confidence threshold until it is inverted and
scaled. The scale has to be per page class. A normal page's residual is bounded by the book's head
window, which can be as small as 8 pixels, while a chapter opening is measured against a template
fitted from pages that sank at least 150 pixels by widely differing amounts. One divisor cannot
serve both.

`PageTemplate` today carries only medians and counts. This task adds the missing spread, computed
the same way the book-level deviation already is: the median absolute deviation of the group's
first-band tops around their own median.

**Files:**

- Modify: `src/pdomain_pgdp_measure/page_templates.py`
- Modify: `src/pdomain_pgdp_measure/profile_models.py`
- Modify: `src/pdomain_pgdp_measure/profiling.py`
- Test: `tests/test_pgdp_page_templates.py`

**Interfaces:**

- Consumes: `_PageGeometry.first_band_top` and the existing `_fit_template` grouping.
- Produces: `PageTemplate.first_band_spread_px: int`, `PageTemplateRecord.first_band_spread_px: int`,
  and the serialized key `"first_band_spread_px"` inside each entry of `"page_templates"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pgdp_page_templates.py`, reusing the existing `_page` helper in that file:

```python
def test_a_template_records_the_spread_of_its_own_group() -> None:
    from pdomain_pgdp_measure.page_templates import fit_book_templates

    # Recto pages sit tightly around 300; the spread should be small.
    pages = [
        _page("p001.png", first_band_top=300),
        _page("p003.png", first_band_top=302),
        _page("p005.png", first_band_top=298),
        _page("p002.png", first_band_top=301),
        _page("p004.png", first_band_top=299),
    ]
    templates = fit_book_templates(pages)
    assert templates.templates
    for template in templates.templates:
        assert template.first_band_spread_px >= 0
        assert template.first_band_spread_px <= 4


def test_a_single_page_group_has_zero_spread() -> None:
    from pdomain_pgdp_measure.page_templates import _PageGeometry, _fit_template

    only = _PageGeometry(
        page_name="p001.png",
        band_tops=(300,),
        text_left=80,
        text_right=920,
        band_count=1,
        recto=True,
    )
    template = _fit_template("normal_recto", [only], total=1)
    assert template is not None
    assert template.first_band_spread_px == 0


def test_the_spread_reaches_the_serialized_profile() -> None:
    from pdomain_pgdp_measure.profile_models import PageTemplateRecord

    record = PageTemplateRecord(
        page_class="normal_recto",
        first_band_top_px=300,
        first_band_spread_px=2,
        text_left_px=80,
        text_right_px=920,
        band_count=24,
        page_count=5,
        page_share=0.5,
    )
    assert record.to_dict()["first_band_spread_px"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pgdp_page_templates.py -v`
Expected: FAIL with `AttributeError: 'PageTemplate' object has no attribute 'first_band_spread_px'`

- [ ] **Step 3: Add the field to `PageTemplate` and compute it**

In `src/pdomain_pgdp_measure/page_templates.py`, add one field to `PageTemplate`, after
`first_band_top_px`:

```python
    first_band_spread_px: int
```

Then compute it in `_fit_template`. The median absolute deviation around the group's own median is
the same statistic `fit_book_templates` already uses at book level, so the two are comparable:

```python
def _fit_template(
    page_class: PageClass, group: Sequence[_PageGeometry], *, total: int
) -> PageTemplate | None:
    if not group:
        return None
    tops = [item.first_band_top for item in group]
    center = median(tops)
    return PageTemplate(
        page_class=page_class,
        first_band_top_px=int(center),
        first_band_spread_px=int(median(abs(top - center) for top in tops)),
        text_left_px=int(median(item.text_left for item in group)),
        text_right_px=int(median(item.text_right for item in group)),
        band_count=int(median(item.band_count for item in group)),
        page_count=len(group),
        page_share=len(group) / total if total else 0.0,
    )
```

- [ ] **Step 4: Carry it through the profile record**

In `src/pdomain_pgdp_measure/profile_models.py`, add the field to `PageTemplateRecord` and to that
class's `to_dict` so it reaches the serialized profile:

```python
    first_band_spread_px: int = 0
```

**Put it at the END of the dataclass, not beside `first_band_top_px`.** `PageTemplateRecord` is a
plain frozen dataclass, not `kw_only`, and `first_band_top_px` is followed by five required fields.
A defaulted field placed before them raises `TypeError: non-default argument 'text_left_px' follows
default argument` when the class is defined. Order the key beside `first_band_top_px` inside
`to_dict` instead, where dict literal order carries no such constraint.

```python
                "first_band_spread_px": self.first_band_spread_px,
```

It defaults to zero so an existing stored profile still loads.

In `src/pdomain_pgdp_measure/profiling.py`, copy the new field in the `PageTemplateRecord`
construction inside `profile_project`:

```python
                first_band_spread_px=template.first_band_spread_px,
```

- [ ] **Step 5: Carry it through the wire model, or the value is lost on every reload**

`PageTemplateWire` at `profile_models.py:1048` is a separate pydantic model with its own hardcoded
field list and its own `to_domain`. `ProfileReport.from_json` and `from_dict` round-trip through
`ProjectProfileWire` and then `PageTemplateWire.to_domain()`. If the wire model does not carry the
field, every profile read back from disk silently resets `first_band_spread_px` to zero, which
destroys the one signal this task exists to record.

Add the field to `PageTemplateWire` after `first_band_top_px`. This model is a pydantic
`BaseModel`, so the dataclass ordering rule above does not apply and the field can sit where it
reads best:

```python
    first_band_spread_px: StrictInt = 0
```

and to its `to_domain`:

```python
            first_band_spread_px=self.first_band_spread_px,
```

It defaults so an existing stored profile without the key still validates.

- [ ] **Step 6: Prove the round trip keeps the value**

```python
def test_the_spread_survives_a_profile_round_trip() -> None:
    from pdomain_pgdp_measure.profile_models import PageTemplateWire

    wire = PageTemplateWire.model_validate(
        {
            "page_class": "normal_recto",
            "first_band_top_px": 300,
            "first_band_spread_px": 2,
            "text_left_px": 80,
            "text_right_px": 920,
            "band_count": 24,
            "page_count": 5,
            "page_share": 0.5,
        }
    )
    assert wire.to_domain().first_band_spread_px == 2


def test_a_stored_profile_without_the_key_still_validates() -> None:
    from pdomain_pgdp_measure.profile_models import PageTemplateWire

    wire = PageTemplateWire.model_validate(
        {
            "page_class": "normal_recto",
            "first_band_top_px": 300,
            "text_left_px": 80,
            "text_right_px": 920,
            "band_count": 24,
            "page_count": 5,
            "page_share": 0.5,
        }
    )
    assert wire.to_domain().first_band_spread_px == 0
```

- [ ] **Step 7: Regenerate the profile schema**

`schemas/pgdp-profile-v2.schema.json` documents `PageTemplateWire` and is now stale. The generator
is `profile_schema_json()` in `src/pdomain_pgdp_measure/profile_models.py`. Run it and write the
result, then confirm the new property appears:

Run: `grep -n "first_band_spread_px" schemas/pgdp-profile-v2.schema.json`
Expected: at least one hit, on `PageTemplateWire`, styled like `first_band_top_px`.

- [ ] **Step 8: Run the tests**

Run: `uv run pytest tests/test_pgdp_page_templates.py -v`
Expected: PASS, 25 tests: the five new ones plus the twenty already in that file.

- [ ] **Step 9: Run the full suite**

Run: `uv run pytest`
Expected: PASS. Warnings are errors in this repository, so a new deprecation surfaces as a failure.

- [ ] **Step 10: Run lint and typecheck, then commit**

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
git add src/pdomain_pgdp_measure schemas/pgdp-profile-v2.schema.json \
  tests/test_pgdp_page_templates.py
git commit -m "feat(templates): record the spread each page template was fitted from"
```

---

---

### Task 4: Widen `ALLOWED_BLOCK_ROLE_LABELS` to the same 34 roles

`Block.ALLOWED_BLOCK_ROLE_LABELS` holds the original twenty role strings. The vocabularies plan puts
34 into `pdomain-book-contracts`, and until this frozenset matches, `Block._normalize_label` raises
`ValueError` for all fourteen additions. Every route that sets a region role would fail on
`catchword`, `signature mark`, `plate`, and the rest.

Widen the frozenset and its alias map in place. `Block` keeps its own `frozenset[str]` rather than
importing the enum, because `Block` pulls in the imaging stack and the enum must not.

**Files:**

- Modify: `pdomain_book_tools/pdomain_book_tools/ocr/block.py`
- Test: `pdomain-book-tools/tests/ocr/test_block_role_vocabulary.py`

**Interfaces:**

- Consumes: the 34 role strings and their aliases, as listed in the vocabularies plan Task 2.
- Produces: no new symbol. `ALLOWED_BLOCK_ROLE_LABELS` and `BLOCK_ROLE_LABEL_ALIASES` grow.

- [ ] **Step 1: Read the current frozenset and alias map**

Run: `sed -n '55,100p' pdomain_book_tools/ocr/block.py`
Note the exact declaration style, and that canonical strings use spaces rather than underscores.

- [ ] **Step 2: Write the failing test**

```python
# tests/ocr/test_block_role_vocabulary.py
from __future__ import annotations

import pytest

from pdomain_book_tools.ocr.block import Block

_ADDITIONS = frozenset(
    {
        "signature mark", "catchword", "press figure", "rule", "brace",
        "bracket", "group label", "plate", "speaker label", "stage direction",
        "interlinear gloss", "abandoned", "decorated initial", "unknown",
    }
)


def test_the_twenty_shipped_roles_survive() -> None:
    shipped = {
        "paragraph", "sidenote", "page header", "page footer", "page number",
        "printers mark", "blockquote", "poetry", "recovered", "illustration",
        "decoration", "caption", "figure", "table", "footnote", "title",
        "section", "list", "formula", "artefact",
    }
    assert shipped <= Block.ALLOWED_BLOCK_ROLE_LABELS


def test_the_fourteen_additions_are_accepted() -> None:
    assert _ADDITIONS <= Block.ALLOWED_BLOCK_ROLE_LABELS
    assert len(Block.ALLOWED_BLOCK_ROLE_LABELS) == 34


@pytest.mark.parametrize("role", sorted(_ADDITIONS))
def test_each_addition_normalizes_without_raising(role: str) -> None:
    # `items` has no default on Block.__init__ — pass it explicitly, matching
    # the idiom in tests/ocr/test_block.py.
    block = Block(items=[], block_role_labels=[role])
    assert role in block.block_role_labels


def test_the_new_aliases_fold() -> None:
    assert Block(items=[], block_role_labels=["frontispiece"]).block_role_labels == ["plate"]
    assert Block(items=[], block_role_labels=["signaturemark"]).block_role_labels == [
        "signature mark"
    ]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `make test-single TEST='tests/ocr/test_block_role_vocabulary.py'`
Expected: FAIL. The additions raise `ValueError` from `_normalize_label`.

- [ ] **Step 4: Add the fourteen roles and five aliases**

Append the fourteen strings to `ALLOWED_BLOCK_ROLE_LABELS`, keeping the existing twenty untouched
and using spaces rather than underscores. Add to `BLOCK_ROLE_LABEL_ALIASES`: `frontispiece` to
`plate`, `signaturemark` to `signature mark`, `pressfigure` to `press figure`, `stagedirection` to
`stage direction`, and `speakerlabel` to `speaker label`.

- [ ] **Step 5: Run the tests**

Run: `make test-single TEST='tests/ocr/test_block_role_vocabulary.py'`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `make test AI=1`
Expected: FAIL on first run, then PASS after the doc update below.

`tests/test_page_model_doc.py::test_doc_lists_every_allowed_block_role_label` is a drift gate: it
asserts every value in `ALLOWED_BLOCK_ROLE_LABELS` appears backtick-quoted in
`docs/architecture/page-serialization.md`. Widening the frozenset without touching that doc fails it
with thirteen missing labels. Add the fourteen roles and five aliases to the "Block roles" and alias
listings in that document. The addition is documentation only; remove and rename nothing.

Then confirm `dropcap._SKIP_ROLES` and `route_sidenote_reading_order` still pass, since both match
role strings literally and a widened set must not disturb them.

- [ ] **Step 7: Run the gate and commit**

```bash
make ci AI=1
git add pdomain_book_tools/ocr/block.py tests/ocr/test_block_role_vocabulary.py
git commit -m "feat(ocr): widen the block role vocabulary to 34 roles"
```

## What this plan does not do

- It does not build the normalizer that turns `template_residual_px` into a confidence. This task
  supplies the missing input; the normalizer belongs with the proposal engine, which is slice 4 and
  needs its own design.
- It does not replace `ALLOWED_BLOCK_ROLE_LABELS` with `RegionRole` as the sole authority. Task 4
  widens the frozenset to the same 34 values; making `Block` import the enum itself is a larger
  change and is not required for any consumer.
- It does not resolve the conflict between a region's explicit box and `Block.recompute_bounding_box`.
  That is a larger change and the additive-only rule means nothing is broken by deferring it.
- It does not change `validate_word_preservation`. Its contract and its five existing tests are
  untouched by design.
- It does not add explicit word membership to regions. That arrives with the region stores in the
  third plan.

## Related

- [Annotation provenance and
  persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) — the design.
- [Annotation vocabularies in
  book-contracts](2026-09-08-annotation-vocabularies-in-book-contracts.md) — the first plan. Task 2
  here depends on its Task 4.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — the seven slices.
