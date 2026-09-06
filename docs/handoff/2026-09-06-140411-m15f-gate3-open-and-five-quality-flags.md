---
kind: handoff
status: "active"
created: "2026-09-06"
created_at: "2026-09-06T14:04:11Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "36b9a77"
supersedes: "2026-09-05-051753-m15f-glyph-inventory-shipped.md"
handoff_reason: user_requested
host: claude-code
---

# The glyph inventory ships with Gate 3 open, and the ceiling is measured

## Read this first

**Gate 3 fails at 0.978 pooled against a floor of 0.98, and that is the recorded result.** Two
books fail: `projectID67a80fde44d34` at 0.943 and `projectID603d7d5e04ca0` at 0.962. The other
three pass at 0.990 to 1.000. Nothing about this needs a decision from you; the gate measures the
inventory as shipped and I did not move it.

Filtering the five quality flags takes the pooled figure to 0.994 with every book over the floor,
for 23 of 1,050 sampled glyphs and six false positives. That is what a consumer gets from one line
of filtering, not the gate passing.

`glyphs-pgdp` itself works: 266,549 glyphs from 1,367 of 1,385 pages across the five aligned
books, deterministic, atlas reproducing byte for byte, every other gate passing.

## What the milestone is

`glyphs-pgdp` cuts a labelled per-character glyph inventory from a book's own scans: `glyphs.jsonl`
one row per glyph, `manifest.json` for provenance and coverage, and a per-character atlas rendered
from the rows. Two label tiers that never mix. `transcribed` comes from words on lines reconciled
against PGDP F2, so the character is a human proofer's; `recognized` comes from running heads and
folios on accepted pages, where PGDP carries no text at all and a DocTR read is the only label.

Full detail is in the plan, `docs/plans/2026-09-05-pgdp-per-book-glyph-inventory.md`. This handoff
is the state, not the design.

## Every gate

| Gate | Result | Verdict |
| --- | --- | ---: |
| 1. Determinism | 5 of 5 inventory trees byte-identical across two runs, atlas included | pass |
| 2. Provenance | every row unique on page, tier, line, word and ordinal; a mismatched profile refused | pass |
| 3. Labels, `transcribed` | 23 wrong of 1,050 reviewed at random, **0.978 pooled**; filtered 0.994 | **fail** |
| 3b. Labels, `recognized` | 340 furniture glyphs reviewed, 0 wrong | pass |
| 3c. Labels, recognizer-admitted | 420 glyphs on non-accepted pages, 5 wrong, 0.988 | pass |
| 4. Lowercase coverage | all 26 in every book | pass |
| 4b. Digit coverage | 128 to 2,837 per book, floor 20 | pass |
| 5. Yield floor | 68 to 308 glyphs per harvested page, floor 50 | pass |
| 6. Atlas reproduction | every sheet re-rendered byte for byte from the JSONL | pass |
| 7. Latent discipline | 0 violations | pass |

## The five quality flags, and what each is for

Each is an observation recorded on the row, never a verdict and never a change to a label.

| flag | says | catches | cost |
| --- | --- | --- | ---: |
| `flat_ascender` | the word's ascenders run no taller than its x-height letters | unmarked small capitals, a word bound to the wrong ink | 0.2 to 2.8% of words |
| `narrow` | under 0.6x the letter's usual width in the book | a broken arch leaving half a letter, `h` worst in four books | 0.17 to 1.31% |
| `wide` | at or over 1.5x that width | a missed blank column leaving several letters in one box | 0.06 to 0.91% |
| `overtall` | taller than its line's own x-height letters | a capital where the label says lowercase | 0.03 to 1.2% |
| `unlike_character` | the ink is far from the character's median shape in this book | wrong letterforms and multi-letter boxes size cannot see | 0.5 to 5.1% |

`DEFECT_FLAGS` in `glyph_quality.py` names these five. The other flags on a row, `ascends`,
`descends` and the two `touches_line_*`, are ordinary facts about a letter and are not defects.

## Two ceilings, both measured rather than assumed

**Small capitals cannot be found geometrically.** Against the lines PGDP itself marks `<sc>`, a
line's x-height reads 1.00 where roman lines read 1.00 in `projectID603d7d5e04ca0`, and 1.08
against 1.08 in `projectID64a479f51ce5b`. Descender share separates no better and points the
opposite way in the two books.

**The shape check has a blind list a finer grid does not fix.** Fourteen character pairs in
`projectID603d7d5e04ca0` have references closer to each other than a character scatters from
itself, and the count holds at 14, 15 and 14 across grids of 16 by 12, 24 by 18 and 32 by 24. Four
are a capital and its lowercase of the same outline, `I`/`l`, `O`/`o`, `W`/`w`, `S`/`s`, which
normalising size away deliberately erases; the rest differ by a few pixels, `b` from `h` by whether
the bowl closes. The `b` reference sits 3.34 from the `h` reference while `h` scatters 3.46 from
its own, so a `b` labelled `h` is inside ordinary `h` variation.

**The next experiment is named.** Scale each glyph against its line's x-height rather than onto a
fixed grid. That restores the capital-versus-lowercase distinction, at the cost of depending on a
per-line x-height this milestone already found unreliable on badly printed pages, which is where
the errors are. It may trade one blind spot for another, so measure before building.

## How to review Gate 3 yourself

Two commands, from the repo:

```text
uv run python ../.m15f-evidence/gate3.py render
python3 ../.m15f-evidence/gate3.py score
```

`render` draws 30 glyphs each for `a e h n o s t` per book at random under seed 20260905 and
writes numbered sheets plus one CSV a book. Mark a wrong label in its `wrong` column and `score`
reports each book against the floor. `--filtered` on both measures the inventory with flagged
glyphs dropped. Scoring needs only the standard library.

The same 1,050 cells are also a page at
`https://claude.ai/code/artifact/f17a1b33-fa41-4d74-af70-70b8169a812e`, where hovering a cell shows
it inside its own line at full height with the cut boxed, beside the PGDP transcription word it was
labelled from.

**Render at most fifteen cells to a row.** At thirty a bare stem cut from an `h` is
indistinguishable from a whole letter, and an earlier pass of the same sample scored
`projectID67a80fde44d34` at 4 wrong where a legible pass found 12.

## What this milestone changed about its own inputs

**Every page is harvested, not only the 665 alignment accepted.** Page acceptance is a page-level
judgement and a poor proxy for whether one line bound to the right text. A line on a non-accepted
page is admitted when the recognizer reads at least four of every five of its transcription words
inside its own box; the same check now runs on accepted pages too, which is what removed the
wrong-ink bindings. It needs `--geometry`.

**Furniture stays on accepted pages.** Elsewhere, most words fall outside every matched line
simply because few lines matched, and the `recognized` tier would stop meaning the running head.

## Still open

Six reviewed errors survive filtering: three boxes holding a letter and just enough of its
neighbour to sit inside the ordinary width spread, and three of the confusable pairs above.

490 flat-ascender words across the five books are queued in each manifest and unreviewed.

Each page now records its `page_class` and its lines' x-height median and spread, and nothing
consumes them. Spread over about 8 px marks a mixed-size page and is 43 to 67 percent chapter
openings; an elevated median marks heavy inking rather than larger type.

The corpus atlases, 7.4 MB across five books, live in the evidence directory rather than the repo.
The plan's decision 1 says that policy is due now five books have landed.

## Still not implemented

Composing pages from an inventory, sampling rules for exemplar reuse, font building, outlines,
autotracing, shaping tables, and any point-size or leading claim.

## Two operating notes

**Use the `alignment-t2-*` reports, not `alignment-wholebook-*`.** Only t2 carries the
page-classification fixes; it accepts 665 pages against 367.

**A Bash call is capped at ten minutes.** A book now harvests in 1 to 10 minutes with the atlas and
the shape pass, so run one book a call and the largest alone.

## Resume steps

1. Nothing is blocked on you.
2. If you want the next increment on Gate 3, try the x-height-relative shape scaling described
   above, measured against the confusable pairs before it is built.
3. Work the flat-ascender queues. `.m15f-evidence/render_flat_queue.py <book> <start> <count>`
   renders them as labelled crops.
4. Decide whether the corpus atlases belong in the repo.

## Pointers

- Glyph inventory plan: `docs/plans/2026-09-05-pgdp-per-book-glyph-inventory.md`
- OCR witness plan: `docs/plans/2026-09-04-pgdp-ocr-witness-for-continuation-fragments.md`
- M15d plan: `docs/plans/2026-09-02-pgdp-font-free-typographic-observables.md`
- Previous handoff: `docs/_archive/handoff/2026-09-05-051753-m15f-glyph-inventory-shipped.md`
- Manifest contract: `schemas/pgdp-glyphs-v1.schema.json`
- Per-glyph row contract: `schemas/pgdp-glyphs-row-v1.schema.json`
- Command and flags: `docs/usage/recipe-workflow.md`
- Reviewed cut fixtures: `tests/fixtures/pgdp_glyphs/`
- Every gate number: `/workspaces/pdomain/.m15f-evidence/gate-summary.json`
- Gate 3 verdicts, per cell: `/workspaces/pdomain/.m15f-evidence/gate3-review.json`
- Gate 3 marked samples: `/workspaces/pdomain/.m15f-evidence/gate3-<book>.csv`
- Why every page is harvested: `/workspaces/pdomain/.m15f-evidence/nonaccepted-agreement-<book>.json`
- What the flat queue holds: `/workspaces/pdomain/.m15f-evidence/flat-queue-review.json`
- The five inventories: `/workspaces/pdomain/.m15f-evidence/inventory-<book>/`
