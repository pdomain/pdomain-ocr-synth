# PGDP Source-Line Alignment Design

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-08-23
- **Last verified:** 2026-08-23
- **Provenance:** derived from the active PGDP typography design, shipped M14 and M15a code, local
  corpus inspection, and owner direction in this session
- **Disposition:** Active M15b design for conservative F2 source-line alignment.
- **Read when:** implementing or reviewing PGDP line candidates, F2 source spans, or scan-to-text
  alignment.
- **Search terms:** PGDP, M15b, F2, source line, alignment, dynamic programming, gutter, ink band.

M15b will align byte-preserved F2 source lines to scan line candidates on eligible single-column
pages. It will preserve ambiguity instead of turning weak matches into typography evidence.

## Goal

Produce deterministic page-level alignment evidence that later measurement stages can use without
losing the original F2 bytes or scan coordinate frame.

## Architecture

The pipeline creates two ordered sequences. A lossless F2 tokenizer emits source lines with stable
UTF-8 byte spans, visible analysis text, formatting spans, and continued-block identity.

A two-dimensional image pass emits conservative line candidates. It rejects pages with a likely
column gutter.

A monotone dynamic program aligns the sequences with one-to-one match, source-skip, and
candidate-skip operations. A separate `pgdp-alignment/v1` report stores every operation, cost
component, exclusion, input hash, and method version. It does not modify `pgdp-profile/v1`.

## Tech Stack

Use Python 3.13, frozen dataclasses, Pydantic, Pillow, NumPy, argparse, pytest, Ruff, and
basedpyright. Do not add an OCR engine or network dependency.

## Global Constraints

- Preserve every F2 source string and address it with UTF-8 half-open byte spans.
- Keep all image geometry in the original source frame.
- Keep `pgdp-rank/v1` and `pgdp-profile/v1` byte compatible.
- Process one full-resolution image at a time.
- Keep processing local and deterministic.
- Treat numeric confidence as uncalibrated in version 1.
- Exclude uncertain pages and lines instead of manufacturing evidence.
- Write reports atomically outside the source corpus.

## Version 1 has a narrow eligibility gate

M15b accepts a selected page only when all required source and scan evidence is present. The F2
page must parse without a source-span-breaking control error.

The corresponding M15a page must have a readable source-frame image, foreground bounds, and at
least two retained ink bands.

The image pass searches for a persistent vertical whitespace gutter inside the foreground bounds.
Its versioned detector removes border components and long horizontal rules before measuring column
occupancy. The implementation plan fixes the numeric detector constants in tested code and records
them in the report. Any constant change requires a new algorithm version.

The page is also excluded when it is blank, border-dominated, high-foreground, or missing either
input page. It is excluded when it falls outside the 4-to-80 visible-line range or has an invalid
continued-block state.

Table, illustration, and persistent-gutter evidence also exclude the page. Braces and ornaments may
pass the mechanical gate, but the result thresholds below still exclude low-quality alignments.
Table evidence reuses the versioned M14 aligned-field predicate on the same F2 snapshot. It requires
three table-like rows. Illustration evidence reuses the M14 bracketed illustration or decoration
marker. The report names both predicate method versions and records their source lines.

A compatibility adapter builds the existing `ParsedF2Page` feature input only from the tokenized
snapshot. Parity tests require the adapter to reproduce current valid-page features and bind every
table or illustration predicate to its tokenized source-line ordinal.

These thresholds are algorithm constants. Changing any threshold requires a new algorithm version.

## F2 tokenization preserves source bytes

The tokenizer reads each JSON string as Unicode and computes offsets in its UTF-8 encoding. It
splits on `\n`, `\r\n`, and `\r` while retaining each separator's byte span. Each `SourceLine`
contains the page name, zero-based ordinal, full and content byte spans, and a separator byte span.
It also contains original text, normalized visible text, formatting spans, and continued-block
identifiers.

Normalization is an analysis view, not a replacement string. It preserves visible case,
punctuation, spacing, and Unicode code points.

It normalizes `\r\n` and `\r` to `\n`. It deletes valid F2 control markers, proof notes, and
recognized `i`, `b`, `sc`, `f`, `g`, and `tb` tags. It records ordered `copy`, `delete_control`,
`delete_tag`, `delete_note`, and `normalize_newline` operations.

Concatenating operation output must reproduce the normalized text. Every operation addresses a
UTF-8 half-open byte range in the original string. The report records normalization method
`pgdp-f2-visible/v1`.

The tokenizer emits style runs with normalized character offsets and source UTF-8 byte offsets.
Standalone `tb` is a zero-width structural marker. Unknown tags remain visible, add a diagnostic,
and exclude the affected line from later style fitting.

Formatting spans refer to UTF-8 byte offsets in the original page string. Local `/* ... */` spans
and cross-page `/# ... #/` spans receive stable identifiers. The identifiers derive from block kind,
opening page, opening byte offset, and, when available, closing page plus closing byte offset. An
open continued block keeps the same identifier on every page. An unmatched or overlapping control
produces a diagnostic and makes affected lines ineligible for matching.

Blank visible lines remain in the source record but do not enter the dynamic-program sequence.
Their absence is explicit, so a later reader can reconstruct the exact source-line ordering.

## Image candidates use connected components in two dimensions

M15a row-projection ink bands are useful evidence but can merge neighboring lines and mistake rules
for text. Candidate extraction receives the validated M15a foreground bounds and all retained bands.
It requires at least two bands. Within each band's half-open y-range, M15b derives the tight
foreground x-range and creates one initial two-dimensional box. It rejects empty bands.

It labels and removes full-frame border components before clipping the mask to M15a bands. This
prevents one surrounding border from becoming several band-local candidates. It then removes long
rules and joins compatible components using vertical overlap, center distance, and horizontal gap.

Each candidate stores its contributing M15a band ordinal, a half-open source-frame box, component
count, foreground pixel count, width, height, fill ratio, and normalized horizontal ink profile. At
most one retained candidate represents a band. Candidates sort by band ordinal, then box
coordinates and stable component ordinal.

If the deterministic join rules leave several component clusters in one band, version 1 does not
union them or choose one. It excludes the page as `fragmented_band` and preserves every sorted
cluster as rejected evidence.

Version 1 removes page-border components and long horizontal rules before joining candidates. It
records rejected components and reasons. The implementation fixes and tests every component,
joining, and gutter threshold, then serializes the effective constants. A future reviewed corpus
may replace those constants under a new algorithm version.

Candidate extraction does not claim baselines, glyphs, words, reading order across columns, or
rectified geometry.

## Monotone alignment records every edit operation

The dynamic program operates on visible nonblank source lines and ordered image candidates. It may
emit these operations:

| Operation | Source lines | Candidates | Base cost |
|---|---:|---:|---:|
| `match` | 1 | 1 | 0.00 |
| `skip_text` | 1 | 0 | 1.00 |
| `skip_image` | 0 | 1 | 1.00 |

A match adds weak, normalized costs for:

- width agreement between visible source length and candidate ink width;
- indentation agreement between source leading space and candidate left edge;
- vertical-gap agreement with blank source lines;
- weak style agreement between retained F2 style spans and candidate height or density.

The implementation plan fixes each formula and weight in tests. All arithmetic uses Python binary64
values. JSON serialization stores exact computed values without display rounding.

The selected path has the lowest total cost. Equal-cost transitions prefer `match`, then
`skip_image`, then `skip_text`. Source and candidate ordinals break any remaining ties. This rule
makes repeated runs byte-identical.

The algorithm is deliberately visual. It does not compare recognized scan text because M15b must
not use OCR output as its own verification signal.

## Acceptance separates page and line evidence

Version 1 reports `confidence: null` and `confidence_kind: "uncalibrated"`. It exposes costs and
acceptance states instead of converting them into unsupported probabilities.

A page is accepted when all of these conditions hold:

- the page has between 4 and 80 eligible source lines;
- no border-dominated, high-foreground, persistent-gutter, table, illustration, or malformed-control
  exclusion applies;
- at least 90 percent of eligible source lines participate in a match;
- the absolute source-line and candidate count difference is no more than the larger of 2 and 10
  percent of the source-line count;
- normalized total path cost is at most `0.22`;
- the absolute total cost of the second-best complete path exceeds the best complete path by at
  least `0.15`.

An individual match is usable only when it belongs to an accepted page. Skipped and rejected items
remain serialized with their reasons.

These are conservative seed thresholds. Corpus review in this milestone measures precision and
coverage but does not tune against the held-out test partition. Any later calibration creates a new
algorithm version or an explicit calibrated successor field.

## The alignment report is a separate wire contract

The report uses schema version `1` and algorithm version `pgdp-alignment/v1`. Its checked-in JSON
Schema is `schemas/pgdp-alignment-v1.schema.json`.

The top level contains:

- schema and algorithm versions;
- tool version;
- a safe profile label containing only its file name and its SHA-256 hash;
- method identifiers and every eligibility, extraction, cost, and acceptance constant;
- naturally ordered projects and pages;
- corpus-level diagnostics.

Each page contains source page identity, F2 source SHA-256, scan SHA-256, source frame, exact source
lines, style runs, image candidates, and alignment operations. It also contains total and second-best
costs, matched-line coverage, width residual, indentation residual, best-to-next-path margin,
acceptance state, exclusions, diagnostics, and uncalibrated confidence fields.

State is `accepted`, `proposed`, or `excluded`. The report does not embed scan bytes or absolute
paths.

Unknown major schema or algorithm versions fail validation. Version 1 readers accept additive
unknown fields as opaque JSON values and preserve them unchanged when rewriting. Readers may not
assign meaning or defaults to an unknown field.

## Snapshot validation prevents mixed evidence

The command reads an M15a profile report and live corpus files. It validates the profile structure
and SHA-256 before processing. It stores only `Path(profile_path).name` as the safe profile label;
it never serializes the supplied path.

It checks project and page identities against the profile. For each project, it reads, hashes, and
parses F2 exactly once. It then binds every page to that immutable parsed value. After all project
pages finish, it hashes F2 again. A changed hash discards every provisional project alignment and
excludes all its pages as `source_changed`.

Each scan uses `open_image_snapshot`. The pipeline compares that snapshot's SHA-256 with M15a before
decoding, then decodes and extracts candidates from the same seekable snapshot bytes. After the
snapshot closes, it hashes the live path again. A different live hash excludes the page as
`source_changed`; candidate evidence from the snapshot is not accepted.

M15b maps inherited M15a diagnostics explicitly. `blank_page` stays unchanged. `one_ink_band` and
`no_ink_bands` map to `insufficient_ink_bands`. `border_dominated`, `high_foreground_ratio`,
`image_missing`, `image_unreadable`, `image_decode_failed`, and `foreground_bounds_unavailable` stay
unchanged. Any other inherited code, including an empty code, excludes the page as
`inherited_profile_diagnostic` before candidate extraction while preserving the original code and
message. This prevents additive profile diagnostics from silently weakening eligibility.

If a scan changes during its page measurement, that page is excluded as `source_changed`. A profile
scan hash mismatch excludes the page as `scan_hash_mismatch`. The project-wide rule above handles F2
mutation coherently. Missing and malformed inputs add diagnostics and do not stop other projects.

The command records all effective input hashes in the output. This makes an alignment report a
snapshot of exact source evidence rather than a claim about a mutable corpus directory.

## The CLI fails safely

The command is:

```text
pdomain-ocr-synth align-pgdp CORPUS_ROOT \
  --profile profile.json \
  --output alignment.json
```

Both file flags are required. The output must be a file outside the corpus root and must not resolve
to the profile input. Writes reuse the existing atomic report writer.

Malformed report structure, unsupported versions, invalid limits, and unusable output paths return
the repository's validation or destination exit code with a concise error. A bad project or page
inside valid reports becomes a diagnostic and processing continues. The command performs no network
access.

## Visual review proves geometry, not textual correctness

Corpus validation reviews at least 20 pages and 400 lines across at least five books. It writes two
reports from the same inputs and requires byte identity.

It also records exclusion counts and the distribution of page and match costs.

A reviewer inspects overlays for every reviewed page. Overlays draw candidate boxes and source-line
ordinals but are temporary validation artifacts, not report content. The review set includes dense
prose, indented prose, italics, bold, small caps, poetry, quotations, tables, rules, and pages
rejected for probable columns.

The milestone requires at least 98 percent accepted-line precision and at least 70 percent eligible
page coverage. The reviewed selected-page total must equal four disjoint counts. Those counts are
declared complex exclusions, unavailable or malformed inputs, source-changed pages, and eligible
pages. Eligible pages pass all pre-alignment source, snapshot, scan, line-count, foreground,
gutter, table, and illustration gates. Eligible coverage is accepted eligible pages divided by all
eligible pages. `proposed` and alignment-quality exclusions stay in its denominator. The milestone
accepts zero declared complex pages. Rejected correct lines reduce coverage and are documented, but
they do not weaken the precision gate.

Version 1 assigns every exclusion code to exactly one count using a fixed priority: source changed,
unavailable or malformed, declared complex, then eligible. Validation rejects unknown codes and
requires the four counts to sum to the reviewed selected-page total.

## Non-goals

- Page rotation, dewarping, perspective correction, or local warp correction. These are M15c.
- True baselines, x-height, cap height, or glyph boxes.
- Multi-column reading order or column-aware alignment.
- OCR transcription or OCR-based verification.
- Typeface identification, font fitting, kerning, tracking, or word-spacing inference.
- Poetry, blockquote, table, brace, or bracket semantic classification.
- Changes to renderer or trainer output contracts.

## M15c rectifies before typographic fitting

M15c will estimate rotation and page warp, then bind source and rectified frames with invertible
transforms. It will rerun line extraction in the rectified frame and may then introduce baseline and
indentation measurements. Keeping that work separate prevents M15b from presenting source-frame row
geometry as normalized typography.

## Reviewed gates

- Unit tests cover UTF-8 byte spans, newline variants, formatting controls, stable continued-block
  identifiers, candidate ordering, gutter detection, every dynamic-program operation, tie-breaking,
  thresholds, and immutable serialization.
- Fixture tests cover missing and changed files, mismatched hashes, malformed reports, blank pages,
  probable columns, table rules, Unicode, and skipped lines.
- CLI tests cover required flags, exit codes, safe output paths, atomic writes, and deterministic
  output.
- JSON Schema fixtures validate the typed wire model and reject unknown major versions.
- Focused tests and `make ci AI=1` pass before each implementation commit.
- Corpus and visual validation meet the precision-first gate above.

## Adversarial Review

- **Stage and source:** Pending pre-implementation review of this M15b design and its implementation
  plan.
- **Accepted findings:** None yet.
- **Effect on this document:** The scope remains conservative source-frame alignment for eligible
  single-column pages.
- **Residual risks:** Candidate extraction may reject decorative or irregular lines. The initial
  costs are heuristics until reviewed corpus evidence supports calibration.
