# PGDP Source-Line Alignment Implementation Plan

## Agent Index

- **Kind:** plan
- **Status:** partial
- **Owner:** CT
- **Created:** 2026-08-23
- **Last verified:** 2026-08-24
- **Provenance:** implementation, tests, and the 2026-08-24 five-book corpus review
- **Disposition:** Active executable plan for the second M15 scan-measurement slice.
- **Read when:** implementing or reviewing conservative PGDP source-line alignment.
- **Search terms:** PGDP, M15b, F2 tokenizer, line candidate, gutter, dynamic programming, alignment.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local `align-pgdp` command that conservatively aligns lossless F2 source lines with
source-frame scan line candidates on eligible single-column pages.

**Architecture:** Tokenize F2 into byte-addressed source records, extract two-dimensional line
candidates, and align both ordered sequences with deterministic monotone dynamic programming. Write
the evidence into a separate `pgdp-alignment/v1` report. Keep rectification and typographic fitting
for later milestones.

**Tech Stack:** Python 3.13, frozen dataclasses, Pydantic, Pillow, NumPy, argparse, pytest, Ruff,
basedpyright, JSON Schema.

---

## Goal

Produce precision-first source-line alignment that preserves the evidence required for later scan
measurement.

## Architecture

Keep source normalization, formatting spans, image candidates, sequence alignment, wire records,
orchestration, and CLI wiring in focused modules.

Read M15a profiles as the page selection and scan snapshot. Reuse the atomic report writer without
modifying earlier report formats.

## Tech Stack

Use only the repository's installed Python, Pydantic, Pillow, NumPy, argparse, pytest, Ruff, and
basedpyright dependencies.

## Global Constraints

- Follow [the M15b design](../specs/2026-08-23-pgdp-source-line-alignment-design.md).
- Preserve `pgdp-rank/v1` and `pgdp-profile/v1` byte compatibility.
- Preserve visible F2 content and address source with half-open UTF-8 byte spans.
- Keep geometry in the source frame. Rectification is M15c.
- Accept only eligible single-column pages with 4 to 80 source lines.
- Require 90 percent matched text, bounded count difference, cost at most 0.22, and uniqueness at
  least 0.15.
- Store `confidence: null` and `confidence_kind: "uncalibrated"`.
- Keep processing local, deterministic, snapshot-safe, and one image at a time.
- Add no OCR engine and do not use OCR output for verification.
- Run `make ci AI=1` after focused checks and before every implementation commit.

## Task 1: Add lossless F2 tokenization and normalization records

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/alignment_source.py`
- Create: `tests/test_pgdp_alignment_source.py`

- [ ] **Step 1: Write failing tests for UTF-8 byte spans and normalization operations**

Add table-driven tests for ASCII, `é`, CRLF, bare CR, proof notes, controls, and recognized tags.
Require byte slicing to reproduce every input segment and operation output to reproduce normalized
text.

```python
def test_tokenize_source_preserves_utf8_ranges_and_visible_case() -> None:
    source = "Éire\r\n<i>Mixed Case</i> [** proof note]\r"
    tokenized = tokenize_source_page("001.png", source)

    assert tokenized.source_utf8 == source.encode("utf-8")
    assert [line.visible_text for line in tokenized.lines] == ("Éire", "Mixed Case ", "")
    assert tokenized.operations[0].byte_start == 0
    assert tokenized.operations[-1].byte_end == len(tokenized.source_utf8)
    assert all(
        left.byte_end == right.byte_start
        for left, right in pairwise(tokenized.operations)
    )
    assert all(
        operation.output
        == tokenized.source_utf8[operation.byte_start : operation.byte_end].decode("utf-8")
        for operation in tokenized.operations
        if operation.kind == "copy"
    )
    assert "".join(operation.output for operation in tokenized.operations) == tokenized.visible_text
```

- [ ] **Step 2: Run the focused test and confirm the missing module failure**

Run: `uv run pytest tests/test_pgdp_alignment_source.py -q`

Expected: FAIL with `ModuleNotFoundError` for `pgdp.alignment_source`.

- [ ] **Step 3: Implement immutable source and operation records**

Define `NormalizationOperation`, `StyleRun`, `SourceLine`, and `TokenizedSourcePage` as frozen,
slotted dataclasses. `SourceLine` has `page_name`, `ordinal`, `byte_start`, `byte_end`,
`content_byte_start`, `content_byte_end`, `separator_byte_start`, `separator_byte_end`,
`original_text`, `visible_text`, `operation_ordinals`, `formatting_span_ids`, and
`continued_block_ids`. Use these exact operation names:

```python
NormalizationKind = Literal[
    "copy",
    "delete_control",
    "delete_tag",
    "delete_note",
    "normalize_newline",
]

@dataclass(frozen=True, slots=True)
class NormalizationOperation:
    kind: NormalizationKind
    byte_start: int
    byte_end: int
    output: str
```

Scan the UTF-8 source once. Normalize CRLF and CR to `\n`. Delete `/*`, `*/`, `/#`, and `#/` only
when the F2 control parser recognizes them. Delete proof notes matching `[** ...]` on one line.

Delete case-insensitive opening and closing `i`, `b`, `sc`, `f`, `g`, and `tb` tags with optional
attributes. Copy all other bytes unchanged. Preserve case, punctuation, whitespace, and Unicode.

Emit style runs with normalized character offsets and source byte offsets. Treat standalone `tb` as
a zero-width structural marker. Keep an unknown tag visible, diagnose it, and mark that line
ineligible for style fitting. Require operations to account for every source byte in monotone order.

- [ ] **Step 4: Run source tests and static checks**

Run: `uv run pytest tests/test_pgdp_alignment_source.py -q`

Expected: PASS.

Run:

```bash
uv run ruff check src/pdomain_ocr_synth/pgdp/alignment_source.py \
  tests/test_pgdp_alignment_source.py
uv run basedpyright src/pdomain_ocr_synth/pgdp/alignment_source.py
```

Expected: both commands exit 0.

- [ ] **Step 5: Commit the tokenizer slice**

Run: `make ci AI=1`

Expected: PASS.

```bash
git add src/pdomain_ocr_synth/pgdp/alignment_source.py tests/test_pgdp_alignment_source.py
git commit -m "feat: tokenize PGDP alignment source losslessly"
```

## Task 2: Add stable local and continued formatting spans

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/alignment_source.py`
- Modify: `tests/test_pgdp_alignment_source.py`
- Modify: `src/pdomain_ocr_synth/pgdp/f2.py`

- [ ] **Step 1: Write failing cross-page span tests**

Require a continued block to retain one identity across naturally ordered pages. Require local block
identity to depend on its opening page and byte offset. Cover unmatched, nested, and overlapping
controls.

```python
def test_continued_span_id_uses_opening_page_and_utf8_byte() -> None:
    result = tokenize_f2_pages({"p1.png": "é /#alpha", "p2.png": "beta#/ tail"})

    first = result.pages[0].formatting_spans[0]
    second = result.pages[1].formatting_spans[0]
    assert first.opening_id == second.opening_id == "continued:p1.png:3"
    assert first.block_id == second.block_id == "continued:p1.png:3:p2.png:6"
    assert first.byte_start == len("é /#".encode("utf-8"))
    assert second.byte_end == len("beta".encode("utf-8"))
```

- [ ] **Step 2: Confirm the new API is absent**

Run: `uv run pytest tests/test_pgdp_alignment_source.py -q`

Expected: FAIL because `tokenize_f2_pages` and `FormattingSpan` are missing.

- [ ] **Step 3: Implement formatting spans without changing the M14 parser contract**

Add these records and API to `alignment_source.py`. `FormattingSpan` carries both the stable
opening identity and the completed identity:

```python
BlockKind = Literal["local", "continued"]

@dataclass(frozen=True, slots=True)
class FormattingSpan:
    opening_id: str
    block_id: str
    kind: BlockKind
    page_name: str
    byte_start: int
    byte_end: int
    closed: bool

def tokenize_f2_pages(source_pages: Mapping[str, str]) -> TokenizedF2:
    ...
```

Use `natural_page_key` ordering. Open IDs are `local:{opening_page}:{opening_byte}` or
`continued:{opening_page}:{opening_byte}`. When closed, append
`:{closing_page}:{closing_byte_end}`.

Each segment also retains its opening ID, so references remain stable while scanning. Carry the
continued opening ID until `#/`. Expose diagnostics with page and byte offsets.

Do not change `ParsedF2Page` fields or its serializer. Only factor a private shared control scanner
into `f2.py` if both parsers can use it without output changes.

- [ ] **Step 4: Prove span stability and M14 compatibility**

Run: `uv run pytest tests/test_pgdp_alignment_source.py tests/test_pgdp_f2.py tests/test_pgdp_ranking.py -q`

Expected: PASS.

- [ ] **Step 5: Commit stable formatting evidence**

Run: `make ci AI=1`

Expected: PASS.

```bash
git add src/pdomain_ocr_synth/pgdp/alignment_source.py src/pdomain_ocr_synth/pgdp/f2.py tests/test_pgdp_alignment_source.py
git commit -m "feat: preserve PGDP formatting source spans"
```

## Task 3: Extract source-frame line candidates and detect gutters

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/alignment_image.py`
- Create: `tests/test_pgdp_alignment_image.py`
- Reuse: `src/pdomain_ocr_synth/pgdp/image_measurement.py`

- [ ] **Step 1: Write failing synthetic-image tests**

Create Pillow fixtures in memory for five prose rows, a page border, a long rule, two columns, and a
blank page. Assert exact half-open boxes, stable ordering, border/rule rejection, and gutter state.

```python
def test_extract_candidates_removes_border_and_long_rule() -> None:
    image = page_with_rows_border_and_rule()
    result = extract_line_candidates(
        image,
        source_frame=CoordinateFrame(400, 600),
        foreground_bounds=(20, 30, 380, 570),
        ink_bands=(InkBand(80, 95), InkBand(110, 125), InkBand(140, 155)),
    )

    assert [candidate.box for candidate in result.candidates] == EXPECTED_ROW_BOXES
    assert [candidate.band_ordinal for candidate in result.candidates] == [0, 1, 2]
    assert {item.reason for item in result.rejected} == {"page_border", "long_horizontal_rule"}
    assert result.probable_multi_column is False
```

- [ ] **Step 2: Confirm candidate extraction is missing**

Run: `uv run pytest tests/test_pgdp_alignment_image.py -q`

Expected: FAIL with `ModuleNotFoundError` for `pgdp.alignment_image`.

- [ ] **Step 3: Implement deterministic two-dimensional extraction**

Add `LineCandidate`, `RejectedComponent`, `Gutter`, and `CandidateExtraction`. Require validated
M15a foreground bounds and at least two retained M15a bands. Exclude a page missing either. Reuse
M15a grayscale and foreground-mask behavior. Restrict the mask to each band's half-open y-range.
Derive one tight foreground x-range and reject an empty band. Label eight-connected components
inside each band.

Before clipping to bands, label the full-frame foreground mask. Reject each connected component
touching at least three source-frame edges as `page_border`, and clear all its pixels from the mask.
This prevents a surrounding border from becoming four band-local fragments. Test a border spanning
five bands and require one full-frame rejection with no border pixels in any candidate.

Reject remaining components wider than 80 percent of foreground width with height below 2 percent
of foreground height as long rules. Join remaining components only within their source band.
Require vertical overlap of at least 40 percent of the smaller height, vertical-center distance of
no more than 60 percent of the larger height, and a
horizontal gap no more than twice median component height. Retain at most one candidate per band and
store `band_ordinal` on it.

After applying the join rules, sort surviving clusters by half-open box and component ordinal. If a
band has more than one cluster, do not union or select one. Exclude the page as `fragmented_band` and
serialize every cluster as rejected evidence. Tests cover two widely separated clusters, reversed
component discovery order, and three clusters. Every ordering must yield the same exclusion and
sorted rejected boxes.

Search interior column occupancy after rejected components are removed. Mark `probable_multi_column`
when a whitespace gutter at least 3 percent of foreground width crosses at least 60 percent of the
candidate vertical extent. Store every constant in `ALIGNMENT_IMAGE_METHODS`.

- [ ] **Step 4: Run image and M15a regression tests**

Run:

```bash
uv run pytest tests/test_pgdp_alignment_image.py tests/test_image_measurement.py \
  tests/test_pgdp_profile_models.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit image candidate extraction**

Run: `make ci AI=1`

Expected: PASS.

```bash
git add src/pdomain_ocr_synth/pgdp/alignment_image.py tests/test_pgdp_alignment_image.py
git commit -m "feat: extract PGDP source-frame line candidates"
```

## Task 4: Align sequences with deterministic costs and exclusions

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/alignment_dp.py`
- Create: `tests/test_pgdp_alignment_dp.py`

- [ ] **Step 1: Write failing operation, tie, and threshold tests**

Cover exact matches, one missing text line, one extra image row, equal-cost ties, 3 and 81 lines,
probable columns, low match ratio, excessive count difference, path cost, and uniqueness margin.

```python
def test_equal_cost_prefers_match_then_skip_image_then_skip_text() -> None:
    result = align_sequences(equal_cost_source(), equal_cost_candidates())
    assert [operation.kind for operation in result.operations] == [
        "match",
        "skip_image",
        "skip_text",
    ]

def test_acceptance_requires_precision_first_thresholds() -> None:
    result = assess_alignment(
        alignment_fixture(matched_ratio=0.90, normalized_cost=0.22, unique_margin=0.15)
    )
    assert result.accepted is True
```

- [ ] **Step 2: Confirm the dynamic-program module is absent**

Run: `uv run pytest tests/test_pgdp_alignment_dp.py -q`

Expected: FAIL with `ModuleNotFoundError` for `pgdp.alignment_dp`.

- [ ] **Step 3: Implement cost records and monotone transitions**

Use exact operations and tie priority:

```python
OperationKind = Literal["match", "skip_image", "skip_text"]
TIE_PRIORITY: Final = {"match": 0, "skip_image": 1, "skip_text": 2}

@dataclass(frozen=True, slots=True)
class MatchCost:
    width: float
    indent: float
    gaps: float
    style: float

    @property
    def total(self) -> float:
        return 0.55 * self.width + 0.25 * self.indent + 0.15 * self.gaps + 0.05 * self.style
```

For source line `i` and candidate `j`, define the components exactly:

```python
width = abs(len(text_i) / max_text_length - box_j.width / foreground_width)
indent = abs(leading_spaces_i / max_leading_spaces - (box_j.x0 - foreground_x0) / foreground_width)
gaps = abs(min(blank_lines_before_i, 3) / 3 - gap_before_j / max_candidate_gap)
style = min(abs(box_j.height / median_candidate_height - (1.10 if styled_i else 1.0)), 1.0)
```

Define `gap_before_j = 0` for the first candidate. Otherwise, use
`max(0, box_j.y0 - box_(j-1).y1)`. Define `max_candidate_gap` as the maximum `gap_before_j` on the
page. It is zero for zero or one candidate and when all candidates touch or overlap. Use denominator
`1` when `max_text_length`, `max_leading_spaces`, `foreground_width`, `max_candidate_gap`, or
`median_candidate_height` is zero. Clamp `gap_before_j / max_candidate_gap` to `[0, 1]`.

Define `blank_lines_before_i = 0` for the first eligible nonblank source line. For each later
eligible nonblank line, count intervening `SourceLine` records whose normalized
`visible_text == ""` since the previous eligible nonblank line. A proof-note-only or tag-only line
counts when normalization makes it empty. The cost formula clamps this count at 3. Tests cover the
first line, zero, one, three, and four intervening blank lines and the proof-note-only boundary.

`styled_i` means a recognized non-`tb` style run overlaps the visible line. Source and candidate
skips cost `1.0`.

Normalize a path cost by `max(source_count, candidate_count, 1)`. The second-best path is the
lowest-cost complete path with a different operation-and-ordinal sequence from the best path. The
uniqueness margin is the absolute total-cost difference `second_best_cost - best_cost`. Do not divide
it by line count. Retain both complete paths and use exact binary64 values.

Accept only 4 to 80 lines with no border-dominated, high-foreground, persistent-gutter, table,
illustration, or malformed-control exclusion. Require a matched text ratio of at least 0.90, a count
difference of at most `max(2, ceil(0.10 * source_count))`, normalized path cost of at most 0.22,
and a uniqueness margin of at least 0.15.

Derive table and illustration exclusions from the same immutable tokenized F2 snapshot. Reuse the
`extract_page_features` method `pgdp-rank/v1`. Table evidence requires its three-row aligned-field
predicate. Illustration evidence requires its bracketed illustration or decoration marker. Record
predicate versions and evidence source ordinals. Tests cover both positive markers, nearby negative
text, and mutation after feature extraction.

Add `to_feature_page(page: TokenizedSourcePage) -> ParsedF2Page`. It derives `source_text`,
`feature_text`, valid local and continued `special_blocks`, and `has_special_format` only from the
tokenized snapshot and its formatting spans. It never reads or reparses live F2. For all valid local,
continued, Unicode, and naturally ordered fixtures, require equality with the existing
`parse_f2_pages` result. For every table or illustration feature, require its reported source
ordinal to contain the exact matching predicate text in the tokenized page.

Store every reason on rejection. Emit `accepted`, `proposed`, or `excluded`, plus mean width and
indentation residuals across matches.

Add a numeric fixture with four equal-length unindented source lines and four equal boxes. It must
produce four `match` operations, zero normalized path cost, 1.0 matched coverage, and the exact
second-best absolute margin produced by one skip pair. Add separate fixtures that land exactly on
0.22 and 0.15. They prove inclusive thresholds and denominator handling. Add accepted 14-line and
80-line fixtures whose absolute uniqueness margins exceed 0.15.

- [ ] **Step 4: Run DP tests and deterministic replay**

Run: `uv run pytest tests/test_pgdp_alignment_dp.py -q`

Expected: PASS, including 100 repeated equal-cost alignments with identical operations.

- [ ] **Step 5: Commit the alignment algorithm**

Run: `make ci AI=1`

Expected: PASS.

```bash
git add src/pdomain_ocr_synth/pgdp/alignment_dp.py tests/test_pgdp_alignment_dp.py
git commit -m "feat: align PGDP text and image line sequences"
```

## Task 5: Define the `pgdp-alignment/v1` wire contract

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/alignment_models.py`
- Create: `schemas/pgdp-alignment-v1.schema.json`
- Create: `tests/test_pgdp_alignment_models.py`
- Modify: `src/pdomain_ocr_synth/pgdp/__init__.py`

- [ ] **Step 1: Write failing serialization and schema tests**

Require tuple normalization, finite costs, valid UTF-8 spans, source-frame boxes, ordered operations,
uncalibrated confidence, deterministic dictionaries, unknown-version rejection, and schema parity.

```python
def test_alignment_report_keeps_uncalibrated_confidence() -> None:
    payload = make_report().to_dict()
    page = payload["projects"][0]["pages"][0]
    assert page["confidence"] is None
    assert page["confidence_kind"] == "uncalibrated"
    assert payload["schema_version"] == 1
    assert payload["algorithm_version"] == "pgdp-alignment/v1"
```

- [ ] **Step 2: Confirm model imports fail**

Run: `uv run pytest tests/test_pgdp_alignment_models.py -q`

Expected: FAIL with `ModuleNotFoundError` for `pgdp.alignment_models`.

- [ ] **Step 3: Implement frozen records and explicit serializers**

Define `AlignmentDiagnostic`, `WireSourceLine`, `WireFormattingSpan`, `WireLineCandidate`,
`AlignmentOperation`, `PageAlignment`, `ProjectAlignment`, and `AlignmentReport`. Validate fields in
`__post_init__`; serialize tuples as lists and stable mappings with sorted keys. Include:

```python
ALIGNMENT_SCHEMA_VERSION: Final = 1
ALIGNMENT_ALGORITHM_VERSION: Final = "pgdp-alignment/v1"
CONFIDENCE_KIND: Final = "uncalibrated"

class AlignmentReportInput(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    schema_version: Literal[1]
    algorithm_version: Literal["pgdp-alignment/v1"]
    profile_label: str
    profile_sha256: str
```

Validate `profile_label == Path(profile_label).name` and reject empty, `.` or `..` labels. Preserve
every additive unknown version-1 field as an opaque JSON value when reading and rewriting. Tests add
nested unknown objects at report, project, and page levels. They then require equal JSON values after
a typed round trip. Unknown major schema or algorithm versions still fail.

The full report also stores tool version, methods and thresholds, naturally ordered projects and
pages, hashes, source lines, formatting spans, candidates, operations, costs, coverage, acceptance,
exclusions, and diagnostics.

Make the checked-in JSON Schema express the same required fields and closed enums.

- [ ] **Step 4: Validate model/schema parity**

Run: `uv run pytest tests/test_pgdp_alignment_models.py -q`

Expected: PASS.

Run:

```bash
uv run ruff check src/pdomain_ocr_synth/pgdp/alignment_models.py \
  tests/test_pgdp_alignment_models.py
uv run basedpyright src/pdomain_ocr_synth/pgdp/alignment_models.py
```

Expected: both commands exit 0.

- [ ] **Step 5: Commit the wire contract**

Run: `make ci AI=1`

Expected: PASS.

```bash
git add src/pdomain_ocr_synth/pgdp/alignment_models.py src/pdomain_ocr_synth/pgdp/__init__.py schemas/pgdp-alignment-v1.schema.json tests/test_pgdp_alignment_models.py
git commit -m "feat: define PGDP alignment report contract"
```

## Task 6: Orchestrate alignment and add `align-pgdp`

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/alignment.py`
- Create: `tests/test_pgdp_alignment.py`
- Create: `tests/test_cli_align_pgdp.py`
- Modify: `src/pdomain_ocr_synth/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_spec_docs.py`

- [ ] **Step 1: Write failing pipeline and CLI tests**

Build corpus fixtures with `rounds/F2.json`, scans, and an M15a profile. Cover required flags,
natural order, missing F2 pages, scan/profile hash mismatch in the orchestration profile fixture,
F2 mutation after one project page, malformed profile, unsupported version, output inside corpus,
output equal to profile, output directory, M15a `border_dominated` and `high_foreground_ratio`
diagnostics, and successful atomic JSON.

```python
def test_align_pgdp_writes_snapshot_safe_report(tmp_path: Path) -> None:
    corpus, profile = build_alignment_fixture(tmp_path)
    output = tmp_path / "alignment.json"

    result = main([
        "align-pgdp", str(corpus), "--profile", str(profile), "--output", str(output)
    ])

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["algorithm_version"] == "pgdp-alignment/v1"
    assert payload["profile_label"] == profile.name
    assert payload["profile_sha256"] == sha256(profile.read_bytes()).hexdigest()
```

- [ ] **Step 2: Confirm orchestration and command are absent**

Run: `uv run pytest tests/test_pgdp_alignment.py tests/test_cli_align_pgdp.py -q`

Expected: FAIL because `build_alignment_report` and `align-pgdp` do not exist.

- [ ] **Step 3: Implement the streaming snapshot-safe pipeline**

Add this public entry point:

```python
def build_alignment_report(
    corpus_root: str | Path,
    profile_path: str | Path,
    *,
    tool_version: str,
) -> AlignmentReport:
    ...
```

Validate `pgdp-profile/v1` while accepting additive version-1 fields without assigning them meaning.
Resolve its corpus-relative paths with the existing safe path rules. Hash the profile once and store
only its safe file-name label.

For each project, read, hash, and parse F2 exactly once. Bind every page to that parsed snapshot.
Rehash F2 after the project's last page. If it changed, discard every provisional project result and
exclude all its pages as `source_changed`.

For each scan, call `open_image_snapshot` and compare `snapshot.sha256` with M15a before decoding.
Decode the image and extract candidates from `snapshot.source_file`, not the live path. After closing
the snapshot, hash the live path with `sha256_file`. Exclude the page as `source_changed` if it
differs from the snapshot. Exclude mismatched pages and continue.

Propagate every M15a page diagnostic into eligibility, including mandatory `border_dominated` and
`high_foreground_ratio` exclusions. Load and release one image per page. Pass profile foreground
bounds and retained bands to candidate extraction. Pass tokenized source and candidates into the DP.
Preserve all diagnostics.

Map inherited M15a codes exactly: `blank_page` to `blank_page`; `one_ink_band` and `no_ink_bands` to
`insufficient_ink_bands`; `border_dominated` and `high_foreground_ratio` unchanged; `image_missing`,
`image_unreadable`, and `image_decode_failed` unchanged; and `foreground_bounds_unavailable`
unchanged. Any other M15a page diagnostic, including an empty code, produces the M15b exclusion
`inherited_profile_diagnostic`; retain its original code and message as evidence. Exclude it before
candidate extraction. Parameterized tests cover every current mapping, an empty code, and a future
additive code. Both unrecognized cases must be conservatively excluded without losing their payload.

- [ ] **Step 4: Wire the exact CLI and exit behavior**

Register:

```text
align-pgdp CORPUS_ROOT --profile PATH --output PATH
```

Require both flags. Reuse `write_report`. Reject an output that resolves to the profile input before
opening either for writing. Return `VALIDATION_EXIT` for malformed or unsupported profiles and
`DESTINATION_EXIT` for output-path failures. Print no report JSON to stdout. Add `align-pgdp` to the
CLI command drift tests.

- [ ] **Step 5: Run focused CLI and compatibility tests**

Run:

```bash
uv run pytest tests/test_pgdp_alignment.py tests/test_cli_align_pgdp.py tests/test_cli.py \
  tests/test_spec_docs.py tests/test_cli_profile_pgdp.py tests/test_cli_rank_pgdp.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the runnable slice**

Run: `make ci AI=1`

Expected: PASS.

```bash
git add src/pdomain_ocr_synth/pgdp/alignment.py src/pdomain_ocr_synth/cli.py tests/test_pgdp_alignment.py tests/test_cli_align_pgdp.py tests/test_cli.py tests/test_spec_docs.py
git commit -m "feat: add PGDP source-line alignment command"
```

## Task 7: Check in reviewed positive and exclusion fixtures

**Files:**

- Create: `tests/fixtures/pgdp_alignment/manifest.json`
- Create: `tests/fixtures/pgdp_alignment/accepted/`
- Create: `tests/fixtures/pgdp_alignment/excluded/`
- Create: `tests/test_pgdp_alignment_fixtures.py`
- Modify: `docs/process/lint-deviations.md` only if a justified suppression is unavoidable

- [ ] **Step 1: Select fixture cases from real scans**

Choose at least five accepted pages from three books and five excluded pages. Accepted pages must
include ordinary prose, indentation, and styled F2 text. Exclusions must include probable columns,
a long rule or table, too few lines, a source diagnostic, and an illustration marker. Keep
scan-hash mismatch only in Task 6's orchestration profile fixture because this fixture runner has no
M15a report boundary. Store cropped or downsampled PNG fixtures only when their source license
permits repository inclusion. Otherwise, create byte-stable synthetic derivatives that reproduce the
measured geometry and record that fact.

Task 6's orchestration fixtures separately cover profile pages carrying `border_dominated` and
`high_foreground_ratio`. Both must be excluded before candidate extraction.

The manifest is a JSON object with `schema_version: 1` and a `cases` array. Each case contains
`case_id`, `project_id`, `page_name`, `f2_text`, `image_path`, `source_sha256`, `fixture_sha256`,
`transform`, `foreground_bounds`, `expected_candidates`, `reviewed_on`, `accepted`, `exclusions`,
and `operations`.

Bounds and candidate boxes are four-integer half-open arrays. Each operation contains `kind`,
`source_ordinal`, `candidate_ordinal`, and `cost`.

The fixture test defines frozen `AlignmentCase` and `ExpectedOperation` records. It loads this exact
shape through a strict Pydantic adapter and invokes the public tokenizer, candidate extractor, and
aligner in `run_alignment_case`.

- [ ] **Step 2: Write failing fixture assertions before adding expected output**

```python
@pytest.mark.parametrize("case", load_alignment_cases())
def test_reviewed_alignment_case(case: AlignmentCase) -> None:
    result = run_alignment_case(case)
    assert result.accepted is case.accepted
    assert result.exclusions == case.exclusions
    assert result.operations == case.operations
```

Define `load_alignment_cases() -> tuple[AlignmentCase, ...]` to load and validate the manifest.
Define `run_alignment_case(case: AlignmentCase) -> AlignmentResult` to open the relative fixture
image, tokenize `f2_text`, extract candidates with the manifest bounds, and call `align_sequences`.
Seed the failing manifest with the ten named cases and empty expected `operations` arrays. Before the
test may pass, the review step replaces each empty array with exact reviewed operations.

Run: `uv run pytest tests/test_pgdp_alignment_fixtures.py -q`

Expected: FAIL because the reviewed expected records are not present.

- [ ] **Step 3: Review and record exact expected evidence**

Inspect each fixture with a candidate-box overlay. Record exact candidate boxes, operations, costs,
acceptance, and exclusions in `manifest.json`. Do not change algorithm constants to make an excluded
complex page pass. Have a second reviewer confirm every accepted mapping against the image.

- [ ] **Step 4: Run fixtures and all PGDP tests**

Run:

```bash
uv run pytest tests/test_pgdp_alignment_fixtures.py tests/test_pgdp_*.py \
  tests/test_cli_rank_pgdp.py tests/test_cli_profile_pgdp.py tests/test_cli_align_pgdp.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit reviewed fixtures**

Run: `make ci AI=1`

Expected: PASS.

```bash
git add tests/fixtures/pgdp_alignment tests/test_pgdp_alignment_fixtures.py docs/process/lint-deviations.md
git commit -m "test: add reviewed PGDP alignment fixtures"
```

## Task 8: Validate a bounded corpus report and visual overlays

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/alignment_review.py`
- Create: `tests/test_pgdp_alignment_review.py`
- Modify: `docs/usage/recipe-workflow.md`
- Modify: `docs/context/current-state.md`
- Modify: `docs/plans/README.md`
- Modify: `docs/plans/2026-08-23-pgdp-source-line-alignment.md`

- [x] **Step 1: Write failing overlay tests**

Require an RGB overlay that preserves source dimensions, draws each candidate box, labels matched
source ordinals, distinguishes skipped candidates, and never changes the alignment report.

```python
def test_overlay_is_source_sized_and_report_is_unchanged(tmp_path: Path) -> None:
    before = report_path.read_bytes()
    overlay = render_alignment_overlay(scan_path, page_alignment, tmp_path / "overlay.png")
    assert overlay.size == source_frame.size
    assert report_path.read_bytes() == before
```

- [x] **Step 2: Implement the review-only overlay helper**

Add `render_alignment_overlay(scan_path, page_alignment, output_path) -> Image.Image`. Draw accepted
matches in green, rejected matches in amber, skipped image candidates in red, and source ordinals in
the left margin. Keep it outside the production report path. Reject an overlay output inside the
corpus root when the caller supplies that root.

Run: `uv run pytest tests/test_pgdp_alignment_review.py -q`

Expected: PASS.

- [x] **Step 3: Generate two bounded real-corpus reports**

Use a temporary directory outside the corpus. First create or reuse an M15a profile bounded to at
least 20 reviewable pages and five books, then run:

```bash
uv run pdomain-ocr-synth align-pgdp /workspaces/pdomain-data/pgdp-corpus \
  --profile /tmp/pgdp-m15b-profile.json \
  --output /tmp/pgdp-m15b-alignment-a.json
uv run pdomain-ocr-synth align-pgdp /workspaces/pdomain-data/pgdp-corpus \
  --profile /tmp/pgdp-m15b-profile.json \
  --output /tmp/pgdp-m15b-alignment-b.json
cmp /tmp/pgdp-m15b-alignment-a.json /tmp/pgdp-m15b-alignment-b.json
```

Expected: both commands exit 0 and `cmp` reports no difference.

- [x] **Step 4: Complete the precision and coverage review**

Review at least 20 pages, 400 source lines, and five books. Include indented prose, italic, bold,
small-cap, poetry, and quotation pages. Include excluded columns, tables, rules, covers,
illustrations, and malformed source.

Record a confusion ledger with intended source-line mapping, observed operation, and reviewer
decision. Also record every exclusion count and the distributions for normalized path cost, width
residual, indentation residual, and uniqueness margin.

Reconcile every reviewed selected page into exactly one of four counts: declared complex exclusion,
unavailable or malformed input, source changed, or eligible. A page is eligible only after it passes
all pre-alignment source, snapshot, scan, line-count, foreground, gutter, table, and illustration
gates. Compute eligible-page coverage as accepted eligible pages divided by all eligible pages. Keep
`proposed` and alignment-quality exclusions in the denominator. Report source-changed pages
separately and never count them as eligible or accepted.

Use this exhaustive version-1 mapping. `declared_complex` contains `probable_multi_column`,
`persistent_gutter`, `table_like`, `illustration_marker`, `border_dominated`, and
`high_foreground_ratio`.
`unavailable_or_malformed` contains `f2_missing`, `page_missing`, `image_missing`,
`image_unreadable`, `image_decode_failed`, `profile_page_missing`,
`foreground_bounds_unavailable`, `insufficient_ink_bands`, `blank_page`,
`fragmented_band`, `line_count_out_of_range`, `malformed_control`, `scan_hash_mismatch`, and
`inherited_profile_diagnostic`. `source_changed` alone maps to the source-changed count. A page with
no pre-alignment exclusion maps to `eligible`, including `proposed` and alignment-quality exclusions.
When several codes apply, priority is source changed, unavailable or malformed, declared complex,
then eligible. Reject an unknown M15b exclusion code from the review ledger. An unknown inherited
M15a code maps to `inherited_profile_diagnostic`. Test every code, every priority pair, this mapping,
and
`selected_total == sum(the_four_disjoint_counts)`.

Pass only when accepted-line precision is at least 98 percent, eligible-page coverage is at least
70 percent, and zero declared complex pages are accepted.

If a gate fails, leave this plan `partial`, record the exact counts, and open a threshold or
extractor follow-up. Do not weaken a gate in the same review run.

- [x] **Step 5: Document the command and verified result**

Add the exact CLI example, wire-version description, exclusions, and interpretation limits to
`docs/usage/recipe-workflow.md`. Update current state and the M15b roadmap row with measured counts,
precision, coverage, deterministic replay, and residual risks. Mark this plan `implemented` only if
all gates pass.

- [x] **Step 6: Run complete verification**

Run: `uv run pytest tests/test_pgdp_alignment_review.py tests/test_pgdp_alignment_fixtures.py -q`

Expected: PASS.

Run: `make ci AI=1`

Expected: PASS with no new lint, type, test, or build failures.

Run: `docgraph reindex && docgraph check --strict && git diff --check`

Expected: docgraph reports no new blocking issue and `git diff --check` exits 0.

- [x] **Step 7: Commit the verified milestone record**

```bash
git add src/pdomain_ocr_synth/pgdp/alignment_review.py tests/test_pgdp_alignment_review.py docs/usage/recipe-workflow.md docs/context/current-state.md docs/plans/README.md docs/plans/2026-08-23-pgdp-source-line-alignment.md
git commit -m "docs: record PGDP alignment milestone results"
```

## Final review and handoff

Request a branch-wide review against the design and this plan. Resolve every accepted finding with a
focused test. Then rerun `make ci AI=1`, deterministic corpus replay, the visual precision ledger,
`docgraph check --strict`, and `git diff --check` before claiming completion.

Do not start M15c in this branch. The handoff must state that rotation, dewarping, rectified frames,
baselines, multi-column reading order, OCR verification, and font fitting remain unimplemented.

## Corpus review result

Two balanced runs over 25 pages from five books were byte-identical. Their report SHA-256 was
`2d71eb3bef6ac953c82b9e581ffa92dc77436f90f592a6952a4ec27a232eb107`. The report contained 1,681
raw source-line records. The review ledger covered all 1,107 operation rows across prose,
indentation, poetry-like text, italics, bold, small capitals, quotations, columns, tables, rules, a
cover, an illustration, and malformed source.

All 25 pages were classified as unavailable or malformed before alignment. There were zero
declared complex, source-changed, or eligible pages under the required priority mapping. No line
was accepted, so accepted-line precision and eligible-page coverage were undefined. The
zero-complex-acceptance gate passed, but the 98 percent precision and 70 percent coverage gates did
not.

The confusion ledger covered all 1,107 operation rows and had SHA-256
`54fd9f18b508e20afb57fec9f3db1415111307747cd9751db22104ca5c56ad8b`. Visual inspection found
that `fragmented_band` incorrectly excluded 12 pages and 359 rows that otherwise appeared
alignable. The remaining 13 pages and 748 rows were correctly kept out as complex, malformed, or
too short. This plan therefore remains partial. A separate extractor follow-up must rerun the fixed
selection against the unchanged quality gates. That work is tracked in
[ocr-container-meta issue 403](https://github.com/ConcaveTrillion/ocr-container-meta/issues/403).

## Adversarial Review

- **Stage and source:** Per-task specification and quality reviews used the M15b design, this plan,
  implementation diffs, focused tests, and real-corpus evidence.
- **Accepted findings:** Candidate extraction now measures persistent-gutter coverage over its full
  vertical extent. Wire validation rejects invalid operation references and inconsistent review
  ledgers. Overlay rendering verifies the scan hash and cannot overwrite its source. Missing,
  unreadable, or malformed project F2 retains every selected page as an explicit exclusion. An
  unavailable F2 hash is null only on an excluded `f2_missing` page. The declared-complex mapping
  now includes `persistent_gutter`.
- **Effect on this document:** Implementation work is complete, but the milestone stays
  partial because the corpus precision and coverage gates did not pass.
- **Residual risks:** Fragmented-band detection rejects visually alignable single-column pages.
  Until that extractor is corrected and the fixed review set passes, alignment confidence remains
  uncalibrated and eligible-page coverage is undefined.
