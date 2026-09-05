---
kind: handoff
status: "active"
created: "2026-09-05"
created_at: "2026-09-05T05:17:53Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "d7df685"
supersedes: "2026-09-04-093000-ocr-witness-shipped.md"
handoff_reason: stopping
host: claude-code
---

# The glyph inventory ships, and reviewing it changed the cutting rule

## What changed

`glyphs-pgdp` cuts a labelled per-character glyph inventory from a book's own
scans and writes it as a directory: `glyphs.jsonl`, one row per glyph, plus
`manifest.json` and a per-character atlas. All eight tasks of
`docs/plans/2026-09-05-pgdp-per-book-glyph-inventory.md` shipped and
every gate passes, so it moves from `proposed` to `complete`.

Nothing in this repo runs OCR, opens a font, renders text, or leaves the
`source` frame. The `recognized` tier reads the `geometry-v1` records
`pdomain-source-data` already wrote, the same file the M15d witness reads.

## Eight commits, each gated on `make ci AI=1`

| commit | what |
| --- | --- |
| `7628a44` | furniture selection through the OCR witness |
| `1ed50b3` | the column-run cut |
| `995b602` | quality flags read against the line, not the word |
| `8ed91d9` | the `pgdp-glyphs/v1` contract and two schemas |
| `19d5783` | the `glyphs-pgdp` command |
| `f89277a` | the per-character atlas |
| `6b6700d` | reviewed fixtures for every cut outcome |
| `1123467` | the counting-rule fix review forced |
| `d7df685` | the corpus run, every gate, the plan closed |

## The one thing you should read first

**Reviewing the first corpus run overturned the plan's own cutting rule, and the
fix is the ninth commit.** The rule as scoped counted a word's ink runs against
its alphanumeric characters. A comma or an apostrophe makes its own ink run as
readily as a letter does, so a word could match by coincidence: one mark
standing alone adds a run while one touching letter pair removes one, and the
two cancel. Every label in such a word then bound to the wrong ink.

It was found by looking at the atlas grids, which is what they are for. A `t`
and an apostrophe both sat in the `n` grid of `projectID609bfa0449bdf`, and
three cells of its `a` grid held `at`.

Measured over four books on 40 pages each, the coincidence covered 1.4 to 15.4
percent of the words the letters-only rule called separable, and in not one of
those 927 cases did the ink actually carry one run per printed character. The
shipped rule, `blank-column-runs/v2`, counts every printing character and labels
only the alphanumerics, so a mark is cut and discarded rather than shifting its
neighbours. In three of the four measured books this raised the yield as well.

Measurement in `/workspaces/pdomain/.m15f-evidence/punctuation-risk-*.json`.

## The scoping numbers were reproduced exactly first

Before the rule changed, the command reproduced all five books' scoping counts
to the glyph: 70,916, 61,701, 30,905, 13,663 and 10,654 transcribed glyphs, the
same separable shares, and the same word-gap thresholds. That is how the defect
was isolated as a defect rather than confused with a regression, and it is why
the shipped counts differing from `.m15f-evidence/coverage-*.json` is a result
rather than a divergence to stop on.

## Every gate, measured on 2026-09-05

Full numbers in `/workspaces/pdomain/.m15f-evidence/gate-summary.json`.

| Gate | Result | Verdict |
| --- | --- | ---: |
| 1. Determinism | 5 of 5 inventory trees byte-identical across two runs, atlas PNGs included | pass |
| 2. Provenance | every row unique on page, tier, line, word and ordinal; a mismatched profile refused | pass |
| 3. Labels, `transcribed` | 0.994 over 1,050 reviewed glyphs, worst book 0.981, floor 0.98 | pass |
| 3b. Labels, `recognized` | 1.000 over 340 reviewed furniture glyphs, floor 0.90 | pass |
| 4. Lowercase coverage | all 26 in every book, none missing | pass |
| 4b. Digit coverage | 83 to 1,879 per book, floor 20 | pass |
| 5. Yield floor | 87 to 547 glyphs per accepted page, floor 50 | pass |
| 6. Atlas reproduction | all 651 sheets re-rendered byte for byte from the JSONL | pass |
| 7. Latent discipline | 0 violations in any manifest or row | pass |

## What the five books yield

| book | pages | glyphs | transcribed | recognized | per page | separable | digits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| projectID657550412c8dc | 155 | 84,733 | 82,321 | 2,412 | 547 | 0.886 | 564 |
| projectID609bfa0449bdf | 226 | 64,417 | 61,692 | 2,725 | 285 | 0.543 | 563 |
| projectID64a479f51ce5b | 75 | 31,578 | 30,669 | 909 | 421 | 0.355 | 1,879 |
| projectID603d7d5e04ca0 | 177 | 15,367 | 12,748 | 2,619 | 87 | 0.248 | 306 |
| projectID67a80fde44d34 | 32 | 11,233 | 11,159 | 74 | 351 | 0.624 | 83 |

207,328 glyphs from 665 pages in 8 minutes 10 seconds. No page was excluded in
any book.

**Furniture closed the digit gap exactly as the scoping predicted.**
`projectID609bfa0449bdf` yields 8 digits from 226 pages of body prose and 555
from its running heads and folios. Mean recognition confidence on the
`recognized` tier runs 0.77 to 0.85.

## Gate 3 is model-reviewed, not human-reviewed

Sheets of 30 samples each for `a e h n o s t` were rendered from the scans at 7x
and read by eye, 210 glyphs a book across all five. Six were wrong: a `g`
labelled `a`, a `Th` labelled `h`, an `re` labelled `e`, a `th` labelled `h`, a
`ho` labelled `o`, and a near-empty cell labelled `t`. All six are residual
coincidences inside pure-alphanumeric words, where one letter broke into two
runs while another pair touched. The sheets are kept as
`.m15f-evidence/review-<book>-<tier>-<characters>-<offset>.png` so you can
confirm the count.

One reading trap worth passing on: at 7x this book's `n` and `u` are easy to
confuse, and an early pass wrongly called several `n` samples wrong. At 14x they
are plainly distinct. Zoom before counting.

## What did not change

`pgdp-typography/v1` and its schema. The glyph inventory is a new report family
with its own two schemas in `schemas/`, so no existing contract moved a byte.

Word segmentation and line measurement. `glyphs-pgdp` calls the same
`measure_line_words` and `measure_line_typography` the typography stage does;
`matched_lines` and a new `book_word_gap_threshold` were made public rather than
copied.

## Decisions worth knowing

**Quality flags are read against the line box, never the word box.** A word box
is tight to its own ink, so its tallest and lowest glyphs always touch it. An
earlier check made against the word box read 0.69 to 0.84 of glyphs as clipped,
which measured the definition and nothing else.

**The atlas is a render, not a source.** One grid per character per tier,
sharded at 1,024 cells a sheet, cells sized at the character's 95th-percentile
extent so one runaway box does not stretch every other cell. `verify_atlas`
re-renders from the written JSONL and names any sheet that did not reproduce.

**Corpus atlases were not committed.** Decision 1 in the plan says atlases ship,
and they do: they are a first-class output of the command written beside the
manifest. What is committed is the fixture atlas, compared pixel for pixel in
CI. The five books' 651 sheets total 7.4 MB and live in the evidence directory;
if you want them in the repo, say so, because that choice needs the corpus-scale
policy the plan's decision 1 already flags as due.

**The output directory gets a `.nobackup` marker,** because the whole inventory
rebuilds from the corpus and the two reports.

## Still open

**The last coincidence.** A pure-alphanumeric word can still match by luck when
one letter breaks into two runs while another pair touches. That is all six
reviewed label errors, about 0.006 of reviewed glyphs. Refusing a word whose
glyph widths vary implausibly against the book's own distribution would catch
most of them, and deserves its own slice if 0.994 is not good enough.

**Separability.** `projectID603d7d5e04ca0` separates 0.248 of its reconciled
words and yields 87 glyphs a page against `projectID657550412c8dc`'s 0.886 and
547. Connected-component labelling is the named next lever and now has a
measured baseline to beat.

**Books outside the five.** Alignment is still the bottleneck: 5 of 286.

## Still not implemented

Composing pages from an inventory, sampling rules for exemplar reuse, font
building, outlines, autotracing, shaping tables, and any point-size or leading
claim. None of it is started.

## Two operating notes that still hold

**Use the `alignment-t2-*` reports, not `alignment-wholebook-*`.** Only the t2
set carries the page-classification fixes; it accepts 665 pages against 367.

**A Bash call is capped at ten minutes and background runs get killed in this
container.** A book harvests in 25 to 170 seconds with the atlas, so two books
a call is comfortable.

## Resume steps

1. Nothing is blocked on you. Every task shipped and every gate passes.
2. If you want Gate 3 human-reviewed rather than model-reviewed, the sheets are
   in `.m15f-evidence/` and named per book; the M15d precedent for that is
   `gate4-review.csv`.
3. Decide whether the corpus atlases belong in the repo. That is the question
   the plan's decision 1 says should be answered before the second book lands,
   and five books have now landed.

## Pointers

- Glyph inventory plan: `docs/plans/2026-09-05-pgdp-per-book-glyph-inventory.md`
- OCR witness plan: `docs/plans/2026-09-04-pgdp-ocr-witness-for-continuation-fragments.md`
- M15d plan: `docs/plans/2026-09-02-pgdp-font-free-typographic-observables.md`
- What word reconciliation still misses: `docs/research/2026-09-04-what-word-reconciliation-still-misses.md`
- Previous handoff: `docs/_archive/handoff/2026-09-04-093000-ocr-witness-shipped.md`
- `schemas/pgdp-glyphs-v1.schema.json` — the manifest contract
- `schemas/pgdp-glyphs-row-v1.schema.json` — the per-glyph row contract
- `docs/usage/recipe-workflow.md` — the `glyphs-pgdp` flag table and what it does
- `tests/fixtures/pgdp_glyphs/` — the four reviewed cut outcomes and their atlas
- `/workspaces/pdomain/.m15f-evidence/gate-summary.json` — every gate number
- `/workspaces/pdomain/.m15f-evidence/gates-<book>.json` — one book's own numbers
- `/workspaces/pdomain/.m15f-evidence/punctuation-risk-<book>.json` — why the rule changed
- `/workspaces/pdomain/.m15f-evidence/label-agreement-<book>.json` — F2 against the read, per word
- `/workspaces/pdomain/.m15f-evidence/inventory-<book>/` — the five shipped inventories
- `/workspaces/pdomain/.m15f-evidence/harvest_book.py` — the runner that measured the gates
