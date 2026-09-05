# Recipe workflow

## Agent Index

- **Kind:** usage
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-08-22
- **Provenance:** verified against the CLI, recipe system, bundled recipe, and PGDP ranking implementation
- **Disposition:** Replaces the implemented CLI spec and stale recipe tutorial as current usage.
- **Provenance note:** Promoted from the retired CLI and recipe-tutorial documents; see `docs/context/decisions.md`.

Create a recipe with the CLI, add licensed assets and a supported corpus, then
validate, preview, render, and optionally publish it.

## Create and locate a recipe

```bash
pdomain-ocr-synth init my-recipe
pdomain-ocr-synth list
```

`init` creates `recipes/my-recipe/recipe.yaml`, a recipe README, and empty
`corpora/`, `fonts/`, and `textures/` directories. Use `--dir` to choose another
parent or `--force` to replace an existing scaffold. A single YAML file under a
recipe search directory is also valid.

## Configure supported inputs

Set the recipe identity, seed, recognition or detection output, rendering, and
layout in YAML. Current corpus providers are `local`, `web`, and `wikisource`.
Do not copy catalog-only `web_list`, `hf_dataset`, Internet Archive, or
Gutenberg examples into a working recipe; validation rejects providers that
have no implementation.

The shipped transforms include whitespace normalization and the Gaelic-focused
lenition, Tironian-et, and long-s transforms used by `recipes/gaelic.yaml`.
Third-party reusable transforms can use the entry-point registry. The package
does not ship recipe-local inline Python or the cataloged `u_v_swap`,
`i_j_swap`, and ligature-marker transforms.

Use HarfBuzz rendering. Required fonts must exist and open successfully;
optional missing fonts produce warnings. Font coverage remains a render-time
boundary rather than a complete validation-time corpus scan. Use only registered
degradation stages; validation reports known but unimplemented stages.

## Rank a local PGDP corpus

```bash
pdomain-ocr-synth rank-pgdp /path/to/pgdp-corpus \
  --output ./pgdp-ranking.json \
  --project-limit 50 \
  --pages-per-project 12
```

`rank-pgdp` reads projects from the local `corpus_root` positional argument. It
does not use the network, an LLM, or a recipe. The command does not modify the
corpus, and the report path must be outside the corpus root. `--project-limit`
and `--pages-per-project` must be positive integers.

The command writes deterministic JSON to `--output`, which defaults to
`./pgdp-ranking.json`. The report contains schema and algorithm versions, the
requested limits, corpus counts, stable diagnostics, ranked projects, selected
pages, feature evidence, and score components. It does not contain absolute
source paths. Re-running the command with the same corpus and limits produces
the same report bytes.

## Profile selected PGDP scans

```bash
pdomain-ocr-synth profile-pgdp /path/to/pgdp-corpus \
  --ranking ./pgdp-ranking.json \
  --output ./pgdp-profile.json
```

`profile-pgdp` reads the selected pages in an M14 `rank-pgdp` report. Both
`--ranking` and `--output` are required. The profile output must be outside the
corpus root, differ from the ranking input, and name a file rather than a
directory.

The command measures scan geometry locally and writes deterministic JSON. It
stores corpus-relative source paths, source-byte hashes, observed ink geometry,
and non-fatal diagnostics. Missing or undecodable scans remain in the report as
excluded pages with diagnostics. A completed measurement returns exit code 0
even when diagnostics are present. Input errors return 2 and output errors
return 6.

## Align PGDP source lines with scan rows

```bash
pdomain-ocr-synth align-pgdp /path/to/pgdp-corpus \
  --profile ./pgdp-profile.json \
  --output ./pgdp-alignment.json
```

`align-pgdp` reads F2 source and the scans referenced by a
`pgdp-profile/v2` report. It writes a deterministic `pgdp-alignment/v3` report.
The output must be outside the corpus root, differ from the profile input, and
name a file rather than a directory. Source or scan changes remain explicit
exclusions instead of being silently realigned.

The report keeps UTF-8 source byte spans, normalized visible text, formatting
spans, source-frame candidate boxes, monotone alignment operations, costs,
residuals, and exclusion evidence. Accepted alignments require a single-column
page and four to 80 nonblank source lines eligible for matching. Matched
operations must cover at least 90 percent of those lines. Normalized cost must
be at most 0.22, and uniqueness margin at least 0.15. Confidence is always null
with `confidence_kind` set to `uncalibrated` in version 1.

## Measure typography from an alignment

```bash
pdomain-ocr-synth typography-pgdp /path/to/pgdp-corpus \
  --alignment ./pgdp-alignment.json \
  --profile ./pgdp-profile.json \
  --output ./pgdp-typography.json
```

`typography-pgdp` measures per-line baseline row, x-height, ascender and
descender extents, stroke width, skew slope, word runs, and per-word ink boxes
from the accepted pages of a `pgdp-alignment/v3` report, then pools them per
page, per book, and per page class into a deterministic `pgdp-typography/v1`
report.

The atlas is a render of the JSONL, not a second source. One grid per
character per tier holds every sample of that character in the book, sharded at
1,024 cells a sheet, so opening `atlas/transcribed/U+0065-000.png` shows every
`e` at once and a bad cut is obvious next to its neighbours. Cells are the
character's 95th-percentile extent and nothing is scaled; a larger glyph is
centre-cropped and its sheet records how many that happened to. Re-rendering
from the JSONL reproduces every sheet byte for byte, which is what makes the
atlas safe to ship. `--no-atlas` skips the render.

The command refuses to run unless the profile hashes to the value the alignment
report recorded, so the two inputs are provably the pair that produced each
other. On every page it rebuilds the same ink mask the alignment extractor
built and checks that the mask reproduces each matched candidate's recorded
`foreground_pixels` and `horizontal_ink_profile` exactly and that the rebuilt
Otsu threshold equals the recorded one. A page that fails is excluded as
`mask_mismatch` carrying both values.

Every value is a pixel count in the `source` frame with `confidence` null and
`confidence_kind` set to `uncalibrated`. The report names nothing the design
treats as latent: no font identity, nominal point size, advance, side bearing,
native word-space width, tracking, kerning, leading, or physical margin.

`--geometry` is optional and off by default. Without it the command behaves
exactly as it does without the flag existing. With it, the command reads an OCR
geometry JSONL produced elsewhere and checks what the recognizer read where each
matched line's first ink run sits. PGDP F2 rejoins a word broken across two
printed lines onto the line where it started, so the next line's first run has
no transcription word to bind to; the flag makes that visible. A page whose
geometry `image_sha256` disagrees with the alignment's `scan_sha256` gets no
witness. Nothing here runs OCR or opens a model.

Pooled estimates and per-page aggregates cover every accepted page. Per-line
and per-word rows are emitted only for the first `--evidence-pages` measured
pages of each book, which keeps a five-book run from emitting roughly 150,000
word records.

Exclusions cover missing or changed inputs, malformed F2 controls, unusable ink
bands, implausible line counts, persistent gutters, probable columns, tables,
illustrations, borders, and high foreground ratios. An excluded or proposed page
is evidence for review, not an accepted mapping. Candidate boxes remain in the
original scan frame. The command does not infer baselines, reading order across
columns, typography, font identity, semantics, rotation, or dewarping, and it
does not use OCR output as verification.

## Cut a glyph inventory

```bash
pdomain-ocr-synth glyphs-pgdp /path/to/pgdp-corpus \
  --alignment ./pgdp-alignment.json \
  --profile ./pgdp-profile.json \
  --geometry ./geometry-v1.jsonl \
  --output ./pgdp-glyphs/
```

`glyphs-pgdp` cuts one book's glyphs from its own scans and writes an inventory
directory: `glyphs.jsonl`, one row per glyph, and `manifest.json`, the
provenance and per-character coverage. The JSONL is the authority.

An inventory is per book. X-heights run 10 to 18 px across the five aligned
corpus books and glyph pixel sizes scale with them, so a pooled inventory would
be a chimera of sizes; the command refuses an alignment report covering more
than one book.

Glyphs carry one of two label tiers and the two never mix. A `transcribed`
glyph comes from a word on a line reconciled against PGDP F2, so its character
is a human proofer's. A `recognized` glyph comes from a word outside every
matched line, which is where the running head and the folio sit; proofers strip
both from F2, so the only label available is the OCR read that `--geometry`
supplies, and the row carries that read's confidence. Every row names its tier,
so a consumer can take digits from `recognized` while training characters only
on `transcribed`.

A glyph is cut only when the word's box splits at blank columns into exactly as
many ink runs as the word has alphanumeric characters. Measured over the five
aligned books, that holds for 0.256 to 0.799 of reconciled words; the rest fail
because letters touch, and the manifest records how many failed and why rather
than dropping them silently.

Quality is recorded and never enforced. Each row carries where its rows sit
against the line's x-height top and baseline, whether it reaches the line box's
own top or bottom row, and its ink density. The reference is the line box, not
the word box: a word box is tight to its own ink, so its tallest and lowest
glyphs always touch it.

The atlas is a render of the JSONL, not a second source. One grid per
character per tier holds every sample of that character in the book, sharded at
1,024 cells a sheet, so opening `atlas/transcribed/U+0065-000.png` shows every
`e` at once and a bad cut is obvious next to its neighbours. Cells are the
character's 95th-percentile extent and nothing is scaled; a larger glyph is
centre-cropped and its sheet records how many that happened to. Re-rendering
from the JSONL reproduces every sheet byte for byte, which is what makes the
atlas safe to ship. `--no-atlas` skips the render.

The command refuses to run unless the profile hashes to the value the alignment
report recorded, the same check `typography-pgdp` makes. A page whose geometry
`image_sha256` disagrees with the alignment's `scan_sha256` yields no furniture,
and the manifest counts those pages. The output directory gets an empty
`.nobackup` marker, because the whole inventory can be rebuilt from the corpus
and the two reports.

## Validate and render

```bash
pdomain-ocr-synth validate my-recipe
pdomain-ocr-synth lint my-recipe --strict
pdomain-ocr-synth fetch my-recipe
pdomain-ocr-synth preview my-recipe --count 200
pdomain-ocr-synth render my-recipe
```

Use `validate --offline` when checks must not touch the network. `fetch` warms
remote corpus caches and accepts `--cache-dir` and `--no-cache`; it does not
accept render controls. `preview --no-degrade` isolates the renderer from the
degradation pipeline. `render --resume` continues only when the saved snapshot
matches; `render --force` clears the destination, and the two flags cannot be
combined.

Recognition output is the simplest starting point. Detection requires a
paragraph or page layout and produces polygon annotations. See
[Output and publishing](../architecture/output-and-publishing.md) for exact
layouts and continuation guarantees.

## Inspect and publish

`describe my-recipe --format json` prints resolved configuration and corpus
information. `audit OUTPUT` reads the render audit; use `--global`,
`--audit-file`, time bounds, recipe-SHA filtering, limits, or `--summary` for
other views.

```bash
pdomain-ocr-synth publish my-recipe --dry-run
pdomain-ocr-synth publish my-recipe --repo OWNER/NAME --render-first
```

Publishing accepts visibility, license, tag, token, local-output, repository
creation, and dry-run controls. A custom message is accepted, but the current
large-folder Hub transport cannot apply it and reports that limitation.

## CLI reference

Run `pdomain-ocr-synth --help` or `pdomain-ocr-synth COMMAND --help` for the
exhaustive parser-generated option list. The command/configuration boundary and
schema implementation are recorded in
[Development and recipe system](../architecture/development-and-recipe-system.md).

## Detailed CLI contract

The tables below are drift-guarded against the parser and implementation. They
are retained here because parser help is exhaustive per command but does not
provide one reviewable cross-command contract.

## Invocation

```
pdomain-ocr-synth <subcommand> [options]
```

Installed as a console script via `pyproject.toml`:
```
[project.scripts]
pdomain-ocr-synth = "pdomain_ocr_synth.cli:main"
```

## Subcommands

| Command | Purpose |
|---------|---------|
| `init <name>` | Scaffold a new recipe directory with a commented template |
| `list` | List recipes discovered on the recipe search path |
| `validate <recipe>` | Schema-check a recipe; verify fonts and corpus paths |
| `lint <recipe>` | Run `validate` + heuristic lint checks (M10) |
| `describe <recipe>` | Print resolved config + corpus stats (word count, etc.) |
| `schema` | Emit the recipe JSON Schema (default: write `docs/specs/recipe.schema.json`) |
| `fetch <recipe>` | Pre-fetch and cache all web/HF corpora for a recipe |
| `preview <recipe>` | Render N samples to a preview directory for visual review |
| `render <recipe>` | Full run; writes the dataset to the output destination |
| `publish <recipe>` | Upload rendered output to a Hugging Face dataset repo (see [10 — Publishing](../architecture/output-and-publishing.md)) |
| `clean <recipe>` | Remove cached corpora (and optionally rendered output) |
| `audit [output-dir]` | Read back the per-render audit JSONL log written by `render` (M10) |
| `rank-pgdp <corpus_root>` | Rank local PGDP projects and select bounded review pages |
| `profile-pgdp <corpus_root>` | Measure selected local PGDP scan geometry |
| `align-pgdp <corpus_root>` | Align PGDP F2 source lines with measured scan lines |
| `typography-pgdp <corpus_root>` | Measure font-free typographic observables from an alignment |
| `glyphs-pgdp <corpus_root>` | Cut a per-book labelled glyph inventory from an alignment |

## Render-family options

Apply to `preview` and `render` (and to `publish` via
`--render-first`):

| Flag | Meaning |
|------|---------|
| `-c, --count N` | Override sample count from the recipe |
| `-o, --output PATH` | Override output destination |
| `-s, --seed N` | Override random seed (default from recipe, then 0) |
| `-w, --workers N` | Parallel render workers (default: CPU count) |
| `--cache-dir PATH` | Corpus cache root (default: `~/.cache/pdomain-ocr-synth/`) |
| `--no-cache` | Bypass corpus cache (force re-fetch) |
| `--dry-run` | Validate + plan only; no fetch, no render |

`fetch` is corpus-only. It walks `recipe.corpus` and warms the cache, so it
accepts only the two cache-related flags: `--cache-dir` and `--no-cache`. The
other render-family flags above, `--count`, `--output`, `--seed`, `--workers`,
and `--dry-run`, have no meaning at fetch time. The `fetch` subparser does not
accept them.

## Per-subcommand flags

The following tables cover flags outside the render-family set. Each table is
the canonical surface for its subcommand. A flag listed here must exist in the
parser, and every parser flag must appear here. A meta-test in
`tests/test_spec_docs.py` enforces both directions.

### `init <name>`

| Flag | Meaning |
|------|---------|
| `--dir PATH` | Directory to scaffold under (default: `./recipes`) |
| `--force` | Overwrite an existing recipe with the same name |

### `validate <recipe>`

| Flag | Meaning |
|------|---------|
| `--offline` | Skip network-touching checks |

### `lint <recipe>`

| Flag | Meaning |
|------|---------|
| `--offline` | Skip network-touching checks (forwarded to validate) |
| `--json` | Emit a JSON object of validation + lint issues (machine-readable) |
| `--strict` | Treat lint warnings as failures: exit 1 if any warning is present (validation errors still take precedence with exit 3); use as a CI / pre-commit gate |

### `describe <recipe>`

| Flag | Meaning |
|------|---------|
| `--format {text,json}` | Output format (default: text) |

### `schema`

| Flag | Meaning |
|------|---------|
| `-o, --output PATH` | Write the schema to this path instead of stdout |

### `preview <recipe>`

| Flag | Meaning |
|------|---------|
| `--no-degrade` | Skip the recipe's degradation pipeline; output raw render only |

### `render <recipe>`

| Flag | Meaning |
|------|---------|
| `--force` | Clear destination before render |
| `--resume` | Resume an interrupted render (mutually exclusive with `--force`) |
| `--no-audit` | Suppress the per-run audit JSONL line under `<output>/_audit.jsonl` |

### `publish <recipe>`

| Flag | Meaning |
|------|---------|
| `--repo OWNER/NAME` | Override the recipe's `publish.hf_dataset.repo` |
| `--private` / `--public` | Force visibility (overrides recipe default) |
| `--license SPDX` | Override the recipe's dataset license |
| `--tag NAME` | Pin the upload to a release tag |
| `--message TEXT` | Custom commit message for the dataset upload |
| `--token TOKEN` | HF auth token (overrides env / cached login) |
| `-o, --output PATH` | Override the local render output path being uploaded |
| `--render-first` | Run `render` before publishing (chained step) |
| `--no-create` | Refuse to create the repo if it doesn't exist (default: create on first publish) |
| `--dry-run` | Preview the publish plan without uploading |

### `clean <recipe>`

| Flag | Meaning |
|------|---------|
| `--cache-dir PATH` | Cache root (default: `$PD_OCR_SYNTH_CACHE` or `~/.cache/pdomain-ocr-synth`) |

### `audit [output-dir]`

The positional `output_dir` is required *unless* `--global` or
`--audit-file` is passed.

| Flag | Meaning |
|------|---------|
| `--audit-file PATH` | Read audit entries from this JSONL path instead of `<output_dir>/_audit.jsonl`; useful for archived or aggregated audit logs |
| `--global` | Read entries from the global aggregate at `<cache_root>/audit.jsonl` (default `~/.cache/pdomain-ocr-synth/`); mutually exclusive with `--audit-file` |
| `--json` | Emit a JSON array of entries (machine-readable) instead of the table |
| `--limit N` | Only show the most recent N entries (tail behaviour) |
| `--since ISO` | Only show entries with timestamp >= this ISO-8601 value (e.g. `2026-05-06` or `2026-05-06T10:30:00Z`); applied before `--limit` |
| `--until ISO` | Only show entries with timestamp <= this ISO-8601 value (same parser as `--since`); applied before `--limit` |
| `--recipe-sha PREFIX` | Only show entries whose `recipe_sha` starts with this hex prefix (case-insensitive); entries with a null sha are excluded |
| `--summary` | Print aggregate statistics over the matched entries instead of the per-row table; combine with `--json` for a single JSON object |

### `rank-pgdp <corpus_root>`

The positional `corpus_root` is the local PGDP corpus directory.

| Flag | Meaning |
|------|---------|
| `--output PATH` | Write the JSON report here (default: `./pgdp-ranking.json`); the path must be outside the corpus root |
| `--project-limit N` | Limit the number of ranked projects in the report (default: 50; must be positive) |
| `--pages-per-project N` | Limit selected review pages per reported project (default: 12; must be positive) |

### `profile-pgdp <corpus_root>`

The positional `corpus_root` is the local PGDP corpus directory. The command
profiles only the selected pages in the supplied M14 ranking report, unless
`--whole-book` widens what it measures.

| Flag | Meaning |
|------|---------|
| `--ranking PATH` | Read this required `pgdp-rank/v1` JSON report |
| `--output PATH` | Write the required `pgdp-profile/v2` JSON report here; it must be outside the corpus root, differ from `--ranking`, and not name a directory |
| `--whole-book` | Measure every page image in each ranked project directory, but emit only the ranked pages |

`--whole-book` separates what is measured from what is reported. Book-level
estimates describe a book, so they are pooled over every page of it. The
emitted page list is unchanged, so a later `align-pgdp` run still sees the
ranking's selection. Profiling costs about 9.5ms per page against alignment's
1s, which is why the two stages take different page sets.

The run prints `pages pooled` alongside `pages measured` in this mode, and each
pooled estimate records the pages that contributed in `evidence_pages`.

Whole-book measurement also fits per-book page templates. A book whose first ink
band holds a steady position across the volume gets templates for its normal
recto, normal verso, and chapter-opening pages, and every page is classified
against them as `normal_recto`, `normal_verso`, `chapter_opening`, or `unknown`.
A book whose first band wanders gets no templates and every page classifies
`unknown`.

The class decides which bands `align-pgdp` ignores. A normal page's first band
is its running head, which is printed but deleted from F2, so no candidate is
emitted for it. Every other class suppresses nothing. Front matter and plates
have no class of their own because the corpus offers no discriminator for them.

### `align-pgdp <corpus_root>`

The `corpus_root` positional argument is the local PGDP corpus directory.
The command aligns F2 source lines with candidates derived from the referenced
corpus scans. Those scans must still be available and match the supplied M15a
`profile-pgdp` report.

| Flag | Meaning |
|------|---------|
| `--profile PATH` | Read this required `pgdp-profile/v2` JSON report |
| `--output PATH` | Write the required `pgdp-alignment/v1` JSON report here; it must be outside the corpus root, differ from `--profile`, and not name a directory |

### `typography-pgdp <corpus_root>`

The `corpus_root` positional argument is the local PGDP corpus directory. The
command measures typographic observables from the accepted pages of an
alignment report, and it opens no font, renders no text, and never leaves the
`source` coordinate frame.

| Flag | Meaning |
|------|---------|
| `--alignment PATH` | Read this required `pgdp-alignment/v3` JSON report |
| `--profile PATH` | Read this required `pgdp-profile/v2` JSON report; it must hash to the value the alignment recorded |
| `--output PATH` | Write the required `pgdp-typography/v1` JSON report here; it must be outside the corpus root, differ from both inputs, and not name a directory |
| `--evidence-pages N` | Emit per-line and per-word rows for this many measured pages per book (default 12) |
| `--geometry PATH` | Optional OCR geometry JSONL for this book. Marks a line whose first ink run is a continuation fragment the transcription does not carry |

### `glyphs-pgdp <corpus_root>`

The `corpus_root` positional argument is the local PGDP corpus directory. The
command cuts one book's glyph inventory from its own scans and writes it as a
directory. It opens no font, renders no text, runs no OCR, and never leaves the
`source` coordinate frame.

| Flag | Meaning |
|------|---------|
| `--alignment PATH` | Read this required `pgdp-alignment/v3` JSON report; it must cover exactly one book |
| `--profile PATH` | Read this required `pgdp-profile/v2` JSON report; it must hash to the value the alignment recorded |
| `--output PATH` | Write the required `pgdp-glyphs/v1` inventory directory here; it must be outside the corpus root and must not name a file |
| `--geometry PATH` | Optional OCR geometry JSONL for this book. Harvests the running head and the folio as the `recognized` label tier |
| `--no-atlas` | Write the JSONL and manifest without rendering the per-character atlas |

## Audit log schema

Each `render` invocation appends one JSONL line to
`<output_dir>/_audit.jsonl`. Unless `PD_OCR_SYNTH_NO_GLOBAL_AUDIT=1` is set,
it also mirrors that line to `<cache_root>/audit.jsonl`. The shape below is the
contract that `audit` reads and that tools such as `jq` and
`pandas.read_json(lines=True)` receive.

The on-disk fields appear in the order shown. This order keeps identity first,
provenance second, the run outcome last, and the schema-version anchor at the
end when using `cat _audit.jsonl`.

A meta-test in `tests/test_spec_docs.py` keeps this table in sync with the
`AuditEntry` dataclass in `src/pdomain_ocr_synth/audit.py`. Adding a field to
either one without adding it to the other is a hard test failure.

| Field | Type | Since | Description |
|-------|------|-------|-------------|
| `timestamp` | string | v1 | ISO-8601 UTC, second precision, `Z` suffix (e.g. `2026-05-06T10:30:00Z`); finalized after the render completes |
| `recipe_name` | string | v1 | `recipe.name` verbatim (free-text identifier) |
| `recipe_sha` | string \| null | v1 | SHA-256 hex of the on-disk recipe YAML bytes, or `null` when the recipe was constructed in-memory (no `source_path`) |
| `output_dir` | string | v1 | Absolute path the writer wrote into |
| `count` | integer | v1 | Effective sample count (post `--count` override) |
| `seed` | integer | v1 | Effective seed (post `--seed` override) |
| `workers` | integer | v1 | Worker pool size as the runner saw it |
| `rendered` | integer | v1 | Samples rendered (from `RunResult`) |
| `skipped` | integer | v1 | Samples skipped, e.g. by `--resume` (from `RunResult`) |
| `runtime_seconds` | float | v1 | Wall time of the render, from the writer's stats |
| `schema_version` | integer | v1 | On-disk shape version; bumps on shape changes (current: `1`) |

### Forward-compatibility policy

The `audit` reader skips rows whose `schema_version` does not match the version
it understands. It emits an `AuditSchemaVersionWarning` naming the encountered
version. A v1 reader cannot trust v2 field semantics. A future bump might
rename `count` to `planned_count` or change `runtime_seconds` from float
seconds to integer milliseconds. Silently summing those rows would produce
wrong totals. Rows without `schema_version` are treated as legacy v1. The field
was introduced in v1, so its absence implies pre-versioning or hand-edited
input.

## Lint codes

Every issue from `lint <recipe>`, beyond validation errors forwarded from
`validate`, carries a stable `code` field. The catalog below uses codes that
appear verbatim in human-readable output, the `--json` payload, and structured
logs. They are safe to grep or filter.

A meta-test in `tests/test_spec_docs.py` keeps this table in sync with the
`LINT_CODES` constant in `src/pdomain_ocr_synth/lint.py`. Adding a lint helper
or code to only one of them is a hard test failure.

| Code | Trigger |
|------|---------|
| `lint_degradation_always_certain` | Every degradation stage has `probability=1.0`; every sample receives identical augmentation, defeating the point of randomized augmentation. |
| `lint_single_font` | Recipe declares one or zero fonts; models trained on a single typeface tend to overfit to its rasterization quirks. |
| `lint_no_text_transforms` | Recipe declares no `text_transforms`; suspicious for historical-typography targets where the corpus is in modern spelling. |
| `lint_low_sample_count` | `output.count` is below 100, the suggested minimum for a useful training run; usually a forgotten `--count` flag or misconfigured recipe. |
| `lint_seed_default` | `seed` is left at the schema default of `0`; every render of every fork produces bit-identical samples. Set an explicit seed in the recipe. |
| `lint_zero_weight_font` | A declared font has `weight=0.0` and will never be sampled; almost always a typo or a leftover from a temporarily disabled font. |
| `lint_all_optional_fonts` | Every font is marked `optional=True`; if no font files are present on disk the loader ends up with an empty font set and rendering fails. |

All lint issues use `severity="warning"`. A recipe that triggers every lint
check still renders correctly. Lint alone never exits non-zero unless
`--strict` is passed. See the exit codes below.

## Validation codes

Every issue from `validate <recipe>` carries a stable `code` field, as do the
validation phases of `lint <recipe>`, `render`, `preview`, `fetch`, and
`publish`. Each issue also carries `severity` and a free-form `message`. The
codes appear verbatim in the human-readable `[severity] [code] location:
message` output, the `--json` payload, and structured logs. They are safe to
grep or filter.

A meta-test in `tests/test_spec_docs.py` keeps this table in sync with the
`VALIDATION_CODES` constant in `src/pdomain_ocr_synth/validation.py`. Adding
an emission site or code to only one of them is a hard test failure. A second
test in `tests/test_validation.py` asserts that every code emitted by
`validate_recipe` belongs to `VALIDATION_CODES`. A new code therefore cannot
ship undocumented.

| Code | Severity | Trigger |
|------|----------|---------|
| `schema_version_unsupported` | error | `schema_version` is not in `SUPPORTED_SCHEMA_VERSIONS`. Defensive — pydantic normally rejects this on load. |
| `output_destination_unresolved` | error | `output.destination` still contains `${VAR}` or starts with `~`; the env var isn't set, or the recipe was passed unresolved. |
| `output_destination_unwritable` | error | No writable ancestor exists for `output.destination` — typically a permission problem or a path under a non-existent mount. |
| `output_layout_mode_mismatch` | error | `output.mode` and `layout.mode` aren't a valid pairing (recognition needs `word_crops`/`lines`; detection needs `paragraphs`/`pages`). See [spec 08](../architecture/output-and-publishing.md). |
| `optional_font_missing` | warning | A font marked `optional: true` doesn't exist on disk; it will be skipped at render time. |
| `font_missing` | error | A required (non-optional) font path doesn't exist. |
| `font_unreadable` | error | The font file exists but `open_font` couldn't parse it (corrupt header, unsupported format). |
| `font_empty` | error | The font opened but reports zero glyphs or an empty cmap; almost always a placeholder or stub file. |
| `local_corpus_missing` | error | A `type: local` corpus references a `path:` that doesn't exist on disk. |
| `corpus_provider_not_implemented` | error | A `corpus[].type` is structurally valid but no runtime provider is registered for it (typically a future provider type listed in spec 04 that hasn't shipped yet). |
| `corpus_max_chars_not_implemented` | error | A corpus entry sets `max_chars` to a value other than the schema default; the option is reserved by spec 04 but not yet honored. |
| `corpus_min_word_length_not_implemented` | error | A corpus entry sets `min_word_length` to a value > 1; reserved by spec 04, not yet honored. |
| `text_transform_not_implemented` | error | A `text_transforms[].kind` is structurally valid but isn't yet implemented by `pdomain_ocr_synth.text_transforms` (e.g., a future kind from spec 05). |
| `shaping_engine_not_implemented` | error | `rendering.shaping_engine` is set to a value other than the implemented engine; reserved for future engines per spec 06. |
| `antialiasing_disable_not_implemented` | error | `rendering.antialiasing` is `false`; the renderer doesn't yet support disabling AA per spec 06. |
| `layout_key_unused` | warning | A layout key is set but doesn't apply to the active `layout.mode` (e.g., `paragraph_spacing` under `paragraphs`). It will be ignored. |
| `degradation_kind_unknown` | error | A `degradation[].kind` isn't in `KNOWN_DEGRADATION_KINDS` — typically a typo or a kind from a future spec bump. |
| `degradation_kind_not_implemented` | error | The `kind` is in the spec catalog but no runtime stage class is registered; the recipe declares a stage the renderer can't apply. |
| `degradation_stage_unknown_option` | error | A degradation stage carries an option key the registered stage class doesn't accept (typo or stale field name). |
| `paper_texture_missing_directory` | error | A `kind: paper_texture` stage doesn't set `directory:`; required by spec 07. |
| `paper_texture_directory_missing` | error | The configured `paper_texture` directory doesn't exist on disk. |
| `paper_texture_directory_not_dir` | error | The configured `paper_texture` directory path exists but isn't a directory. |
| `publish_description_file_missing` | warning | `publish.hf_dataset.description_file` is set but the file doesn't exist; publish will skip it. |
| `publish_repo_placeholder` | warning | `publish.hf_dataset.repo` looks like the scaffold placeholder (`CHANGE-ME/...` or no `/`); edit it before publishing or pass `--repo`. |

## Recipe resolution

A recipe argument may be:

1. A path to a YAML file (`./my-recipe.yaml`)
2. A name resolvable on the recipe search path (`gaelic` → `recipes/gaelic.yaml`)

The search path is, in order:

1. `$PD_OCR_SYNTH_RECIPES` (colon-separated)
2. `./recipes/` relative to CWD
3. `<package>/recipes/` shipped with the install

`list` walks this path and prints `name → path`.

## Examples

```bash
# Scaffold a new recipe
pdomain-ocr-synth init fraktur
# → creates ./recipes/fraktur/recipe.yaml + README

# Validate the Gaelic recipe ships
pdomain-ocr-synth validate gaelic

# Pre-fetch corpora once (writes to ~/.cache/pdomain-ocr-synth/)
pdomain-ocr-synth fetch gaelic

# Render 200 samples to a temp dir for visual inspection
pdomain-ocr-synth preview gaelic --count 200 --output /tmp/gaelic-preview

# Full render (50k samples per the recipe) into the trainer profile dir
pdomain-ocr-synth render gaelic

# Override count and output for a quick sanity run
pdomain-ocr-synth render gaelic -c 500 -o /tmp/gaelic-500

# Publish the rendered output to a Hugging Face dataset repo
pdomain-ocr-synth publish gaelic                            # uses recipe defaults
pdomain-ocr-synth publish gaelic --repo me/pdomain-ocr-synth-ga  # explicit repo
pdomain-ocr-synth publish gaelic --tag v2026.05.05          # pin a release
pdomain-ocr-synth publish gaelic --dry-run                  # preview only
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic error (also: `lint --strict` with warnings present) |
| 2 | CLI usage error (bad flags, unknown subcommand) |
| 3 | Recipe validation failed |
| 4 | Corpus fetch failed |
| 5 | Render failed (partial output may exist) |
| 6 | Output destination invalid or unwritable |
| 7 | Publish failed (auth, network, or repo-state error) |

`lint --strict` changes a clean run with validation or lint warnings from exit
code 0 to 1. It can therefore serve as a CI or pre-commit gate. Validation
errors keep their stricter exit code 3 either way. Strict mode never
*downgrades* a stricter exit code.

## Logging

- Default: human-readable progress to stderr; results summary to stdout.
- `--log-format json` emits one JSON record per line (for piping into
  `jq`, log collectors, or wrapping scripts).
- Render reports rate (samples/sec), ETA, and a final manifest path.

## Evidence

- Code: `src/pdomain_ocr_synth/cli.py`, `src/pdomain_ocr_synth/recipe/`,
  `src/pdomain_ocr_synth/corpus/providers/`, `src/pdomain_ocr_synth/validation.py`,
  and `recipes/gaelic.yaml`.
- Tests: `tests/test_cli.py`, `tests/test_recipe_loader.py`,
  `tests/test_validation.py`, `tests/test_cli_preview.py`, and
  `tests/test_cli_render.py`.
- Verified: 2026-07-14 by repository inspection during the docgraph migration.
