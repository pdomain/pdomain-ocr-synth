# Style Span Review Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a person a way to confirm or reject one `StyleSpan` at a time. `StyleSpan` is a
grapheme range on `TypographyPageRecord.style_spans`, and today nothing lets a reviewer act on it
at that granularity — the only typography review routes are word-scoped.

**Architecture:** Style spans are read, never written. `TypographyPageRecord` (and its
`style_spans` field) is already validated on every book-labeling-session page load but is not
retained anywhere — this plan re-derives it from bytes the session already hash-verified, rather
than changing what `BookLabelingSession` retains. A span carries no id of its own, so a
deterministic `span_id` is derived from the page's content-addressed `page_sha256` plus the span's
own position and content — never a bare list index. A new append-only JSONL journal,
`StyleSpanDecisionLog`, records a person's confirm-or-reject verdict per span, modeled on
`ImportedTextValidationLog` (the closest existing precedent: a small CAS-bound yes/no decision per
identity) rather than on `TypographyCorrectionLog`'s multi-revision word-correction lineage, which
solves a different problem. A span's word-crossing extent is surfaced read-only, via the existing
`project_style_span` alignment utility — it is never merged into `stable_word_id` or the
word-scoped `TypographyCorrectionLog`, which stay untouched by every route this plan adds.

**Tech Stack:** Python 3.13, pydantic `BaseModel`, `StrEnum`, JSONL journals with an OS append
lock, FastAPI, pytest, ruff, basedpyright.

**Spec:** [Annotation provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md), section "Style spans
have the model and the wrong review granularity."

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-08
- **Last verified:** 2026-09-08
- **Provenance:** authored 2026-09-08 from the spec above and direct inspection of
  `pdomain-book-contracts/pdomain_book_contracts/typography/spans.py`, `labels.py`, `records.py`
  (`TypographyPageRecord`, `Grapheme`, `OcrTokenRef`, and the `_validate_record` /
  `_validate_f2_artifact` / `_validate_alignment_artifacts` validators), `review.py`
  (`TypographySpan`, `WordTypography`, `TypographyCorrection`, `make_word_id`),
  `pdomain_book_contracts/matching/alignment.py` (`project_style_span`, `ProjectedStyleSpan`), and
  `pdomain_book_contracts/text/label_normalization.py`; `pdomain-book-tools`'s
  `pdomain_book_tools/typography/__init__.py` and its `spans.py` / `labels.py` / `records.py` /
  `alignment.py` re-export shims, `pdomain_book_tools/ocr/word.py`, and
  `pdomain_book_tools/ocr/label_normalization.py`; `pdomain-source-data`'s
  `pdomain_source_data/tasks/typography/crops.py` (a live `project_style_span` consumer);
  `pdomain-ocr-labeler-spa`'s `core/typography_review.py`, `api/typography.py`, `api/words.py`
  (`update_word_ground_truth`), `core/persistence/book_labeling_session.py`,
  `core/persistence/labeling_bundle.py`, `core/project_state.py`, `api/dependencies.py`,
  `tests/unit/core/test_typography_review.py`, `tests/unit/api/test_typography_corrections.py`,
  `tests/unit/core/persistence/test_book_labeling_session.py`, its Makefile, and `pyproject.toml`
- **Disposition:** Active. Closes the style-span gap the spec names under "What each level is
  missing." Independent of the region-store plans; touches no region code.
- **Read when:** implementing span-scoped typography review routes, a per-span decision journal, or
  reconciling a grapheme-range annotation with the word-scoped correction system.
- **Search terms:** StyleSpan, StyleSpanDecisionLog, stable_style_span_id, span_id,
  project_style_span, ProjectedStyleSpan, TypographyPageRecord, style_spans, KnowledgeState,
  ImportedTextValidationLog, verified_negative, TypographyCorrectionLog, word-scoped correction.

## Global Constraints

- Python floor is `>=3.13,<3.14` for `pdomain-ocr-labeler-spa`. `make AI=1 <target>` captures
  verbose output to `.ci-ai.log`; run `make AI=1 ci` before committing.
- **Style spans are never edited.** `TypographyPageRecord.style_spans` is immutable
  content addressed by its page's `page_sha256`. Nothing in this plan mutates a `StyleSpan` or
  writes to a page's materialized `page-record.json`; it only records what a person decided about
  one, in a separate journal.
- **A span carries no id of its own.** `StyleSpan` (`pdomain_book_contracts/typography/spans.py`)
  has no `span_id` field, unlike the word-scoped `TypographySpan`. `stable_style_span_id` (Task 1)
  derives one from `page_sha256` plus the span's position and content, so identity is stable across
  reads of the same page content and changes automatically — never silently — the moment that
  content does.
- **The `PagePayload` / `pstate.generation` mutation convention does not apply here.** Every
  mutating route in `api/words.py` (verified against `update_word_ground_truth`) takes the per-page
  lock, bumps `PageState.generation`, persists through the page store, and returns a full
  `PagePayload`. Style spans never enter `PageState.page_record.payload` — they live only in the
  content-addressed `TypographyPageRecord` reached through `state.loaded_labeling_bundle`. The
  existing word-scoped typography routes in the same file (`get_typography_head`,
  `append_typography_correction`) already establish the precedent this plan follows instead: take
  `state.get_page_lock(page_index)` for read/write consistency, but return a small typed response
  with a CAS `head_token`, never a `PagePayload`, and never touch `PageState.generation`.
- **New routes get explicit `operation_id` values.** The spec notes the repository has no
  `operation_id` anywhere and no `generate_unique_id_function`, so FastAPI derives identifiers from
  the function name and a path hash, which change when a route moves — and calls for new routes to
  set one explicitly rather than inherit that instability. This plan's two routes do.
- **Reuse `TypographyCorrectionLog`'s file primitives, don't re-invent them.**
  `ImportedTextValidationLog` (already in `core/typography_review.py`) holds a
  `TypographyCorrectionLog` instance and calls its private `_open_journal_directory`,
  `_open_regular_file`, and `_write_all` directly — an established in-file composition pattern, not
  a cross-module reach into private members. `StyleSpanDecisionLog` (Task 2) follows the same
  pattern, in the same file.
- **`heads_for_page` reads the journal once.** A page can hold many spans (the reason a decision
  store is needed here at all, per the spec's sparse-answer rule). The list route reads the whole
  decision journal once and resolves every span's head in memory, the same shape
  `TypographyCorrectionLog.records()` already uses, rather than reopening the file once per span.

## File Structure

Paths are relative to `pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/`, except the two test
paths, which are relative to `pdomain-ocr-labeler-spa/`.

| file | responsibility |
| --- | --- |
| `core/typography_review.py` | span id helper, `SpanDisposition`, `StyleSpanBinding`, `StyleSpanDecisionLog` |
| `api/typography.py` | span read/write helpers, response models, the two new routes |
| `tests/unit/core/test_typography_review.py` | add unit tests for the span id helper and the decision log |
| `tests/unit/api/test_typography_spans.py` | new: route tests for listing spans, recording decisions |

---

### Task 1: A deterministic identity for an id-less span

`StyleSpan` has no `span_id`. `stable_style_span_id` derives one from the page's content-addressed
`page_sha256` plus the span's own position and content, matching how `stable_page_id` already
derives a page identity in this same file (line 333) rather than trusting a caller-supplied index.

**Files:**

- Edit: `src/pdomain_ocr_labeler_spa/core/typography_review.py`
- Test: `tests/unit/core/test_typography_review.py`

**Interfaces:**

- Produces: `stable_style_span_id(*, page_sha256: str, index: int, label: str, start: int, end:
  int) -> str`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/test_typography_review.py` (extend the existing `from
pdomain_ocr_labeler_spa.core.typography_review import (...)` block with `stable_style_span_id`,
alongside `stable_page_id` and `stable_word_id`):

```python
def test_stable_style_span_id_is_deterministic_and_content_sensitive() -> None:
    first = stable_style_span_id(page_sha256="a" * 64, index=0, label="italic", start=0, end=3)
    again = stable_style_span_id(page_sha256="a" * 64, index=0, label="italic", start=0, end=3)
    assert first == again

    different_page = stable_style_span_id(page_sha256="b" * 64, index=0, label="italic", start=0, end=3)
    different_index = stable_style_span_id(page_sha256="a" * 64, index=1, label="italic", start=0, end=3)
    different_range = stable_style_span_id(page_sha256="a" * 64, index=0, label="italic", start=0, end=4)
    different_label = stable_style_span_id(page_sha256="a" * 64, index=0, label="bold", start=0, end=3)
    assert len({first, different_page, different_index, different_range, different_label}) == 5


def test_stable_style_span_id_rejects_an_empty_range() -> None:
    with pytest.raises(ValueError, match="nonempty half-open"):
        stable_style_span_id(page_sha256="a" * 64, index=0, label="italic", start=3, end=3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/test_typography_review.py -k stable_style_span_id -v`
Expected: FAIL with `NameError: name 'stable_style_span_id' is not defined` (the test file already
imports from `pdomain_ocr_labeler_spa.core.typography_review`, so add `stable_style_span_id` to
that import block before running).

- [ ] **Step 3: Write the implementation**

In `src/pdomain_ocr_labeler_spa/core/typography_review.py`, insert immediately after `stable_page_id`
(which ends at line 337) and before `class TypographyCorrectionLog` (line 340):

```python
_STYLE_SPAN_ID_NAMESPACE = UUID("ec20acdb-b54e-4c68-a38b-837ed06c661f")


def stable_style_span_id(*, page_sha256: str, index: int, label: str, start: int, end: int) -> str:
    """Return a deterministic identity for one immutable page-level style span.

    ``StyleSpan`` carries no id of its own. ``TypographyPageRecord.style_spans`` is reached only
    through its page's content-addressed ``page_sha256``, so combining that hash with the span's
    own position and content produces an id that never collides across pages and changes
    automatically the moment the page record's content does — unlike a bare positional index into
    a list, which a content change can silently renumber underneath it.
    """
    if index < 0:
        raise ValueError("index must be nonnegative")
    if start < 0 or start >= end:
        raise ValueError("style span must be a nonempty half-open grapheme range")
    key = f"{page_sha256}\0{index}\0{label}\0{start}\0{end}"
    return str(uuid5(_STYLE_SPAN_ID_NAMESPACE, key))
```

`UUID` and `uuid5` are already imported at the top of the file (`from uuid import UUID, uuid4,
uuid5`), so no import change is needed for this step.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/test_typography_review.py -k stable_style_span_id -v`
Expected: PASS, both tests.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/typography_review.py tests/unit/core/test_typography_review.py
git commit -m "feat(typography): derive a deterministic id for an id-less style span"
```

---

### Task 2: The span decision journal

A page can hold many style spans, and a reviewer may confirm some and ignore the rest — absence
stays ambiguous unless a rejection is recorded as a fact. `StyleSpanDecisionLog` records a person's
confirm-or-reject verdict per span, CAS-bound the same way `ImportedTextValidationLog` binds a
text-validation verdict per word: no revision-chain lineage (spans have no successors to chain,
unlike `TypographyCorrection`), just a current head and an append that requires the caller to name
the head it saw.

**Files:**

- Edit: `src/pdomain_ocr_labeler_spa/core/typography_review.py`
- Test: `tests/unit/core/test_typography_review.py`

**Interfaces:**

- Consumes: `stable_style_span_id` from Task 1; `KnowledgeState` from `pdomain_book_tools.typography`.
- Produces: `SpanDisposition` (`CONFIRMED`, `REJECTED`), `StyleSpanBinding`,
  `StyleSpanDecisionHead`, `StaleStyleSpanDecisionError`, `unreviewed_style_span_head(binding) ->
  StyleSpanDecisionHead`, and `StyleSpanDecisionLog(project_root, *, corpus_root=None)` with
  `head(binding) -> StyleSpanDecisionHead`, `append(binding, *, disposition, actor, expected_head)
  -> StyleSpanDecisionHead`, and `heads(logical_page_id, page_sha256) -> dict[str,
  StyleSpanDecisionHead]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/test_typography_review.py` (extend the import block with
`SpanDisposition`, `StaleStyleSpanDecisionError`, `StyleSpanBinding`, `StyleSpanDecisionLog`):

```python
def _span_binding(span_id: str = "span-1", page_sha256: str = "a" * 64) -> StyleSpanBinding:
    return StyleSpanBinding(logical_page_id="pgdp:alpha:001.png", page_sha256=page_sha256, span_id=span_id)


def test_a_style_span_starts_unreviewed(tmp_path: Path) -> None:
    log = StyleSpanDecisionLog(tmp_path, corpus_root=tmp_path)
    head = log.head(_span_binding())
    assert head.disposition is None
    assert head.revision == 0


def test_confirming_a_span_is_persistent_and_cas_bound(tmp_path: Path) -> None:
    log = StyleSpanDecisionLog(tmp_path, corpus_root=tmp_path)
    head = log.head(_span_binding())

    saved = log.append(
        _span_binding(), disposition=SpanDisposition.CONFIRMED, actor="local", expected_head=head.head_token
    )

    assert saved.disposition is SpanDisposition.CONFIRMED
    assert StyleSpanDecisionLog(tmp_path, corpus_root=tmp_path).head(_span_binding()) == saved
    with pytest.raises(StaleStyleSpanDecisionError):
        log.append(_span_binding(), disposition=SpanDisposition.REJECTED, actor="local", expected_head=head.head_token)


def test_a_rejection_is_distinguishable_from_never_looking(tmp_path: Path) -> None:
    log = StyleSpanDecisionLog(tmp_path, corpus_root=tmp_path)
    unreviewed = log.head(_span_binding("span-unreviewed"))
    rejected_head = log.head(_span_binding("span-rejected"))

    log.append(
        _span_binding("span-rejected"),
        disposition=SpanDisposition.REJECTED,
        actor="local",
        expected_head=rejected_head.head_token,
    )

    assert unreviewed.disposition is None
    assert log.head(_span_binding("span-rejected")).disposition is SpanDisposition.REJECTED


def test_a_change_of_mind_advances_the_revision_and_both_decisions_stay_on_disk(tmp_path: Path) -> None:
    log = StyleSpanDecisionLog(tmp_path, corpus_root=tmp_path)
    binding = _span_binding()

    first = log.append(
        binding, disposition=SpanDisposition.REJECTED, actor="local", expected_head=log.head(binding).head_token
    )
    second = log.append(
        binding, disposition=SpanDisposition.CONFIRMED, actor="local", expected_head=first.head_token
    )

    assert second.revision == first.revision + 1
    assert second.disposition is SpanDisposition.CONFIRMED
    lines = (tmp_path / ".pd-pages" / "style-span-decisions.jsonl").read_text().splitlines()
    assert len(lines) == 2


def test_decisions_from_different_pages_do_not_collide(tmp_path: Path) -> None:
    log = StyleSpanDecisionLog(tmp_path, corpus_root=tmp_path)
    page_a = _span_binding(page_sha256="a" * 64)
    page_b = _span_binding(page_sha256="b" * 64)

    log.append(page_a, disposition=SpanDisposition.CONFIRMED, actor="local", expected_head=log.head(page_a).head_token)

    assert log.head(page_b).disposition is None


def test_heads_reads_the_journal_once_for_a_whole_page(tmp_path: Path) -> None:
    log = StyleSpanDecisionLog(tmp_path, corpus_root=tmp_path)
    first = _span_binding("span-1")
    second = _span_binding("span-2")
    log.append(first, disposition=SpanDisposition.CONFIRMED, actor="local", expected_head=log.head(first).head_token)
    log.append(second, disposition=SpanDisposition.REJECTED, actor="local", expected_head=log.head(second).head_token)

    heads = log.heads("pgdp:alpha:001.png", "a" * 64)

    assert heads["span-1"].disposition is SpanDisposition.CONFIRMED
    assert heads["span-2"].disposition is SpanDisposition.REJECTED
    assert "span-missing" not in heads
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/test_typography_review.py -k StyleSpanDecisionLog -v`
Expected: FAIL with `NameError` / `ImportError` for the not-yet-defined names.

- [ ] **Step 3: Write the implementation**

In `src/pdomain_ocr_labeler_spa/core/typography_review.py`:

- Add `from enum import StrEnum` to the imports (the file currently has none; `StrEnum` is only
  used by the new `SpanDisposition`).
- Add `KnowledgeState` to the existing `from pdomain_book_tools.typography import (...)` block, so
  it reads:

```python
from pdomain_book_tools.typography import (
    CoordinateTransform,
    KnowledgeState,
    ModelRun,
    PageGeometry,
    ReplacementArtifact,
    TypographyCorrection,
    WordGeometry,
    make_word_id,
)
```

- Insert the following after the `stable_style_span_id` function from Task 1 and before `class
  TypographyCorrectionLog`:

```python
class SpanDisposition(StrEnum):
    """What a person decided about one immutable page-level style span."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"

    @property
    def knowledge_state(self) -> KnowledgeState:
        """The knowledge state this disposition asserts about the span."""
        if self is SpanDisposition.REJECTED:
            return KnowledgeState.VERIFIED_NEGATIVE
        return KnowledgeState.POSITIVE


class StyleSpanBinding(BaseModel):
    """Exact immutable page and span identity presented for span review."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    logical_page_id: str
    page_sha256: str = Field(min_length=64, max_length=64)
    span_id: str


class StaleStyleSpanDecisionError(ValueError):
    """A span decision was based on a head no longer current."""


class StyleSpanDecisionHead(BaseModel):
    """Current persistent review decision for one immutable page-level style span."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    binding: StyleSpanBinding
    revision: int = Field(ge=0)
    disposition: SpanDisposition | None
    actor: str | None
    decided_at: str | None
    head_token: str = Field(min_length=64, max_length=64)


def unreviewed_style_span_head(binding: StyleSpanBinding) -> StyleSpanDecisionHead:
    """Return the head an unreviewed span has, with no journal read required."""
    return StyleSpanDecisionHead(
        binding=binding,
        revision=0,
        disposition=None,
        actor=None,
        decided_at=None,
        head_token=StyleSpanDecisionLog._token(binding, revision=0, disposition=None),
    )


@final
class StyleSpanDecisionLog:
    """Project-local JSONL journal of what a person decided about each style span.

    A style span in ``TypographyPageRecord.style_spans`` is immutable and reached only through its
    page's content-addressed ``page_sha256`` (see ``stable_style_span_id``). This journal never
    edits a span; it records a person's confirm-or-reject verdict beside it, so an unreviewed span
    and a rejected span stay distinguishable. It reuses ``TypographyCorrectionLog``'s file
    primitives exactly as ``ImportedTextValidationLog`` above does, and drops that log's
    activation/occurrence step: a span's id already changes the moment its page's content does, so
    there is no separate occurrence to track.
    """

    _NAME: ClassVar[str] = "style-span-decisions.jsonl"
    _RECOVERY_NAME: ClassVar[str] = "style-span-decisions.recovery.jsonl"

    def __init__(self, project_root: Path, *, corpus_root: Path | None = None) -> None:
        self._files = TypographyCorrectionLog(project_root, corpus_root=corpus_root)
        self.path = self._files.path.with_name(self._NAME)

    @staticmethod
    def _token(binding: StyleSpanBinding, *, revision: int, disposition: SpanDisposition | None) -> str:
        payload = {
            "binding": binding.model_dump(mode="json"),
            "revision": revision,
            "disposition": disposition.value if disposition is not None else None,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def head(self, binding: StyleSpanBinding) -> StyleSpanDecisionHead:
        """Return the current head for one span, unreviewed if nothing was ever appended."""
        parent, descriptor = self._open(create=True)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH)
            rows = self._read(descriptor, parent=parent)
        finally:
            os.close(descriptor)
            os.close(parent)
        return self._head(rows, binding)

    def append(
        self, binding: StyleSpanBinding, *, disposition: SpanDisposition, actor: str, expected_head: str
    ) -> StyleSpanDecisionHead:
        """CAS-append one confirm-or-reject decision against the current head."""
        parent, descriptor = self._open(create=True)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            rows = self._read(descriptor, parent=parent)
            current = self._head(rows, binding)
            if current.head_token != expected_head:
                raise StaleStyleSpanDecisionError("expected_head is not current")
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

    def heads(self, logical_page_id: str, page_sha256: str) -> dict[str, StyleSpanDecisionHead]:
        """Return the current head for every span decided so far on one page.

        One read of the whole journal, resolved in memory, rather than reopening the file once per
        span — the shape a page-level span list needs.
        """
        parent, descriptor = self._open(create=True)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH)
            rows = self._read(descriptor, parent=parent)
        finally:
            os.close(descriptor)
            os.close(parent)
        by_span: dict[str, dict[str, object]] = {}
        for row in rows:
            binding_raw = row.get("binding")
            if not isinstance(binding_raw, dict):
                continue
            if binding_raw.get("logical_page_id") != logical_page_id or binding_raw.get("page_sha256") != page_sha256:
                continue
            span_id = binding_raw.get("span_id")
            if isinstance(span_id, str):
                by_span[span_id] = row
        heads: dict[str, StyleSpanDecisionHead] = {}
        for span_id, row in by_span.items():
            binding = StyleSpanBinding.model_validate(row["binding"])
            heads[span_id] = self._make_head(
                binding,
                int(row["revision"]),  # type: ignore[arg-type]
                SpanDisposition(row["disposition"]),  # type: ignore[arg-type]
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
            raise ValueError("invalid style span decision journal record")
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
                descriptor, (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
            )
            os.fsync(descriptor)
            if created:
                os.fsync(parent)
        finally:
            os.close(descriptor)

    def _append_row(self, descriptor: int, row: object) -> None:
        payload = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self._files._write_all(descriptor, payload)

    def _head(self, rows: list[dict[str, object]], binding: StyleSpanBinding) -> StyleSpanDecisionHead:
        for row in reversed(rows):
            binding_raw = row.get("binding")
            if not isinstance(binding_raw, dict):
                continue
            try:
                candidate = StyleSpanBinding.model_validate(binding_raw)
            except ValueError:
                continue
            if candidate == binding:
                revision = row.get("revision")
                disposition = row.get("disposition")
                decided_at = row.get("decided_at")
                actor = row.get("actor")
                if isinstance(revision, int) and isinstance(disposition, str) and isinstance(decided_at, str):
                    return self._make_head(binding, revision, SpanDisposition(disposition), str(actor), decided_at)
        return self._make_head(binding, 0, None, None, None)

    def _make_head(
        self,
        binding: StyleSpanBinding,
        revision: int,
        disposition: SpanDisposition | None,
        actor: str | None,
        decided_at: str | None,
    ) -> StyleSpanDecisionHead:
        return StyleSpanDecisionHead(
            binding=binding,
            revision=revision,
            disposition=disposition,
            actor=actor,
            decided_at=decided_at,
            head_token=self._token(binding, revision=revision, disposition=disposition),
        )
```

- Add `"SpanDisposition"`, `"StaleStyleSpanDecisionError"`, `"StyleSpanBinding"`,
  `"StyleSpanDecisionHead"`, `"StyleSpanDecisionLog"`, `"stable_style_span_id"`, and
  `"unreviewed_style_span_head"` to the `__all__` list at the bottom of the file.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/test_typography_review.py -v`
Expected: PASS, including every pre-existing test in the file (no regression).

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/typography_review.py tests/unit/core/test_typography_review.py
git commit -m "feat(typography): add the per-span confirm/reject decision journal"
```

---

### Task 3: List a page's style spans

The read route surfaces every span on a page plus its current decision, and — because a span is a
grapheme range that can cross word boundaries — which OCR tokens it overlaps. That overlap is
read-only display metadata computed with the existing `project_style_span` alignment utility
(already used by `pdomain-source-data`'s crop-synthesis task); it is never merged into
`stable_word_id`, the identity the word-scoped correction routes above use.

**Files:**

- Edit: `src/pdomain_ocr_labeler_spa/api/typography.py`
- Test: `tests/unit/api/test_typography_spans.py`

**Interfaces:**

- Consumes: `stable_style_span_id`, `SpanDisposition`, `StyleSpanBinding`, `StyleSpanDecisionLog`,
  `unreviewed_style_span_head` from Task 2; `project_style_span`, `TypographyPageRecord`,
  `StyleSpan`, `OcrTokenRef` from `pdomain_book_tools.typography`.
- Produces: `GET
  /api/projects/{project_id}/pages/{page_index}/typography/spans -> StyleSpanListResponse`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/api/test_typography_spans.py`:

```python
"""Unit tests for the page-level style span review routes."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pdomain_book_tools.geometry import BoundingBox, Point
from pdomain_book_tools.typography import (
    REVIEW_CONTRACT_VERSION,
    TYPOGRAPHY_PAGE_RECORD_LEGACY_SCHEMA_VERSION,
    AlignmentEvidence,
    ArtifactReference,
    ArtifactRef,
    ArtifactSource,
    ConfidenceTier,
    Grapheme,
    KnowledgeState,
    LabelSource,
    LabelingBundle,
    OcrTokenRef,
    SourceCoordinateSpace,
    StyleLabel,
    StyleSpan,
    TargetCoordinateSpace,
    TextIdentity,
    TypographyPageRecord,
)

from pdomain_ocr_labeler_spa.api.typography import TYPOGRAPHY_TAXONOMY
from pdomain_ocr_labeler_spa.bootstrap import build_app
from pdomain_ocr_labeler_spa.core.models import Project
from pdomain_ocr_labeler_spa.core.persistence.labeling_bundle import LoadedLabelingBundle
from pdomain_ocr_labeler_spa.core.typography_review import stable_page_id
from pdomain_ocr_labeler_spa.settings import Settings


def _artifact(*, sha256: str) -> ArtifactRef:
    return ArtifactRef(
        source=ArtifactSource.HUMAN,
        source_url=None,
        local_path="fixture.bin",
        retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
        sha256=sha256,
        version="1",
        license_ref=None,
    )


def _page_record(*, page_id: str, image_sha256: str) -> TypographyPageRecord:
    """A two-word page, ``"AB CD"``, with one italic span crossing both words."""
    text_artifact_sha256 = hashlib.sha256(b"fixture-text-artifact").hexdigest()
    graphemes = tuple(
        Grapheme(index=index, text=character, source_slices=(), normalized_from=None)
        for index, character in enumerate("AB CD")
    )
    alignment = AlignmentEvidence(
        alignment_id="align-1",
        method="exact",
        source_artifact_sha256=text_artifact_sha256,
        target_artifact_sha256=image_sha256,
        source_coordinate_space=SourceCoordinateSpace.SOURCE_GRAPHEMES,
        target_coordinate_space=TargetCoordinateSpace.OCR_GRAPHEMES,
        source_range=(0, 5),
        target_range=(0, 4),
        operations=(),
        score=1.0,
        margin=None,
        alternatives=(),
        accepted=True,
    )
    ocr_tokens = (
        OcrTokenRef(
            token_id="t0",
            text="AB",
            confidence=1.0,
            bbox=BoundingBox(
                top_left=Point(0, 0, is_normalized=False), bottom_right=Point(10, 10, is_normalized=False)
            ),
            line_id="line-1",
            grapheme_start=0,
            grapheme_end=2,
            alignment_id="align-1",
        ),
        OcrTokenRef(
            token_id="t1",
            text="CD",
            confidence=1.0,
            bbox=BoundingBox(
                top_left=Point(20, 0, is_normalized=False), bottom_right=Point(30, 10, is_normalized=False)
            ),
            line_id="line-1",
            grapheme_start=3,
            grapheme_end=5,
            alignment_id="align-1",
        ),
    )
    style_span = StyleSpan(
        label=StyleLabel.ITALIC,
        start=1,
        end=4,
        state=KnowledgeState.POSITIVE,
        label_source=LabelSource.F2,
        confidence_tier=ConfidenceTier.GOLD,
        source_slices=(),
        rule_ref="fixture",
        semantic_reason=None,
        warnings=(),
    )
    return TypographyPageRecord(
        schema_version=TYPOGRAPHY_PAGE_RECORD_LEGACY_SCHEMA_VERSION,
        identity=TextIdentity(
            work_id="work",
            edition_id="edition",
            book_id="book",
            project_id="alpha",
            pg_ebook_id=None,
            se_repository=None,
            page_id=page_id,
            image_artifact=_artifact(sha256=image_sha256),
            text_artifacts=(_artifact(sha256=text_artifact_sha256),),
        ),
        original_f2_artifact_base64=None,
        original_f2_artifact_sha256=None,
        external_f2_artifact=None,
        f2_page_key=None,
        f2_page_value_lexical_byte_range=None,
        f2_decoded_page_utf8_sha256=None,
        parsed_text="AB CD",
        graphemes=graphemes,
        ocr_tokens=ocr_tokens,
        style_spans=(style_span,),
        structural_context=("body",),
        parser_warnings=(),
        alignments=(alignment,),
        project_comments_artifact=None,
        guideline_version="fixture",
    )


def _client_with_style_spans(tmp_path: Path) -> tuple[TestClient, str, str]:
    project_root = tmp_path / "alpha"
    project_root.mkdir()
    image = project_root / "page001.png"
    image.write_bytes(b"image-bytes")
    image_sha256 = hashlib.sha256(image.read_bytes()).hexdigest()
    project_id = "alpha"
    page_id = stable_page_id(project_id=project_id, page_index=0)
    page_record = _page_record(page_id=page_id, image_sha256=image_sha256)
    page_record_bytes = page_record.model_dump_json().encode()
    page_sha256 = hashlib.sha256(page_record_bytes).hexdigest()

    app = build_app(Settings(mode="api_only", data_root=tmp_path / "data"))
    project = Project(
        project_id=project_id,
        project_root=project_root,
        image_paths=[image],
        ground_truth_map={image.name: "AB CD"},
        total_pages=1,
    )
    bundle = LabelingBundle(
        schema_version=REVIEW_CONTRACT_VERSION,
        configuration_hash="c" * 64,
        taxonomy=TYPOGRAPHY_TAXONOMY,
        page_id=page_id,
        page_sha256=page_sha256,
        image_sha256=image_sha256,
        text_sha256=hashlib.sha256(b"AB CD").hexdigest(),
        page_head_sha256=hashlib.sha256(b"head").hexdigest(),
        artifacts=(
            ArtifactReference(
                artifact_id="page_record",
                relative_path="page-record.json",
                sha256=page_sha256,
                media_type="application/json",
            ),
        ),
        words=(),
    )
    loaded = LoadedLabelingBundle(
        root=project_root,
        bundle=bundle,
        artifact_paths={"page_record": project_root / "page-record.json"},
        artifact_payloads={"page_record": page_record_bytes},
        image_descriptor=os.open(image, os.O_RDONLY),
    )
    app.state.project_state.set_loaded_project(project, labeling_bundle=loaded)
    app.state.active_project_carrier.set_active_project(project_root)
    return TestClient(app), project_id, page_id


def _client_without_bundle(tmp_path: Path) -> tuple[TestClient, str]:
    project_root = tmp_path / "alpha"
    project_root.mkdir()
    image = project_root / "page001.png"
    image.write_bytes(b"image-bytes")
    project_id = "alpha"
    app = build_app(Settings(mode="api_only", data_root=tmp_path / "data"))
    app.state.project_state.set_loaded_project(
        Project(
            project_id=project_id, project_root=project_root, image_paths=[image], ground_truth_map={}, total_pages=1
        )
    )
    app.state.active_project_carrier.set_active_project(project_root)
    return TestClient(app), project_id


def test_list_style_spans_reports_word_boundary_crossing_and_default_disposition(tmp_path: Path) -> None:
    client, project_id, page_id = _client_with_style_spans(tmp_path)

    response = client.get(f"/api/projects/{project_id}/pages/0/typography/spans")

    assert response.status_code == 200
    body = response.json()
    assert body["logical_page_id"] == page_id
    assert len(body["spans"]) == 1
    span = body["spans"][0]
    assert span["label"] == "italic"
    assert span["text"] == "B C"
    assert span["disposition"] is None
    assert sorted(span["overlapping_ocr_token_ids"]) == ["t0", "t1"]
    assert body["unreviewed_count"] == 1
    assert body["confirmed_count"] == 0
    assert body["rejected_count"] == 0


def test_list_style_spans_requires_a_loaded_labeling_bundle(tmp_path: Path) -> None:
    client, project_id = _client_without_bundle(tmp_path)

    response = client.get(f"/api/projects/{project_id}/pages/0/typography/spans")

    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/api/test_typography_spans.py -v`
Expected: FAIL — `404` becomes the route-not-found response (no such route yet), so
`test_list_style_spans_reports_word_boundary_crossing_and_default_disposition` fails its
`assert response.status_code == 200`.

- [ ] **Step 3: Write the implementation**

In `src/pdomain_ocr_labeler_spa/api/typography.py`:

- Update the `from pdomain_book_tools.typography import (...)` block (lines 13-34) to add
  `ConfidenceTier`, `KnowledgeState`, `LabelSource`, `OcrTokenRef`, `StyleSpan`,
  `TypographyPageRecord`, and `project_style_span`, keeping the existing alphabetical grouping
  (constants, then classes, then functions):

```python
from pdomain_book_tools.typography import (
    GRAPHEME_SEGMENTATION_VERSION,
    REVIEW_CONTRACT_VERSION,
    ConfidenceTier,
    CoordinateTransform,
    CorrectionBundle,
    CorrectionDecision,
    KnowledgeState,
    LabelSource,
    LabelingBundle,
    LabelState,
    ModelRun,
    OcrTokenRef,
    PageGeometry,
    ReplacementArtifact,
    ReviewState,
    StyleLabel,
    StyleSpan,
    TypographyCorrection,
    TypographyPageRecord,
    TypographyReviewMetadata,
    TypographySpan,
    TypographyTaxonomy,
    TypographyTaxonomyLabel,
    WordGeometry,
    WordTypography,
    project_style_span,
    split_graphemes,
)
```

- Add `SpanDisposition`, `StyleSpanBinding`, `StyleSpanDecisionLog`, `stable_style_span_id`, and
  `unreviewed_style_span_head` to the existing `from ..core.typography_review import (...)` block
  (lines 39-50).
- Insert the following immediately before `def install_typography_router` (currently line 1331),
  after `export_typography_correction_bundle`:

```python
def _style_span_page_record(state: ProjectState) -> TypographyPageRecord | None:
    """Return the page's immutable typography record, if a labeling bundle is loaded.

    Style spans live only in ``TypographyPageRecord.style_spans``. ``BookLabelingSession``
    validates that record on every page load but never retains it on ``LoadedLabelingBundle``
    (``core/persistence/book_labeling_session.py`` ``_load_page_at`` / ``_load_page_record``). The
    verified bytes survive as the ``"page_record"`` entry in ``artifact_payloads`` — the same
    artifact id ``_validate_primary_page_artifacts`` pins against ``bundle.page_sha256`` before a
    page is ever cached — so re-parsing them here re-trusts nothing new.
    """
    loaded = state.loaded_labeling_bundle
    if loaded is None:
        return None
    payload = loaded.artifact_payloads.get("page_record")
    if payload is None:
        return None
    return TypographyPageRecord.model_validate_json(payload)


def _style_span_text(page_record: TypographyPageRecord, start: int, end: int) -> str:
    graphemes_by_index = {grapheme.index: grapheme.text for grapheme in page_record.graphemes}
    return "".join(graphemes_by_index.get(index, "") for index in range(start, end))


def _style_span_token_ids(page_record: TypographyPageRecord, span_id: str, span: StyleSpan) -> tuple[str, ...]:
    """Read-only OCR-token overlap for one span, computed with the existing alignment utility.

    ``token_id`` here names a ``TypographyPageRecord.ocr_tokens`` entry, an id space local to this
    page record — never a ``stable_word_id`` from the word-scoped typography routes above. This is
    display metadata for a reviewer, not a join key into the word-scoped correction system.
    """
    projections = project_style_span(span, source_span_id=span_id, tokens=page_record.ocr_tokens)
    seen: dict[str, None] = {}
    for projection in projections:
        seen.setdefault(projection.token_id, None)
    return tuple(seen)


class StyleSpanEntry(BaseModel):
    """One page-level style span, its evidence, and its current review decision."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    span_id: str
    label: StyleLabel
    start: int
    end: int
    text: str
    state: KnowledgeState
    label_source: LabelSource
    confidence_tier: ConfidenceTier
    rule_ref: str | None
    semantic_reason: str | None
    warnings: tuple[str, ...]
    overlapping_ocr_token_ids: tuple[str, ...]
    disposition: SpanDisposition | None
    decision_revision: int
    decision_actor: str | None
    decision_at: str | None
    head_token: str


class StyleSpanListResponse(BaseModel):
    """Every style span on one page, with its current review disposition."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    page_index: int
    logical_page_id: str
    page_sha256: str
    spans: tuple[StyleSpanEntry, ...]
    confirmed_count: int
    rejected_count: int
    unreviewed_count: int


def _style_span_entries(
    project: Project, page_index: int, state: ProjectState
) -> tuple[str, str, tuple[StyleSpanEntry, ...]]:
    page_record = _style_span_page_record(state)
    bundle = state.labeling_bundle
    if page_record is None or bundle is None:
        raise HTTPException(status_code=404, detail="style spans require a loaded labeling bundle")
    logical_page_id = _logical_page_id(project, page_index, state)
    log = StyleSpanDecisionLog(project.project_root, corpus_root=project.project_root.parent)
    heads = log.heads(logical_page_id, bundle.page_sha256)
    entries: list[StyleSpanEntry] = []
    for index, span in enumerate(page_record.style_spans):
        span_id = stable_style_span_id(
            page_sha256=bundle.page_sha256, index=index, label=span.label.value, start=span.start, end=span.end
        )
        head = heads.get(span_id) or unreviewed_style_span_head(
            StyleSpanBinding(logical_page_id=logical_page_id, page_sha256=bundle.page_sha256, span_id=span_id)
        )
        entries.append(
            StyleSpanEntry(
                span_id=span_id,
                label=span.label,
                start=span.start,
                end=span.end,
                text=_style_span_text(page_record, span.start, span.end),
                state=span.state,
                label_source=span.label_source,
                confidence_tier=span.confidence_tier,
                rule_ref=span.rule_ref,
                semantic_reason=span.semantic_reason,
                warnings=span.warnings,
                overlapping_ocr_token_ids=_style_span_token_ids(page_record, span_id, span),
                disposition=head.disposition,
                decision_revision=head.revision,
                decision_actor=head.actor,
                decision_at=head.decided_at,
                head_token=head.head_token,
            )
        )
    return logical_page_id, bundle.page_sha256, tuple(entries)


@router.get(
    "/api/projects/{project_id}/pages/{page_index}/typography/spans",
    response_model=StyleSpanListResponse,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="list_style_spans",
)
def list_style_spans(
    project_id: str,
    page_index: int,
    state: ProjectState = Depends(get_project_state),
) -> StyleSpanListResponse:
    """Return every page-level style span and its current review decision."""
    project = _project_page(project_id, page_index, state)
    with state.get_page_lock(page_index):
        logical_page_id, page_sha256, entries = _style_span_entries(project, page_index, state)
    confirmed = sum(1 for entry in entries if entry.disposition is SpanDisposition.CONFIRMED)
    rejected = sum(1 for entry in entries if entry.disposition is SpanDisposition.REJECTED)
    return StyleSpanListResponse(
        project_id=project_id,
        page_index=page_index,
        logical_page_id=logical_page_id,
        page_sha256=page_sha256,
        spans=entries,
        confirmed_count=confirmed,
        rejected_count=rejected,
        unreviewed_count=len(entries) - confirmed - rejected,
    )
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/api/test_typography_spans.py -v`
Expected: PASS, both tests.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/api/typography.py tests/unit/api/test_typography_spans.py
git commit -m "feat(typography): list page-level style spans with their review decisions"
```

---

### Task 4: Record a span decision

The write route lets a person confirm or reject one span. It never edits
`TypographyPageRecord.style_spans` and never touches `TypographyCorrectionLog`, the word-scoped
correction journal above — a direct test proves the two journals stay independent files that
neither route reads from nor writes to the other.

**Files:**

- Edit: `src/pdomain_ocr_labeler_spa/api/typography.py`
- Test: `tests/unit/api/test_typography_spans.py`

**Interfaces:**

- Consumes: `StyleSpanBinding`, `StyleSpanDecisionLog`, `StaleStyleSpanDecisionError`,
  `SpanDisposition`, `stable_style_span_id` from Task 2 / Task 3.
- Produces: `POST
  /api/projects/{project_id}/pages/{page_index}/typography/spans/{span_id}/decisions ->
  StyleSpanDecisionResponse`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/api/test_typography_spans.py` (add `TypographyCorrectionLog` to the
`pdomain_ocr_labeler_spa.core.typography_review` import):

```python
def test_confirming_a_span_persists_and_is_reflected_in_the_list(tmp_path: Path) -> None:
    client, project_id, _page_id = _client_with_style_spans(tmp_path)
    listed = client.get(f"/api/projects/{project_id}/pages/0/typography/spans").json()
    span_id = listed["spans"][0]["span_id"]
    head_token = listed["spans"][0]["head_token"]

    response = client.post(
        f"/api/projects/{project_id}/pages/0/typography/spans/{span_id}/decisions",
        json={"expected_head": head_token, "disposition": "confirmed", "labeler_id": "reviewer-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["disposition"] == "confirmed"
    assert body["revision"] == 1

    relisted = client.get(f"/api/projects/{project_id}/pages/0/typography/spans").json()
    assert relisted["spans"][0]["disposition"] == "confirmed"
    assert relisted["confirmed_count"] == 1


def test_a_stale_decision_head_is_rejected_with_409(tmp_path: Path) -> None:
    client, project_id, _page_id = _client_with_style_spans(tmp_path)
    listed = client.get(f"/api/projects/{project_id}/pages/0/typography/spans").json()
    span_id = listed["spans"][0]["span_id"]
    head_token = listed["spans"][0]["head_token"]
    decision_url = f"/api/projects/{project_id}/pages/0/typography/spans/{span_id}/decisions"

    client.post(decision_url, json={"expected_head": head_token, "disposition": "rejected", "labeler_id": "reviewer-1"})
    stale = client.post(
        decision_url, json={"expected_head": head_token, "disposition": "confirmed", "labeler_id": "reviewer-1"}
    )

    assert stale.status_code == 409


def test_an_unknown_span_id_is_a_404(tmp_path: Path) -> None:
    client, project_id, _page_id = _client_with_style_spans(tmp_path)

    response = client.post(
        f"/api/projects/{project_id}/pages/0/typography/spans/not-a-real-span/decisions",
        json={"expected_head": "a" * 64, "disposition": "confirmed", "labeler_id": "reviewer-1"},
    )

    assert response.status_code == 404


def test_deciding_a_span_never_touches_the_word_scoped_correction_log(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.typography_review import TypographyCorrectionLog

    client, project_id, page_id = _client_with_style_spans(tmp_path)
    listed = client.get(f"/api/projects/{project_id}/pages/0/typography/spans").json()
    span_id = listed["spans"][0]["span_id"]
    head_token = listed["spans"][0]["head_token"]
    project = client.app.state.project_state.loaded_project  # type: ignore[attr-defined]
    project_root = project.project_root
    word_log = TypographyCorrectionLog(project_root, corpus_root=project_root.parent)
    before = word_log.records(page_id)

    client.post(
        f"/api/projects/{project_id}/pages/0/typography/spans/{span_id}/decisions",
        json={"expected_head": head_token, "disposition": "confirmed", "labeler_id": "reviewer-1"},
    )

    assert word_log.records(page_id) == before == ()
    span_decisions_path = project_root / ".pd-pages" / "style-span-decisions.jsonl"
    word_corrections_path = project_root / ".pd-pages" / "typography-corrections.jsonl"
    assert span_decisions_path.exists()
    assert not word_corrections_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/api/test_typography_spans.py -v`
Expected: FAIL — the four new tests get `404` (route not found) instead of the expected `200` /
`409` / `404`-for-unknown-span responses.

- [ ] **Step 3: Write the implementation**

Add `StaleStyleSpanDecisionError` to the `from ..core.typography_review import (...)` block updated
in Task 3. Insert the following immediately after the `list_style_spans` route from Task 3:

```python
class StyleSpanDecisionSubmission(BaseModel):
    """Confirm-or-reject intent against the current span decision head."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    expected_head: str = Field(min_length=64, max_length=64)
    disposition: Literal["confirmed", "rejected"]
    labeler_id: str = "local"


class StyleSpanDecisionResponse(BaseModel):
    """Current review decision for one page-level style span."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    page_index: int
    span_id: str
    disposition: SpanDisposition | None
    revision: int
    actor: str | None
    decided_at: str | None
    head_token: str


@router.post(
    "/api/projects/{project_id}/pages/{page_index}/typography/spans/{span_id}/decisions",
    response_model=StyleSpanDecisionResponse,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="record_style_span_decision",
)
def record_style_span_decision(
    project_id: str,
    page_index: int,
    span_id: str,
    submission: StyleSpanDecisionSubmission,
    state: ProjectState = Depends(get_project_state),
) -> StyleSpanDecisionResponse:
    """Append a person's confirm-or-reject verdict for one immutable style span.

    This never edits ``TypographyPageRecord.style_spans`` and never touches
    ``TypographyCorrectionLog``, the word-scoped correction journal above: a span review is a
    separate decision, recorded in its own journal, about a page-level source artifact that a
    word-scoped correction never reads.
    """
    project = _project_page(project_id, page_index, state)
    page_record = _style_span_page_record(state)
    bundle = state.labeling_bundle
    if page_record is None or bundle is None:
        raise HTTPException(status_code=404, detail="style spans require a loaded labeling bundle")
    with state.get_page_lock(page_index):
        logical_page_id = _logical_page_id(project, page_index, state)
        known_span_ids = {
            stable_style_span_id(
                page_sha256=bundle.page_sha256, index=index, label=span.label.value, start=span.start, end=span.end
            )
            for index, span in enumerate(page_record.style_spans)
        }
        if span_id not in known_span_ids:
            raise HTTPException(status_code=404, detail="span not found on page")
        binding = StyleSpanBinding(logical_page_id=logical_page_id, page_sha256=bundle.page_sha256, span_id=span_id)
        log = StyleSpanDecisionLog(project.project_root, corpus_root=project.project_root.parent)
        try:
            head = log.append(
                binding,
                disposition=SpanDisposition(submission.disposition),
                actor=submission.labeler_id,
                expected_head=submission.expected_head,
            )
        except StaleStyleSpanDecisionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return StyleSpanDecisionResponse(
            project_id=project_id,
            page_index=page_index,
            span_id=span_id,
            disposition=head.disposition,
            revision=head.revision,
            actor=head.actor,
            decided_at=head.decided_at,
            head_token=head.head_token,
        )
```

- [ ] **Step 4: Run the tests, the fast suite, and the gate**

Run: `uv run pytest tests/unit/api/test_typography_spans.py -v`
Expected: PASS, all six tests in the file.

Run: `make AI=1 test`
Expected: PASS with no regression in the existing typography test files.

Run: `make AI=1 ci`
Expected: PASS. `openapi-export` regenerates `frontend/src/api/types.ts` with the two new routes;
include that regenerated file in the commit.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/api/typography.py tests/unit/api/test_typography_spans.py \
  frontend/src/api/types.ts
git commit -m "feat(typography): record and enforce CAS-bound style span decisions"
```

---

## What this plan does not do

- It adds no UI. The two routes are a server-authoritative review surface; a labeler screen that
  renders spans and calls them is separate front-end work.
- It does not change what `BookLabelingSession` retains. `TypographyPageRecord` is re-derived from
  already-hash-verified bytes on every read rather than cached on `LoadedLabelingBundle`; caching it
  there, if warranted, is a separate change with its own performance case to make.
- It does not extend `Word.text_style_labels` / `Word.text_style_label_scopes`, and it does not
  touch the `{"whole", "part"}` scope vocabulary. That is a within-word qualifier on a different
  model; `StyleSpan` is the phrase-crossing mechanism, and the two stay separate.
- It does not merge span review into `TypographyCorrectionLog` or `stable_word_id`. The overlap a
  span reports is read-only OCR-token metadata for display, not a join key, and Task 4 tests the
  boundary directly.
- It does not build a page-kind or region proposal/decision pipeline. Those are separate annotation
  levels under the same spec, with their own open plans.
- It does not batch-confirm spans or add a review-progress rollup beyond the three counts on
  `StyleSpanListResponse`. A worklist-style completion gate, if wanted, is separate follow-up work
  once a UI exists to drive it.

## Related

- [Annotation provenance and
  persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) — the design this
  plan implements one slice of.
- [Region vocabulary](../specs/2026-09-07-region-vocabulary-design.md) — the sibling annotation
  level with the same eight-property bar; unrelated code.
- [Region stores and resolver](2026-09-08-region-stores-and-resolver.md) — the plan-format template
  this document matches; independent work, no shared files.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — the seven slices this plan is
  part of.
