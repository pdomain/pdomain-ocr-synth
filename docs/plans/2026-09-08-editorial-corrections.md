# Editorial Corrections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a labeler record that a page's ink should have read differently — a printer's error,
a dropped word, a name misspelled through a chapter — without that claim ever entering
`Word.ground_truth_text`. Corrections are captured and held apart, never applied.

**Architecture:** `EditorialCorrection` is a new portable pydantic model in `pdomain-book-contracts`,
sibling to `StyleSpan`, over a half-open grapheme range that — unlike `StyleSpan` — may be empty, to
represent a printer's dropped word as a zero-extent insertion. It carries no id and no page hash of
its own, the same restraint `StyleSpan` shows; identity is derived in the labeler. The labeler adds
two append-only JSONL journals, both composing `TypographyCorrectionLog`'s file primitives exactly as
`StyleSpanDecisionLog` already does: `EditorialCorrectionLog` records what was recorded (a correction
is authored, not re-parsed from immutable source content, so this journal both mints the id and
stores the record), and `EditorialCorrectionDecisionLog` records a reviewer's confirm-or-reject
verdict per correction, CAS-bound the same way `StyleSpanDecisionLog` is. Three routes expose this:
record, list, and decide.

**Tech Stack:** Python 3.11+ (book-contracts), Python 3.13 (labeler), pydantic `BaseModel`,
`StrEnum`, JSONL journals with an OS append lock, FastAPI, pytest, ruff, basedpyright.

**Spec:** [Annotation provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md), section "Editorial
corrections say what the page should have said, and never touch ground truth."

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-08
- **Last verified:** 2026-09-08
- **Provenance:** authored 2026-09-08 from the spec above and direct inspection of
  `pdomain-book-contracts/pdomain_book_contracts/typography/spans.py` (`StyleSpan._validate_range`,
  `CanonicalModel`), `typography/records.py` (`ParserNoteEvidence`, `ParserNoteStatus`),
  `typography/labels.py`, `typography/review.py` (`TypographyCorrection`, distinct from this plan's
  model), `typography/__init__.py`, `pyproject.toml`, `tests/test_torch_free_import.py`;
  `pdomain-book-tools/pdomain_book_tools/typography/{__init__,labels,spans,records}.py` (the
  re-export shim convention, and its absence for the new module — see Global Constraints);
  `pdomain-book-tools/pdomain_book_tools/ocr/word.py` (`Word.ground_truth_text`,
  `_ground_truth_text`); `pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/typography_review.py`
  (`stable_page_id`, `stable_word_id`, `TypographyCorrectionLog`, its private `_open_journal_directory`
  / `_open_regular_file` / `_write_all`, and the absence of a module logger), `api/typography.py`
  (`_project_page`, `_logical_page_id`, `bind_page_labeling_lease`, `get_typography_head`,
  `append_typography_correction`), `core/models.py` (`Project`), `core/project_state.py`
  (`ProjectState.get_page_lock`, `.loaded_project`, `.labeling_bundle`), `api/dependencies.py`
  (`bind_page_labeling_lease` tolerates no loaded labeling bundle), `pyproject.toml` (labeler depends
  directly on both `pdomain-book-tools` and `pdomain-book-contracts`), and its Makefile; and the two
  companion plans this one depends on (see Global Constraints)
- **Disposition:** Active. Closes the editorial-correction gap the spec names under "Editorial
  corrections say what the page should have said, and never touch ground truth." Independent of the
  region-store plans; touches no region code.
- **Read when:** implementing editorial-correction capture, its decision journal, or reconciling an
  editorial correction with the word-scoped `TypographyCorrectionLog` or the span-scoped
  `StyleSpanDecisionLog`.
- **Search terms:** EditorialCorrection, CorrectionReason, stable_editorial_correction_id,
  EditorialCorrectionLog, EditorialCorrectionDecisionLog, EditorialCorrectionDisposition,
  reading_as_printed, reading_intended, ground_truth_text invariant, ParserNoteEvidence, quarantined
  correction, half-open grapheme range, insertion, deletion.

## Global Constraints

- **This plan depends on two companion plans landing first, in either order relative to each other,
  both before this plan's Task 1:**
  - [Annotation vocabularies in
    book-contracts](2026-09-08-annotation-vocabularies-in-book-contracts.md) — Task 1 imports
    `ConfidenceTier`, `KnowledgeState`, `LabelSource` from `pdomain_book_contracts.annotation`, which
    that plan creates. Verified absent today: `pdomain_book_contracts/annotation/` does not exist in
    the current tree: only `pdomain_book_contracts/typography/labels.py` defines these three enums.
  - [Style span review surface](2026-09-08-style-span-review-surface.md) — Tasks 2–5 extend
    `core/typography_review.py` and `api/typography.py` immediately after the classes and routes that
    plan adds (`StyleSpanDecisionLog`, `record_style_span_decision`), and Task 4's imports assume that
    plan already added `ConfidenceTier`, `KnowledgeState`, `LabelSource` to `api/typography.py`'s
    `from pdomain_book_tools.typography import (...)` block. Verified absent today: neither file
    contains `StyleSpanDecisionLog`, `SpanDisposition`, or `stable_style_span_id` in the current tree.
  - Both are themselves unimplemented as of this plan's authoring (verified: `git log` on
    `pdomain-book-contracts` shows no commit past `9bde881`, and neither `core/regions/` nor
    `pdomain_book_contracts/annotation/` exists). Insertion points below are anchored to symbol names,
    not line numbers, so they survive whichever of the two companion plans lands first.
- **An editorial correction never enters `Word.ground_truth_text`.** `EditorialCorrection` carries no
  field that could be mistaken for it (verified: `Word.ground_truth_text` lives on
  `pdomain_book_tools/ocr/word.py:197-207`, `_ground_truth_text` at line 98 — this plan's model and
  routes never import or reference `pdomain_book_tools.ocr.word`, `Word`, or `ground_truth_text` at
  all). Task 1 asserts this structurally; Task 4 asserts it against a live `Project`.
- **A correction's grapheme range may be empty.** `StyleSpan._validate_range`
  (`pdomain_book_contracts/typography/spans.py:76-81`, verified) requires `self.start < self.end` and
  so cannot model a zero-width insertion. `EditorialCorrection._validate_range` instead requires
  `start <= end`, and a second validator forbids a nonempty `reading_as_printed` when `start == end`
  — see Task 1.
- **Identity is derived, not caller-supplied, for the same reason `stable_style_span_id` is** (style
  span plan, `core/typography_review.py` Task 1): a bare caller-supplied string can collide or drift.
  Unlike a style span, a correction is authored rather than re-parsed from an existing immutable page
  record, so there is no fixed list position to enumerate — `EditorialCorrectionLog.append` supplies
  the `index` `stable_editorial_correction_id` needs as the count of corrections already recorded for
  the page, read under the journal's own exclusive lock at write time (Task 2).
- **The CAS `head_token` pattern applies to the decision route, not the `generation`/`PagePayload`
  convention.** Verified against `api/words.py`'s `update_word_ground_truth`: every mutating word
  route takes the page lock, bumps `PageState.generation`, persists through the page store, and
  returns a full `PagePayload`. An editorial correction's data never enters
  `PageState.page_record.payload` — it lives only in the two journals this plan adds. The design's
  rule is explicit: "Any annotation level whose data does not live on the page follows the typography
  pattern rather than this one." The record route needs no CAS (there is no prior state for a brand
  new correction to be stale against); the decision route does, exactly like
  `record_style_span_decision`.
- **No book-tools re-export shim is added.** Every other `pdomain_book_contracts.typography.*` module
  has a matching `pdomain_book_tools/typography/*.py` shim (verified: `labels.py`, `spans.py`,
  `records.py` each just re-export). Adding `pdomain_book_tools/typography/editorial.py` would touch
  a third repository this plan's scope excludes. The labeler instead imports `EditorialCorrection` and
  `CorrectionReason` directly from `pdomain_book_contracts.typography.editorial` — verified as an
  already-declared direct dependency (`pdomain-book-contracts>=0.1.0`, `pyproject.toml` line 35) that
  the labeler simply has not imported from directly before now.
- **No hand-maintained field list can drift out of sync with a domain type.** `EditorialCorrection`
  itself is the wire model (a pydantic `CanonicalModel`, not a dataclass paired with a separate
  hand-written `to_dict`/`from_dict`), and every labeler-side record (`EditorialCorrectionEnvelope`,
  `EditorialCorrectionBinding`, `EditorialCorrectionDecisionHead`) is a pydantic `BaseModel` whose
  `model_dump`/`model_validate` cover every field automatically. There is no second field list to
  update when a field is added.
- **The module logger name.** `core/typography_review.py` declares no logger at all today (verified:
  no `logging` import, no `log = logging.getLogger(__name__)` in the current file). This plan follows
  that — it adds no logger either. `api/typography.py` likewise declares none.
- Python floor: `>=3.11,<3.14` for `pdomain-book-contracts`; `>=3.13,<3.14` for
  `pdomain-ocr-labeler-spa`.
- Book-contracts commands: `make test`, `make ci` (lint, typecheck, test, build,
  `docgraph check --strict`). No `AI=1` convention.
- Labeler commands: `make AI=1 <target>` captures verbose output to `.ci-ai.log`; run
  `make AI=1 ci` before committing. `make test` excludes `e2e/` and the `slow`/`integration` markers
  by default.
- Journals are append-only. An existing record is never rewritten; a decision journal represents a
  change of mind as a new record with an advanced revision, exactly like `StyleSpanDecisionLog`.

---

## File Structure

| file | responsibility |
| --- | --- |
| `pdomain_book_contracts/typography/editorial.py` | `CorrectionReason`, `EditorialCorrection` |
| `pdomain_book_contracts/typography/__init__.py` | modified: exports the two names above |
| `pdomain-book-contracts/tests/test_editorial_correction.py` | model validation and the ground-truth invariant |
| `core/typography_review.py` (labeler) | modified: id helper, envelope, `EditorialCorrectionLog`, disposition, binding, head, `EditorialCorrectionDecisionLog` |
| `api/typography.py` (labeler) | modified: request/response models, record/list/decide routes |
| `tests/unit/core/test_typography_review.py` (labeler) | modified: unit tests for the two new journals |
| `tests/unit/api/test_typography_editorial_corrections.py` (labeler) | new: route tests |

---

### Task 1: `EditorialCorrection` in book-contracts

The model that says what the page should have said, and nothing that could be mistaken for what it
does say. It generalizes `ParserNoteEvidence`'s discipline — captured, held apart, never applied —
from PGDP's `[** ... ]` note convention to any correction from any source.

**Files:**

- Create: `pdomain_book_contracts/typography/editorial.py`
- Modify: `pdomain_book_contracts/typography/__init__.py`
- Test: `pdomain-book-contracts/tests/test_editorial_correction.py`

**Interfaces:**

- Consumes: `ConfidenceTier`, `KnowledgeState`, `LabelSource` from `pdomain_book_contracts.annotation`
  (the first companion plan); `CanonicalModel`, `SourceSlice` from
  `pdomain_book_contracts.typography.spans`.
- Produces: `CorrectionReason`, `EditorialCorrection`, both importable from
  `pdomain_book_contracts.typography` and from `pdomain_book_contracts.typography.editorial`.

- [ ] **Step 1: Write the failing test**

```python
# pdomain-book-contracts/tests/test_editorial_correction.py
"""Unit tests for EditorialCorrection: what a page should have said, never what it says."""

from __future__ import annotations

import pytest


def _correction(**overrides: object) -> object:
    from pdomain_book_contracts.annotation import ConfidenceTier, KnowledgeState, LabelSource
    from pdomain_book_contracts.typography.editorial import CorrectionReason, EditorialCorrection

    fields: dict[str, object] = {
        "start": 4,
        "end": 7,
        "reading_as_printed": "adn",
        "reading_intended": "and",
        "reason": CorrectionReason.PRINTERS_ERROR,
        "reason_note": None,
        "state": KnowledgeState.POSITIVE,
        "label_source": LabelSource.HUMAN,
        "confidence_tier": ConfidenceTier.GOLD,
        "source_slices": (),
        "rule_ref": None,
        "warnings": (),
    }
    fields.update(overrides)
    return EditorialCorrection(**fields)


def test_a_substitution_round_trips() -> None:
    from pdomain_book_contracts.typography.editorial import EditorialCorrection

    correction = _correction(start=4, end=7, reading_as_printed="adn", reading_intended="and")
    restored = EditorialCorrection.from_json_bytes(correction.to_json_bytes())
    assert restored == correction


def test_an_insertion_has_an_empty_range_and_empty_reading_as_printed() -> None:
    correction = _correction(start=5, end=5, reading_as_printed="", reading_intended="the")
    assert correction.start == correction.end == 5
    assert correction.reading_as_printed == ""


def test_an_insertion_rejects_a_nonempty_reading_as_printed() -> None:
    with pytest.raises(ValueError, match="empty reading_as_printed"):
        _correction(start=5, end=5, reading_as_printed="x", reading_intended="the")


def test_a_deletion_has_an_empty_reading_intended() -> None:
    correction = _correction(start=10, end=13, reading_as_printed="the", reading_intended="")
    assert correction.reading_intended == ""
    assert correction.start < correction.end


def test_range_rejects_start_greater_than_end() -> None:
    with pytest.raises(ValueError, match="start <= end"):
        _correction(start=8, end=4)


def test_rejects_a_no_op_correction() -> None:
    with pytest.raises(ValueError, match="must differ"):
        _correction(reading_as_printed="and", reading_intended="and")


def test_reason_is_a_five_member_controlled_vocabulary() -> None:
    from pdomain_book_contracts.typography.editorial import CorrectionReason

    assert {member.value for member in CorrectionReason} == {
        "printers_error",
        "missing_punctuation",
        "modernization",
        "editorial_conjecture",
        "other",
    }


def test_the_model_carries_no_field_that_could_be_mistaken_for_ground_truth() -> None:
    """The invariant: nothing here can leak into Word.ground_truth_text by construction."""
    from pdomain_book_contracts.typography.editorial import EditorialCorrection

    field_names = set(EditorialCorrection.model_fields)
    assert not any("ground_truth" in name for name in field_names)


def test_state_label_source_and_confidence_tier_come_from_the_shared_vocabulary() -> None:
    """A conjecture and a certain fix must be distinguishable."""
    from pdomain_book_contracts.annotation import ConfidenceTier, KnowledgeState, LabelSource

    correction = _correction(
        state=KnowledgeState.UNKNOWN,
        label_source=LabelSource.MODEL,
        confidence_tier=ConfidenceTier.BRONZE,
    )
    assert correction.state is KnowledgeState.UNKNOWN
    assert correction.label_source is LabelSource.MODEL
    assert correction.confidence_tier is ConfidenceTier.BRONZE


def test_typography_still_exports_it() -> None:
    from pdomain_book_contracts.typography import CorrectionReason as ReExported
    from pdomain_book_contracts.typography.editorial import CorrectionReason as Direct

    assert ReExported is Direct
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_editorial_correction.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pdomain_book_contracts.typography.editorial'`

- [ ] **Step 3: Write the implementation**

Create `pdomain_book_contracts/typography/editorial.py`:

```python
"""Editorial corrections: what a page should have said, never what it says.

The five other typography and annotation models all describe the ink as printed.
An ``EditorialCorrection`` is the one thing that departs from it — a printer's
error, a dropped word, a name misspelled through a chapter — recorded beside the
reading, never inside it.

The invariant this module exists to protect: an editorial correction never enters
``Word.ground_truth_text``. Ground truth is what the ink says, always. If "should
have said" leaks into it, the recognition trainer learns to read words that are
not on the page. Nothing in ``EditorialCorrection`` can cause that leak by
construction — the model has no field, and no method, that writes anywhere but
its own record. Applying a correction to a training corpus is a post-processing
stage that does not yet exist; this module only lets one be recorded.

The nearest existing precedent is ``ParserNoteEvidence`` (``records.py``), which
quarantines a PGDP proofer's ``[** ... ]`` note: captured, held apart, never
applied. This generalizes that discipline from PGDP's note convention to any
correction from any source.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from pdomain_book_contracts.annotation import ConfidenceTier, KnowledgeState, LabelSource
from pdomain_book_contracts.typography.spans import CanonicalModel, SourceSlice

_StrictIndex = Annotated[int, Field(strict=True)]


class CorrectionReason(StrEnum):
    """Why an editorial correction departs from what the ink says.

    A controlled vocabulary, not free text: ``EditorialCorrection.reason_note``
    may add detail, but ``reason`` is always the classifier a reviewer or a
    trainer filters on.
    """

    PRINTERS_ERROR = "printers_error"
    MISSING_PUNCTUATION = "missing_punctuation"
    MODERNIZATION = "modernization"
    EDITORIAL_CONJECTURE = "editorial_conjecture"
    OTHER = "other"


class EditorialCorrection(CanonicalModel):
    """One editorial correction over a half-open grapheme range.

    ``reading_as_printed`` is what the ink says over ``[start, end)``.
    ``reading_intended`` is what it should have said. Neither is
    ``Word.ground_truth_text`` — this model carries no field that could be
    mistaken for it, and nothing here writes to a ``Word`` at all.

    The range may be empty (``start == end``): a printer's dropped word is an
    insertion with no extent in the ink, which is why this cannot reuse
    ``StyleSpan`` — its range validator requires ``start < end`` and so forbids
    exactly this case. A deletion is the mirror case: extent in the ink, an
    empty ``reading_intended``, for a word the printer set twice.
    """

    start: _StrictIndex
    end: _StrictIndex
    reading_as_printed: str
    reading_intended: str
    reason: CorrectionReason
    reason_note: str | None
    state: KnowledgeState
    label_source: LabelSource
    confidence_tier: ConfidenceTier
    source_slices: tuple[SourceSlice, ...]
    rule_ref: str | None
    warnings: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_range(self) -> Self:
        if self.start < 0 or self.start > self.end:
            msg = "editorial correction must be a half-open grapheme range with start <= end"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_insertion_shape(self) -> Self:
        if self.start == self.end and self.reading_as_printed != "":
            msg = "an insertion (start == end) must have an empty reading_as_printed"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_actually_corrects(self) -> Self:
        if self.reading_as_printed == self.reading_intended:
            msg = "reading_intended must differ from reading_as_printed"
            raise ValueError(msg)
        return self
```

Edit `pdomain_book_contracts/typography/__init__.py`:

1. Add `` and ``editorial.py``` to the module docstring's owned-file list (currently "Owns
   ``labels.py``, ``spans.py``, ``normalization.py``, ``records.py``, ``annotations.py``,
   ``exchange.py``, ``book_manifest.py``, and ``review.py``"), so it reads "... ``book_manifest.py``,
   ``editorial.py``, and ``review.py``".
1. Insert a new import block, alphabetically between the `book_manifest` and `exchange` blocks:

```python
from pdomain_book_contracts.typography.editorial import CorrectionReason, EditorialCorrection
```

1. Add `"CorrectionReason"` and `"EditorialCorrection"` to `__all__`, alphabetically: immediately
   after `"CorrectionDecision"` and before `"Evidence"`.

- [ ] **Step 4: Run the tests**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_editorial_correction.py -v`
Expected: PASS, all nine tests.

- [ ] **Step 5: Run the full suite and the gate**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest -v`
Expected: PASS, including `tests/test_torch_free_import.py` — no change needed there, since
`editorial.py` lives inside the already-covered `pdomain_book_contracts.typography` subpackage
(verified: `test_every_subpackage_imports_without_heavy_stack` imports
`pdomain_book_contracts.typography` as a whole, not module-by-module).

Run: `make ci`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pdomain_book_contracts/typography/editorial.py pdomain_book_contracts/typography/__init__.py \
  tests/test_editorial_correction.py
git commit -m "feat(typography): add EditorialCorrection, captured and held apart from ground truth"
```

---

### Task 2: The correction journal

An editorial correction is authored — by a person today, potentially by a model later, distinguished
by `LabelSource` — not re-parsed from an existing immutable page record the way a `StyleSpan` is. So
this journal both mints the correction's stable id and durably stores the record, reusing
`TypographyCorrectionLog`'s file primitives by composition exactly as `StyleSpanDecisionLog` does.

**Files:**

- Edit: `src/pdomain_ocr_labeler_spa/core/typography_review.py`
- Test: `tests/unit/core/test_typography_review.py`

**Interfaces:**

- Consumes: `EditorialCorrection` from `pdomain_book_contracts.typography.editorial`;
  `TypographyCorrectionLog`'s private `_open_journal_directory`, `_open_regular_file`, `_write_all`
  (already reused this way by `ImportedTextValidationLog` and, once the style-span plan lands,
  `StyleSpanDecisionLog`).
- Produces: `stable_editorial_correction_id(*, logical_page_id: str, index: int, start: int, end:
  int, reading_as_printed: str, reading_intended: str) -> str`, `EditorialCorrectionEnvelope`,
  `EditorialCorrectionLog(project_root: Path, *, corpus_root: Path | None = None)` with
  `append(correction: EditorialCorrection, *, logical_page_id: str, labeler_id: str) ->
  EditorialCorrectionEnvelope` and `records(logical_page_id: str) ->
  tuple[EditorialCorrectionEnvelope, ...]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/test_typography_review.py` (extend the existing `from
pdomain_ocr_labeler_spa.core.typography_review import (...)` block with
`EditorialCorrectionEnvelope`, `EditorialCorrectionLog`, `stable_editorial_correction_id`):

```python
def test_stable_editorial_correction_id_is_deterministic_given_the_same_index() -> None:
    first = stable_editorial_correction_id(
        logical_page_id="page-1", index=0, start=4, end=7,
        reading_as_printed="adn", reading_intended="and",
    )
    again = stable_editorial_correction_id(
        logical_page_id="page-1", index=0, start=4, end=7,
        reading_as_printed="adn", reading_intended="and",
    )
    assert first == again

    different_page = stable_editorial_correction_id(
        logical_page_id="page-2", index=0, start=4, end=7,
        reading_as_printed="adn", reading_intended="and",
    )
    different_index = stable_editorial_correction_id(
        logical_page_id="page-1", index=1, start=4, end=7,
        reading_as_printed="adn", reading_intended="and",
    )
    assert len({first, different_page, different_index}) == 3


def test_stable_editorial_correction_id_rejects_start_after_end() -> None:
    with pytest.raises(ValueError, match="start <= end"):
        stable_editorial_correction_id(
            logical_page_id="page-1", index=0, start=7, end=4,
            reading_as_printed="", reading_intended="",
        )


def _editorial_correction(**overrides: object) -> EditorialCorrection:
    from pdomain_book_contracts.annotation import ConfidenceTier, KnowledgeState, LabelSource
    from pdomain_book_contracts.typography.editorial import CorrectionReason, EditorialCorrection

    fields: dict[str, object] = {
        "start": 4,
        "end": 7,
        "reading_as_printed": "adn",
        "reading_intended": "and",
        "reason": CorrectionReason.PRINTERS_ERROR,
        "reason_note": None,
        "state": KnowledgeState.POSITIVE,
        "label_source": LabelSource.HUMAN,
        "confidence_tier": ConfidenceTier.GOLD,
        "source_slices": (),
        "rule_ref": None,
        "warnings": (),
    }
    fields.update(overrides)
    return EditorialCorrection(**fields)


def test_appending_a_correction_mints_an_id_and_reads_back(tmp_path: Path) -> None:
    log = EditorialCorrectionLog(tmp_path, corpus_root=tmp_path)

    envelope = log.append(_editorial_correction(), logical_page_id="page-1", labeler_id="reviewer-1")

    assert envelope.logical_page_id == "page-1"
    assert envelope.labeler_id == "reviewer-1"
    assert envelope.correction == _editorial_correction()
    found = log.records("page-1")
    assert found == (envelope,)


def test_two_corrections_on_the_same_page_get_distinct_stable_ids(tmp_path: Path) -> None:
    log = EditorialCorrectionLog(tmp_path, corpus_root=tmp_path)

    first = log.append(_editorial_correction(), logical_page_id="page-1", labeler_id="reviewer-1")
    second = log.append(
        _editorial_correction(start=10, end=13, reading_as_printed="teh", reading_intended="the"),
        logical_page_id="page-1",
        labeler_id="reviewer-1",
    )

    assert first.correction_id != second.correction_id
    assert [envelope.correction_id for envelope in log.records("page-1")] == [
        first.correction_id,
        second.correction_id,
    ]


def test_recording_identical_content_twice_still_yields_two_distinct_ids(tmp_path: Path) -> None:
    log = EditorialCorrectionLog(tmp_path, corpus_root=tmp_path)

    first = log.append(_editorial_correction(), logical_page_id="page-1", labeler_id="reviewer-1")
    second = log.append(_editorial_correction(), logical_page_id="page-1", labeler_id="reviewer-2")

    assert first.correction_id != second.correction_id


def test_corrections_from_different_pages_do_not_collide(tmp_path: Path) -> None:
    log = EditorialCorrectionLog(tmp_path, corpus_root=tmp_path)

    log.append(_editorial_correction(), logical_page_id="page-1", labeler_id="reviewer-1")

    assert log.records("page-2") == ()


def test_a_fresh_log_has_no_records(tmp_path: Path) -> None:
    log = EditorialCorrectionLog(tmp_path, corpus_root=tmp_path)
    assert log.records("page-1") == ()


def test_appending_never_rewrites_an_existing_record(tmp_path: Path) -> None:
    log = EditorialCorrectionLog(tmp_path, corpus_root=tmp_path)
    log.append(_editorial_correction(), logical_page_id="page-1", labeler_id="reviewer-1")
    first = (tmp_path / ".pd-pages" / "editorial-corrections.jsonl").read_bytes()

    log.append(
        _editorial_correction(start=10, end=13, reading_as_printed="teh", reading_intended="the"),
        logical_page_id="page-1",
        labeler_id="reviewer-1",
    )
    second = (tmp_path / ".pd-pages" / "editorial-corrections.jsonl").read_bytes()

    assert second.startswith(first)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/test_typography_review.py -k editorial -v`
Expected: FAIL with `ImportError` / `NameError` for the not-yet-defined names (add
`EditorialCorrectionEnvelope`, `EditorialCorrectionLog`, `stable_editorial_correction_id`, and
`from pdomain_book_contracts.typography.editorial import EditorialCorrection` to the test file's
imports before running).

- [ ] **Step 3: Write the implementation**

In `src/pdomain_ocr_labeler_spa/core/typography_review.py`:

- Add `from pdomain_book_contracts.typography.editorial import EditorialCorrection` as a new import,
  directly beneath the existing `from pdomain_book_tools.typography import (...)` block (this module
  does not yet import from `pdomain_book_contracts` directly; see Global Constraints for why this one
  does).
- Insert the following immediately after the `StyleSpanDecisionLog` class the style-span-review-surface
  plan's Task 2 adds, and before `__all__`:

```python
_EDITORIAL_CORRECTION_ID_NAMESPACE = UUID("a1d4c8f2-3e6b-4a90-9c7d-1f5b8e2a6d34")


def stable_editorial_correction_id(
    *,
    logical_page_id: str,
    index: int,
    start: int,
    end: int,
    reading_as_printed: str,
    reading_intended: str,
) -> str:
    """Return a deterministic identity for one recorded editorial correction.

    An editorial correction is authored, not re-parsed from immutable page content
    the way a ``StyleSpan`` is (see ``stable_style_span_id``), so there is no fixed
    list position to enumerate. ``EditorialCorrectionLog.append`` instead supplies
    ``index`` as the count of corrections already recorded for ``logical_page_id``
    at the moment of the write, taken under the journal's own exclusive lock — so
    two corrections appended for the same page never collide, and identical content
    recorded twice still gets two distinct, stable identities.
    """
    if index < 0:
        raise ValueError("index must be nonnegative")
    if start < 0 or start > end:
        raise ValueError(
            "editorial correction must be a half-open grapheme range with start <= end"
        )
    key = f"{logical_page_id}\0{index}\0{start}\0{end}\0{reading_as_printed}\0{reading_intended}"
    return str(uuid5(_EDITORIAL_CORRECTION_ID_NAMESPACE, key))


class EditorialCorrectionEnvelope(BaseModel):
    """One durably recorded editorial correction, with who recorded it and when."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    correction_id: str
    logical_page_id: str
    correction: EditorialCorrection
    labeler_id: str
    created_at: str


@final
class EditorialCorrectionLog:
    """Project-local JSONL journal of what a page should have said.

    Recording a correction here never touches ``Word.ground_truth_text`` or
    ``Project.ground_truth_map`` — this journal has no path to either. It
    generalizes ``ParserNoteEvidence``'s discipline (captured, held apart, never
    applied) from PGDP's note convention to any correction from any source. Reuses
    ``TypographyCorrectionLog``'s file primitives exactly as ``StyleSpanDecisionLog``
    does, and takes the same operating-system append lock so writers across worker
    processes serialize.
    """

    _NAME: ClassVar[str] = "editorial-corrections.jsonl"
    _RECOVERY_NAME: ClassVar[str] = "editorial-corrections.recovery.jsonl"

    def __init__(self, project_root: Path, *, corpus_root: Path | None = None) -> None:
        self._files = TypographyCorrectionLog(project_root, corpus_root=corpus_root)
        self.path = self._files.path.with_name(self._NAME)

    def append(
        self, correction: EditorialCorrection, *, logical_page_id: str, labeler_id: str
    ) -> EditorialCorrectionEnvelope:
        """Mint a stable id and durably append one editorial correction."""
        parent, descriptor = self._open(create=True)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            rows = self._read(descriptor, parent=parent)
            index = sum(
                1
                for row in rows
                if isinstance(row.get("record"), dict)
                and row["record"].get("logical_page_id") == logical_page_id
            )
            correction_id = stable_editorial_correction_id(
                logical_page_id=logical_page_id,
                index=index,
                start=correction.start,
                end=correction.end,
                reading_as_printed=correction.reading_as_printed,
                reading_intended=correction.reading_intended,
            )
            envelope = EditorialCorrectionEnvelope(
                correction_id=correction_id,
                logical_page_id=logical_page_id,
                correction=correction,
                labeler_id=labeler_id,
                created_at=datetime.now(UTC).isoformat(),
            )
            payload = (
                json.dumps(
                    {"kind": "correction", "record": envelope.model_dump(mode="json")},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode()
            self._files._write_all(descriptor, payload)
            os.fsync(descriptor)
            return envelope
        finally:
            os.close(descriptor)
            os.close(parent)

    def records(self, logical_page_id: str) -> tuple[EditorialCorrectionEnvelope, ...]:
        """Every correction recorded for one page, in the order they were written."""
        parent, descriptor = self._open(create=True)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH)
            rows = self._read(descriptor, parent=parent)
        finally:
            os.close(descriptor)
            os.close(parent)
        found: list[EditorialCorrectionEnvelope] = []
        for row in rows:
            record = row.get("record")
            if not isinstance(record, dict):
                continue
            envelope = EditorialCorrectionEnvelope.model_validate(record)
            if envelope.logical_page_id == logical_page_id:
                found.append(envelope)
        return tuple(found)

    def _open(self, *, create: bool) -> tuple[int, int]:
        parent = self._files._open_journal_directory(create=create)
        try:
            descriptor, created = self._files._open_regular_file(
                parent, self._NAME, flags=os.O_RDWR | os.O_APPEND, create=create
            )
            if created:
                os.fsync(parent)
            return parent, descriptor
        except Exception:
            os.close(parent)
            raise

    def _read(self, descriptor: int, *, parent: int) -> list[dict[str, object]]:
        _ = os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        raw = b"".join(chunks)
        if not raw:
            return []
        terminated = raw.endswith(b"\n")
        lines = raw.split(b"\n")
        if terminated:
            lines.pop()
        trailing = None if terminated else lines.pop()
        rows = [self._parse_row(line) for line in lines]
        if trailing is None:
            return rows
        try:
            rows.append(self._parse_row(trailing))
            return rows
        except json.JSONDecodeError:
            truncate_at = len(raw) - len(trailing)
            os.ftruncate(descriptor, truncate_at)
            os.fsync(descriptor)
            self._write_recovery(parent, trailing, truncate_at)
            return rows

    @staticmethod
    def _parse_row(payload: bytes) -> dict[str, object]:
        value = json.loads(payload)
        if not isinstance(value, dict) or value.get("kind") != "correction":
            raise ValueError("invalid editorial correction journal record")
        return value

    def _write_recovery(self, parent: int, removed: bytes, truncate_at: int) -> None:
        descriptor, created = self._files._open_regular_file(
            parent, self._RECOVERY_NAME, flags=os.O_WRONLY | os.O_APPEND, create=True
        )
        try:
            payload = {
                "at": datetime.now(UTC).isoformat(),
                "removed_bytes": len(removed),
                "removed_sha256": hashlib.sha256(removed).hexdigest(),
                "truncate_at": truncate_at,
            }
            self._files._write_all(
                descriptor,
                (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode(),
            )
            os.fsync(descriptor)
            if created:
                os.fsync(parent)
        finally:
            os.close(descriptor)
```

- Add `"EditorialCorrectionEnvelope"`, `"EditorialCorrectionLog"`, and
  `"stable_editorial_correction_id"` to the `__all__` list at the bottom of the file, sorted.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/test_typography_review.py -v`
Expected: PASS, including every pre-existing test in the file (no regression).

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/typography_review.py tests/unit/core/test_typography_review.py
git commit -m "feat(typography): add the append-only editorial correction journal"
```

---

### Task 3: The correction decision journal

A page may hold many corrections, and a reviewer may confirm some and ignore the rest — absence stays
ambiguous unless a rejection is recorded as a fact, the same rule that requires a decision store for
regions and style spans. `EditorialCorrectionDecisionLog` is `StyleSpanDecisionLog` adapted: CAS-bound
per correction, no revision-chain lineage, because a correction record itself is never edited — only
its disposition changes.

**Files:**

- Edit: `src/pdomain_ocr_labeler_spa/core/typography_review.py`
- Test: `tests/unit/core/test_typography_review.py`

**Interfaces:**

- Consumes: nothing new from book-contracts; `KnowledgeState` already imported in this file (added by
  the style-span-review-surface plan's Task 2).
- Produces: `EditorialCorrectionDisposition` (`CONFIRMED`, `REJECTED`), `EditorialCorrectionBinding`,
  `StaleEditorialCorrectionDecisionError`, `unreviewed_editorial_correction_head(binding) ->
  EditorialCorrectionDecisionHead`, and `EditorialCorrectionDecisionLog(project_root, *,
  corpus_root=None)` with `head(binding) -> EditorialCorrectionDecisionHead`, `append(binding, *,
  disposition, actor, expected_head) -> EditorialCorrectionDecisionHead`, and `heads(logical_page_id)
  -> dict[str, EditorialCorrectionDecisionHead]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/test_typography_review.py` (extend the import block with
`EditorialCorrectionBinding`, `EditorialCorrectionDecisionLog`, `EditorialCorrectionDisposition`,
`StaleEditorialCorrectionDecisionError`):

```python
def _correction_binding(
    correction_id: str = "correction-1", logical_page_id: str = "page-1"
) -> EditorialCorrectionBinding:
    return EditorialCorrectionBinding(logical_page_id=logical_page_id, correction_id=correction_id)


def test_a_correction_starts_unreviewed(tmp_path: Path) -> None:
    log = EditorialCorrectionDecisionLog(tmp_path, corpus_root=tmp_path)
    head = log.head(_correction_binding())
    assert head.disposition is None
    assert head.revision == 0


def test_confirming_a_correction_is_persistent_and_cas_bound(tmp_path: Path) -> None:
    log = EditorialCorrectionDecisionLog(tmp_path, corpus_root=tmp_path)
    head = log.head(_correction_binding())

    saved = log.append(
        _correction_binding(),
        disposition=EditorialCorrectionDisposition.CONFIRMED,
        actor="reviewer-1",
        expected_head=head.head_token,
    )

    assert saved.disposition is EditorialCorrectionDisposition.CONFIRMED
    assert EditorialCorrectionDecisionLog(tmp_path, corpus_root=tmp_path).head(_correction_binding()) == saved
    with pytest.raises(StaleEditorialCorrectionDecisionError):
        log.append(
            _correction_binding(),
            disposition=EditorialCorrectionDisposition.REJECTED,
            actor="reviewer-1",
            expected_head=head.head_token,
        )


def test_a_rejection_is_distinguishable_from_never_looking(tmp_path: Path) -> None:
    log = EditorialCorrectionDecisionLog(tmp_path, corpus_root=tmp_path)
    unreviewed = log.head(_correction_binding("correction-unreviewed"))
    rejected_head = log.head(_correction_binding("correction-rejected"))

    log.append(
        _correction_binding("correction-rejected"),
        disposition=EditorialCorrectionDisposition.REJECTED,
        actor="reviewer-1",
        expected_head=rejected_head.head_token,
    )

    assert unreviewed.disposition is None
    assert log.head(_correction_binding("correction-rejected")).disposition is EditorialCorrectionDisposition.REJECTED


def test_a_change_of_mind_advances_the_revision_and_both_decisions_stay_on_disk(tmp_path: Path) -> None:
    log = EditorialCorrectionDecisionLog(tmp_path, corpus_root=tmp_path)
    binding = _correction_binding()

    first = log.append(
        binding,
        disposition=EditorialCorrectionDisposition.REJECTED,
        actor="reviewer-1",
        expected_head=log.head(binding).head_token,
    )
    second = log.append(
        binding,
        disposition=EditorialCorrectionDisposition.CONFIRMED,
        actor="reviewer-2",
        expected_head=first.head_token,
    )

    assert second.revision == first.revision + 1
    assert second.disposition is EditorialCorrectionDisposition.CONFIRMED
    lines = (tmp_path / ".pd-pages" / "editorial-correction-decisions.jsonl").read_text().splitlines()
    assert len(lines) == 2


def test_decisions_from_different_pages_do_not_collide(tmp_path: Path) -> None:
    log = EditorialCorrectionDecisionLog(tmp_path, corpus_root=tmp_path)
    page_a = _correction_binding(logical_page_id="page-a")
    page_b = _correction_binding(logical_page_id="page-b")

    log.append(
        page_a,
        disposition=EditorialCorrectionDisposition.CONFIRMED,
        actor="reviewer-1",
        expected_head=log.head(page_a).head_token,
    )

    assert log.head(page_b).disposition is None


def test_heads_reads_the_journal_once_for_a_whole_page(tmp_path: Path) -> None:
    log = EditorialCorrectionDecisionLog(tmp_path, corpus_root=tmp_path)
    first = _correction_binding("correction-1")
    second = _correction_binding("correction-2")
    log.append(
        first,
        disposition=EditorialCorrectionDisposition.CONFIRMED,
        actor="reviewer-1",
        expected_head=log.head(first).head_token,
    )
    log.append(
        second,
        disposition=EditorialCorrectionDisposition.REJECTED,
        actor="reviewer-1",
        expected_head=log.head(second).head_token,
    )

    heads = log.heads("page-1")

    assert heads["correction-1"].disposition is EditorialCorrectionDisposition.CONFIRMED
    assert heads["correction-2"].disposition is EditorialCorrectionDisposition.REJECTED
    assert "correction-missing" not in heads


def test_disposition_maps_onto_a_knowledge_state() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState

    assert EditorialCorrectionDisposition.CONFIRMED.knowledge_state is KnowledgeState.POSITIVE
    assert EditorialCorrectionDisposition.REJECTED.knowledge_state is KnowledgeState.VERIFIED_NEGATIVE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/test_typography_review.py -k EditorialCorrectionDecisionLog -v`
Expected: FAIL with `NameError` / `ImportError` for the not-yet-defined names.

- [ ] **Step 3: Write the implementation**

In `src/pdomain_ocr_labeler_spa/core/typography_review.py`, insert the following immediately after
the `EditorialCorrectionLog` class from Task 2 and before `__all__`:

```python
class EditorialCorrectionDisposition(StrEnum):
    """What a person decided about one recorded editorial correction."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"

    @property
    def knowledge_state(self) -> KnowledgeState:
        """The knowledge state this disposition asserts about the correction."""
        if self is EditorialCorrectionDisposition.REJECTED:
            return KnowledgeState.VERIFIED_NEGATIVE
        return KnowledgeState.POSITIVE


class EditorialCorrectionBinding(BaseModel):
    """Exact identity of one recorded correction presented for decision review."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    logical_page_id: str
    correction_id: str


class StaleEditorialCorrectionDecisionError(ValueError):
    """A correction decision was based on a head no longer current."""


class EditorialCorrectionDecisionHead(BaseModel):
    """Current persistent review decision for one recorded editorial correction."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    binding: EditorialCorrectionBinding
    revision: int = Field(ge=0)
    disposition: EditorialCorrectionDisposition | None
    actor: str | None
    decided_at: str | None
    head_token: str = Field(min_length=64, max_length=64)


def unreviewed_editorial_correction_head(
    binding: EditorialCorrectionBinding,
) -> EditorialCorrectionDecisionHead:
    """Return the head an unreviewed correction has, with no journal read required."""
    return EditorialCorrectionDecisionHead(
        binding=binding,
        revision=0,
        disposition=None,
        actor=None,
        decided_at=None,
        head_token=EditorialCorrectionDecisionLog._token(binding, revision=0, disposition=None),
    )


@final
class EditorialCorrectionDecisionLog:
    """Project-local JSONL journal of what a person decided about each editorial correction.

    A correction is captured and held apart the same way ``ParserNoteEvidence``
    quarantines a PGDP proofer's note — recorded, never applied. This journal is
    where a reviewer marks one confirmed or rejected; it never edits the correction
    record, and it never writes to ``Word.ground_truth_text`` or
    ``Project.ground_truth_map`` — neither is reachable from any method here.
    """

    _NAME: ClassVar[str] = "editorial-correction-decisions.jsonl"
    _RECOVERY_NAME: ClassVar[str] = "editorial-correction-decisions.recovery.jsonl"

    def __init__(self, project_root: Path, *, corpus_root: Path | None = None) -> None:
        self._files = TypographyCorrectionLog(project_root, corpus_root=corpus_root)
        self.path = self._files.path.with_name(self._NAME)

    @staticmethod
    def _token(
        binding: EditorialCorrectionBinding,
        *,
        revision: int,
        disposition: EditorialCorrectionDisposition | None,
    ) -> str:
        payload = {
            "binding": binding.model_dump(mode="json"),
            "revision": revision,
            "disposition": disposition.value if disposition is not None else None,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def head(self, binding: EditorialCorrectionBinding) -> EditorialCorrectionDecisionHead:
        """Return the current head for one correction, unreviewed if never decided."""
        parent, descriptor = self._open(create=True)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH)
            rows = self._read(descriptor, parent=parent)
        finally:
            os.close(descriptor)
            os.close(parent)
        return self._head(rows, binding)

    def append(
        self,
        binding: EditorialCorrectionBinding,
        *,
        disposition: EditorialCorrectionDisposition,
        actor: str,
        expected_head: str,
    ) -> EditorialCorrectionDecisionHead:
        """CAS-append one confirm-or-reject decision against the current head."""
        parent, descriptor = self._open(create=True)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            rows = self._read(descriptor, parent=parent)
            current = self._head(rows, binding)
            if current.head_token != expected_head:
                raise StaleEditorialCorrectionDecisionError("expected_head is not current")
            revision = current.revision + 1
            decided_at = datetime.now(UTC).isoformat()
            self._append_row(
                descriptor,
                {
                    "kind": "decision",
                    "binding": binding.model_dump(mode="json"),
                    "revision": revision,
                    "disposition": disposition.value,
                    "actor": actor,
                    "decided_at": decided_at,
                },
            )
            os.fsync(descriptor)
            return self._make_head(binding, revision, disposition, actor, decided_at)
        finally:
            os.close(descriptor)
            os.close(parent)

    def heads(self, logical_page_id: str) -> dict[str, EditorialCorrectionDecisionHead]:
        """Return the current head for every correction decided so far on one page.

        One read of the whole journal, resolved in memory, rather than reopening the
        file once per correction.
        """
        parent, descriptor = self._open(create=True)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH)
            rows = self._read(descriptor, parent=parent)
        finally:
            os.close(descriptor)
            os.close(parent)
        by_correction: dict[str, dict[str, object]] = {}
        for row in rows:
            binding_raw = row.get("binding")
            if not isinstance(binding_raw, dict):
                continue
            if binding_raw.get("logical_page_id") != logical_page_id:
                continue
            correction_id = binding_raw.get("correction_id")
            if isinstance(correction_id, str):
                by_correction[correction_id] = row
        heads: dict[str, EditorialCorrectionDecisionHead] = {}
        for correction_id, row in by_correction.items():
            binding = EditorialCorrectionBinding.model_validate(row["binding"])
            heads[correction_id] = self._make_head(
                binding,
                int(row["revision"]),  # type: ignore[arg-type]
                EditorialCorrectionDisposition(row["disposition"]),  # type: ignore[arg-type]
                str(row["actor"]),
                str(row["decided_at"]),
            )
        return heads

    def _open(self, *, create: bool) -> tuple[int, int]:
        parent = self._files._open_journal_directory(create=create)
        try:
            descriptor, created = self._files._open_regular_file(
                parent, self._NAME, flags=os.O_RDWR | os.O_APPEND, create=create
            )
            if created:
                os.fsync(parent)
            return parent, descriptor
        except Exception:
            os.close(parent)
            raise

    def _read(self, descriptor: int, *, parent: int) -> list[dict[str, object]]:
        _ = os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        raw = b"".join(chunks)
        if not raw:
            return []
        terminated = raw.endswith(b"\n")
        lines = raw.split(b"\n")
        if terminated:
            lines.pop()
        trailing = None if terminated else lines.pop()
        rows = [self._parse_row(line) for line in lines]
        if trailing is None:
            return rows
        try:
            rows.append(self._parse_row(trailing))
            return rows
        except json.JSONDecodeError:
            truncate_at = len(raw) - len(trailing)
            os.ftruncate(descriptor, truncate_at)
            os.fsync(descriptor)
            self._write_recovery(parent, trailing, truncate_at)
            return rows

    @staticmethod
    def _parse_row(payload: bytes) -> dict[str, object]:
        value = json.loads(payload)
        if not isinstance(value, dict) or value.get("kind") != "decision":
            raise ValueError("invalid editorial correction decision journal record")
        return value

    def _write_recovery(self, parent: int, removed: bytes, truncate_at: int) -> None:
        descriptor, created = self._files._open_regular_file(
            parent, self._RECOVERY_NAME, flags=os.O_WRONLY | os.O_APPEND, create=True
        )
        try:
            payload = {
                "at": datetime.now(UTC).isoformat(),
                "removed_bytes": len(removed),
                "removed_sha256": hashlib.sha256(removed).hexdigest(),
                "truncate_at": truncate_at,
            }
            self._files._write_all(
                descriptor,
                (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode(),
            )
            os.fsync(descriptor)
            if created:
                os.fsync(parent)
        finally:
            os.close(descriptor)

    def _append_row(self, descriptor: int, row: object) -> None:
        payload = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self._files._write_all(descriptor, payload)

    def _head(
        self, rows: list[dict[str, object]], binding: EditorialCorrectionBinding
    ) -> EditorialCorrectionDecisionHead:
        for row in reversed(rows):
            binding_raw = row.get("binding")
            if not isinstance(binding_raw, dict):
                continue
            try:
                candidate = EditorialCorrectionBinding.model_validate(binding_raw)
            except ValueError:
                continue
            if candidate == binding:
                revision = row.get("revision")
                disposition = row.get("disposition")
                decided_at = row.get("decided_at")
                actor = row.get("actor")
                if (
                    isinstance(revision, int)
                    and isinstance(disposition, str)
                    and isinstance(decided_at, str)
                ):
                    return self._make_head(
                        binding,
                        revision,
                        EditorialCorrectionDisposition(disposition),
                        str(actor),
                        decided_at,
                    )
        return self._make_head(binding, 0, None, None, None)

    def _make_head(
        self,
        binding: EditorialCorrectionBinding,
        revision: int,
        disposition: EditorialCorrectionDisposition | None,
        actor: str | None,
        decided_at: str | None,
    ) -> EditorialCorrectionDecisionHead:
        return EditorialCorrectionDecisionHead(
            binding=binding,
            revision=revision,
            disposition=disposition,
            actor=actor,
            decided_at=decided_at,
            head_token=self._token(binding, revision=revision, disposition=disposition),
        )
```

- Add `"EditorialCorrectionBinding"`, `"EditorialCorrectionDecisionHead"`,
  `"EditorialCorrectionDecisionLog"`, `"EditorialCorrectionDisposition"`,
  `"StaleEditorialCorrectionDecisionError"`, and `"unreviewed_editorial_correction_head"` to
  `__all__`, sorted.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/test_typography_review.py -v`
Expected: PASS, including every pre-existing test in the file (no regression).

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/typography_review.py tests/unit/core/test_typography_review.py
git commit -m "feat(typography): add the per-correction confirm/reject decision journal"
```

---

### Task 4: Record and list corrections

The record route lets a labeler capture one correction; the list route surfaces every correction on a
page beside its current review decision, the same shape `StyleSpanListResponse` uses. This task also
carries the ground-truth invariant test against a live `Project`.

Neither route requires a loaded labeling bundle: unlike a style span, an editorial correction is not
reached through `TypographyPageRecord` — it can be recorded on any project (verified:
`bind_page_labeling_lease` yields `None` rather than failing when no bundle is loaded, and
`_logical_page_id` already falls back to `stable_page_id` in that case).

**Files:**

- Edit: `src/pdomain_ocr_labeler_spa/api/typography.py`
- Test: `tests/unit/api/test_typography_editorial_corrections.py`

**Interfaces:**

- Consumes: `stable_editorial_correction_id`... no — consumes `EditorialCorrectionEnvelope`,
  `EditorialCorrectionLog`, `EditorialCorrectionDecisionLog`, `EditorialCorrectionDisposition`,
  `EditorialCorrectionBinding`, `unreviewed_editorial_correction_head` from Tasks 2–3;
  `CorrectionReason`, `EditorialCorrection` from `pdomain_book_contracts.typography.editorial`.
- Produces: `POST /api/projects/{project_id}/pages/{page_index}/typography/corrections ->
  EditorialCorrectionEntry` and `GET
  /api/projects/{project_id}/pages/{page_index}/typography/corrections ->
  EditorialCorrectionListResponse`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/api/test_typography_editorial_corrections.py`:

```python
"""Unit tests for the editorial correction record and list routes."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from pdomain_ocr_labeler_spa.bootstrap import build_app
from pdomain_ocr_labeler_spa.core.models import Project
from pdomain_ocr_labeler_spa.settings import Settings


def _client(tmp_path: Path) -> tuple[TestClient, str, Project]:
    project_root = tmp_path / "alpha"
    project_root.mkdir()
    image = project_root / "page001.png"
    image.write_bytes(b"image-bytes")
    project_id = "alpha"
    app = build_app(Settings(mode="api_only", data_root=tmp_path / "data"))
    project = Project(
        project_id=project_id,
        project_root=project_root,
        image_paths=[image],
        ground_truth_map={"page001.png": "The cat sat on teh mat."},
        total_pages=1,
    )
    app.state.project_state.set_loaded_project(project)
    app.state.active_project_carrier.set_active_project(project_root)
    return TestClient(app), project_id, project


_SUBMISSION = {
    "start": 20,
    "end": 23,
    "reading_as_printed": "teh",
    "reading_intended": "the",
    "reason": "printers_error",
    "reason_note": None,
    "labeler_id": "reviewer-1",
}


def test_recording_a_correction_returns_it_unreviewed(tmp_path: Path) -> None:
    client, project_id, _project = _client(tmp_path)

    response = client.post(
        f"/api/projects/{project_id}/pages/0/typography/corrections", json=_SUBMISSION
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reading_as_printed"] == "teh"
    assert body["reading_intended"] == "the"
    assert body["reason"] == "printers_error"
    assert body["disposition"] is None
    assert body["decision_revision"] == 0


def test_recording_an_insertion_correction_succeeds(tmp_path: Path) -> None:
    client, project_id, _project = _client(tmp_path)
    submission = {**_SUBMISSION, "start": 4, "end": 4, "reading_as_printed": "", "reading_intended": "very"}

    response = client.post(
        f"/api/projects/{project_id}/pages/0/typography/corrections", json=submission
    )

    assert response.status_code == 200
    assert response.json()["start"] == response.json()["end"] == 4


def test_an_invalid_correction_is_rejected_with_422(tmp_path: Path) -> None:
    client, project_id, _project = _client(tmp_path)
    submission = {**_SUBMISSION, "reading_as_printed": "the", "reading_intended": "the"}

    response = client.post(
        f"/api/projects/{project_id}/pages/0/typography/corrections", json=submission
    )

    assert response.status_code == 422


def test_listing_corrections_reports_counts(tmp_path: Path) -> None:
    client, project_id, _project = _client(tmp_path)
    client.post(f"/api/projects/{project_id}/pages/0/typography/corrections", json=_SUBMISSION)

    response = client.get(f"/api/projects/{project_id}/pages/0/typography/corrections")

    assert response.status_code == 200
    body = response.json()
    assert len(body["corrections"]) == 1
    assert body["unreviewed_count"] == 1
    assert body["confirmed_count"] == 0
    assert body["rejected_count"] == 0


def test_recording_a_correction_never_touches_ground_truth(tmp_path: Path) -> None:
    """The invariant: an editorial correction never enters ground truth."""
    client, project_id, project = _client(tmp_path)
    before = dict(project.ground_truth_map)

    client.post(f"/api/projects/{project_id}/pages/0/typography/corrections", json=_SUBMISSION)
    client.get(f"/api/projects/{project_id}/pages/0/typography/corrections")

    loaded_project = client.app.state.project_state.loaded_project  # type: ignore[attr-defined]
    assert dict(loaded_project.ground_truth_map) == before
    word_corrections_path = project.project_root / ".pd-pages" / "typography-corrections.jsonl"
    assert not word_corrections_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/api/test_typography_editorial_corrections.py -v`
Expected: FAIL — the four success-path tests get `404` (route not found) instead of `200`; the 422
test fails its status-code assertion.

- [ ] **Step 3: Write the implementation**

In `src/pdomain_ocr_labeler_spa/api/typography.py`:

- Add a new import, directly beneath the existing `from pdomain_book_tools.typography import (...)`
  block:

```python
from pdomain_book_contracts.typography.editorial import CorrectionReason, EditorialCorrection
```

- Extend the existing `from ..core.typography_review import (...)` block with
  `EditorialCorrectionBinding`, `EditorialCorrectionDecisionLog`, `EditorialCorrectionDisposition`,
  `EditorialCorrectionEnvelope`, `EditorialCorrectionLog`, `unreviewed_editorial_correction_head`.
- Insert the following immediately after the `record_style_span_decision` route the
  style-span-review-surface plan's Task 4 adds, and before `install_typography_router`:

```python
class EditorialCorrectionSubmission(BaseModel):
    """One editorial correction a labeler is recording against the page's ink."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    start: int = Field(ge=0)
    end: int = Field(ge=0)
    reading_as_printed: str
    reading_intended: str
    reason: CorrectionReason
    reason_note: str | None = None
    rule_ref: str | None = None
    warnings: tuple[str, ...] = ()
    labeler_id: str = "local"


class EditorialCorrectionEntry(BaseModel):
    """One recorded editorial correction, with its current review decision."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    correction_id: str
    start: int
    end: int
    reading_as_printed: str
    reading_intended: str
    reason: CorrectionReason
    reason_note: str | None
    rule_ref: str | None
    warnings: tuple[str, ...]
    labeler_id: str
    created_at: str
    disposition: EditorialCorrectionDisposition | None
    decision_revision: int
    decision_actor: str | None
    decision_at: str | None
    head_token: str


class EditorialCorrectionListResponse(BaseModel):
    """Every editorial correction on one page, with its current review disposition."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    page_index: int
    logical_page_id: str
    corrections: tuple[EditorialCorrectionEntry, ...]
    confirmed_count: int
    rejected_count: int
    unreviewed_count: int


def _editorial_correction_entry(
    envelope: EditorialCorrectionEnvelope, head: object
) -> EditorialCorrectionEntry:
    correction = envelope.correction
    return EditorialCorrectionEntry(
        correction_id=envelope.correction_id,
        start=correction.start,
        end=correction.end,
        reading_as_printed=correction.reading_as_printed,
        reading_intended=correction.reading_intended,
        reason=correction.reason,
        reason_note=correction.reason_note,
        rule_ref=correction.rule_ref,
        warnings=correction.warnings,
        labeler_id=envelope.labeler_id,
        created_at=envelope.created_at,
        disposition=head.disposition,  # type: ignore[attr-defined]
        decision_revision=head.revision,  # type: ignore[attr-defined]
        decision_actor=head.actor,  # type: ignore[attr-defined]
        decision_at=head.decided_at,  # type: ignore[attr-defined]
        head_token=head.head_token,  # type: ignore[attr-defined]
    )


@router.post(
    "/api/projects/{project_id}/pages/{page_index}/typography/corrections",
    response_model=EditorialCorrectionEntry,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="record_editorial_correction",
)
def record_editorial_correction(
    project_id: str,
    page_index: int,
    submission: EditorialCorrectionSubmission,
    state: ProjectState = Depends(get_project_state),
) -> EditorialCorrectionEntry:
    """Record one editorial correction.

    This route never touches ``Word.ground_truth_text`` or ``Project.ground_truth_map``
    — it has no dependency, import, or code path that could reach either. What the ink
    says is untouched; what it should have said is recorded beside it, in
    ``EditorialCorrectionLog`` only.
    """
    project = _project_page(project_id, page_index, state)
    with state.get_page_lock(page_index):
        logical_page_id = _logical_page_id(project, page_index, state)
        try:
            correction = EditorialCorrection(
                start=submission.start,
                end=submission.end,
                reading_as_printed=submission.reading_as_printed,
                reading_intended=submission.reading_intended,
                reason=submission.reason,
                reason_note=submission.reason_note,
                state=KnowledgeState.POSITIVE,
                label_source=LabelSource.HUMAN,
                confidence_tier=ConfidenceTier.GOLD,
                source_slices=(),
                rule_ref=submission.rule_ref,
                warnings=submission.warnings,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail="invalid editorial correction") from exc
        log = EditorialCorrectionLog(project.project_root, corpus_root=project.project_root.parent)
        envelope = log.append(correction, logical_page_id=logical_page_id, labeler_id=submission.labeler_id)
        decision_log = EditorialCorrectionDecisionLog(
            project.project_root, corpus_root=project.project_root.parent
        )
        binding = EditorialCorrectionBinding(
            logical_page_id=logical_page_id, correction_id=envelope.correction_id
        )
        head = decision_log.head(binding)
    return _editorial_correction_entry(envelope, head)


@router.get(
    "/api/projects/{project_id}/pages/{page_index}/typography/corrections",
    response_model=EditorialCorrectionListResponse,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="list_editorial_corrections",
)
def list_editorial_corrections(
    project_id: str,
    page_index: int,
    state: ProjectState = Depends(get_project_state),
) -> EditorialCorrectionListResponse:
    """Return every editorial correction on one page and its current review decision."""
    project = _project_page(project_id, page_index, state)
    with state.get_page_lock(page_index):
        logical_page_id = _logical_page_id(project, page_index, state)
        log = EditorialCorrectionLog(project.project_root, corpus_root=project.project_root.parent)
        envelopes = log.records(logical_page_id)
        decision_log = EditorialCorrectionDecisionLog(
            project.project_root, corpus_root=project.project_root.parent
        )
        heads = decision_log.heads(logical_page_id)
        entries = tuple(
            _editorial_correction_entry(
                envelope,
                heads.get(envelope.correction_id)
                or unreviewed_editorial_correction_head(
                    EditorialCorrectionBinding(
                        logical_page_id=logical_page_id, correction_id=envelope.correction_id
                    )
                ),
            )
            for envelope in envelopes
        )
    confirmed = sum(
        1 for entry in entries if entry.disposition is EditorialCorrectionDisposition.CONFIRMED
    )
    rejected = sum(
        1 for entry in entries if entry.disposition is EditorialCorrectionDisposition.REJECTED
    )
    return EditorialCorrectionListResponse(
        project_id=project_id,
        page_index=page_index,
        logical_page_id=logical_page_id,
        corrections=entries,
        confirmed_count=confirmed,
        rejected_count=rejected,
        unreviewed_count=len(entries) - confirmed - rejected,
    )
```

**Note on `_editorial_correction_entry`'s `head` parameter type:** write it as
`head: EditorialCorrectionDecisionHead` (the `# type: ignore[attr-defined]` comments above are only
needed if the plan's own snippet is type-checked in isolation without that import in scope; with
`EditorialCorrectionDecisionHead` imported per the step above, remove the four `# type: ignore`
comments and the `object` annotation — basedpyright resolves the attributes directly).

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/api/test_typography_editorial_corrections.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/api/typography.py tests/unit/api/test_typography_editorial_corrections.py
git commit -m "feat(typography): record and list editorial corrections"
```

---

### Task 5: Decide a correction

The write route lets a reviewer confirm or reject one recorded correction. It never edits
`EditorialCorrection` or `TypographyCorrectionLog`, the word-scoped correction journal — a direct test
proves the two journals stay independent files that neither route reads from nor writes to the other.

**Files:**

- Edit: `src/pdomain_ocr_labeler_spa/api/typography.py`
- Test: `tests/unit/api/test_typography_editorial_corrections.py`

**Interfaces:**

- Consumes: `EditorialCorrectionBinding`, `EditorialCorrectionDecisionLog`,
  `StaleEditorialCorrectionDecisionError`, `EditorialCorrectionDisposition` from Task 3.
- Produces: `POST
  /api/projects/{project_id}/pages/{page_index}/typography/corrections/{correction_id}/decisions ->
  EditorialCorrectionDecisionResponse`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/api/test_typography_editorial_corrections.py`:

```python
def test_confirming_a_correction_persists_and_is_reflected_in_the_list(tmp_path: Path) -> None:
    client, project_id, _project = _client(tmp_path)
    recorded = client.post(
        f"/api/projects/{project_id}/pages/0/typography/corrections", json=_SUBMISSION
    ).json()

    response = client.post(
        f"/api/projects/{project_id}/pages/0/typography/corrections/{recorded['correction_id']}/decisions",
        json={"expected_head": recorded["head_token"], "disposition": "confirmed", "labeler_id": "reviewer-2"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["disposition"] == "confirmed"
    assert body["revision"] == 1

    relisted = client.get(f"/api/projects/{project_id}/pages/0/typography/corrections").json()
    assert relisted["corrections"][0]["disposition"] == "confirmed"
    assert relisted["confirmed_count"] == 1


def test_a_stale_decision_head_is_rejected_with_409(tmp_path: Path) -> None:
    client, project_id, _project = _client(tmp_path)
    recorded = client.post(
        f"/api/projects/{project_id}/pages/0/typography/corrections", json=_SUBMISSION
    ).json()
    decision_url = (
        f"/api/projects/{project_id}/pages/0/typography/corrections/{recorded['correction_id']}/decisions"
    )

    client.post(
        decision_url,
        json={"expected_head": recorded["head_token"], "disposition": "rejected", "labeler_id": "reviewer-1"},
    )
    stale = client.post(
        decision_url,
        json={"expected_head": recorded["head_token"], "disposition": "confirmed", "labeler_id": "reviewer-1"},
    )

    assert stale.status_code == 409


def test_an_unknown_correction_id_is_a_404(tmp_path: Path) -> None:
    client, project_id, _project = _client(tmp_path)

    response = client.post(
        f"/api/projects/{project_id}/pages/0/typography/corrections/not-a-real-correction/decisions",
        json={"expected_head": "a" * 64, "disposition": "confirmed", "labeler_id": "reviewer-1"},
    )

    assert response.status_code == 404


def test_deciding_a_correction_never_touches_the_word_scoped_correction_log(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.typography_review import TypographyCorrectionLog, stable_page_id

    client, project_id, project = _client(tmp_path)
    recorded = client.post(
        f"/api/projects/{project_id}/pages/0/typography/corrections", json=_SUBMISSION
    ).json()
    page_id = stable_page_id(project_id=project_id, page_index=0)
    word_log = TypographyCorrectionLog(project.project_root, corpus_root=project.project_root.parent)
    before = word_log.records(page_id)

    client.post(
        f"/api/projects/{project_id}/pages/0/typography/corrections/{recorded['correction_id']}/decisions",
        json={"expected_head": recorded["head_token"], "disposition": "confirmed", "labeler_id": "reviewer-1"},
    )

    assert word_log.records(page_id) == before == ()
    correction_decisions_path = project.project_root / ".pd-pages" / "editorial-correction-decisions.jsonl"
    word_corrections_path = project.project_root / ".pd-pages" / "typography-corrections.jsonl"
    assert correction_decisions_path.exists()
    assert not word_corrections_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/api/test_typography_editorial_corrections.py -v`
Expected: FAIL — the four new tests get `404` (route not found) instead of `200` / `409` /
`404`-for-unknown-correction responses.

- [ ] **Step 3: Write the implementation**

Add `StaleEditorialCorrectionDecisionError` to the `from ..core.typography_review import (...)` block
updated in Task 4. Insert the following immediately after the `list_editorial_corrections` route from
Task 4:

```python
class EditorialCorrectionDecisionSubmission(BaseModel):
    """Confirm-or-reject intent against the current correction decision head."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    expected_head: str = Field(min_length=64, max_length=64)
    disposition: Literal["confirmed", "rejected"]
    labeler_id: str = "local"


class EditorialCorrectionDecisionResponse(BaseModel):
    """Current review decision for one recorded editorial correction."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    page_index: int
    correction_id: str
    disposition: EditorialCorrectionDisposition | None
    revision: int
    actor: str | None
    decided_at: str | None
    head_token: str


@router.post(
    "/api/projects/{project_id}/pages/{page_index}/typography/corrections/{correction_id}/decisions",
    response_model=EditorialCorrectionDecisionResponse,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="record_editorial_correction_decision",
)
def record_editorial_correction_decision(
    project_id: str,
    page_index: int,
    correction_id: str,
    submission: EditorialCorrectionDecisionSubmission,
    state: ProjectState = Depends(get_project_state),
) -> EditorialCorrectionDecisionResponse:
    """Append a person's confirm-or-reject verdict for one recorded correction.

    This never edits the correction record and never touches
    ``TypographyCorrectionLog``, the word-scoped correction journal above: a
    correction decision is a separate fact, in its own journal, about a
    page-level record a word-scoped correction never reads.
    """
    project = _project_page(project_id, page_index, state)
    with state.get_page_lock(page_index):
        logical_page_id = _logical_page_id(project, page_index, state)
        log = EditorialCorrectionLog(project.project_root, corpus_root=project.project_root.parent)
        known_ids = {envelope.correction_id for envelope in log.records(logical_page_id)}
        if correction_id not in known_ids:
            raise HTTPException(status_code=404, detail="correction not found on page")
        binding = EditorialCorrectionBinding(logical_page_id=logical_page_id, correction_id=correction_id)
        decision_log = EditorialCorrectionDecisionLog(
            project.project_root, corpus_root=project.project_root.parent
        )
        try:
            head = decision_log.append(
                binding,
                disposition=EditorialCorrectionDisposition(submission.disposition),
                actor=submission.labeler_id,
                expected_head=submission.expected_head,
            )
        except StaleEditorialCorrectionDecisionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return EditorialCorrectionDecisionResponse(
            project_id=project_id,
            page_index=page_index,
            correction_id=correction_id,
            disposition=head.disposition,
            revision=head.revision,
            actor=head.actor,
            decided_at=head.decided_at,
            head_token=head.head_token,
        )
```

- [ ] **Step 4: Run the tests, the fast suite, and the gate**

Run: `uv run pytest tests/unit/api/test_typography_editorial_corrections.py -v`
Expected: PASS, all nine tests in the file.

Run: `uv run pytest tests/unit/core/test_typography_review.py tests/unit/api/ -v`
Expected: PASS, including every pre-existing typography test file (no regression).

Run: `make AI=1 test`
Expected: PASS.

Run: `make AI=1 ci`
Expected: PASS. `openapi-export` regenerates `frontend/src/api/types.ts` with the three new routes;
include that regenerated file in the commit.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/api/typography.py tests/unit/api/test_typography_editorial_corrections.py \
  frontend/src/api/types.ts
git commit -m "feat(typography): record and enforce CAS-bound editorial correction decisions"
```

---

## What this plan does not do

- **It does not apply corrections.** The post-processor that turns a confirmed `EditorialCorrection`
  into a change anywhere is a separate stage that does not yet exist, by owner direction. The
  synthesizer never sees corrections at all — it renders what the ink said.
- **It does not model a correction spanning a page boundary.** The design leaves this unmodeled; this
  plan's grapheme range is always page-local.
- **It does not populate `EditorialCorrection.source_slices` from live page content.** The field
  exists on the model for a future producer (an automated corrector, or a person attaching byte
  evidence) to fill; the record route in this plan always writes an empty tuple, since a person typing
  a correction in today's labeler has no byte-offset evidence to attach.
- **It does not verify `reading_as_printed` against the page's live OCR or ground-truth text at the
  given range.** The server trusts the caller's assertion. Cross-checking it would require reading
  `Word.ground_truth_text`, and doing that safely — without ever writing to it — is future work with
  its own design case to make.
- **It adds no UI.** The three routes are a server-authoritative capture-and-review surface; a
  labeler screen that renders corrections and calls them is separate front-end work.
- **It adds no `pdomain_book_tools.typography.editorial` re-export shim.** See Global Constraints:
  the labeler imports `EditorialCorrection` and `CorrectionReason` directly from
  `pdomain_book_contracts.typography.editorial`, an already-declared dependency it simply had not
  imported from before now.
- **It does not batch-confirm corrections or add a book-wide review-progress rollup** beyond the
  three per-page counts on `EditorialCorrectionListResponse`, matching the style-span plan's same
  scope limit.
- **It does not build a page-kind or region proposal/decision pipeline.** Those are separate
  annotation levels under the same spec, with their own plans.

## Related

- [Annotation provenance and
  persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) — the design, section
  "Editorial corrections say what the page should have said, and never touch ground truth."
- [Annotation vocabularies in
  book-contracts](2026-09-08-annotation-vocabularies-in-book-contracts.md) — must land first; supplies
  `pdomain_book_contracts.annotation`.
- [Style span review surface](2026-09-08-style-span-review-surface.md) — must land first; this plan's
  Tasks 2–5 extend the same two labeler files immediately after the classes and routes it adds, and
  its `stable_style_span_id` is the identity-derivation precedent `stable_editorial_correction_id`
  follows.
- [Region stores and resolver](2026-09-08-region-stores-and-resolver.md) — the sibling annotation
  level with the same eight-property bar; unrelated code, no shared files.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — the seven slices this plan is part
  of.
