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

# The glyph inventory ships, and every review of it found something

## Read this first

**Gate 3 fails on one book and the plan does not close.** Everything below shipped and works, but
`projectID603d7d5e04ca0` reads 0.962 label correctness against a 0.98 floor. Four books pass at
0.981 to 1.000 and the pooled figure is 0.987. Details in "Gate 3 fails on one book" below.

The wrong-ink bindings found in this session are fixed: every line is now checked against the
recognizer, accepted pages included, which took that book from 0.943 to 0.962 and the pool from
0.980 to 0.987. What remains is capitals labelled lowercase.

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

Nine of ten pass. Full numbers in `/workspaces/pdomain/.m15f-evidence/gate-summary.json` and
`gate3-random-review.json`.

| Gate | Result | Verdict |
| --- | --- | ---: |
| 1. Determinism | 5 of 5 inventory trees byte-identical across two runs, 900 atlas sheets included | pass |
| 2. Provenance | every row unique on page, tier, line, word and ordinal; a mismatched profile refused | pass |
| 3. Labels, `transcribed` | 1,050 glyphs drawn at random, 14 wrong, 0.987 pooled; per book 1.000, 1.000, 0.990, **0.962**, 0.981. With `flat_ascender` and `overtall` filtered the worst book reads 1.000 | **fail on one book, unfiltered** |
| 3b. Labels, `recognized` | 340 furniture glyphs reviewed, 0 wrong, 1.000, floor 0.90 | pass |
| 3c. Labels, recognizer-admitted | 420 glyphs on non-accepted pages, 5 wrong, 0.988, floor 0.98 | pass |
| 4. Lowercase coverage | all 26 in every book | pass |
| 4b. Digit coverage | 128 to 2,837 per book, floor 20 | pass |
| 5. Yield floor | 68 to 308 glyphs per harvested page, floor 50 | pass |
| 6. Atlas reproduction | all 900 sheets re-rendered byte for byte from the JSONL | pass |
| 7. Latent discipline | 0 violations | pass |

## Gate 3 fails on one book

The first pass sampled the first 30 rows per character in page order, so it read only each book's
earliest pages and scored 0.994. Drawn at random under seed 20260905 the same 1,050 glyphs gave 21
wrong, and after the line check 14: pooled 0.987, with `projectID603d7d5e04ca0` at 0.962.

What remained in that book was capitals labelled lowercase and boxes holding several letters. A
second measure, `overtall`, now flags an x-height letter running at least 1.35 times the median
height of its line's own x-height letters. Filtering `flat_ascender` and `overtall` together, the
same random sample reads **210 of 210 correct** against 0.962 unfiltered, at a cost of 0.79 percent
of the corpus.

So the gate's verdict depends on what it measures: 0.962 against the inventory as shipped, 1.000
against the inventory with its own flags applied. Redefining it to measure the filtered inventory
would be weakening it without your say-so, so it stays open with both numbers recorded. What is no
longer true is that this book has an unfindable defect.

## What the five books yield

Every page is harvested now, not only the 665 alignment accepted.

| book | pages | glyphs | transcribed | recognized | per page | separable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| projectID657550412c8dc | 298/312 | 91,887 | 89,475 | 2,412 | 308 | 0.883 |
| projectID609bfa0449bdf | 308/312 | 70,441 | 67,716 | 2,725 | 229 | 0.537 |
| projectID64a479f51ce5b | 237/237 | 52,646 | 51,737 | 909 | 222 | 0.358 |
| projectID603d7d5e04ca0 | 426/426 | 28,824 | 26,205 | 2,619 | 68 | 0.246 |
| projectID67a80fde44d34 | 98/98 | 23,731 | 23,657 | 74 | 242 | 0.617 |

267,529 glyphs from 1,367 of 1,385 pages, 258,790 on the `transcribed` tier against 198,589 when
only accepted pages were harvested.

**A line on a non-accepted page is admitted when the recognizer agrees with its transcription.**
Page acceptance is a page-level judgement and a poor proxy for whether one line bound to the right
text: lines excluded only for alignment score agree at 0.887 to 0.962 against 0.926 to 0.976 for
accepted, while lines on illustration pages agree at 0.560 to 0.683. The bar is four of every five
transcription words read inside the line's own box. It needs `--geometry`, and the recognizer only
ever rejects.

**Furniture stays on accepted pages.** Harvesting every page first pushed the `recognized` tier to
165,670 glyphs, because on a page where few lines matched most words fall outside every matched
line. That stops meaning the running head and starts meaning body text, which the tier does not
document and its review does not cover.

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

## The flat-ascender queue, and what it found

A word whose ascender letters run no taller than its x-height letters is flagged `flat_ascender`
and queued in the manifest. In lowercase an ascender runs about half again the x-height, 1.46 to
1.58 at the median; small capitals and wrong-ink bindings both score 1.00. Calibrated on the 76
words PGDP marks `<sc>` in `projectID603d7d5e04ca0`, a cut at 1.10 catches 74.

The queues are small: 33, 32, 68, 180 and 203 words a book, 0.2 to 2.8 percent of separable words.

**Classifying the first 20 of the 180 in `projectID603d7d5e04ca0` found something worse than small
caps.** 7 are unmarked small capitals, 3 are bad cuts, and **10 are a word bound to the wrong ink
entirely**: `They` cut from WILL, `and` from `side,`, `being` from `morning,`, `off` from `her`.
Every glyph in such a word carries the wrong character, and nothing had surfaced it, because
word-level agreement against the OCR read scores 0.9965 when a shifted binding still reads as a
real word somewhere on the line.

Those bindings sit on accepted pages at the same rate as on recognizer-admitted ones, so
harvesting every page did not cause them.

The queue on `projectID657550412c8dc` hit its 200-entry cap at 203, the first truncation. The
count stays exact and the queue is ordered by page, not by flatness, so truncation does not
preferentially drop the entries near 1.00 where small capitals sit.

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

1. **Decide what Gate 3 measures.** It reads 0.962 against the inventory as
   shipped and 1.000 with `flat_ascender` and `overtall` filtered, on the same
   random sample of the worst book. Filtering costs 0.79 percent of the corpus.
   Either the gate measures the filtered inventory and passes, or the flagged
   glyphs stop being emitted at all, or the book is accepted at a stated lower
   number. That call is yours; I did not want to redefine the gate to pass it.
2. **Work the flat-ascender queues.** 490 words across the five books, in each
   manifest's `flat_ascender_words`. `.m15f-evidence/render_flat_queue.py <book>
   <start> <count>` renders them as labelled crops. The wrong-ink class is
   largely gone from them now, so what is left should be mostly small capitals
   and bad cuts.
3. If you want Gate 3 human-reviewed rather than model-reviewed, the random
   sheets are in `.m15f-evidence/review-*-random.png`; the M15d precedent is
   `gate4-review.csv`.
4. Decide whether the corpus atlases belong in the repo. That is the question the
   plan's decision 1 says should be answered before the second book lands, and
   five books have now landed.

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
- `/workspaces/pdomain/.m15f-evidence/gate3-random-review.json` — the random-sample Gate 3 result
- `/workspaces/pdomain/.m15f-evidence/flat-queue-review.json` — what the flat queue holds
- `/workspaces/pdomain/.m15f-evidence/nonaccepted-agreement-<book>.json` — why every page is harvested
- `/workspaces/pdomain/.m15f-evidence/gates-<book>.json` — one book's own numbers
- `/workspaces/pdomain/.m15f-evidence/punctuation-risk-<book>.json` — why the rule changed
- `/workspaces/pdomain/.m15f-evidence/label-agreement-<book>.json` — F2 against the read, per word
- `/workspaces/pdomain/.m15f-evidence/inventory-<book>/` — the five shipped inventories
- `/workspaces/pdomain/.m15f-evidence/harvest_book.py` — the runner that measured the gates
