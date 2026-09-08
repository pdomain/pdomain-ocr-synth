# Word and Glyph Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two annotation levels the provenance design left half-built. Every writer of
`Word.ground_truth_text` stamps which source produced it. Glyph predictions survive past the request
that computed them, a rejection is recorded as a fact, and a reject route exists to record it.

**Architecture:** Words already have the right shape — `text`/`ocr_confidence` (the machine's claim),
`_ground_truth_text` (the human's answer), and `review: ReviewMetadata | None` (the marker
distinguishing unreviewed from reviewed). Nothing new is stored. `Word` gains one method that sets
`ground_truth_text` and stamps `review.source`/`review.state` in the same call, and the four writers
that currently assign the field directly call it instead. Glyphs get the same two-store-plus-marker
treatment: the existing `glyph_annotations_map` sidecar (the human's answer) is joined by a
newly-persisted `glyph_predictions_map` sidecar (the machine's claim), `GlyphAnnotationsModel` gains
`confidence`, `evidence`, and `state` fields so a rejection is expressible, and a reject route writes
that rejection as a `KnowledgeState.VERIFIED_NEGATIVE` fact rather than leaving no trace. Per the
design's rule, neither level needs a decision journal: a word has one answer and a glyph annotation
set is per-word, so a diff plus the existing reviewed marker is enough.

**Tech Stack:** Python 3.11+ (book-tools) / 3.13 (labeler-spa), dataclasses, Pydantic v2, pytest,
ruff, basedpyright.

**Spec:** [Annotation provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md), sections "The same
three stores apply to OCR words", "Built properly means eight properties", "What each level is
missing", and "When a decision store is required".

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-08
- **Last verified:** 2026-09-08
- **Provenance:** authored 2026-09-08 from the design spec above and direct inspection of
  `pdomain-book-tools` `pdomain_book_tools/ocr/word.py`, `ocr/ground_truth_matching.py`,
  `ocr/review.py`, `ocr/glyph_annotations.py`, its Makefile and `pyproject.toml`, and
  `tests/ocr/test_word_review.py`, `tests/ocr/test_ground_truth_matching.py`; and
  `pdomain-ocr-labeler-spa` `src/pdomain_ocr_labeler_spa/api/words.py`,
  `api/lines_paragraphs.py`, `core/jobs/handlers/export.py`, `core/glyph/predictions.py`,
  `core/project_state.py`, `core/labeler_sidecars.py`, `core/page_state.py`, `core/models.py`,
  `core/page_to_line_matches.py`, `adapters/ocr/local_doctr.py`, `api/pages.py`, its Makefile and
  `pyproject.toml`; and `pdomain-book-contracts` `pdomain_book_contracts/ocr/review.py` and
  `ocr/glyph_annotations.py`, and the companion plan
  `2026-09-08-annotation-vocabularies-in-book-contracts.md`
- **Disposition:** Active. Depends on the vocabularies plan's Task 5 (`ReviewMetadata.source` /
  `.state`) and Task 1 (`KnowledgeState`, `LabelSource` importable from
  `pdomain_book_contracts.annotation`) already being released.
- **Read when:** implementing word-level ground-truth provenance, persisting glyph predictions,
  adding the glyph reject route, or tracing which of the four writers filled a word's ground truth.
- **Search terms:** ReviewMetadata source, set_ground_truth_text_with_provenance, LabelSource F2,
  LabelSource MODEL, GlyphAnnotationsModel, glyph_predictions_map, IGlyphPredictor,
  word_identity_key, migrate_legacy_glyph_keys, reject-prediction, KnowledgeState VERIFIED_NEGATIVE,
  LabelerSidecars.

## Global Constraints

- **`ReviewMetadata.source` and `.state` must already exist in a released `pdomain-book-contracts`
  version before Task 1 starts.** They land in the vocabularies plan's Task 5. Verify inside the
  book-tools venv with:
  `uv run python -c "from pdomain_book_contracts.ocr.review import ReviewMetadata as R; print(R.__dataclass_fields__)"`
  — `source` and `state` must be in the output.
- **book-tools floor is `>=3.11,<3.14`; labeler-spa floor is `>=3.13,<3.14`.** Both run
  `filterwarnings = ["error"]` (book-tools) or an equivalent strict pytest config; nothing in this
  plan emits a warning.
- book-tools commands: `make AI=1 test`, `make AI=1 test-single TEST='tests/...::test_name'`,
  `make AI=1 ci`. No bare `uv run pytest` — the Makefile wraps `--cov-config` and `-n auto`.
- labeler-spa commands: `make AI=1 test`, `make AI=1 ci`. `make AI=1 ci` includes `openapi-export`,
  which regenerates `frontend/src/api/types.ts` — required after Task 6 adds a route, and a CI job
  fails on drift if it is skipped.
- **Word identity, not position.** The four writers this plan touches all mutate a `Word` object
  already resolved by line/word index elsewhere; nothing here introduces a new positional key.
- **`GlyphAnnotationsModel.source` is `LabelSource`, not a private three-value `Literal`.** An
  earlier draft of this plan kept `Literal["human", "predicted", "human_confirmed"]` (ADR D-044)
  because none of `LabelSource`'s five original values (`f2`, `gutenberg_html`, `se_computed_css`,
  `human`, `synthetic`) could name a model. `LabelSource.MODEL` has since landed — see the
  vocabularies plan's Task 1 — which removes that reason: Task 3 uses `LabelSource.HUMAN` for a
  person-typed annotation set and `LabelSource.MODEL` for a prediction, and drops
  `human_confirmed` — a model-authored prediction a person accepted stays `source=MODEL`
  (the model still made the claim) with `state=KnowledgeState.POSITIVE` recording that a person
  looked at it and agreed, the same pattern `Disposition.ACCEPTED`/`EDITED` use for regions.
  `ConfidenceTier` is not used anywhere in this plan: a raw `confidence: float | None` matches the
  pattern the sibling region-stores plan already established for `RegionProposal.confidence`, and
  `ConfidenceTier`'s four buckets are calibrated for `StyleSpan`, not glyph predictions.
- **Glyph maps are keyed on a stable word identity, not a line/word ordinal.** `glyph_annotations_map`
  and `glyph_predictions_map` move from `"{line_index}_{word_index}"` to a bounding-box-signature
  key (`Word.bbox_signature`) — the same rule that already governs region identity, and for the same
  reason: line numbering is not stable across the band-identification fixes, and matching glyphs on
  line ordinal across a renumbering already invalidated an analysis in this project. A page reloaded
  with an existing legacy-keyed map is migrated once, at load time, while the current page structure
  still resolves the old positions — see Task 5.
- After Task 1 releases a new book-tools version, Task 2 must run
  `make update-pdomain-deps` in labeler-spa (or hand-edit the `pdomain-book-tools==X.Y.Z` pin in
  `pyproject.toml`) before its own tests can import the new `Word` method.

---

## File Structure

Paths are relative to each repo's root. `labeler-spa` abbreviates `pdomain-ocr-labeler-spa`, and its
package paths are relative to `src/pdomain_ocr_labeler_spa/`.

| repo | file | responsibility |
| --- | --- | --- |
| book-tools | `pdomain_book_tools/ocr/word.py` | modified: `set_ground_truth_text_with_provenance` |
| book-tools | `pdomain_book_tools/ocr/ground_truth_matching.py` | modified: 3 F2 writers stamp `LabelSource.F2` |
| book-tools | `tests/ocr/test_word_review.py` | modified: fixes the now-stale `to_dict` assertion |
| book-tools | `tests/ocr/test_ground_truth_matching.py` | modified: asserts F2 provenance |
| labeler-spa | `pyproject.toml` | modified: `pdomain-book-tools` pin bump |
| labeler-spa | `api/words.py` | modified: HUMAN provenance + reject route |
| labeler-spa | `api/lines_paragraphs.py` | modified: HUMAN provenance on line-GT redistribution |
| labeler-spa | `core/jobs/handlers/export.py` | modified: SYNTHETIC provenance on the export fallback |
| labeler-spa | `core/models.py` | modified: `GlyphAnnotationsModel` gains confidence/evidence/state |
| labeler-spa | `core/labeler_sidecars.py` | modified: persists `glyph_predictions_map` |
| labeler-spa | `core/glyph/predictions.py` | modified: `IGlyphPredictor` takes `Word`, page-level runner |
| labeler-spa | `core/page_state.py` | modified: `ensure_page_model` calls the predictor once per load |
| labeler-spa | `adapters/ocr/local_doctr.py` | modified: `LocalDoctrPageLoader.glyph_predictor` field |
| labeler-spa | `tests/unit/test_glyph_endpoints.py` | modified: covers new fields and the reject route |
| labeler-spa | `tests/unit/test_glyph_predictor_none.py` | modified: covers the page-level runner |
| labeler-spa | `tests/unit/core/test_labeler_sidecars.py` | modified/created: `glyph_predictions_map` round-trip |

---

### Task 1: book-tools — stamp ground-truth provenance where F2 writes it

`Word` already carries `text`/`ocr_confidence` (the machine's claim), `_ground_truth_text` (the
human's answer), and `review: ReviewMetadata | None` (the marker). What's missing is a single place
that sets ground truth and records provenance together — so three F2-alignment call sites in this
file (not the one the design doc names, since it turns out there are three) can all be fixed the
same way.

`ground_truth_matching.py` has exactly three raw assignments to `word.ground_truth_text`:
`update_line_match_difflib_lines_equal` (line 353), `update_line_with_ground_truth` (line 523), and
`update_line_with_ground_truth_replace_words` (line 960). All three are F2 word-level alignment —
the design's "F2 alignment is best effort" writer — so all three get `LabelSource.F2`.

**Files:**

- Modify: `pdomain_book_tools/ocr/word.py`
- Modify: `pdomain_book_tools/ocr/ground_truth_matching.py`
- Test: `tests/ocr/test_word_review.py`
- Test: `tests/ocr/test_ground_truth_matching.py`

**Interfaces:**

- Consumes: `KnowledgeState`, `LabelSource` from `pdomain_book_contracts.annotation`;
  `ReviewMetadata` from `pdomain_book_tools.ocr.review` (already imported by `word.py`).
- Produces: `Word.set_ground_truth_text_with_provenance(text, *, source, state=KnowledgeState.POSITIVE)`.

- [ ] **Step 1: Write the failing test**

Add to `tests/ocr/test_word_review.py` (reuses the existing `_bbox()` helper already in that file):

```python
def test_set_ground_truth_text_with_provenance_stamps_source_and_state() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    w = Word(text="teh", bounding_box=_bbox())
    w.set_ground_truth_text_with_provenance("the", source=LabelSource.F2, state=KnowledgeState.POSITIVE)

    assert w.ground_truth_text == "the"
    assert w.review is not None
    assert w.review.source == LabelSource.F2
    assert w.review.state == KnowledgeState.POSITIVE


def test_set_ground_truth_text_with_provenance_preserves_existing_review_fields() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    w = Word(
        text="teh",
        bounding_box=_bbox(),
        review=ReviewMetadata(validated=True, reviewer_note="flagged earlier", flagged_for_attention=True),
    )
    w.set_ground_truth_text_with_provenance("the", source=LabelSource.HUMAN, state=KnowledgeState.POSITIVE)

    assert w.review is not None
    assert w.review.validated is True
    assert w.review.reviewer_note == "flagged earlier"
    assert w.review.flagged_for_attention is True
    assert w.review.source == LabelSource.HUMAN


def test_word_to_dict_includes_review_when_set() -> None:
    rm = ReviewMetadata(validated=True, reviewer_note="ok", flagged_for_attention=True)
    w = Word(text="hello", bounding_box=_bbox(), review=rm)
    d = w.to_dict()
    assert d["review"] == {
        "validated": True,
        "reviewer_note": "ok",
        "flagged_for_attention": True,
        "source": None,
        "state": "unknown",
    }
```

The third test replaces the existing `test_word_to_dict_includes_review_when_set` in that file —
`ReviewMetadata.to_dict()` now always emits `source` and `state`, so the old three-key expected dict
no longer matches.

- [ ] **Step 2: Run test to verify it fails**

Run: `make AI=1 test-single TEST='tests/ocr/test_word_review.py'`
Expected: FAIL — `AttributeError: 'Word' object has no attribute 'set_ground_truth_text_with_provenance'`
on the first two new tests, and a dict-equality failure on the third (proving the stale assertion is
really stale before it's replaced).

- [ ] **Step 3: Write the implementation**

In `pdomain_book_tools/ocr/word.py`, add the import beside the existing `ReviewMetadata` import:

```python
from pdomain_book_contracts.annotation import KnowledgeState, LabelSource
from pdomain_book_tools.ocr.review import ReviewMetadata
```

Add the method to the `Word` class, directly after `clear_ground_truth`:

```python
    def set_ground_truth_text_with_provenance(
        self,
        text: str | None,
        *,
        source: LabelSource,
        state: KnowledgeState = KnowledgeState.POSITIVE,
    ) -> None:
        """Set ``ground_truth_text`` and record which source produced it.

        Four call sites across book-tools and the labeler fill
        ``ground_truth_text`` — F2 alignment, a person typing, split/merge
        token redistribution, and an export fallback — and none of them used
        to record which one did. This is the single place that does both at
        once, so ``review.source`` never has to be guessed at from context.

        Preserves ``validated``, ``reviewer_note``, and
        ``flagged_for_attention`` from any existing ``review``; only
        ``source`` and ``state`` are overwritten, because writing new ground
        truth always changes who is answerable for it.
        """
        self.ground_truth_text = text
        existing = self.review
        self.review = ReviewMetadata(
            validated=existing.validated if existing is not None else False,
            reviewer_note=existing.reviewer_note if existing is not None else None,
            flagged_for_attention=existing.flagged_for_attention if existing is not None else False,
            source=source,
            state=state,
        )
```

Then wire the three F2 writers in `pdomain_book_tools/ocr/ground_truth_matching.py`. Add the import
beside the existing top-level imports:

```python
from pdomain_book_contracts.annotation import KnowledgeState, LabelSource
```

Replace the assignment at line 353 (inside `update_line_match_difflib_lines_equal`):

```python
        word.set_ground_truth_text_with_provenance(
            ground_truth_line[word_idx], source=LabelSource.F2, state=KnowledgeState.POSITIVE
        )
        word.ground_truth_match_keys = {
            "match_type": MatchType.LINE_EQUAL.value,
            "match_score": 100,
        }
```

Replace the assignment at line 523 (inside `update_line_with_ground_truth`):

```python
                word.set_ground_truth_text_with_provenance(
                    ground_truth_tuple[gt_word_nbr], source=LabelSource.F2, state=KnowledgeState.POSITIVE
                )
                word.ground_truth_match_keys = {
                    "match_type": MatchType.WORD_EXACTLY_EQUAL.value,
                    "match_score": 100,
                }
```

Replace the assignment at line 960 (inside `update_line_with_ground_truth_replace_words`):

```python
        word.set_ground_truth_text_with_provenance(
            ground_truth_tuple[gt_word_nbr], source=LabelSource.F2, state=KnowledgeState.POSITIVE
        )
        logger.debug("GT Word: " + str(ground_truth_tuple[gt_word_nbr]))
```

Add to `tests/ocr/test_ground_truth_matching.py`, using the existing `_make_line`/`_make_page`
helpers already in that file:

```python
def test_update_line_match_difflib_lines_equal_stamps_f2_provenance() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    from pdomain_book_tools.ocr.ground_truth_matching import update_line_match_difflib_lines_equal

    line = _make_line(["hello", "world"], y=20)
    update_line_match_difflib_lines_equal(line, ["hello", "world"])

    for word in line.words:
        assert word.review is not None
        assert word.review.source == LabelSource.F2
        assert word.review.state == KnowledgeState.POSITIVE


def test_update_line_with_ground_truth_replace_words_stamps_f2_provenance() -> None:
    from pdomain_book_contracts.annotation import LabelSource

    from pdomain_book_tools.ocr.ground_truth_matching import (
        update_line_with_ground_truth_replace_words,
    )
    from pdomain_book_tools.ocr.ground_truth_matching_helpers.match_type import MatchType

    line = _make_line(["teh"], y=20)
    update_line_with_ground_truth_replace_words(
        line, ("teh",), ("the",), match_type=MatchType.LINE_REPLACE_WORD_REPLACE
    )

    assert line.words[0].review is not None
    assert line.words[0].review.source == LabelSource.F2
```

Check `update_line_with_ground_truth_replace_words`'s actual signature before writing the second
test — its keyword arguments were not re-verified beyond the line-960 body during this plan's
research and must be confirmed against the live function signature
(`grep -n "^def update_line_with_ground_truth_replace_words" -A 15 pdomain_book_tools/ocr/ground_truth_matching.py`)
before this test is finalized.

- [ ] **Step 4: Run the tests**

Run: `make AI=1 test-single TEST='tests/ocr/test_word_review.py'`
Run: `make AI=1 test-single TEST='tests/ocr/test_ground_truth_matching.py'`
Expected: PASS.

- [ ] **Step 5: Run the full gate and release**

Run: `make AI=1 ci`
Expected: PASS.

Release a new book-tools version so labeler-spa's Task 2 can pin to it:

```bash
make release-patch
```

- [ ] **Step 6: Commit**

```bash
git add pdomain_book_tools/ocr/word.py pdomain_book_tools/ocr/ground_truth_matching.py \
  tests/ocr/test_word_review.py tests/ocr/test_ground_truth_matching.py
git commit -m "feat(ocr): stamp F2 provenance on every word ground-truth write"
```

---

### Task 2: labeler-spa — bump the pin and stamp the three labeler writers

Three writers in this repo set `word.ground_truth_text` directly: a person typing a correction
(`api/words.py:555`), split/merge token redistribution (`api/lines_paragraphs.py:951-955`), and an
export fallback that copies the OCR's own text in as a placeholder (`core/jobs/handlers/export.py:204`).
The first two are human-sourced; the third is the sharpest case the design calls out — "an export
stamps the OCR's own output in as ground truth" — so it gets `LabelSource.SYNTHETIC` and
`KnowledgeState.UNKNOWN`, making it legible as a fabricated placeholder rather than a confirmed
reading.

**Files:**

- Modify: `pyproject.toml`
- Modify: `src/pdomain_ocr_labeler_spa/api/words.py`
- Modify: `src/pdomain_ocr_labeler_spa/api/lines_paragraphs.py`
- Modify: `src/pdomain_ocr_labeler_spa/core/jobs/handlers/export.py`
- Test: `tests/unit/test_words_ground_truth_provenance.py`
- Test: `tests/unit/test_export_ground_truth_provenance.py`

**Interfaces:**

- Consumes: `Word.set_ground_truth_text_with_provenance` from Task 1's released book-tools version;
  `KnowledgeState`, `LabelSource` from `pdomain_book_contracts.annotation`.
- Produces: no new public interface — the three routes' observable behavior is unchanged except for
  the `review` field now present on affected words.

- [ ] **Step 1: Bump the pin**

```bash
make update-pdomain-deps
```

Confirm `pyproject.toml`'s `pdomain-book-tools==X.Y.Z` line now names the version released in Task 1.
If the script does not pick it up (e.g. the private index has propagation lag), hand-edit the pin and
run `uv lock && uv sync`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/unit/test_words_ground_truth_provenance.py
"""Word-level ground-truth writes stamp LabelSource / KnowledgeState provenance."""

from __future__ import annotations

from pdomain_book_contracts.annotation import KnowledgeState, LabelSource
from pdomain_book_tools.geometry.bounding_box import BoundingBox
from pdomain_book_tools.ocr.word import Word


def _bbox() -> BoundingBox:
    return BoundingBox.from_dict(
        {"top_left": {"x": 0, "y": 0}, "bottom_right": {"x": 10, "y": 10}, "is_normalized": None}
    )


def test_update_word_ground_truth_stamps_human_provenance() -> None:
    """Mirrors the mutation ``api/words.py:555`` performs under the page lock."""
    word = Word(text="teh", bounding_box=_bbox())
    word.set_ground_truth_text_with_provenance("the", source=LabelSource.HUMAN, state=KnowledgeState.POSITIVE)

    assert word.ground_truth_text == "the"
    assert word.review is not None
    assert word.review.source == LabelSource.HUMAN
    assert word.review.state == KnowledgeState.POSITIVE


def test_set_line_gt_token_distribution_stamps_human_provenance() -> None:
    """Mirrors the mutation ``api/lines_paragraphs.py:951-955`` performs per token."""
    words = [Word(text="teh", bounding_box=_bbox()), Word(text="qwik", bounding_box=_bbox())]
    tokens = "the quick".split()
    for i, word in enumerate(words):
        token = " ".join(tokens[i:]) if i == len(words) - 1 else tokens[i]
        word.set_ground_truth_text_with_provenance(token, source=LabelSource.HUMAN, state=KnowledgeState.POSITIVE)

    assert [w.ground_truth_text for w in words] == ["the", "quick"]
    assert all(w.review is not None and w.review.source == LabelSource.HUMAN for w in words)
```

```python
# tests/unit/test_export_ground_truth_provenance.py
"""The export GT-first fallback marks its placeholder text as SYNTHETIC/UNKNOWN."""

from __future__ import annotations

from pdomain_book_contracts.annotation import KnowledgeState, LabelSource
from pdomain_book_tools.geometry.bounding_box import BoundingBox
from pdomain_book_tools.ocr.word import Word

from pdomain_ocr_labeler_spa.core.jobs.handlers.export import _prepare_page_gt_first


def _bbox() -> BoundingBox:
    return BoundingBox.from_dict(
        {"top_left": {"x": 0, "y": 0}, "bottom_right": {"x": 10, "y": 10}, "is_normalized": None}
    )


class _FakePage:
    def __init__(self, words: list[Word]) -> None:
        self.words = words


def test_export_fallback_stamps_synthetic_unknown_when_gt_was_empty() -> None:
    word = Word(text="ocr-text", bounding_box=_bbox())
    page = _FakePage([word])

    _prepare_page_gt_first(page)

    assert word.ground_truth_text == "ocr-text"
    assert word.review is not None
    assert word.review.source == LabelSource.SYNTHETIC
    assert word.review.state == KnowledgeState.UNKNOWN


def test_export_fallback_does_not_touch_a_word_with_real_ground_truth() -> None:
    word = Word(text="ocr-text", bounding_box=_bbox())
    word.set_ground_truth_text_with_provenance("real gt", source=LabelSource.HUMAN, state=KnowledgeState.POSITIVE)
    page = _FakePage([word])

    _prepare_page_gt_first(page)

    assert word.ground_truth_text == "real gt"
    assert word.review is not None
    assert word.review.source == LabelSource.HUMAN
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `make AI=1 test`
Expected: the two new files fail — the first two tests pass immediately (they exercise book-tools
directly, already fixed in Task 1), but the export test fails because `_prepare_page_gt_first` has
not been changed yet: `word.review is None`.

- [ ] **Step 4: Write the implementation**

In `src/pdomain_ocr_labeler_spa/api/words.py`, replace the assignment at line 555 inside
`update_word_ground_truth`:

```python
    page_lock = project_state.get_page_lock(page_index)
    with page_lock:
        word = _resolve_word(page, line_index, word_index)
        if word is None:
            return _word_not_found(line_index, word_index)
        from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

        word.set_ground_truth_text_with_provenance(
            body.text, source=LabelSource.HUMAN, state=KnowledgeState.POSITIVE
        )
        pstate.generation += 1
```

In `src/pdomain_ocr_labeler_spa/api/lines_paragraphs.py`, replace the `_mutate` body inside
`set_line_gt` (lines 946-955):

```python
    def _mutate(_page: Any, line: Any) -> bool:
        from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

        words = list(getattr(line, "words", []) or [])
        if not words:
            return True
        tokens = body.text.split()
        for i, word in enumerate(words):
            if i < len(tokens):
                token = " ".join(tokens[i:]) if i == len(words) - 1 else tokens[i]
            else:
                token = ""
            word.set_ground_truth_text_with_provenance(
                token, source=LabelSource.HUMAN, state=KnowledgeState.POSITIVE
            )
        return True
```

In `src/pdomain_ocr_labeler_spa/core/jobs/handlers/export.py`, replace the body of
`_prepare_page_gt_first`:

```python
def _prepare_page_gt_first(page: Any) -> None:
    """Set GT-first text/bbox on every word in place.

    A word with no ground truth yet gets the OCR's own text copied in so the
    export has *something* in the GT slot. That text was never asserted by
    anyone — F2 didn't align it, no person typed it — so it is stamped
    ``LabelSource.SYNTHETIC`` / ``KnowledgeState.UNKNOWN`` rather than left
    unmarked, so a trainer reading ``review.source`` later does not mistake
    it for a confirmed reading.
    """
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    for word in getattr(page, "words", []) or []:
        if not getattr(word, "ground_truth_text", None):
            word.set_ground_truth_text_with_provenance(
                getattr(word, "text", "") or "", source=LabelSource.SYNTHETIC, state=KnowledgeState.UNKNOWN
            )
        gt_bbox = getattr(word, "ground_truth_bounding_box", None)
        if gt_bbox is not None:
            word.bounding_box = gt_bbox
```

- [ ] **Step 5: Run the tests**

Run: `make AI=1 test`
Expected: PASS, including the existing `test_glyph_endpoints.py` / `test_glyph_bulk_mark.py` suites
(unaffected by this task).

- [ ] **Step 6: Run the full gate**

Run: `make AI=1 ci`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/pdomain_ocr_labeler_spa/api/words.py \
  src/pdomain_ocr_labeler_spa/api/lines_paragraphs.py \
  src/pdomain_ocr_labeler_spa/core/jobs/handlers/export.py \
  tests/unit/test_words_ground_truth_provenance.py tests/unit/test_export_ground_truth_provenance.py
git commit -m "feat(words): stamp HUMAN/SYNTHETIC provenance on the three labeler GT writers"
```

---

### Task 3: labeler-spa — give `GlyphAnnotationsModel` confidence, evidence, and a knowledge state

`GlyphAnnotationsModel` mirrors book-contracts' `GlyphAnnotations` but is its own independent wire
shape — the labeler never constructs the canonical dataclass; every read/write in `_page_payload`
goes through `pstate.glyph_annotations_map`/`glyph_predictions_map` dicts validated against this
Pydantic model. Adding fields here is therefore the whole fix; book-contracts is untouched. `source`
switches from a private three-value `Literal` to the shared `LabelSource` (`LabelSource.MODEL` now
exists — see Global Constraints); `state` reuses `KnowledgeState` so a rejection (Task 6) and an
acceptance can both be recorded as facts instead of one being silence.

**Files:**

- Modify: `src/pdomain_ocr_labeler_spa/core/models.py`
- Test: `tests/unit/test_glyph_endpoints.py`

**Interfaces:**

- Consumes: `KnowledgeState`, `LabelSource` from `pdomain_book_contracts.annotation`.
- Produces: `GlyphAnnotationsModel.source: LabelSource`, `.confidence: float | None`,
  `.evidence: dict[str, object]`, `.state: KnowledgeState`.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_glyph_endpoints.py`:

```python
def test_glyph_annotations_model_defaults_confidence_evidence_state() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState

    ga = GlyphAnnotationsModel()
    assert ga.confidence is None
    assert ga.evidence == {}
    assert ga.state == KnowledgeState.UNKNOWN


def test_glyph_annotations_model_round_trips_confidence_evidence_state() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    ga = GlyphAnnotationsModel(
        source=LabelSource.MODEL,
        confidence=0.83,
        evidence={"classifier": "none_v1"},
        state=KnowledgeState.UNKNOWN,
    )
    d = ga.model_dump(mode="json")
    restored = GlyphAnnotationsModel.model_validate(d)
    assert restored == ga
    assert d["state"] == "unknown"
    assert d["source"] == "model"


def test_glyph_annotations_model_expresses_a_rejection_as_verified_negative() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    rejected = GlyphAnnotationsModel(
        source=LabelSource.HUMAN,
        state=KnowledgeState.VERIFIED_NEGATIVE,
        evidence={"rejected_prediction": {"swash": True}},
    )
    assert rejected.state == KnowledgeState.VERIFIED_NEGATIVE
    assert rejected.evidence["rejected_prediction"] == {"swash": True}


def test_glyph_annotations_model_accepts_a_model_prediction_a_person_agreed_with() -> None:
    """An accepted prediction stays source=MODEL; state carries the human's agreement."""
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    accepted = GlyphAnnotationsModel(source=LabelSource.MODEL, state=KnowledgeState.POSITIVE, swash=True)
    assert accepted.source is LabelSource.MODEL
    assert accepted.state is KnowledgeState.POSITIVE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make AI=1 test`
Expected: FAIL — `TypeError: GlyphAnnotationsModel() got an unexpected keyword argument 'confidence'`.

- [ ] **Step 3: Write the implementation**

In `src/pdomain_ocr_labeler_spa/core/models.py`, add the import beside the existing `pydantic`
import:

```python
from pdomain_book_contracts.annotation import KnowledgeState, LabelSource
```

Replace the `GlyphAnnotationsModel` class body:

```python
class GlyphAnnotationsModel(BaseModel):
    """Glyph-level side-channel annotations for one word — spec §3 + D-044.

    Mirrors ``pdomain_book_tools.ocr.glyph_annotations.GlyphAnnotations`` and adds
    ``source`` (D-044: object-level provenance, not per-mark).

    Tri-state semantics (spec §1):
    - ``WordMatch.glyph_annotations is None`` — not yet reviewed.
    - ``WordMatch.glyph_annotations == GlyphAnnotationsModel()`` — reviewed, nothing to annotate.
    - ``WordMatch.glyph_annotations`` with marks — reviewed, marks present.

    ``glyph_predictions`` on ``WordMatch`` uses the same shape but with
    ``source=LabelSource.MODEL``; predictions are persisted (see
    ``core.labeler_sidecars.LabelerSidecars.glyph_predictions_map``) so a
    later run can be scored against what a person did with them.

    ``confidence`` and ``evidence`` carry what a prediction claimed —
    ``None``/``{}`` on a human-authored annotation set. ``state`` reuses the
    shared ``KnowledgeState`` vocabulary: ``UNKNOWN`` (default) for an
    unreviewed prediction or a plain "reviewed, nothing to mark" set,
    ``POSITIVE`` for an accepted or human-typed annotation set, and
    ``VERIFIED_NEGATIVE`` for a specific prediction a person looked at and
    refused (spec: "Built properly means eight properties", item 6 — a
    rejection is expressible, not merely an absence). ``source`` and
    ``state`` are independent axes: an accepted model prediction stays
    ``source=LabelSource.MODEL`` — the model still made the claim — with
    ``state=KnowledgeState.POSITIVE`` recording that a person agreed, the
    same split ``Disposition.ACCEPTED``/``EDITED`` use for regions. There is
    no ``human_confirmed`` source; that fact lives in ``state``.
    """

    ligatures: list[LigatureMarkModel] = Field(default_factory=list)
    long_s_positions: list[int] = Field(default_factory=list)
    swash: bool = False
    source: LabelSource = LabelSource.HUMAN
    confidence: float | None = None
    evidence: dict[str, object] = Field(default_factory=dict)
    state: KnowledgeState = KnowledgeState.UNKNOWN
```

- [ ] **Step 4: Run the tests**

Run: `make AI=1 test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/models.py tests/unit/test_glyph_endpoints.py
git commit -m "feat(glyph): give GlyphAnnotationsModel confidence, evidence, and a knowledge state"
```

---

### Task 4: labeler-spa — persist glyph predictions through `LabelerSidecars`

`PageState.glyph_predictions_map` exists but `LabelerSidecars` — the object that decides what
survives into the content blob — only carries `char_bboxes_map` and `glyph_annotations_map`.
Predictions are computed and thrown away every request. This task makes the third map durable the
same way the first two already are.

**Files:**

- Modify: `src/pdomain_ocr_labeler_spa/core/labeler_sidecars.py`
- Modify: `src/pdomain_ocr_labeler_spa/core/project_state.py`
- Test: `tests/unit/core/test_labeler_sidecars.py`

**Interfaces:**

- Consumes: nothing new.
- Produces: `LabelerSidecars.glyph_predictions_map: dict[str, Any]`, threaded through `is_empty`,
  `to_blob_section`, `from_page_state`, `from_content_dict`, and `apply_sidecars_to_page_state`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/core/test_labeler_sidecars.py` (or add to it if it already exists — check first
with `test -f tests/unit/core/test_labeler_sidecars.py`):

```python
"""Unit tests for LabelerSidecars, including glyph_predictions_map persistence."""

from __future__ import annotations

from pdomain_ocr_labeler_spa.core.labeler_sidecars import LabelerSidecars

# LabelerSidecars stores glyph_predictions_map as an opaque dict[str, Any] — it neither
# interprets nor validates keys or values, so a placeholder key below stands in for a
# real word-identity key without changing what this test proves.


def test_glyph_predictions_map_round_trips_through_blob_section() -> None:
    sidecars = LabelerSidecars(glyph_predictions_map={"0_0": {"source": "model", "swash": True}})
    section = sidecars.to_blob_section()
    assert section is not None
    assert section["glyph_predictions_map"] == {"0_0": {"source": "model", "swash": True}}

    restored = LabelerSidecars.from_content_dict({"labeler_sidecars": section})
    assert restored.glyph_predictions_map == {"0_0": {"source": "model", "swash": True}}


def test_glyph_predictions_map_alone_makes_sidecars_non_empty() -> None:
    sidecars = LabelerSidecars(glyph_predictions_map={"0_0": {}})
    assert sidecars.is_empty() is False


def test_from_page_state_snapshots_glyph_predictions_map() -> None:
    class _FakePageState:
        char_bboxes_map: dict[str, object] = {}
        glyph_annotations_map: dict[str, object] = {}
        glyph_predictions_map: dict[str, object] = {"0_1": {"swash": False}}
        logical_page_id = None

    sidecars = LabelerSidecars.from_page_state(_FakePageState())
    assert sidecars.glyph_predictions_map == {"0_1": {"swash": False}}


def test_apply_sidecars_to_page_state_replaces_glyph_predictions_map() -> None:
    from pdomain_ocr_labeler_spa.core.labeler_sidecars import apply_sidecars_to_page_state

    class _FakePageState:
        char_bboxes_map: dict[str, object] = {}
        glyph_annotations_map: dict[str, object] = {}
        glyph_predictions_map: dict[str, object] = {"stale": {}}
        logical_page_id = None

    pstate = _FakePageState()
    apply_sidecars_to_page_state(pstate, LabelerSidecars(glyph_predictions_map={"0_0": {"swash": True}}))
    assert pstate.glyph_predictions_map == {"0_0": {"swash": True}}

    apply_sidecars_to_page_state(pstate, None)
    assert pstate.glyph_predictions_map == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make AI=1 test`
Expected: FAIL — `TypeError: LabelerSidecars() got an unexpected keyword argument 'glyph_predictions_map'`.

- [ ] **Step 3: Write the implementation**

In `src/pdomain_ocr_labeler_spa/core/labeler_sidecars.py`, replace the `LabelerSidecars` dataclass
and its methods:

```python
@dataclass
class LabelerSidecars:
    """Char/glyph map payload carried beside ``Page.to_dict`` (Wave 0.1 / 2 T3).

    ``glyph_predictions_map`` (added alongside the reject-prediction route)
    is what lets a prediction be scored later against what a person did with
    it — without this, a prediction died with the request that computed it.
    """

    char_bboxes_map: dict[str, Any] = field(default_factory=dict)
    glyph_annotations_map: dict[str, Any] = field(default_factory=dict)
    glyph_predictions_map: dict[str, Any] = field(default_factory=dict)
    logical_page_id: str | None = None

    def is_empty(self) -> bool:
        return (
            not self.char_bboxes_map
            and not self.glyph_annotations_map
            and not self.glyph_predictions_map
            and self.logical_page_id is None
        )

    def to_blob_section(self) -> dict[str, Any] | None:
        """Return the JSON object for ``labeler_sidecars``, or None if empty."""
        if self.is_empty():
            return None
        out: dict[str, Any] = {}
        if self.char_bboxes_map:
            out["char_bboxes_map"] = dict(self.char_bboxes_map)
        if self.glyph_annotations_map:
            out["glyph_annotations_map"] = dict(self.glyph_annotations_map)
        if self.glyph_predictions_map:
            out["glyph_predictions_map"] = dict(self.glyph_predictions_map)
        if self.logical_page_id is not None:
            out["logical_page_id"] = self.logical_page_id
        return out

    @classmethod
    def from_page_state(cls, pstate: Any) -> LabelerSidecars:
        """Snapshot maps from a ``PageState`` (or any object with the attrs)."""
        bboxes = getattr(pstate, "char_bboxes_map", None) or {}
        glyphs = getattr(pstate, "glyph_annotations_map", None) or {}
        predictions = getattr(pstate, "glyph_predictions_map", None) or {}
        logical_page_id = getattr(pstate, "logical_page_id", None)
        return cls(
            char_bboxes_map=dict(bboxes) if isinstance(bboxes, Mapping) else {},
            glyph_annotations_map=dict(glyphs) if isinstance(glyphs, Mapping) else {},
            glyph_predictions_map=dict(predictions) if isinstance(predictions, Mapping) else {},
            logical_page_id=str(logical_page_id) if logical_page_id is not None else None,
        )

    @classmethod
    def from_content_dict(cls, content: Mapping[str, Any]) -> LabelerSidecars:
        """Extract sidecars from a content-blob dict (before or after from_dict)."""
        raw = content.get(LABELER_SIDECARS_KEY)
        if not isinstance(raw, Mapping):
            return cls()
        if "char_ranges_map" in raw:
            raise LegacyTypographyPayloadError("legacy char_ranges_map payload is unsupported")
        bboxes = raw.get("char_bboxes_map")
        glyphs = raw.get("glyph_annotations_map")
        predictions = raw.get("glyph_predictions_map")
        logical_page_id = raw.get("logical_page_id")
        return cls(
            char_bboxes_map=dict(bboxes) if isinstance(bboxes, Mapping) else {},
            glyph_annotations_map=dict(glyphs) if isinstance(glyphs, Mapping) else {},
            glyph_predictions_map=dict(predictions) if isinstance(predictions, Mapping) else {},
            logical_page_id=logical_page_id if isinstance(logical_page_id, str) else None,
        )
```

And `apply_sidecars_to_page_state`:

```python
def apply_sidecars_to_page_state(pstate: Any, sidecars: LabelerSidecars | None) -> None:
    """Replace PageState char/glyph maps from *sidecars* (clear when None/empty version).

    Always assigns new dicts so callers never share mutable maps with the
    blob payload or a previous version.
    """
    if sidecars is None:
        pstate.char_bboxes_map = {}
        pstate.glyph_annotations_map = {}
        pstate.glyph_predictions_map = {}
        return
    pstate.char_bboxes_map = dict(sidecars.char_bboxes_map)
    pstate.glyph_annotations_map = dict(sidecars.glyph_annotations_map)
    pstate.glyph_predictions_map = dict(sidecars.glyph_predictions_map)
    if sidecars.logical_page_id is not None:
        from uuid import UUID

        pstate.logical_page_id = UUID(sidecars.logical_page_id)
```

Also update the stale comment on `PageState.glyph_predictions_map` in `core/project_state.py` (it
currently reads "Predictions are NOT persisted; this sidecar is rebuilt on each page load."):

```python
    # Per-word glyph-predictions sidecar — keyed by a stable word identity (a
    # bounding-box signature, see ``core.glyph.predictions.word_identity_key``),
    # never a line/word ordinal: line numbering is not stable across the
    # band-identification fixes. Populated once per page load by the
    # ``IGlyphPredictor`` adapter (see ``core/glyph/predictions.py``) and
    # durable under content-blob ``labeler_sidecars.glyph_predictions_map`` so
    # a run can be scored later against the decisions made about it
    # (accept / reject).
    glyph_predictions_map: dict[str, object] = field(default_factory=dict)
```

- [ ] **Step 4: Run the tests**

Run: `make AI=1 test`
Expected: PASS, including the existing sidecar tests exercising `char_bboxes_map` /
`glyph_annotations_map` (unaffected by the new field's defaults).

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/labeler_sidecars.py src/pdomain_ocr_labeler_spa/core/project_state.py \
  tests/unit/core/test_labeler_sidecars.py
git commit -m "feat(glyph): persist glyph predictions through LabelerSidecars"
```

---

### Task 5: labeler-spa — wire `IGlyphPredictor.predict()` into page load

Nothing calls `IGlyphPredictor.predict()` today. `NoneGlyphPredictor` — the only implementation
shipped — is a correct no-op, but with no call site the "propose, then persist" pipeline the design
calls for has no proposal. `predict()` is currently typed against `WordMatch`, the API wire model,
which does not exist yet at the point in the load path (`ensure_page_model`) where a fresh
`PageLoadOutcome` first becomes available. This task corrects the seam to take `Word` — the
book-tools model that actually exists there — and wires a call once per page load, not once per
request, matching the guard `ensure_page_model` already uses for OCR itself.

This task also lands the glyph re-keying: both sidecar maps move from `"{line_index}_{word_index}"`
to a stable word-identity key (a bounding-box signature), on the same grounds regions carry no
positional key — line numbering is not stable across the band-identification fixes, and matching on
ordinal across a renumbering already invalidated an analysis in this project. A page that already
has a legacy-keyed map on disk is migrated once, at load time, while the current page structure can
still resolve the old positions to the words they identified.

**Files:**

- Modify: `src/pdomain_ocr_labeler_spa/core/glyph/predictions.py`
- Modify: `src/pdomain_ocr_labeler_spa/core/page_state.py`
- Modify: `src/pdomain_ocr_labeler_spa/adapters/ocr/local_doctr.py`
- Test: `tests/unit/test_glyph_predictor_none.py`
- Test: `tests/unit/core/test_ensure_page_model_glyph_predictions.py`

**Interfaces:**

- Consumes: `Word` from `pdomain_book_tools.ocr.word`.
- Produces: `IGlyphPredictor.predict(words: list[Word]) -> list[dict[str, object] | None]` (signature
  corrected); `predict_glyphs_for_page(predictor, page) -> dict[str, dict[str, object]]`;
  `word_identity_key(word: Word) -> str | None`;
  `migrate_legacy_glyph_keys(sidecar_map: dict[str, object], page: Any) -> dict[str, object]`;
  `migrate_legacy_glyph_source(record: dict[str, object]) -> dict[str, object]`;
  `LocalDoctrPageLoader.glyph_predictor: IGlyphPredictor`.

**The stored `source` values must migrate too, not only the keys.** Every annotation the accept
route has written carries `source="human_confirmed"` (`api/words.py:1565`), and `LabelSource` has no
such member, so those records raise `ValueError` on load unless the value is translated in the same
pass. The three legacy values map as follows, and the third is the reason `human_confirmed`
disappears rather than being kept:

| stored value | becomes |
| --- | --- |
| `"human"` | `source=LabelSource.HUMAN`, `state=KnowledgeState.POSITIVE` |
| `"predicted"` | `source=LabelSource.MODEL`, `state=KnowledgeState.UNKNOWN` |
| `"human_confirmed"` | `source=LabelSource.MODEL`, `state=KnowledgeState.POSITIVE` |

The last row is the whole point of the split: the annotation is still the model's claim, and the
person's agreement is a separate fact recorded in `state` rather than folded into the source.

Add this test alongside the key-migration test:

```python
def test_legacy_source_values_migrate_without_raising() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    from pdomain_ocr_labeler_spa.core.glyph.predictions import (
        migrate_legacy_glyph_source,
    )

    confirmed = migrate_legacy_glyph_source({"source": "human_confirmed", "swash": True})
    assert confirmed["source"] == LabelSource.MODEL
    assert confirmed["state"] == KnowledgeState.POSITIVE
    assert confirmed["swash"] is True

    predicted = migrate_legacy_glyph_source({"source": "predicted"})
    assert predicted["source"] == LabelSource.MODEL
    assert predicted["state"] == KnowledgeState.UNKNOWN

    typed = migrate_legacy_glyph_source({"source": "human"})
    assert typed["source"] == LabelSource.HUMAN
    assert typed["state"] == KnowledgeState.POSITIVE


def test_an_already_migrated_record_is_left_alone() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    from pdomain_ocr_labeler_spa.core.glyph.predictions import (
        migrate_legacy_glyph_source,
    )

    current = {"source": LabelSource.MODEL, "state": KnowledgeState.VERIFIED_NEGATIVE}
    assert migrate_legacy_glyph_source(current) == current
```

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_glyph_predictor_none.py`:

```python
def test_none_predictor_accepts_word_objects() -> None:
    from pdomain_book_tools.geometry.bounding_box import BoundingBox
    from pdomain_book_tools.ocr.word import Word

    bbox = BoundingBox.from_dict(
        {"top_left": {"x": 0, "y": 0}, "bottom_right": {"x": 10, "y": 10}, "is_normalized": None}
    )
    pred = NoneGlyphPredictor()
    out = pred.predict([Word(text="a", bounding_box=bbox), Word(text="b", bounding_box=bbox)])
    assert out == [None, None]


def test_predict_glyphs_for_page_skips_none_predictions() -> None:
    from pdomain_book_tools.geometry.bounding_box import BoundingBox
    from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType
    from pdomain_book_tools.ocr.page import Page
    from pdomain_book_tools.ocr.word import Word

    from pdomain_ocr_labeler_spa.core.glyph.predictions import NoneGlyphPredictor, predict_glyphs_for_page

    bbox = BoundingBox.from_dict(
        {"top_left": {"x": 0, "y": 0}, "bottom_right": {"x": 10, "y": 10}, "is_normalized": None}
    )
    line = Block(
        items=[Word(text="a", bounding_box=bbox), Word(text="b", bounding_box=bbox)],
        block_category=BlockCategory.LINE,
        child_type=BlockChildType.WORDS,
    )
    page = Page(width=100, height=100, page_index=0, blocks=[line])

    result = predict_glyphs_for_page(NoneGlyphPredictor(), page)
    assert result == {}
```

```python
# tests/unit/core/test_ensure_page_model_glyph_predictions.py
"""ensure_page_model calls the glyph predictor once per fresh load, not per request."""

from __future__ import annotations


def test_ensure_page_model_runs_the_predictor_when_loader_has_one() -> None:
    """A stub predictor that returns a fixed prediction lands in glyph_predictions_map."""
    from pdomain_book_tools.geometry.bounding_box import BoundingBox
    from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType
    from pdomain_book_tools.ocr.page import Page
    from pdomain_book_tools.ocr.word import Word

    from pdomain_ocr_labeler_spa.core.page_state import PageLoadOutcome, PageSource, ensure_page_model
    from pdomain_ocr_labeler_spa.core.project_state import ProjectState

    bbox = BoundingBox.from_dict(
        {"top_left": {"x": 0, "y": 0}, "bottom_right": {"x": 10, "y": 10}, "is_normalized": None}
    )
    word = Word(text="a", bounding_box=bbox)
    line = Block(items=[word], block_category=BlockCategory.LINE, child_type=BlockChildType.WORDS)
    page = Page(width=100, height=100, page_index=0, blocks=[line])

    class _StubPredictor:
        def predict(self, words: list[Word]) -> list[dict[str, object] | None]:
            return [{"source": "model", "swash": True} for _ in words]

    class _StubLoader:
        glyph_predictor = _StubPredictor()

        def load_labeled(self, page_index: int) -> PageLoadOutcome | None:
            return None

        def load_cached(self, page_index: int) -> PageLoadOutcome | None:
            return None

        def run_ocr(self, page_index: int, *, edited_image_bytes: bytes | None = None) -> PageLoadOutcome:
            return PageLoadOutcome(page_index=page_index, source=PageSource.OCR, payload=page)

    state = ProjectState()
    # Minimal project stub with one page — check the real ProjectState/Project
    # construction contract before finalizing this test; the fields required
    # to satisfy ``ensure_page_model``'s early guards (project.total_pages,
    # state.loaded_project) must be confirmed against the live classes.
    ensure_page_model(state, 0, loader=_StubLoader())

    from pdomain_ocr_labeler_spa.core.glyph.predictions import word_identity_key

    expected_key = word_identity_key(word)
    assert expected_key is not None

    pstate = state.get_page_state(0)
    assert pstate is not None
    assert pstate.glyph_predictions_map == {expected_key: {"source": "model", "swash": True}}


def test_ensure_page_model_migrates_a_legacy_positionally_keyed_map() -> None:
    """A map keyed ``"{line_index}_{word_index}"`` on disk is re-keyed to word identity on load."""
    from pdomain_book_tools.geometry.bounding_box import BoundingBox
    from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType
    from pdomain_book_tools.ocr.page import Page
    from pdomain_book_tools.ocr.word import Word

    from pdomain_ocr_labeler_spa.core.glyph.predictions import word_identity_key
    from pdomain_ocr_labeler_spa.core.page_state import PageLoadOutcome, PageSource, ensure_page_model
    from pdomain_ocr_labeler_spa.core.project_state import ProjectState

    bbox = BoundingBox.from_dict(
        {"top_left": {"x": 0, "y": 0}, "bottom_right": {"x": 10, "y": 10}, "is_normalized": None}
    )
    word = Word(text="a", bounding_box=bbox)
    line = Block(items=[word], block_category=BlockCategory.LINE, child_type=BlockChildType.WORDS)
    page = Page(width=100, height=100, page_index=0, blocks=[line])

    class _NonePredictor:
        def predict(self, words: list[Word]) -> list[dict[str, object] | None]:
            return [None for _ in words]

    class _StubLoaderWithLegacyMap:
        glyph_predictor = _NonePredictor()

        def load_labeled(self, page_index: int) -> PageLoadOutcome | None:
            return PageLoadOutcome(
                page_index=page_index,
                source=PageSource.CACHED,
                payload=page,
                glyph_annotations_map={"0_0": {"source": "human", "swash": True}},
            )

        def load_cached(self, page_index: int) -> PageLoadOutcome | None:
            return None

        def run_ocr(self, page_index: int, *, edited_image_bytes: bytes | None = None) -> PageLoadOutcome:
            raise AssertionError("load_labeled should have short-circuited OCR")

    # The exact keyword ``load_labeled`` uses to carry a persisted sidecar map must be
    # confirmed against ``PageLoadOutcome``'s live fields before this step is
    # implemented — this test assumes ``glyph_annotations_map`` is one of them,
    # matching the shape ``sidecars_from_page``/``apply_sidecars_from_payload``
    # already read off a loaded page elsewhere in this file.
    state = ProjectState()
    ensure_page_model(state, 0, loader=_StubLoaderWithLegacyMap())

    expected_key = word_identity_key(word)
    assert expected_key is not None

    pstate = state.get_page_state(0)
    assert pstate is not None
    assert pstate.glyph_annotations_map == {expected_key: {"source": "human", "swash": True}}
    assert "0_0" not in pstate.glyph_annotations_map
```

Flag the `ProjectState`/`Project` construction in both tests as unverified — confirm the exact
minimal setup (likely `state.set_loaded_project(...)` with a small `Project` stub carrying
`total_pages=1`) against the live class before this step is implemented; do not guess the
constructor shape. Likewise confirm `PageLoadOutcome`'s exact field for carrying a persisted
`glyph_annotations_map` before implementing the migration test.

- [ ] **Step 2: Run test to verify it fails**

Run: `make AI=1 test`
Expected: FAIL — the first two on `TypeError`/attribute mismatch before the Protocol is corrected;
the third on `pstate.glyph_predictions_map == {}` (nothing calls `.predict()` yet); the fourth
(migration) on `ModuleNotFoundError` / `ImportError` for `word_identity_key` and
`migrate_legacy_glyph_keys`, neither of which exists yet.

- [ ] **Step 3: Write the implementation**

Replace `src/pdomain_ocr_labeler_spa/core/glyph/predictions.py`:

```python
"""IGlyphPredictor — Protocol for glyph-annotation predictions.

Mirrors IOCREngine's seam pattern. v1 ships only `none_`; pd-ocr-trainer
delivers the local classifier when its glyph-feature work lands.

Predictions run once per page load (``core.page_state.ensure_page_model``,
the same guard OCR itself uses) and are persisted through
``core.labeler_sidecars.LabelerSidecars.glyph_predictions_map`` so a run can
be scored later against what a person did with it — accepted, or refused via
the reject-prediction route.

Both sidecar maps (``glyph_annotations_map``, ``glyph_predictions_map``) are
keyed by ``word_identity_key``, a stable bounding-box signature — never a
line/word ordinal. Line numbering is not stable across the band-identification
fixes, and matching on ordinal across a renumbering already invalidated an
analysis in this project; the same rule that forbids positional region keys
applies one level down. ``migrate_legacy_glyph_keys`` re-keys a map still
carrying the old ``"{line_index}_{word_index}"`` form.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Protocol

from pdomain_book_tools.ocr.word import Word

log = logging.getLogger(__name__)

_LEGACY_POSITIONAL_KEY = re.compile(r"^\d+_\d+$")


class IGlyphPredictor(Protocol):
    """Predict glyph annotations for a list of words."""

    def predict(self, words: list[Word]) -> list[dict[str, object] | None]:
        """Return one prediction dict (or None) per input word, same order."""
        ...


class NoneGlyphPredictor:
    """Default adapter — always returns None for every word."""

    def predict(self, words: list[Word]) -> list[dict[str, object] | None]:
        return [None] * len(words)


def word_identity_key(word: Word) -> str | None:
    """A stable sidecar-map key for one word, from its bounding-box signature.

    Returns ``None`` when the word has no bounding box to derive one from —
    callers skip such a word rather than falling back to a position.
    """
    signature = word.bbox_signature
    if signature is None:
        return None
    min_x, min_y, max_x, max_y, is_normalized = signature
    return f"{min_x}_{min_y}_{max_x}_{max_y}_{is_normalized}"


def predict_glyphs_for_page(predictor: IGlyphPredictor, page: Any) -> dict[str, dict[str, object]]:
    """Run *predictor* over every word on *page*.

    Returns a sidecar-shaped map, keyed by ``word_identity_key``, holding only
    the words the predictor had something to say about. A word with no
    bounding box (``word_identity_key`` returns ``None``) is skipped even if
    the predictor had a prediction for it — there is nowhere stable to file it.
    """
    words: list[Word] = []
    keys: list[str | None] = []
    for line in getattr(page, "lines", []) or []:
        for word in getattr(line, "words", []) or []:
            words.append(word)
            keys.append(word_identity_key(word))
    predictions = predictor.predict(words)
    return {
        key: prediction
        for key, prediction in zip(keys, predictions, strict=True)
        if key is not None and prediction is not None
    }


def migrate_legacy_glyph_keys(sidecar_map: dict[str, object], page: Any) -> dict[str, object]:
    """Re-key a glyph sidecar map from ``"{line_index}_{word_index}"`` to word identity.

    Runs once, at load time, while the current page structure can still
    resolve the old positional keys to the words they identified when they
    were written. A key that no longer resolves — the page now has fewer
    lines or words than it did, or the word there has no bounding box — is
    dropped rather than guessed at: silently reattaching an annotation to a
    different piece of ink is exactly what this migration exists to stop. A
    key that is not of the legacy ``\\d+_\\d+`` shape passes through unchanged
    (it is already a word-identity key, or something else entirely).
    """
    if not sidecar_map:
        return {}
    lines = getattr(page, "lines", None) or []
    migrated: dict[str, object] = {}
    for key, value in sidecar_map.items():
        if not _LEGACY_POSITIONAL_KEY.match(key):
            migrated[key] = value
            continue
        line_index_str, word_index_str = key.split("_", 1)
        line_index, word_index = int(line_index_str), int(word_index_str)
        if not (0 <= line_index < len(lines)):
            log.warning("glyph sidecar migration: line %d no longer exists, dropping %r", line_index, key)
            continue
        words = getattr(lines[line_index], "words", None) or []
        if not (0 <= word_index < len(words)):
            log.warning(
                "glyph sidecar migration: word %d/%d no longer exists, dropping %r",
                line_index, word_index, key,
            )
            continue
        new_key = word_identity_key(words[word_index])
        if new_key is None:
            log.warning("glyph sidecar migration: word %d/%d has no bounding box, dropping %r", line_index, word_index, key)
            continue
        migrated[new_key] = value
    return migrated
```

In `src/pdomain_ocr_labeler_spa/adapters/ocr/local_doctr.py`, add the `glyph_predictor` field to
`LocalDoctrPageLoader` (after the existing `image_path_resolver` field, since dataclass fields with
defaults must trail those without):

```python
    image_path_resolver: Callable[[int], Path] | None = None
    glyph_predictor: IGlyphPredictor = field(default_factory=NoneGlyphPredictor)
```

Add the imports near the top of the file:

```python
from dataclasses import dataclass, field

from ...core.glyph.predictions import IGlyphPredictor, NoneGlyphPredictor
```

Check whether `dataclass`/`field` are already imported before adding — if only `dataclass` is
imported today, extend that import line rather than duplicating it.

In `src/pdomain_ocr_labeler_spa/core/page_state.py`, extend the sidecar-application block inside
`ensure_page_model` (directly after the existing `if stamped is not None: ... else: ...` block, and
before the `logical_page_id` block that follows it):

```python
        stamped = sidecars_from_page(payload_obj) if payload_obj is not None else None
        if stamped is not None:
            apply_sidecars_from_payload(existing, payload_obj)
        else:
            apply_sidecars_to_page_state(existing, None)

        # Migrate any legacy "{line_index}_{word_index}"-keyed glyph maps to
        # word-identity keys, once, while the current page structure can still
        # resolve the old positions to the words they identified. Must run
        # before the predictor below, so a freshly-migrated annotations map
        # and a freshly-computed predictions map use the same key shape.
        if payload_obj is not None:
            from .glyph.predictions import migrate_legacy_glyph_keys

            existing.glyph_annotations_map = migrate_legacy_glyph_keys(existing.glyph_annotations_map, payload_obj)
            existing.glyph_predictions_map = migrate_legacy_glyph_keys(existing.glyph_predictions_map, payload_obj)

        # Run the glyph predictor once per fresh load, not once per request —
        # ``ensure_page_model``'s cache-hit early-return above already skips
        # this block on every subsequent fetch of the same page. Only fill a
        # gap: a page reloaded from the store may already carry persisted
        # predictions from an earlier run, and those must not be overwritten.
        if not existing.glyph_predictions_map and payload_obj is not None:
            predictor = getattr(loader, "glyph_predictor", None)
            if predictor is not None:
                from .glyph.predictions import predict_glyphs_for_page

                existing.glyph_predictions_map = predict_glyphs_for_page(predictor, payload_obj)
```

- [ ] **Step 4: Run the tests**

Run: `make AI=1 test`
Expected: PASS.

- [ ] **Step 5: Run the full gate**

Run: `make AI=1 ci`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/glyph/predictions.py src/pdomain_ocr_labeler_spa/core/page_state.py \
  src/pdomain_ocr_labeler_spa/adapters/ocr/local_doctr.py \
  tests/unit/test_glyph_predictor_none.py tests/unit/core/test_ensure_page_model_glyph_predictions.py
git commit -m "feat(glyph): run the glyph predictor once per page load and persist its output"
```

---

### Task 6: labeler-spa — add the reject-prediction route

`POST .../words/{li}/{wi}/accept-prediction` exists; its counterpart does not. A person who
disagrees with a prediction today just edits past it, and the disagreement leaves no trace. This
task adds the reject route and marks the acceptance path's `state` too, so both dispositions are
recorded the same way.

**Files:**

- Modify: `src/pdomain_ocr_labeler_spa/api/words.py`
- Test: `tests/unit/test_glyph_endpoints.py`

**Interfaces:**

- Consumes: `KnowledgeState`, `LabelSource` from `pdomain_book_contracts.annotation`;
  `pstate.glyph_predictions_map`, `word_identity_key` from Task 5.
- Produces: `POST /{project_id}/pages/{page_index}/words/{line_index}/{word_index}/reject-prediction`,
  response model `PagePayload`, matching `accept_glyph_prediction`'s shape and error handling.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_glyph_endpoints.py`:

```python
def test_reject_glyph_prediction_request_has_no_required_fields() -> None:
    from pdomain_ocr_labeler_spa.api.words import RejectGlyphPredictionRequest

    req = RejectGlyphPredictionRequest()
    assert req is not None
```

This is a route-shape smoke test only — the reject route's end-to-end behavior (400 on no
prediction, 404 on an out-of-range `line_index`/`word_index`, `state=VERIFIED_NEGATIVE` on success
keyed by `word_identity_key` rather than position, `pstate.glyph_annotations_map` written) belongs
in `tests/integration/`, which exercises routes against a live app per this repo's four-tier test
plan. Confirm the integration test's project/page fixture setup against an existing glyph-route
integration test (e.g. one covering `accept-prediction`) before writing it — do not invent the
fixture shape here.

- [ ] **Step 2: Run test to verify it fails**

Run: `make AI=1 test`
Expected: FAIL — `ImportError: cannot import name 'RejectGlyphPredictionRequest'`.

- [ ] **Step 3: Write the implementation**

In `src/pdomain_ocr_labeler_spa/api/words.py`, add the request model beside
`AcceptGlyphPredictionRequest`:

```python
class RejectGlyphPredictionRequest(BaseModel):
    """``POST .../words/{li}/{wi}/reject-prediction`` body — spec §6.1.

    No fields — records that a person looked at the current prediction and
    refused it, as a ``KnowledgeState.VERIFIED_NEGATIVE`` fact rather than
    leaving no trace.
    """
```

Add the route directly after `accept_glyph_prediction`:

```python
@router.post(
    "/{project_id}/pages/{page_index}/words/{line_index}/{word_index}/reject-prediction",
    response_model=PagePayload,
)
def reject_glyph_prediction(
    *,
    project_id: str,
    page_index: int,
    line_index: int,
    word_index: int,
    body: RejectGlyphPredictionRequest,  # pyright: ignore[reportUnusedParameter]
    project_state: ProjectState = Depends(get_project_state),  # pyright: ignore[reportCallInDefaultInitializer]
    settings: Settings = Depends(get_settings),  # pyright: ignore[reportCallInDefaultInitializer]
    app_config: AppConfig = Depends(get_app_config),  # pyright: ignore[reportCallInDefaultInitializer]
    store: LabelerPageStore | None = Depends(get_page_store_optional),
) -> JSONResponse:
    """``POST .../words/{li}/{wi}/reject-prediction`` — refuse a glyph prediction.

    Records the refusal as a ``KnowledgeState.VERIFIED_NEGATIVE`` annotation
    set carrying the rejected prediction under ``evidence``, so a rejection
    is distinguishable from a word nobody has looked at. Predictions remain
    on ``glyph_predictions_map`` (not cleared by this call), matching
    ``accept_glyph_prediction``'s handling.

    ``line_index``/``word_index`` address the word in the *current* live
    tree only — resolved once, here, into the word-identity key the sidecar
    maps are actually keyed by. Nothing persists the positional pair itself;
    line numbering is not stable across the band-identification fixes.

    Spec: ``specs/20-glyph-annotations.md`` §6.1.
    """
    err = _check_project_and_page(project_id, page_index, project_state)
    if err is not None:
        return err

    pstate = project_state.get_page_state(page_index)
    page = _resolve_page_object(pstate)
    if pstate is None or page is None:
        return _page_not_loaded(page_index)

    from pdomain_ocr_labeler_spa.core.glyph.predictions import word_identity_key

    lines = page.lines
    if not (0 <= line_index < len(lines)) or not (0 <= word_index < len(lines[line_index].words)):
        return JSONResponse(
            status_code=404,
            content=ApiError(
                error="word_not_found", message=f"word not found: line {line_index}, word {word_index}"
            ).model_dump(),
        )
    sidecar_key = word_identity_key(lines[line_index].words[word_index])
    if sidecar_key is None:
        return JSONResponse(
            status_code=400,
            content=ApiError(
                error="no_predictions",
                message=f"word {line_index}/{word_index} has no bounding box to key a prediction by",
            ).model_dump(),
        )

    predictions_dict = pstate.glyph_predictions_map.get(sidecar_key)
    if predictions_dict is None:
        return JSONResponse(
            status_code=400,
            content=ApiError(
                error="no_predictions",
                message=f"No predictions found for word {line_index}/{word_index}",
            ).model_dump(),
        )

    from pdomain_book_contracts.annotation import KnowledgeState, LabelSource

    rejected: dict[str, object] = {
        "ligatures": [],
        "long_s_positions": [],
        "swash": False,
        "source": LabelSource.HUMAN.value,
        "state": KnowledgeState.VERIFIED_NEGATIVE.value,
        "evidence": {"rejected_prediction": predictions_dict},
    }

    page_lock = project_state.get_page_lock(page_index)
    with page_lock:
        pstate.glyph_annotations_map[sidecar_key] = rejected

        pstate.generation += 1
        if not _save_to_store_best_effort(
            pstate=pstate,
            store=store,
            changes=[
                {
                    "type": "reject_glyph_prediction",
                    "line_index": line_index,
                    "word_index": word_index,
                }
            ],
        ):
            return _store_persist_failed_response(page_id=pstate.page_id)

    return _refresh_payload_response(
        project_id=project_id,
        page_index=page_index,
        project_state=project_state,
        settings=settings,
        app_config=app_config,
    )
```

`accept_glyph_prediction` resolves its own `sidecar_key` the same positional way
`reject_glyph_prediction` used to — read that function's existing body first and apply the same
`word_identity_key(lines[line_index].words[word_index])` resolution shown above in place of its
`f"{line_index}_{word_index}"` line, with the same out-of-range/no-bounding-box handling. This is
required, not optional: `predict_glyphs_for_page` (Task 5) now writes `glyph_predictions_map` keyed
by word identity, so a lookup still keyed positionally would never find what it wrote.

Also mark the acceptance path's disposition, so accept and reject are symmetric. In
`accept_glyph_prediction`, replace the `confirmed` dict construction:

```python
    from pdomain_book_contracts.annotation import KnowledgeState

    predictions_as_dict = cast("dict[str, object]", predictions_dict)
    confirmed: dict[str, object] = {
        **predictions_as_dict,
        "state": KnowledgeState.POSITIVE.value,
    }
```

No `source` override: `predictions_as_dict` already carries `source=LabelSource.MODEL.value`
(`"model"`) from the prediction it was built from, and a model-authored prediction a person
accepted stays model-authored — the acceptance is what `state=KnowledgeState.POSITIVE` records.
There is no `human_confirmed` source to fall back to; that was the private third value this
correction removes (see Global Constraints and Task 3).

- [ ] **Step 4: Run the tests**

Run: `make AI=1 test`
Expected: PASS.

- [ ] **Step 5: Regenerate the OpenAPI client and run the full gate**

Run: `make openapi-export`
Expected: `frontend/src/api/types.ts` gains the new `reject-prediction` operation; commit the
regenerated file alongside the route.

Run: `make AI=1 ci`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/api/words.py tests/unit/test_glyph_endpoints.py \
  frontend/src/api/types.ts frontend/openapi.json
git commit -m "feat(glyph): add the reject-prediction route glyph accept never got a counterpart for"
```

---

---

### Task 7: book-contracts — stamp the ground-truth digest beside each annotation set

`LigatureMark.char_span` is a half-open pair of character indices into `Word.ground_truth_text`, and
`long_s_positions` is a list of indices into the same string. Four writers rewrite that string.
Correcting a word's ground truth shifts every mark on it, and nothing invalidates or remaps them, so
a ligature span survives the edit and silently names different characters.

This is the ordinal problem one level below the word. The fix is the mechanism the page level uses:
store a digest of the text the marks were computed against, and treat a mismatch as stale rather
than as truth.

**Files:**

- Modify: `pdomain_book_contracts/pdomain_book_contracts/ocr/glyph_annotations.py`
- Test: `pdomain-book-contracts/tests/test_glyph_mark_staleness.py`

**Interfaces:**

- Consumes: nothing new.
- Produces: `GlyphAnnotations.ground_truth_digest: str | None`, and
  `GlyphAnnotations.marks_are_stale_for(ground_truth_text: str) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_glyph_mark_staleness.py
from __future__ import annotations

from pdomain_book_contracts.ocr.glyph_annotations import (
    GlyphAnnotations,
    LigatureKind,
    LigatureMark,
)


def _annotations(text: str) -> GlyphAnnotations:
    return GlyphAnnotations(
        ligatures=[LigatureMark(kind=LigatureKind.FI, char_span=(0, 2))],
        long_s_positions=[3],
        ground_truth_digest=GlyphAnnotations.digest_for("fitful"),
    )


def test_marks_are_current_against_the_text_they_were_made_on() -> None:
    assert _annotations("fitful").marks_are_stale_for("fitful") is False


def test_marks_go_stale_when_the_text_changes() -> None:
    assert _annotations("fitful").marks_are_stale_for("fitfull") is True


def test_an_annotation_set_with_no_digest_is_never_called_stale() -> None:
    """Records written before this field existed must not all read as stale."""
    legacy = GlyphAnnotations(long_s_positions=[3])
    assert legacy.ground_truth_digest is None
    assert legacy.marks_are_stale_for("anything") is False


def test_a_set_with_no_positional_marks_is_never_stale() -> None:
    """`swash` is a word-level bool and does not index into the text."""
    coarse = GlyphAnnotations(swash=True, ground_truth_digest=GlyphAnnotations.digest_for("old"))
    assert coarse.marks_are_stale_for("new") is False


def test_the_digest_round_trips() -> None:
    original = _annotations("fitful")
    restored = GlyphAnnotations.from_dict(original.to_dict())
    assert restored.ground_truth_digest == original.ground_truth_digest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_glyph_mark_staleness.py -v`
Expected: FAIL with `TypeError: GlyphAnnotations.__init__() got an unexpected keyword argument
'ground_truth_digest'`

- [ ] **Step 3: Add the field, the digest helper, and the staleness check**

Add to `GlyphAnnotations`, defaulting to `None` so every stored record keeps loading:

```python
    ground_truth_digest: str | None = None
    """SHA-256 of the ``Word.ground_truth_text`` these marks were computed against.

    ``char_span`` and ``long_s_positions`` are character indices into that
    string, and four different writers rewrite it. Without this digest an edit
    silently leaves the marks pointing at different characters. ``None`` means
    the record predates this field, which is not the same as current.
    """

    @staticmethod
    def digest_for(ground_truth_text: str) -> str:
        """Return the digest to store beside marks made against this text."""
        import hashlib

        return hashlib.sha256(ground_truth_text.encode("utf-8")).hexdigest()

    def marks_are_stale_for(self, ground_truth_text: str) -> bool:
        """Whether the positional marks no longer describe this text.

        Returns ``False`` when there is no digest, because a record written
        before this field existed carries no claim either way, and returns
        ``False`` when there are no positional marks to invalidate.
        """
        if self.ground_truth_digest is None:
            return False
        if not self.ligatures and not self.long_s_positions:
            return False
        return self.ground_truth_digest != self.digest_for(ground_truth_text)
```

Add `"ground_truth_digest": self.ground_truth_digest` to `to_dict`, and read it back in `from_dict`
with a `None` default.

- [ ] **Step 4: Run the tests**

Run: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest tests/test_glyph_mark_staleness.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Run the gate and commit**

```bash
make ci
git add pdomain_book_contracts/ocr/glyph_annotations.py tests/test_glyph_mark_staleness.py
git commit -m "feat(glyph): mark sub-word annotations stale when their text changes"
```

## What this plan does not do

- It does not touch `pdomain-book-contracts`. `GlyphAnnotations` (the canonical dataclass) and
  `GlyphSource` are untouched; the labeler's own `GlyphAnnotationsModel` is the operative wire shape
  for every glyph read/write in this codebase, and that is where Task 3's fields land.
- It does not add `ConfidenceTier` anywhere. Global Constraints explains why: its four buckets are
  calibrated for `StyleSpan`, and a raw `confidence: float | None` already matches the sibling
  region-stores plan's `RegionProposal.confidence` pattern.
- It does not build a real glyph classifier. `NoneGlyphPredictor` stays the only implementation;
  this plan only gives its output somewhere durable to land and a call site that runs it.
- It does not add a decision journal for words or glyphs. Per the design's rule, a decision store is
  needed only when the human's answer is sparse against the machine's output — a word has one answer
  and a glyph annotation set is per-word, so the existing `review`/`glyph_annotations_map` marker is
  enough. Regions are the level that needed a journal, and that is the sibling
  `2026-09-08-region-stores-and-resolver.md` plan.
- It does not change page kind or region provenance. Those are the sibling plans' work.
- It does not add a UI affordance for the reject-prediction route. The frontend `GlyphChip` /
  `GlyphAnnotationPanel` components already render accept/reject as a pair per the spec; wiring the
  reject button to the new route is frontend work this plan leaves for whoever picks up
  `frontend/src/components/glyph/`.
- It does not remap a stale `char_span` or `long_s_positions` to the corrected text. Task 7 makes
  the staleness visible; deciding what a person or a job then does with a stale mark is separate
  work.

## Related

- [Annotation provenance and
  persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) — the design.
- [Annotation vocabularies in
  book-contracts](2026-09-08-annotation-vocabularies-in-book-contracts.md) — must land first; this
  plan consumes `ReviewMetadata.source`/`.state` (Task 5) and `KnowledgeState`/`LabelSource` (Task 1)
  from it.
- [Region stores and resolver](2026-09-08-region-stores-and-resolver.md) — the sibling plan for the
  one annotation level that does need a decision journal, and the pattern this plan's Global
  Constraints borrows the `RegionProposal.confidence` precedent from.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — the seven slices.
