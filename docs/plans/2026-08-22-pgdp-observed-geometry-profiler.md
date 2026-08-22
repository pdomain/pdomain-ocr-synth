# PGDP Observed Geometry Profiler Implementation Plan

## Agent Index

- **Kind:** plan
- **Status:** implemented
- **Owner:** CT
- **Created:** 2026-08-22
- **Last verified:** 2026-08-22
- **Provenance:** derived from the approved PGDP typography design, the shipped M14 ranker, and
  2026-08-22 corpus verification.
- **Disposition:** Implemented first M15 scan-measurement slice.
- **Read when:** implementing or reviewing PGDP scan measurement and book profiles.
- **Search terms:** PGDP, M15, image measurement, ink bands, profile, Otsu, margins.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local `profile-pgdp` command. It converts selected scans from an M14 ranking report
into versioned page and book geometry observations.

**Architecture:** The command validates a ranking report and resolves each scan inside its project.
It streams one image at a time through deterministic Pillow and NumPy measurements. Frozen wire
records separate raw observations from derived and pooled estimates. Version 1 measures source-frame
ink geometry only. It does not claim baselines, columns, semantic regions, or fonts.

**Tech Stack:** Python 3.13, frozen dataclasses, Pydantic, Pillow, NumPy, argparse, pytest, ruff,
basedpyright.

---

## Goal

Produce deterministic, evidence-preserving scan measurements for pages selected by the M14 ranker.

## Architecture

Keep input validation, safe path resolution, image measurement, pooled statistics, wire records,
and CLI output in separate modules. Stream images through the pipeline. Preserve raw observations
beside every derived or pooled estimate.

## Tech Stack

Use only the project's existing Python 3.13, Pydantic, Pillow, NumPy, argparse, pytest, ruff, and
basedpyright dependencies.

## Global Constraints

- Preserve `pgdp-rank/v1` output byte compatibility.
- Keep all processing local and deterministic.
- Store only corpus-relative source paths.
- Never replace an unavailable measurement with zero.
- Never describe row-projection ink bands as verified baselines.
- Process one full-resolution image at a time.

## Version 1 measures visible scan geometry

The profiler emits each image's hash, dimensions, mode, grayscale threshold, foreground count,
bounds, four pixel margins, horizontal ink bands, median band height, and median inter-band pitch.
Project summaries pool medians and median absolute deviations across pages.

Every estimate records its truth class, unit, source frame, method version, sample count, page
evidence, exclusions, and confidence state. Version 1 records `confidence: null` and
`confidence_kind: "uncalibrated"` for every estimate. A later reviewed corpus must calibrate a
numeric confidence before the field can contain a number. Missing evidence produces `null` and a
diagnostic, never a numeric zero. Row-projection bands are called ink bands because they are not
verified baselines.

The top-level wire shape contains `schema_version`, `algorithm_version`, `source_ranking`,
`methods`, `projects`, and `diagnostics`. Each project contains identity, ordered pages, pooled
estimates, exclusions, and diagnostics. Each page contains its relative source path, SHA-256,
source frame, image metadata, raw observations, derived estimates, exclusions, and diagnostics.
Each estimate contains name, value, unit, truth class, frame, method, sample count, evidence pages,
exclusions, confidence, and confidence kind.

Version 1 excludes rectification, physical dimensions, true baselines, columns, semantic regions,
text alignment, font matching, style inference, and renderer settings.

## Task 1: Define immutable profile records

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/profile_models.py`
- Create: `schemas/pgdp-profile-v1.schema.json`
- Create: `tests/test_pgdp_profile_models.py`
- Modify: `src/pdomain_ocr_synth/pgdp/__init__.py`

- [x] **Step 1: Write failing serialization and invariant tests**

Require `CoordinateFrame`, `InkBand`, `Estimate`, `PageMeasurement`, `ProjectProfile`, and
`ProfileReport`. Assert deterministic `to_dict()` output, tuple normalization, finite estimates,
valid half-open bounds, and `null` for absent observations.

```python
def test_absent_bounds_do_not_become_zero() -> None:
    page = make_page_measurement(foreground_bounds=None, foreground_pixels=0)
    assert page.to_dict()["observations"]["foreground_bounds"] is None
```

- [x] **Step 2: Run `uv run pytest tests/test_pgdp_profile_models.py -q`**

Expected: fail because `pgdp.profile_models` does not exist.

- [x] **Step 3: Implement frozen, slotted records and serializers**

Use schema `1`, algorithm `pgdp-profile/v1`, frame `source`, and truth classes `observed`, `derived`,
and `pooled`. Reject non-finite values, negative counts, inverted bounds, duplicate evidence, and
sample counts that disagree with their evidence.

Define Pydantic wire models as the compatibility boundary. Generate
`schemas/pgdp-profile-v1.schema.json` from those models. Test that the checked-in schema matches
fresh generation byte for byte. Test typed-model to wire-model to JSON round trips.

Version 1 readers reject unknown major schema and algorithm versions. They accept unknown optional
version 1 fields and preserve their JSON values in the corresponding object's `extensions` mapping.
Tests compare semantic values after canonical deterministic reserialization.

- [x] **Step 4: Run tests and strict checks**

Run: `uv run pytest tests/test_pgdp_profile_models.py -q && make lint AI=1 && make typecheck AI=1`

Expected: all commands pass.

- [x] **Step 5: Commit with `feat: define PGDP geometry profile records`**

## Task 2: Validate input and resolve scans safely

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/profile_input.py`
- Create: `src/pdomain_ocr_synth/pgdp/paths.py`
- Modify: `src/pdomain_ocr_synth/pgdp/ranking.py`
- Create: `tests/test_pgdp_profile_input.py`
- Modify: `tests/test_pgdp_ranking.py`

- [x] **Step 1: Write failing input and path tests**

Cover valid M14 input, unknown versions, malformed JSON, duplicates, missing projects, absolute
paths, traversal, NUL names, symlink escape, and duplicate root and `images/` files.

```python
def test_profile_input_rejects_unknown_algorithm(tmp_path: Path) -> None:
    write_ranking(tmp_path / "ranking.json", algorithm_version="pgdp-rank/v2")
    with pytest.raises(ValueError, match="pgdp-rank/v1"):
        load_profile_input(tmp_path / "ranking.json")
```

- [x] **Step 2: Run `uv run pytest tests/test_pgdp_profile_input.py tests/test_pgdp_ranking.py -q`**

Expected: fail because the loader and shared resolver do not exist.

- [x] **Step 3: Implement the strict boundary and resolver**

Validate consumed JSON with Pydantic `TypeAdapter`. Accept only schema `1` and `pgdp-rank/v1`.
Preserve report order. Move image resolution from `ranking.py` into `paths.py` without changing M14
output. Resolve paths before opening and keep them inside the project and corpus.

Keep M14 semantics separate. Ranking asks only whether any safe candidate image exists. Profiling
uses the same candidate precedence and records the selected relative path. It does not reject a page
because another safe candidate has the same name. Add a golden M14 report fixture and assert that
this refactor leaves its bytes unchanged.

- [x] **Step 4: Run the focused tests and expect all to pass**

- [x] **Step 5: Commit with `feat: load PGDP profile inputs safely`**

## Task 3: Measure foreground geometry

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/image_measurement.py`
- Create: `tests/test_pgdp_image_measurement.py`

- [x] **Step 1: Write failing synthetic-image tests**

Cover blank, solid, grayscale, RGB, RGBA, palette, and separated rectangles. Hash original bytes.
Composite alpha over white. Use 256-bin integer Otsu with the lowest maximizing threshold as its
tie-break. Foreground pixels are at or below the threshold. Bounds are half-open.

```python
def test_two_rectangles_report_source_bounds(tmp_path: Path) -> None:
    result = measure_image(save_two_rectangles(tmp_path / "page.png"))
    assert result.foreground_bounds == (5, 4, 35, 26)
```

- [x] **Step 2: Run `uv run pytest tests/test_pgdp_image_measurement.py -q`**

Expected: fail because `measure_image` does not exist.

- [x] **Step 3: Implement deterministic streaming measurement**

Hash in chunks and reject Pillow decompression bombs. Measure decoded pixels without applying EXIF
orientation. This keeps `source` as the stored raster coordinate frame. Record raw dimensions, mode,
and the EXIF orientation tag as metadata only. Convert to 8-bit grayscale and calculate integer Otsu.

Blank pages have zero foreground pixels and `None` bounds. Release each image array before the next
page. Add an oriented-image overlay test that proves coordinates remain in raw raster space.

- [x] **Step 4: Run the image tests, lint, and type checks**

- [x] **Step 5: Commit with `feat: measure PGDP scan foreground geometry`**

## Task 4: Extract ink bands and page estimates

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/image_measurement.py`
- Modify: `tests/test_pgdp_image_measurement.py`

- [x] **Step 1: Write failing band and noise tests**

A row is active at `max(2, ceil(print_width * 0.005))` foreground pixels. Join active runs separated
by at most one inactive row. Drop joined runs shorter than two rows. Cover specks, gaps, borders,
mixed heights, and tight horizontal bounds.

```python
def test_ink_bands_join_one_row_gap() -> None:
    assert band_ranges(extract_ink_bands(band_mask(((3, 5), (7, 9))))) == [(3, 10)]
```

- [x] **Step 2: Run the image tests and confirm failure**

- [x] **Step 3: Implement bands, margins, and estimates**

Store raw bands, median band height, and median successive band-top pitch when two bands exist.
Emit diagnostics for blank, one-band, border-dominated, and over-60-percent foreground pages.

Pooling eligibility is metric-specific. Blank and corrupt pages contribute to no estimate.
One-band pages contribute band height but not pitch. Border-dominated and over-60-percent pages
retain raw observations but contribute to no pooled margin, band-height, or pitch estimate. Other
valid pages contribute every available margin and band height, plus pitch when they have two bands.
Missing bounds exclude all four margins. Every excluded metric records
`<page>:<diagnostic-code>`.

A page is border-dominated when foreground fills at least 50 percent of both opposing edge strips
on either axis. Each strip is the outer `max(1, ceil(dimension * 0.01))` rows or columns. Tests cover
horizontal borders, vertical borders, a single dark edge, and ordinary text near an edge.

- [x] **Step 4: Run the image tests and expect all to pass**

- [x] **Step 5: Commit with `feat: extract PGDP horizontal ink bands`**

## Task 5: Build and pool project profiles

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/profiling.py`
- Create: `tests/test_pgdp_profiling.py`

- [x] **Step 1: Write failing orchestration and pooling tests**

Use measured, blank, missing, and corrupt pages. Continue after failures. Pool each numeric estimate
with median and median absolute deviation. Evidence contains contributing pages in natural order.
Exclusions name each omitted page and reason.

```python
def test_pool_records_evidence_and_exclusions() -> None:
    result = pool_estimate("median_band_height_px", measured_pages_fixture())
    assert (result.value, result.sample_count) == (9.0, 2)
    assert result.exclusions == ("p002.png:blank_page",)
```

- [x] **Step 2: Run `uv run pytest tests/test_pgdp_profiling.py -q`**

Expected: fail because profiling and pooling do not exist.

- [x] **Step 3: Implement orchestration and robust pooling**

Catch file, decode, and measurement failures at the page boundary. Retain failed records with
`None` observations and stable diagnostics. Use median and median absolute deviation without
outlier removal. Record `otsu-256/v1`, `row-ink-bands/v1`, and `median-mad/v1`.

- [x] **Step 4: Run `uv run pytest tests/test_pgdp_*.py -q` and expect all to pass**

- [x] **Step 5: Commit with `feat: pool PGDP observed geometry profiles`**

## Task 6: Add deterministic output and CLI

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/report.py`
- Modify: `src/pdomain_ocr_synth/cli.py`
- Create: `tests/test_cli_profile_pgdp.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_spec_docs.py`
- Modify: `docs/usage/recipe-workflow.md`

- [x] **Step 1: Write failing CLI, atomicity, and determinism tests**

Cover missing input, output inside corpus, output equal to ranking input, output directory, malformed
scan, interrupted replacement, and two byte-identical runs.

```python
def test_profile_pgdp_is_byte_deterministic(tmp_path: Path) -> None:
    assert run_profile(tmp_path, "a.json").read_bytes() == run_profile(tmp_path, "b.json").read_bytes()
```

- [x] **Step 2: Run `uv run pytest tests/test_cli_profile_pgdp.py tests/test_spec_docs.py -q`**

Expected: fail because `profile-pgdp` is absent.

- [x] **Step 3: Implement `profile-pgdp CORPUS_ROOT --ranking PATH --output PATH`**

Require both options. Reject unsafe output. Reuse atomic same-directory replacement and stable JSON.
Use exit 2 for input errors, 0 for completed measurement with diagnostics, and 6 for output errors.

- [x] **Step 4: Run CLI, documentation, and PGDP tests**

Run: `uv run pytest tests/test_cli_profile_pgdp.py tests/test_spec_docs.py tests/test_pgdp_*.py -q`

Expected: all tests pass.

- [x] **Step 5: Commit with `feat: add PGDP observed geometry profiler`**

## Task 7: Verify the corpus and record results

**Files:**

- Modify: `docs/context/current-state.md`
- Modify: `docs/plans/README.md`
- Modify: `docs/plans/2026-08-22-pgdp-observed-geometry-profiler.md`

- [x] **Step 1: Rank five projects with twelve pages each**

```bash
uv run pdomain-ocr-synth rank-pgdp /workspaces/pdomain-data/pgdp-corpus --output /tmp/pgdp-m15a-ranking.json --project-limit 5 --pages-per-project 12
```

- [x] **Step 2: Profile twice and compare bytes**

```bash
uv run pdomain-ocr-synth profile-pgdp /workspaces/pdomain-data/pgdp-corpus --ranking /tmp/pgdp-m15a-ranking.json --output /tmp/pgdp-m15a-a.json
uv run pdomain-ocr-synth profile-pgdp /workspaces/pdomain-data/pgdp-corpus --ranking /tmp/pgdp-m15a-ranking.json --output /tmp/pgdp-m15a-b.json
cmp /tmp/pgdp-m15a-a.json /tmp/pgdp-m15a-b.json
```

- [x] **Step 3: Inspect ten temporary overlays**

Draw stored bounds and bands for the first two pages of each project. Inspect all ten. Record false
merges, false splits, borders, blank pages, and corrupt pages. Do not commit scans or overlays.

- [x] **Step 4: Add reviewed geometry fixtures and error gates**

Commit five small redistributable synthetic scan fixtures with reviewed source-frame foreground
bounds and ink-band intervals. Include clean text-like rows, noise, a border, an EXIF orientation
tag, and a blank page. Report absolute error for every bounds edge and one-dimensional
intersection-over-union for matched ink bands. Acceptance requires zero bounds-edge error on the
clean and oriented fixtures, mean matched-band intersection-over-union of at least `0.95`, and the
expected exclusion code for the border and blank fixtures. Store expected measurements in reviewed
JSON. Generate overlays only in a temporary directory.

- [x] **Step 5: Update state without claiming excluded measurements**

Mark this plan implemented. Record counts, exclusions, diagnostics, overlay findings, commands, and
commits. Do not claim rectification, alignment, baselines, columns, semantics, or fonts.

- [x] **Step 6: Run final gates**

```bash
make ci AI=1
docgraph reindex
docgraph check --strict
git diff --check
```

- [x] **Step 7: Commit with `docs: record PGDP geometry profiler results`**

## Corpus verification record

The 2026-08-22 local run ranked five projects with twelve selected pages each. It measured all 60
pages and excluded none from measurement. The two profile reports were byte-identical. The profile
used `pgdp-rank/v1` input hash `6f4ca5f025f8a57a77a67b2fcb62f97f53191bc2c029b2daf356b8460ee1f476`.
It emitted `pgdp-profile/v1` with `otsu-256/v1`, `row-ink-bands/v1`, and `median-mad/v1` methods.

Three pages in `projectID63161caf7eafa` had the `one_ink_band` diagnostic: `w0030.png`,
`w0050.png`, and `w0110.png`. They remain measured but are excluded only from the pooled band-pitch
estimate. The run had no blank, corrupt, border-dominated, or high-foreground-ratio selected pages.

Ten temporary overlays covered the first two selected pages from each project. They were reviewed in
`/tmp/pgdp-m15a-overlays.zlSH4u`. Red bounds cover the observed foreground. Green bands follow text
rows on ordinary pages. On tabular pages, they also follow horizontal rules and table rows. They
therefore remain ink bands, not baselines. The review found no false bounds merge or split in these
ten pages and no reviewed blank or corrupt page.

The five redistributable fixtures contain clean text-like rows, isolated noise, opposing borders, an
EXIF orientation tag, and a blank page. Their reviewed JSON expects zero source-bounds edge error
for the clean and oriented images, a mean matched-band IoU of 1.0, `border_dominated` exclusion for
the border, and `blank_page` exclusion for the blank image.

Commands used:

```bash
UV_PROJECT_ENVIRONMENT=.venv uv run pdomain-ocr-synth rank-pgdp /workspaces/pdomain-data/pgdp-corpus --output /tmp/pgdp-m15a-ranking.json --project-limit 5 --pages-per-project 12
UV_PROJECT_ENVIRONMENT=.venv uv run pdomain-ocr-synth profile-pgdp /workspaces/pdomain-data/pgdp-corpus --ranking /tmp/pgdp-m15a-ranking.json --output /tmp/pgdp-m15a-a.json
UV_PROJECT_ENVIRONMENT=.venv uv run pdomain-ocr-synth profile-pgdp /workspaces/pdomain-data/pgdp-corpus --ranking /tmp/pgdp-m15a-ranking.json --output /tmp/pgdp-m15a-b.json
cmp /tmp/pgdp-m15a-a.json /tmp/pgdp-m15a-b.json
```

The implementation ends at `a7e5565`. The reviewed fixture gate is `f182774`.

## Acceptance criteria preserve the evidence boundary

- Identical inputs produce byte-identical profile JSON.
- Every opened image has a corpus-relative path and original-byte SHA-256.
- Blank, missing, corrupt, unsafe, and unsupported pages remain represented with diagnostics.
- Raw bounds and ink bands remain available beside derived estimates.
- Pooled values record medians, median absolute deviations, evidence, and exclusions.
- No output calls an ink-band edge a baseline or treats pixels as physical units.
- Every version 1 estimate records `confidence_kind: "uncalibrated"` and `confidence: null`.
- Reviewed fixtures meet the bounds and ink-band error gates.
- Profiling streams pages and does not retain full-corpus image arrays.
- `pgdp-rank/v1` remains byte-compatible.
- Tests, lint, type checking, build, docgraph, and corpus determinism checks pass.

## Rollback keeps M14 intact

The feature is additive. Rollback removes `profile-pgdp` and its modules while retaining M14 and
`pgdp-rank/v1`. Profile files declare `pgdp-profile/v1`, so readers can reject them cleanly.
