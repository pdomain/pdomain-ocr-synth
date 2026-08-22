# PGDP Ranking and Review Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

## Agent Index

- **Kind:** plan
- **Status:** implemented
- **Owner:** CT
- **Created:** 2026-08-22
- **Last verified:** 2026-08-22
- **Provenance:** derived from the approved PGDP typography and page-structure design and current
  repository evidence
- **Disposition:** M14's first runnable ranking and review-queue slice shipped.
- **Read when:** implementing or reviewing PGDP corpus ranking and multimodal review queues.
- **Search terms:** PGDP ranking, F2 parser, review queue, typography coverage, structure coverage.

**Goal:** Rank local PGDP projects and pages by typography and structure coverage, then write a
deterministic multimodal review queue.

**Architecture:** A new `pgdp` package reads project metadata and F2 text without opening images. It
parses local and continued formatting blocks, extracts versioned features, scores projects and
pages, and writes one stable JSON report. The CLI is local-only and has no LLM or network
dependency.

**Tech Stack:** Python 3.13, standard-library JSON and regular expressions, frozen dataclasses,
argparse, pytest, Ruff, and basedpyright.

---

## Goal

Produce a deterministic local ranking of PGDP projects and a bounded page queue for multimodal
review.

## Architecture

The implementation separates F2 parsing, feature extraction, scoring, selection, and report writing.
Every layer uses typed immutable records and exposes its evidence in the final JSON.

## Tech Stack

The slice uses Python 3.13, the standard library, argparse, pytest, Ruff, and basedpyright. It adds
no runtime dependency.

## Global Constraints

The command must remain local-only, deterministic, and safe for the source corpus. It must preserve
F2 text, expose score components, continue past malformed projects, and never treat an LLM proposal
as ground truth.

## The file boundaries keep evidence separate from policy

- `src/pdomain_ocr_synth/pgdp/models.py` owns immutable typed records and JSON conversion.
- `src/pdomain_ocr_synth/pgdp/ordering.py` owns the natural page-name comparator.
- `src/pdomain_ocr_synth/pgdp/f2.py` owns lossless F2 loading and formatting-control parsing.
- `src/pdomain_ocr_synth/pgdp/features.py` owns page predicates and score components for
  `pgdp-rank/v1`.
- `src/pdomain_ocr_synth/pgdp/ranking.py` owns project discovery, natural ordering, project scores,
  limits, and review selection.
- `src/pdomain_ocr_synth/pgdp/report.py` owns deterministic and atomic JSON output.
- `src/pdomain_ocr_synth/pgdp/__init__.py` exposes the small public ranking API.
- `src/pdomain_ocr_synth/cli.py` owns argument parsing, user errors, and exit codes only.
- `tests/test_pgdp_f2.py` covers the formatting-control state machine.
- `tests/test_pgdp_features.py` covers every versioned predicate and score.
- `tests/test_pgdp_ranking.py` covers project discovery, ranking, selection, limits, and
  determinism.
- `tests/test_cli_rank_pgdp.py` covers CLI behavior and output safety.

### Task 1: Define the report records

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/__init__.py`
- Create: `src/pdomain_ocr_synth/pgdp/models.py`
- Create: `src/pdomain_ocr_synth/pgdp/ordering.py`
- Test: `tests/test_pgdp_ranking.py`

- [x] **Step 1: Write the failing serialization test**

```python
def test_ranking_report_serializes_without_runtime_paths() -> None:
    report = RankingReport.empty(project_limit=50, pages_per_project=12)

    assert report.to_dict() == {
        "schema_version": 1,
        "algorithm_version": "pgdp-rank/v1",
        "limits": {"projects": 50, "pages_per_project": 12},
        "corpus": {"projects_seen": 0, "projects_ranked": 0},
        "diagnostics": [],
        "projects": [],
    }
```

- [x] **Step 2: Run the test and confirm the missing package failure**

Run:

```bash
uv run pytest tests/test_pgdp_ranking.py::test_ranking_report_serializes_without_runtime_paths -q
```

Expected: fail because `pdomain_ocr_synth.pgdp` does not exist.

- [x] **Step 3: Add frozen typed records**

Define `Diagnostic`, `PageFeatures`, `RankedPage`, `RankedProject`,
`CorpusSummary`, `RankingLimits`, and `RankingReport` as frozen, slotted
dataclasses. Give each record an explicit `to_dict()` method with concrete return
types. Do not store `Path`, `Any`, timestamps, hostnames, or absolute source
paths in the report.

`PageFeatures` must expose these integer or boolean components:

```python
special_format: bool
italic_tags: int
bold_tags: int
small_caps_tags: int
dot_leaders: bool
aligned_fields: bool
table_like: bool
poetry_like: bool
quotation_like: bool
multipart_name: bool
illustration_or_ornament: bool
uncertainty_note: bool
```

Add `natural_page_key(name)` in `ordering.py`. Build keys from alternating case-folded text and
integer digit runs. Compare equal integers by original digit-run length. Then use the original full
name. The F2 parser and project ranker both import this function.

- [x] **Step 4: Run the record test**

Run:

```bash
uv run pytest tests/test_pgdp_ranking.py::test_ranking_report_serializes_without_runtime_paths -q
```

Expected: pass.

- [x] **Step 5: Commit the records**

```bash
git add src/pdomain_ocr_synth/pgdp tests/test_pgdp_ranking.py
git commit -m "feat: define PGDP ranking report records"
```

### Task 2: Parse F2 formatting controls without changing source text

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/f2.py`
- Create: `tests/test_pgdp_f2.py`

- [x] **Step 1: Write tests for local and continued blocks**

```python
def test_parse_local_block_preserves_text() -> None:
    result = parse_f2_pages({"p001.png": "before /*  <i>verse</i>  */ after"})

    assert result.pages[0].source_text == "before /*  <i>verse</i>  */ after"
    assert result.pages[0].special_blocks == ("  <i>verse</i>  ",)


def test_parse_continued_block_crosses_natural_page_order() -> None:
    result = parse_f2_pages(
        {
            "p10.png": "continued #/ tail",
            "p2.png": "head /# first",
            "p3.png": "middle",
        }
    )

    assert [page.name for page in result.pages] == ["p2.png", "p3.png", "p10.png"]
    assert [page.has_special_format for page in result.pages] == [True, True, True]
```

Also test nested controls, overlapping local and continued controls, unmatched openers and closers,
a non-object JSON root, and non-string values.

Add a cross-page fixture with italic tags and aligned rows on pages inside one
continued block. Assert that each parsed page exposes only its own valid
continued-block body. Reuse this fixture in Task 3 to assert per-page tag counts
and structural features.

- [x] **Step 2: Run the parser tests and confirm failure**

Run:

```bash
uv run pytest tests/test_pgdp_f2.py -q
```

Expected: fail because `parse_f2_pages` does not exist.

- [x] **Step 3: Implement the state machine**

Load UTF-8 JSON through `load_f2(path)`. Reject any root other than `dict[str, str]` with
`F2LoadError`. Sort pages with `natural_page_key` from Task 1.

Scan `/*`, `*/`, `/#`, and `#/` as exact ASCII controls. Keep `source_text` byte-equivalent after
UTF-8 decoding. Store valid block bodies and page-level continued-format membership. Emit stable
diagnostics for nested, overlapping, and unmatched controls. Exclude invalid block bodies from later
feature predicates.

- [x] **Step 4: Run all parser tests**

Run:

```bash
uv run pytest tests/test_pgdp_f2.py -q
```

Expected: pass.

- [x] **Step 5: Commit the parser**

```bash
git add src/pdomain_ocr_synth/pgdp/f2.py tests/test_pgdp_f2.py
git commit -m "feat: parse PGDP F2 formatting controls"
```

### Task 3: Extract and score version 1 page features

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/features.py`
- Create: `tests/test_pgdp_features.py`

- [x] **Step 1: Write one focused test per predicate**

Use parameterized tests for case-insensitive `<i>`, `<b>`, and `<sc>` opening tags with attributes.
Add separate tests for dot leaders, two aligned-field rows, and three table-like rows. Also test
poetry line shape, four quoted lines, common indentation, multipart page names, illustration and
decoration markers, and `[**` uncertainty notes.

Pin the complete score in one test:

```python
def test_page_score_exposes_every_component() -> None:
    features = PageFeatures(
        special_format=True,
        italic_tags=12,
        bold_tags=2,
        small_caps_tags=1,
        dot_leaders=True,
        aligned_fields=True,
        table_like=True,
        poetry_like=True,
        quotation_like=True,
        multipart_name=True,
        illustration_or_ornament=True,
        uncertainty_note=True,
    )

    score = score_page(features)

    assert score.total == 60
    assert score.components == {
        "special_format": 5,
        "italic_tags": 10,
        "bold_tags": 2,
        "small_caps_tags": 1,
        "leaders_or_fields": 8,
        "table_like": 8,
        "poetry_like": 8,
        "quotation_like": 6,
        "multipart_name": 6,
        "illustration_or_ornament": 4,
        "uncertainty_note": 2,
    }
```

- [x] **Step 2: Run the feature tests and confirm failure**

Run:

```bash
uv run pytest tests/test_pgdp_features.py -q
```

Expected: fail because the feature extractor does not exist.

- [x] **Step 3: Implement exact design predicates**

Count style tags across all valid F2 page text, including tags outside a special block. Apply dot
leader, aligned-field, table, poetry, and quotation predicates only to valid local or continued
block bodies. Use the full page's nonblank lines as the poetry comparison baseline.

Score both `dot_leaders` and `aligned_fields` through one eight-point component named
`leaders_or_fields`, so their overlap cannot double count. Cap each style-tag count at ten.

The exact score is:

```python
total = (
    5 * special_format
    + min(italic_tags, 10)
    + min(bold_tags, 10)
    + min(small_caps_tags, 10)
    + 8 * (dot_leaders or aligned_fields)
    + 8 * table_like
    + 8 * poetry_like
    + 6 * quotation_like
    + 6 * multipart_name
    + 4 * illustration_or_ornament
    + 2 * uncertainty_note
)
```

- [x] **Step 4: Run all feature tests**

Run:

```bash
uv run pytest tests/test_pgdp_features.py -q
```

Expected: pass.

- [x] **Step 5: Commit feature extraction**

```bash
git add src/pdomain_ocr_synth/pgdp/features.py tests/test_pgdp_features.py
git commit -m "feat: score PGDP typography and structure features"
```

### Task 4: Rank projects and select a bounded review queue

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/ranking.py`
- Modify: `src/pdomain_ocr_synth/pgdp/__init__.py`
- Modify: `tests/test_pgdp_ranking.py`

- [x] **Step 1: Write ranking and selection tests**

Create project fixtures under `tmp_path` with `project.json`, `rounds/F2.json`,
and selected image placeholders. Test these rules:

- directories without F2 are counted but excluded with a diagnostic;
- malformed metadata does not stop other projects;
- malformed `pages.json` produces a diagnostic and does not stop other projects;
- project score uses the ten highest page scores plus twenty per target group;
- projects sort by score then project ID;
- pages sort by score then natural page name;
- review selection uses the fixed group order before score fill;
- one page occupies one slot even if it covers several groups;
- missing images remain selected with `image_available: false`;
- limits must be positive;
- project and page caps keep only the highest-ranked entries;
- repeated runs return equal report objects.

- [x] **Step 2: Run ranking tests and confirm failure**

Run:

```bash
uv run pytest tests/test_pgdp_ranking.py -q
```

Expected: fail because `rank_corpus` does not exist.

- [x] **Step 3: Implement project discovery and natural ordering**

Discover only immediate directories named `projectID*`. Read correctly typed
`project.json` fields `projectid`, `title`, `author`, `genre`, `pages_total`, and
`pg_ebook_number`. Preserve missing optional fields as `None`.

Load `pages.json` as a string-to-string object and record `transcription_available` for each
selected F2 page. A missing or malformed `pages.json` adds a diagnostic and sets that field false
without excluding the project.

Build natural keys from alternating case-folded text and integer digit runs. Compare equal integers
by original digit-run length. Then use the original full name.

- [x] **Step 4: Implement project scores and review selection**

Define target groups as:

```python
mixed_typography = italic_tags > 0 or bold_tags > 0 or small_caps_tags > 0
table_like_structure = table_like or dot_leaders or aligned_fields
poetry = poetry_like
quotation = quotation_like
multipart_layout = multipart_name
```

Select groups in the design order, then fill by ranked pages. Store page names,
image availability, feature values, score components, and matched groups. Store
project metadata, component totals, selected pages, and sorted diagnostics.

After sorting, keep only the first `project_limit` projects. Within each project, stop review
selection at `pages_per_project`. Report counts before and after truncation.

- [x] **Step 5: Run ranking tests**

Run:

```bash
uv run pytest tests/test_pgdp_ranking.py -q
```

Expected: pass.

- [x] **Step 6: Commit ranking**

```bash
git add src/pdomain_ocr_synth/pgdp tests/test_pgdp_ranking.py
git commit -m "feat: rank PGDP projects and review pages"
```

### Task 5: Write stable JSON atomically

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/report.py`
- Modify: `tests/test_pgdp_ranking.py`

- [x] **Step 1: Write output tests**

```python
def test_write_report_is_byte_stable(tmp_path: Path) -> None:
    report = fixture_report()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    write_report(report, first)
    write_report(report, second)

    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes().endswith(b"\n")
```

Also test refusal when the output resolves inside the source corpus and cleanup when replacement
fails.

- [x] **Step 2: Run output tests and confirm failure**

Run:

```bash
uv run pytest tests/test_pgdp_ranking.py -k "write_report or output_inside" -q
```

Expected: fail because `write_report` does not exist.

- [x] **Step 3: Implement stable atomic output**

Serialize with `ensure_ascii=False`, `indent=2`, and `sort_keys=True`, followed by one newline.
Write a sibling temporary file, flush it, then use `Path.replace()`. Remove the temporary file after
an error. Reject output equal to or below the resolved corpus root.

- [x] **Step 4: Run output tests**

Run:

```bash
uv run pytest tests/test_pgdp_ranking.py -q
```

Expected: pass.

- [x] **Step 5: Commit output writing**

```bash
git add src/pdomain_ocr_synth/pgdp/report.py tests/test_pgdp_ranking.py
git commit -m "feat: write deterministic PGDP ranking reports"
```

### Task 6: Add the local-only CLI

**Files:**

- Modify: `src/pdomain_ocr_synth/cli.py`
- Modify: `tests/test_cli.py`
- Create: `tests/test_cli_rank_pgdp.py`

- [x] **Step 1: Write parser and end-to-end CLI tests**

Add `rank-pgdp` to `ALL_SUBCOMMANDS`. Pin this interface:

```text
pdomain-ocr-synth rank-pgdp CORPUS_ROOT \
  --output pgdp-ranking.json \
  --project-limit 50 \
  --pages-per-project 12
```

Test successful output, missing corpus root, non-directory root, nonpositive limits, unsafe output
placement, malformed projects with a successful partial report, and an output summary containing
projects seen, ranked, diagnostics, and selected pages.

- [x] **Step 2: Run CLI tests and confirm failure**

Run:

```bash
uv run pytest tests/test_cli.py tests/test_cli_rank_pgdp.py -q
```

Expected: fail because the parser does not know `rank-pgdp`.

- [x] **Step 3: Add parser and dispatch wiring**

Add the four arguments exactly as shown. Use defaults of 50 and 12. Make `--output` default to
`./pgdp-ranking.json`.

Convert expected input, validation, and safety errors into concise stderr messages and exit code 2.
Unexpected errors must still surface rather than being silently converted.

- [x] **Step 4: Run CLI tests**

Run:

```bash
uv run pytest tests/test_cli.py tests/test_cli_rank_pgdp.py -q
```

Expected: pass.

- [x] **Step 5: Commit CLI wiring**

```bash
git add src/pdomain_ocr_synth/cli.py tests/test_cli.py tests/test_cli_rank_pgdp.py
git commit -m "feat: add PGDP ranking CLI"
```

### Task 7: Verify the real corpus and document the result

**Files:**

- Modify: `docs/plans/README.md`
- Modify: `docs/context/current-state.md`
- Modify: `docs/usage/recipe-workflow.md`

- [x] **Step 1: Run the focused Python gate**

Run:

```bash
make lint AI=1
make typecheck AI=1
uv run pytest tests/test_pgdp_f2.py tests/test_pgdp_features.py tests/test_pgdp_ranking.py tests/test_cli_rank_pgdp.py tests/test_cli.py -q
```

Expected: all commands pass.

- [x] **Step 2: Run the ranker on the local corpus**

Run from outside the corpus:

```bash
uv run pdomain-ocr-synth rank-pgdp /workspaces/pdomain-data/pgdp-corpus \
  --output /tmp/pgdp-ranking.json \
  --project-limit 50 \
  --pages-per-project 12
```

Expected: exit 0, 286 projects seen, 285 projects ranked, and a bounded review queue. Inspect the
top five projects and twelve selected pages for the top project.

- [x] **Step 3: Prove byte determinism**

Run the same command with `/tmp/pgdp-ranking-2.json`, then compare:

```bash
cmp /tmp/pgdp-ranking.json /tmp/pgdp-ranking-2.json
```

Expected: exit 0 with no output.

- [x] **Step 4: Run full CI**

Run:

```bash
make ci AI=1
```

Expected: pass.

- [x] **Step 5: Update roadmap and current state with measured results**

Add M14 to `docs/plans/README.md`. Document `rank-pgdp`, all four arguments, its local-only
behavior, and its JSON output in `docs/usage/recipe-workflow.md`.

Record the actual project count, top-ranked project IDs, selected-page count, command, and
verification result in `docs/context/current-state.md`. Do not claim typography measurement or
synthesis shipped.

- [x] **Step 6: Run docgraph completion checks**

Run:

```bash
docgraph reindex
docgraph check --strict
```

Expected: zero blocking issues. Surface existing advisories separately from new issues.

- [x] **Step 7: Commit the verified slice**

```bash
git add docs/plans/README.md docs/context/current-state.md docs/usage/recipe-workflow.md
git commit -m "docs: record PGDP ranking milestone results"
```
