# PGDP Typography and Page-Structure Synthesis Design

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-08-22
- **Last verified:** 2026-08-22
- **Provenance:** authored from repository evidence, the local PGDP corpus, typography research, and
  owner direction in this session
- **Disposition:** Active design for scan-derived typography and structure synthesis.
- **Read when:** planning PGDP profiling, typography measurement, mixed-style rendering, semantic
  layout, or structured-page synthesis.
- **Search terms:** PGDP, F2, typography profile, page structure, mixed styles, poetry, blockquote,
  braces, brackets, synthetic OCR.

The synthesizer will learn reusable book styles from PGDP scans, then generate pages with explicit
typography, structure, semantics, and scan appearance.

## The first pilot proves the whole learning loop

The first pilot selects one PGDP book from the local corpus. When the corpus offers a suitable
candidate, the book must contain ordinary text, multi-column material, poetry, blockquotes, and at
least one table or spanning brace.

The pilot has two outputs:

1. A measured book profile with evidence and uncertainty.
2. Synthetic pages and labels derived from that profile.

The first implementation slice ranks books and pages. It does not claim to measure typography or
reproduce pages yet.

## Goals

- Measure visible typography and page geometry from existing scans.
- Infer shared book and section styles across several pages.
- Keep observed measurements separate from inferred renderer settings.
- Generate mixed roman, italic, bold, and small-cap spans.
- Control kerning, tracking, word spacing, leading, and justification.
- Generate multi-column pages, tables, notes, poetry, blockquotes, and other regions.
- Model horizontal and vertical braces and brackets as structural objects.
- Emit reading order, region geometry, table structure, styled spans, and glyph geometry.
- Use multimodal language models to bootstrap tools and labels without making them a runtime
  dependency.
- Reuse shared page models from `pdomain-book-tools` where they fit.

## Non-goals

- The pilot will not identify an exact historical typeface when the scan cannot prove one.
- The system will not treat LLM output as verified ground truth.
- The system will not bundle licensed fonts.
- The system will not require network access for normal profiling or synthesis.
- The first slice will not train a semantic classifier or change the renderer.

## Three implementation approaches

### Extend the current renderer directly

This approach adds recipe controls and page structures as needs appear. It would produce visible
results quickly.

However, scan measurements would become renderer-specific settings. The schema would also mix
evidence, inference, and generation.

### Compile scan evidence into a book profile

This is the selected approach. Measurement tools produce a versioned profile. The profile stores
observations, inferred style choices, confidence, evidence, and provenance. Renderers consume the
inferred layer without losing source measurements.

This boundary supports several synths. It also lets measurement and rendering improve independently.

### Build fixed templates for each book class

This approach creates hand-tuned templates for poetry, dictionaries, directories, and tables. It
would be predictable, but it would not learn from the PGDP corpus.

As templates grow, rare structures would become expensive to support.

## The system separates four kinds of truth

Each value carries a source class:

- `observed`: read from scan geometry or transcription without a font assumption.
- `derived`: calculated from observed values, such as median baseline distance.
- `pooled`: estimated across several pages, blocks, lines, or glyphs.
- `assumed`: selected to make rendering possible when evidence is weak.

An observed ink x-height might be `18.4 px`. An inferred renderer setting might select a font
candidate at `10.8 pt`. The profile stores both values. It never replaces the observation with the
font choice.

Each estimate also records its unit, coordinate system, sample count, page references, exclusions,
method version, and confidence interval or calibrated confidence.

## The profile follows the physical book hierarchy

The profile uses these levels:

1. Book or edition.
2. Section and recurring page template.
3. Page.
4. Region and block.
5. Line.
6. Styled text run.
7. Word, cluster, and glyph.

Body face, normal size, leading, margins, and paragraph rules usually belong to the book or section.
Warp belongs to a page. Justification expansion belongs to a line. Bold or italic belongs to a run.

This hierarchy prevents independent random choices from producing pages that no compositor would
have made.

## Page structure is a graph

A page is not only a list of rectangles. It is a graph of typed regions and relations.

Regions include body text, heading, running head, folio, poetry, blockquote, marginalia, footnote,
table, table cell, caption, illustration, ornament, rule, brace, and bracket. A region's geometry
may be a polygon, baseline, or path.

Relations include reading order, containment, continuation, label-for, note-for, row membership,
column membership, spans, and groups.

A brace or bracket records its orientation, path, endpoints, linked regions, nesting, and semantic
role when known.

The synth should extend the shared `pdomain-book-tools` page model, not create a private structure
format. A separate cross-repository plan must define the exact shared-model changes.

## Visible structure and inferred meaning stay separate

The profiler records visible structure before semantic role. For example, it may observe an indented
multiline block with ragged right edges.

A local semantic model may infer `poetry` or `blockquote` from the transcription, geometry, and
surrounding pages.

Semantic proposals include confidence and evidence. Low-confidence proposals enter a review queue.

Synthetic pages use explicit semantic roles. Their generated labels are exact even when the source
inference was uncertain.

Poetry and blockquote inference uses:

- source line breaks and sentence continuity;
- rhyme, meter, punctuation, and quotation patterns;
- indentation and line-length distributions;
- leading and space before or after the block;
- recurring styles elsewhere in the book;
- chapter and neighboring-page context.

## PGDP F2 drives cheap discovery

As of 2026-08-22, the local PGDP corpus contains 285 projects with F2 data. F2 `/* ... */` blocks
mark text that needs special formatting.

Inline tags such as `<i>`, `<b>`, and `<sc>` add useful style evidence.

The ranker reads `project.json`, `pages.json`, and `rounds/F2.json`. It scores both books and pages.

The score rewards coverage and diversity, not raw marker count alone.

Book features include:

- page and special-format block counts;
- italic, bold, and small-cap tags;
- title and genre signals for poetry or reference works;
- dot leaders, aligned fields, repeated spacing, and table-like rows;
- multi-part page names such as left, middle, and right scans;
- formatting notes, illustrations, scripts, and uncertain text;
- diversity across page-level feature groups.

The output includes component scores and evidence counts. A deterministic tie-break uses the project
ID.

The ranker never opens images or calls a model.

## Multimodal review is optional and bounded

The ranker produces a small review queue. It selects representative pages, rare structures,
high-value pages, and uncertain pages.

A multimodal LLM may inspect only this queue.

The model proposes page regions, style runs, semantic roles, typography measurements, and tool
rules. Each proposal records the prompt version, model identity, page hash, evidence, and
confidence.

Human corrections remain possible.

Normal profiling and synthesis must run without an LLM. The intended cost reduction comes from
turning repeated LLM decisions into local geometry extractors, rules, and small semantic models.

## Typography measurement uses inverse rendering

Measurement starts by rectifying the page while preserving the mapping to original pixels.

Local tools then estimate page boundaries, print space, columns, baselines, ink height, line
endpoints, connected components, and word gaps.

Typeface matching ranks candidates instead of forcing one name. Candidate fonts render known
transcriptions across plausible size, feature, variation, tracking, blur, and ink-spread settings.

Several words and repeated glyphs contribute evidence.

The profile treats these values as latent or conditional:

- exact font identity;
- nominal point size;
- font advances and side bearings;
- native word-space width;
- tracking and pair kerning;
- original leading;
- physical margins when scans are cropped.

Outlier-resistant estimators pool evidence across pages. Change points separate title pages,
chapters, notes, and other recurring templates from body pages.

## Profiles use an explicit wire contract

Profiles are UTF-8 JSON with a top-level `schema_version`, source-book identity, file hashes,
coordinate frames, estimates, style candidates, page templates, and provenance.

Version 1 readers reject unknown major versions. They accept added optional fields within version 1
and preserve them when rewriting a profile.

Every schema change ships with fixture migrations from each supported older version. A migration
writes a new file and keeps the source unchanged.

Rollback means selecting the earlier profile and the matching tool version recorded in its manifest.
The JSON Schema and typed Python model are generated and tested together.

## Geometry uses a bound coordinate chain

Every image has named `source`, `rectified`, `clean_render`, and `output` frames. A transform record
identifies its type, parameters, input frame, output frame, and inverse support.

Version 1 permits crop, scale, rotation, homography, and a sampled displacement grid for local warp.

Points, polygons, baselines, and brace paths carry their frame. Relations point to stable object
identifiers and never copy geometry.

Each geometry-changing stage must transform all supported geometry types. A stage stays disabled
until round-trip tests bound inverse error and pixel-overlay tests confirm label alignment.

F2 text remains byte-preserved beside a normalized analysis view. Alignment starts at page and line
level and records edit operations. It excludes lines below a declared alignment-confidence threshold
from glyph or font fitting.

Excluded text remains available for page-structure evidence.

## Rendering keeps shaping and composition distinct

The existing HarfBuzz and FreeType renderer remains the deterministic shaping base. A new compositor
interface will eventually itemize styled runs, shape them, break lines, justify text, and place
regions.

Pango with HarfBuzz, FreeType, and Cairo is the preferred candidate for rich paragraph composition.
It must pass a reproducibility and annotation prototype before adoption.

The project should not replace the current renderer until that prototype proves stable cluster
mappings, explicit fallback, per-span styling, and deterministic output.

Real bold and italic faces take priority. Variable-font axes are second. Synthetic emboldening or
oblique styles remain labeled augmentation modes.

Tracking applies at cluster boundaries after shaping. It never splits a ligature or combining-mark
cluster.

Word spacing and justification remain separate controls. Justification policies may expand spaces,
use tracking, hyphenate, choose alternates, or preserve imperfect historical lines.

## Shared and trainer contracts gate rich output

Before M16 changes output, a cross-repository spec must version the shared page graph and assign its
migration owner. `pdomain-ocr-synth` will pin the supporting `pdomain-book-tools` revision.

An adapter will map the new graph to the current detection labels until the structure-model consumer
accepts the versioned graph. Rollback restores the older dependency and adapter output.

The compatibility adapter emits text-region nodes as current DocTR blocks, lines, and words in graph
reading order. It flattens table cells in row-major order.

It omits brace paths, bracket paths, relation edges, and non-text ornaments from `labels.json`, but
keeps them in the rich sidecar. Golden fixtures must list every emitted, flattened, and omitted
object before M17 begins.

The adapter projects each text polygon into the output frame. The current DocTR consumer reduces
polygons to enclosing axis-aligned boxes, so the adapter emits those boxes. The rich sidecar
preserves the original polygon.

A future quadrilateral mode stays disabled until a polygon-preserving consumer is pinned. A line
defined only by a baseline must also provide ascender and descender extents before conversion.

The adapter rejects self-intersecting geometry, inverse-transform failures, and fits above the
declared pixel-error limit. Objects clipped by the image boundary stay in the rich sidecar with
`clipped: true`. They do not enter `labels.json`.

Golden fixtures cover rotated, warped, clipped, and rejected regions.

Detection and recognition datasets retain one page-level typeface from the trainer's closed enum.
Italic and small-cap words also feed `typeface-classification/v1` rows.

Styled spans remain in the rich structure sidecar and do not introduce a `mixed` page typeface.

Rich output stays disabled until the implementation pins the trainer dataset schema version. It must
copy the closed typeface enum into a tested mapping and record the minimum consumer version.

Unknown enum values fail validation. A migration rewrites classifier rows into each newer supported
schema while retaining the source dataset for rollback.

The current detection `labels.json` has no declared schema version. The compatibility adapter must
therefore record the canonical trainer schema fixture's SHA-256 hash and the pinned DocTR version.

A fixture-hash change blocks output until the adapter contract is reviewed and updated.

Glyph facts use the shared canonical ground-truth text and `GlyphAnnotations`. Writers preserve the
difference between `None`, which means unreviewed, and empty `GlyphAnnotations()`, which means
reviewed with no glyph facts.

Every populated annotation validates against its word before output. Glyph output stays disabled
until the implementation pins a `pdomain-book-tools` version whose `GlyphAnnotations` schema is
emitted and stable.

Its migration fixtures must cover absent, reviewed-empty, and populated annotations. The output
manifest records that shared-model version.

## The synth program is a sequence of runnable slices

### M14: PGDP discovery and review queue

Rank books and pages from local metadata and F2 evidence. Emit deterministic JSON for a bounded
multimodal review queue.

### M15: Scan measurement and book profiles

Measure page geometry and typographic observables. Store uncertainty, provenance, source
coordinates, and pooled book styles.

### M16: Styled text and typography controls

Add explicit styled spans, font families, variable axes, tracking, word spacing, kerning controls,
and durable run annotations.

### M17: Structured-page compositor

First land the versioned shared page graph, dependency pin, current-label adapter, migrations, and
rollback fixtures.

Then generate columns, regions, reading order, tables, braces, brackets, poetry, blockquotes, notes,
and recurring page templates.

### M18: Local semantic inference

Train or configure local models for poetry, blockquotes, headings, notes, tables, and other roles.
Use LLM review only for uncertain cases and new structures.

### M19: Scan matching and evaluation

Fit degradation after clean typography and layout. Compare synthetic distributions with held-out
PGDP pages and measure downstream OCR and structure-model gains.

## Failure handling preserves evidence

Malformed project metadata produces a project-level diagnostic and does not stop the corpus scan. A
missing F2 file excludes the project with a stated reason.

A page named in F2 but missing its image remains rankable. Its review item records that the image is
unavailable.

The ranker rejects an output path inside the source corpus when overwrite could damage input data.
Output writing is atomic.

A report includes schema and tool versions for later migration.

Measurement failures keep partial observations. They never invent zero values. Low-confidence font
matches retain several candidates.

## Tests prove determinism and label integrity

The program needs four test layers:

- Unit tests for F2 parsing, feature extraction, scores, tie-breaking, and review selection.
- Fixture tests for malformed projects, missing pages, unusual page names, and Unicode text.
- Rendering tests for mixed spans, cluster geometry, spacing, and structural paths.
- Evaluation tests that compare generated labels with rendered pixels and test downstream model
  gains.

The first slice passes when the same corpus produces byte-identical JSON and all scores expose their
components. A fixture with each target structure must yield the expected review pages.

## Ranking version 1 is fully deterministic

The first slice emits at most 50 projects and 12 pages per project by default. CLI options may lower
or raise both caps. Page features are binary unless named as counts. Version 1 scores use integer
weights:

- 5 for a special-format page;
- up to 10 each for italic, bold, and small-cap tag counts;
- 8 for dot leaders or aligned fields;
- 8 for table-like repeated rows;
- 8 for poetry line-shape evidence;
- 6 for quotation or blockquote evidence;
- 6 for a multi-part page name;
- 4 for an illustration or ornament marker;
- 2 for an uncertainty note.

F2 parsing accepts only a JSON object of string page names to string text. It scans non-nested `/*`
and `*/` local blocks plus `/#` and `#/` continued-format blocks without altering source bytes.

A continued block opens on one page and remains active through following pages until `#/`. Projects
parse in natural page-name order.

Unmatched, nested, or overlapping controls add a diagnostic and exclude the affected block from
content predicates.

Tag counts match case-insensitive opening `<i>`, `<b>`, and `<sc>` tags with optional attributes.
Each tag component scores `min(opening_tag_count, 10)`.

Dot leaders mean three or more periods separated by optional spaces. Aligned fields mean two text
groups separated by at least three spaces on two or more lines. Table-like rows require aligned
fields on three or more lines.

Poetry evidence requires four or more nonblank lines. Their median length must be below 70 percent
of the page's nonblank median, and their line-length median absolute deviation must be nonzero.
Quotation evidence requires four or more consecutive lines inside quotation marks, or a special
block whose lines retain a common indent.

Multi-part names end in `L`, `M`, or `R` before the extension. Illustration and ornament markers
match bracketed `[Illustration...]` or `[Decoration...]` text. Uncertainty notes match `[**`.

Page names compare by alternating case-folded text and base-10 digit runs. Digit runs compare as
integers, then by original run length. The full original page name is the final tie-break.

The project score is the sum of its ten highest page scores. It adds 20 points for each distinct
target group present: mixed typography, table-like structure, poetry, quotation, and multi-part
layout.

Projects sort by descending score, then project ID. Pages sort by descending score, then natural
page-name order.

The report stores algorithm version `pgdp-rank/v1`, every component, and the effective caps. Later
weight changes require a new algorithm version.

Review selection visits target groups in this order: mixed typography, table-like structure, poetry,
quotation, then multi-part layout.

It takes the highest unused page for each group until the cap is reached, then fills remaining slots
by page score.

A page may satisfy several groups but occupies one slot. Any positive page cap is valid because the
fixed group order defines truncation.

This favors coverage before volume and makes selection reproducible.

## Evaluation uses frozen book-disjoint data

Before fitting profiles, the program hashes reviewed family keys into fixed development, validation,
and test splits. A committed `families.json` maps every included project and Gutenberg ebook ID to
one stable work-family ID.

Initial proposals use normalized title and author from `project.json`, after removing parsed volume
and part expressions from the title. Normalization case-folds Unicode text, collapses whitespace,
and removes punctuation.

Ambiguous proposals and projects missing from the reviewed map enter quarantine. Validation rejects
an ebook or project assigned to two families. It also rejects one family split across partitions.
The split manifest is committed before model or threshold tuning.

Partitioning hashes the UTF-8 family ID with SHA-256. It reads the first eight digest bytes as an
unsigned big-endian integer, then takes the value modulo 100.

Buckets 0 through 69 are development, 70 through 84 are validation, and 85 through 99 are test.

M15 reports geometry error for page, region, baseline, and line measurements against reviewed
fixtures. M16 and M17 report label-to-pixel alignment and exact structure serialization.

M19 compares current real-only and existing-synth baselines with the new synth. It measures
recognition character error rate, detection mean average precision, reading-order accuracy, table
structure accuracy, and semantic-role macro F1.

Each later milestone must set numeric gates in its implementation spec after measuring the frozen
baseline. Gains use bootstrap confidence intervals over books, not pages.

A result passes only when its primary metric improves without a statistically supported regression
in the other declared metrics. The structure-model dataset contract and consumer version must be
named before M17 output is enabled.

## Research basis

- [ALTO structure](https://www.loc.gov/standards/alto/techcenter/structure.html) provides page,
  print-space, block, line, string, and space concepts.
- [OCR-D PAGE conventions](https://ocr-d.de/en/spec/page) support fine typography and confidence at
  region, line, word, and glyph levels.
- [HarfBuzz clusters](https://harfbuzz.github.io/clusters.html) define the character-to-glyph
  mapping constraints needed for annotations.
- [Pango rendering](https://docs.gtk.org/Pango/pango_rendering.html) separates itemization, shaping,
  line breaking, and rendering.
- [OpenType OS/2 metrics](https://learn.microsoft.com/en-us/typography/opentype/otspec182/os2)
  distinguish x-height and vertical font metrics from observed ink boxes.
- [DocUNet](https://openaccess.thecvf.com/content_cvpr_2018/html/Ma_DocUNet_Document_Image_CVPR_2018_paper.html)
  shows why page rectification belongs before typography measurement.
- [DeepFont](https://arxiv.org/abs/1507.03196) motivates candidate ranking and adaptation between
  clean renders and real images.

## Adversarial Review

- **Stage and source:** Pre-implementation review on 2026-08-22 by two independent reviewers.
  Evidence included the current synth, local PGDP corpus, `pdomain-book-tools`, `pd-ocr-trainer`,
  and the linked research.
- **Accepted findings:** The design now defines profile versioning, geometry frames, F2 continuation
  parsing, deterministic ranking, shared-model gates, lossy DocTR adaptation, family-safe evaluation
  splits, and trainer schema pins.
- **Effect on this document:** The first slice remains limited to PGDP ranking and review-queue
  output. Rich structure, typography measurement, and renderer changes remain gated milestones.
- **Residual risks:** Historical font matching remains probabilistic. The shared page graph and
  structure-model contract need cross-repository designs before M16 and M17 output can ship.
