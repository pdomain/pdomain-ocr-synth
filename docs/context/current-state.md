# Current state

## Agent Index

- **Kind:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-09-04
- **Provenance:** authored from repository evidence, the 2026-08-24 local PGDP alignment review,
  earlier ranking and geometry-profile corpus runs, tests, plans, CI, and the 2026-08-24 PGDP
  architecture promotion and plan retirement
- **Disposition:** Injected operational ground truth.

M00-M10 are substantially shipped. The repository supports recipe discovery and
validation; local, web, and Wikisource corpora; deterministic HarfBuzz rendering;
recognition and detection output; Hugging Face publishing; recipe linting; audit
logs; and visual regression pins. The baseline `make ci AI=1` passed before the
migration edits.

M14's first runnable slice is also shipped. The local-only `rank-pgdp` command
reads PGDP project metadata and F2 text, ranks projects, and writes a bounded
JSON review queue. It does not measure typography from page images or synthesize
training data.

M15a is shipped and now writes `pgdp-profile/v2`. The local-only `profile-pgdp`
command measures source-frame foreground bounds, margins, horizontal ink bands,
and pooled pixel estimates. Its `--whole-book` mode measures every page image in
a ranked project directory while emitting only the ranked pages, so book
statistics describe the book rather than the ranking. It fits per-book page
templates from first ink-band positions and classifies each page as
`normal_recto`, `normal_verso`, `chapter_opening`, or `unknown`. It does not
rectify scans or claim baselines, columns, semantics, or fonts.

M15b writes `pgdp-alignment/v3` and remains partial. Three defects found on
2026-08-31 are corrected. Version 1 rejected a page whenever any ink band split
into more than one cluster, which excluded ordinary text pages over punctuation
and dust. Specks became ink bands of their own and then candidates matching no
source line. Running heads and page numbers, printed but deleted from F2, were
emitted as candidates, and when a page's candidate count equalled its eligible
source-line count the aligner bound source line 0 to the head and shifted every
match below it.

On the fixed 25-page selection, `fragmented_band` exclusions fell from 23 to 5,
accepted pages rose from 0 to 7, and eligible-page coverage rose to 0.538. All
216 matches across the seven accepted pages are monotone with correct text at
both ends, so no shifted page remains.

All three M15b gates now pass. Accepted-line precision is 1.0000, measured over
760 rows from 26 pages across five books after the band-identification fixes. No
declared-complex page is accepted. All five books clear the 30-page admission
minimum, with 713 accepted pages between them.

Two page-template fitting defects were behind the earlier 0.9716 measurement.
The binding-side split read the trailing digits of the file name, which one book
numbers at ten times the folio, and the first-band deviation ceiling of 2px
refused two books whose heads wander by about 16px. Classified pages rose from
527 of 1385 to 1165, and accepted pages from 367 to 665. The 70 percent coverage
gate was withdrawn on 2026-08-31 and replaced by per-book admission at 30
accepted pages. That ledger was reviewed by a model reading line crops, not
signed off by a person.

## PGDP font-free typography

M15d ships `typography-pgdp` and is complete. The local-only command reads a
`pgdp-alignment/v3` report together with the `pgdp-profile/v2` profile that
alignment recorded, rebuilds each accepted page's ink mask, and measures per
line: baseline row, x-height, ascender and descender extents, stroke width,
skew slope, word runs, and per-word ink boxes. It pools those in two stages,
page then book, and writes a deterministic `pgdp-typography/v1` report. It opens
no font, renders no text, and never leaves the `source` coordinate frame.

The command refuses to run unless the profile hashes to the value the alignment
report recorded. On every page it checks that the rebuilt mask reproduces each
matched candidate's stored `foreground_pixels` and `horizontal_ink_profile`
exactly and that the rebuilt Otsu threshold equals the recorded one. Across 665
accepted pages in five books, all 17,205 matched candidates reproduced and no
page was excluded as `mask_mismatch`.

Per-line and per-word rows are emitted only for the first `--evidence-pages`
measured pages of each book, defaulting to 12. Pooled estimates and per-page
aggregates cover every accepted page, which keeps a five-book run from emitting
roughly 150,000 word records.

All eight gates pass. Two runs per book were byte-identical. The estimator
recovers known geometry within 1 px on all 34 synthetic fixtures and 8 reviewed
ones. Of 210 rendered line crops across three books, CT judged all 210 correct on
2026-09-04, where an earlier model pass had scored 208 and judged none wrong. The
human pass noted a single row of ink past each rule on 11 to 16 percent of ink
columns; that is round-letter overshoot rather than estimator bias, and it is
measured and argued in the M15d plan. The
MAD of per-page x-height medians is 0 in every book, well inside the 0.08
ceiling. No corpus report names anything the design treats as latent.

Word reconciliation clears the 0.50 floor in all five books: 0.805, 0.742,
0.593, 0.800, 0.782. It did not under word segmentation v1, which failed in two
books at 0.476 and 0.208. The cause, found on 2026-09-03, was the gap threshold
itself: `max(2, round(0.25 * x_height_px))` sits below the optimum in all five
books, so it split inside words at ordinary letter gaps. See [the word-gap
threshold finding](../research/2026-09-03-word-gap-threshold-is-too-low.md).

`ink-profile-word-runs/v2` shipped on 2026-09-04 and fixed it. A pre-pass builds
each book's gap-length histogram from the `horizontal_ink_profile` values the
alignment report already carries, so it opens no image, and Otsu splits that
histogram into letter gaps and word gaps. Measured book thresholds are 10, 6, 8,
15, and 9 px. Because Otsu will split a single hump down the middle, the split
is checked before use: the count at the threshold must fall to at most half the
smaller class peak, or the book falls back to the v1 x-height rule per line and
records which rule ran. The guard fired on no book and on 14 of 665 pages, all
evidence-only.

The report contract did not change. `pgdp-typography/v1` and its schema are
exactly as they were; only the method string inside `methods` moved to v2. Each
book's chosen threshold is in the report's `thresholds` and each page's own Otsu
split is in that page's `extensions`. Gates 1 through 5, 7, and 8 came back
unchanged, which is what confines the edit to word segmentation: the 21 Gate 4
review sheets re-render byte-identical.

The residual disagreement was attributed on 2026-09-04. Measured over every
matched line, the detector gets 91.5 to 97 percent of individual word gaps
right, against the 59 to 81 percent of whole lines Gate 6 reports: a line
carries six to twelve gaps and one bad gap fails it. PGDP text is not adding
words either. Across all five books only 12 lines have more transcription words
than the ink has separable runs.

Two causes account for the rest. One is a letter gap sitting a pixel over the
threshold, which no single book-wide value can remove. The other is F2's silent
rejoining of line-break hyphens, which moves a broken word onto the line where
it started and leaves this line's leading ink fragment with no word to bind to.
That second cause is 3.3 to 6.8 percent of all matched lines and 10 to 31
percent of each book's disagreement, which reinstates a mechanism the hyphen
finding had retracted: it was retracted against a residual that a broken
threshold dominated. See [what word reconciliation still
misses](../research/2026-09-04-what-word-reconciliation-still-misses.md).

A separate finding, that [F2 silently rejoins line-break
hyphens](../research/2026-09-03-pgdp-f2-line-break-hyphens.md), is a true fact
about the transcription with a much smaller effect than first supposed. Both of
its predicted consequences were tested and failed.

The sample-size question the 30-page admission minimum depends on now has a
partial answer. Pooled x-height, baseline pitch, and stroke width settle within
0.5 px at 5 body pages in four books and 20 in the fifth, so 30 is comfortably
sufficient for those three. Word gap is the unstable one, though less so under
v2: it now settles in every book, at 5, 50, 5, 30, and 5 body pages, where under
v1 one book did not converge within 100. `MINIMUM_ACCEPTED_PAGES_PER_BOOK` stays
at 30, and font fitting is still an uncalibrated consumer.

`typography-pgdp` also takes an optional `--geometry` OCR record, added on
2026-09-04. Without it the command behaves exactly as before, byte for byte on
all five books. With it, each matched line records what the recognizer read
where its first ink run sits and whether that run is a continuation fragment
the transcription does not carry. Nothing in this repo runs OCR or opens a
model: it reads the records `pdomain-source-data` already produced with the
project's own fine-tuned DocTR checkpoints, so the base install stays
torch-free.

The witness flags 893 lines across the corpus, 3.7 to 7.1 percent of matched
lines, and discounting them lifts agreement with the transcription by 3.0 to
7.0 points, to 0.860, 0.772, 0.632, 0.870, and 0.847. That is reported beside
Gate 6 and does not replace it. Two methods that share no evidence agree on the
fragment rate within 1.1 points. See [the witness
plan](../plans/2026-09-04-pgdp-ocr-witness-for-continuation-fragments.md).

The report also carries per-gap accuracy, added on 2026-09-04. Gate 6 counts
lines and a line carries six to twelve word gaps, so one bad gap fails the whole
line. `word_gap_count`, `word_run_error_count`, and `word_gap_error_rate` appear
per page and per book, and they read 0.923 to 0.972 correct against Gate 6's
0.593 to 0.805. A consumer of word boxes is buying gaps, not lines. Gate 6 keeps
its definition and its value.

Font candidates, inverse rendering, typeface ranking, rectification, rectified
frames, change-point detection, and any point-size or leading claim remain
unimplemented.

## PGDP ranking verification

Two runs over `/workspaces/pdomain-data/pgdp-corpus` used a project limit of 50
and a per-project page limit of 12. Both reports were byte-identical. The corpus
contained 286 projects; 285 were rankable. The report contained 1,777 stable
diagnostics and selected 600 pages across the 50 reported projects.

The first report used this exact command:

```bash
UV_PROJECT_ENVIRONMENT=.venv uv run pdomain-ocr-synth rank-pgdp \
  /workspaces/pdomain-data/pgdp-corpus \
  --output /tmp/pgdp-ranking-task7-a.json \
  --project-limit 50 \
  --pages-per-project 12
```

The second run changed only the output to
`/tmp/pgdp-ranking-task7-b.json`; `cmp` confirmed that the files were
byte-identical.

The top five projects were:

1. `projectID64a479f51ce5b`, *The royal mint*, score 487.
2. `projectID62930b71a45bb`, *The Kilima-Njaro expedition. [1886]*, score 479.
3. `projectID5dc798788ade0`, *The Zoology of the voyage of H.M.S. Beagle [Vol. 5 of 5]*, score 471.
4. `projectID63161caf7eafa`, *Memories of my life [1908]*, score 438.
5. `projectID657550412c8dc`, *In a German colony [1909]*, score 438.

The top project contributed 12 selected pages. In report order, their page
scores were `p092.png` 51, `p178.png` 43, `p179.png` 42, `p090.png` 39,
`p154.png` 41, `p117.png` 40, `p139.png` 39, `p150.png` 38, `p091.png` 37,
`p165.png` 37, `p121.png` 36, and `p152.png` 36. Selection balances feature
groups, so report order is not a simple descending page-score sort.

The verification commands were two identical `rank-pgdp` invocations followed
by `cmp`, focused PGDP and CLI tests, the spec-doc drift test, Markdown lint,
strict docgraph checks, and the full CI and build gates.

## PGDP observed-geometry verification

Two `profile-pgdp` runs used the five-project, 60-page ranking report at
`/tmp/pgdp-m15a-ranking.json`. The profile reports were byte-identical. Every
selected page was measured. Three pages in `projectID63161caf7eafa` retained
one ink band. They were excluded only from pooled band-pitch estimates.

Ten temporary overlays in `/tmp/pgdp-m15a-overlays.zlSH4u` covered the first two
selected pages from each project. Their red bounds covered the observed
foreground. Green ink bands followed text rows and horizontal table rules.
Version 1 must not call them baselines.

The reviewed fixture suite covers clean text-like rows, noise, borders, EXIF
orientation, and blank pages. Clean and oriented source bounds have zero edge
error. Matched ink bands have mean one-dimensional IoU 1.0. Border and blank
fixtures retain the expected `border_dominated` and `blank_page` exclusions.

## PGDP source-line alignment verification

Two balanced `align-pgdp` runs over the same 25 pages from five books produced
byte-identical reports with SHA-256
`2d71eb3bef6ac953c82b9e581ffa92dc77436f90f592a6952a4ec27a232eb107`.
The selection included prose, indentation, poetry-like text, italics, bold,
small capitals, quotations, columns, tables, rules, a cover, an illustration,
and malformed source.

The report contained 1,681 source lines and 1,107 operation rows, with no
accepted alignment. The page reconciliation was 25 unavailable or malformed,
zero declared complex, zero source changed, and zero eligible. Accepted-line
precision and eligible-page coverage were therefore undefined, not zero. No
declared complex page was accepted.

The dominant exclusions were 23 `fragmented_band` and 23
`line_count_difference_exceeds_maximum`. The report also contained six
`line_count_out_of_range`, five `table_like`, four `malformed_control`, four
`persistent_gutter`, four `probable_multi_column`, one `illustration_marker`,
and one `insufficient_ink_bands` exclusion. Twenty-four normalized path costs
were 1.0 and one was 1.3333333333333333. All 25 uniqueness margins were 0.0.
Width and indentation residuals were unavailable because no match operation
survived. Confidence remains null and uncalibrated.

Visual review classified 12 pages and 359 operation rows as incorrectly
excluded by `fragmented_band`. The other 13 pages and 748 rows were
conservatively excluded as complex, malformed, or too short. The reviewed ledger
had SHA-256
`54fd9f18b508e20afb57fec9f3db1415111307747cd9751db22104ca5c56ad8b`.
The milestone remains partial until a separate extractor change passes the
original quality gates on a fixed review selection. The correction is tracked
in [ocr-container-meta issue 403](https://github.com/ConcaveTrillion/ocr-container-meta/issues/403).

## Current architecture

[Development and recipe system](../architecture/development-and-recipe-system.md)
records the shipped development, schema, loader, validation, and CLI contracts.
[Output and publishing](../architecture/output-and-publishing.md) records local
training layouts, determinism, resume, and publishing. [PGDP ranking and review
queue](../architecture/pgdp-ranking-and-review-queue.md) records M14's shipped
corpus-ranking contract. [PGDP observed geometry
profiling](../architecture/pgdp-observed-geometry-profiling.md) records M15a's
shipped scan-measurement contract. Recipe authors should start with [Recipe
workflow](../usage/recipe-workflow.md).

## In-flight milestones

M11 is the local preview UI. Its NiceGUI optional dependency and reusable
preview, search, and validation primitives exist. The UI package, routes,
viewmodels, save flow, and UI tests do not. M12 is glyph-annotation emission.
Its shared model, recipe block, render mapping, sidecar output, and tests have
not shipped. Four non-blocking M11 product choices remain in the
[intent map](intent-map.md). The active roadmap remains
[plans/README](../plans/README.md).

## Current risks and limits

The live plans retain partial work in corpus providers, transforms, rendering,
degradation, detection, and stretch features. The strongest invariants are
deterministic seed-plus-index rendering, trainer-compatible output,
snapshot-guarded resume, and bbox propagation for geometry-changing degradation.
Current limitations and demand-driven options are classified in
[Intent map](intent-map.md). Durable changed-direction decisions are in
[Decisions](decisions.md).

The weekly `dep-refresh` workflow has never executed since it was added on
2026-05-31. It carries the same branch-accumulation design that has already cost
peer repos stray branches, but it remains unexercised here. See
[weekly dep-refresh shares peers' branch-accumulation design](../issues/2026-08-08-dep-refresh-cannot-auto-land.md).
