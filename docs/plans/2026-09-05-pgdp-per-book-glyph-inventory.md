---
Status: proposed
Owner: CT
Created: 2026-09-05
Last verified: 2026-09-05
Kind: plan
---

# PGDP Per-Book Glyph Inventory

## Agent Index

- **Kind:** plan
- **Status:** proposed
- **Owner:** CT
- **Created:** 2026-09-05
- **Last verified:** 2026-09-05
- **Provenance:** scoped on 2026-09-05, with coverage measured by harvesting all 665 accepted
  pages of the five aligned books
- **Disposition:** Proposed, not approved. Three open decisions at the end.
- **Read when:** building or consuming the glyph inventory, or asking what synthesis can render
  in a book's own type.
- **Search terms:** glyph inventory, per-book, harvest, atlas, coverage, synthesis, M15f.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
  (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
  checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut a labelled glyph inventory from each aligned book's own scans, so synthesis can
render arbitrary text in that book's actual type with per-character ground truth.

## What this is for

**Nothing else in the pipeline produces glyph-level ground truth.** PGDP gives line text.
Alignment gives line boxes. M15d gives word boxes on reconciled lines. A recognition model wants
per-character boxes, and only this makes them.

Four things follow. Training pairs stop being bounded by what PGDP has proofed, because any text
can be set in the book's own glyphs at its measured x-height, word gap and baseline pitch.
Degradation gets a known original, which a real scan never has. The observed in-situ glyph
positions give an empirical spacing distribution for the book, which is a measurement of ink
rather than a claim about a typeface. And the ranking slice gets real shapes to score revival
candidates against.

**The labels come from F2, which is human-proofed, not from OCR.** A glyph is cut only from a
word on an exactly reconciled line, so its character is the transcription's. That is what keeps
this from being a model trained on its own output.

## Measured on 2026-09-05: what the five books yield

Every accepted page of all five books was harvested. A glyph is cut when, inside a reconciled
word's box, the count of ink runs separated by a blank column equals the word's letter count, so
every glyph in that word is separable with a known label.

| book | pages | glyphs | per page | separable words | distinct chars | lowercase | uppercase | digits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| projectID657550412c8dc | 155 | 70,916 | 458 | 0.799 | 67 | 69,343 | 1,511 | 62 |
| projectID609bfa0449bdf | 226 | 61,701 | 273 | 0.534 | 51 | 59,958 | 1,743 | 0 |
| projectID64a479f51ce5b | 75 | 30,905 | 412 | 0.345 | 63 | 29,498 | 1,032 | 375 |
| projectID603d7d5e04ca0 | 177 | 13,663 | 77 | 0.256 | 61 | 12,351 | 1,285 | 27 |
| projectID67a80fde44d34 | 32 | 10,654 | 333 | 0.601 | 49 | 10,455 | 197 | 2 |

187,839 glyphs from 665 pages, at roughly 1.6 seconds a page.

Four things follow.

**Every book carries all 26 lowercase, with none missing.** The floors are `q` at 41, `z` at 10,
`z` at 1, and accented rarities at 1. Lowercase is what body prose gives you and it gives it
deeply.

**Uppercase is thin and digits are nearly absent.** 197 to 1,743 uppercase samples per book, and
`projectID609bfa0449bdf` contains **zero digits across 226 pages**. Page numbers live in the
furniture bands the pipeline excludes on purpose. Any consumer needing digits cannot get them
here.

**Yield varies nearly sixfold per page, and separability is why.** `projectID603d7d5e04ca0`
separates only 0.256 of its words and yields 77 glyphs a page against
`projectID657550412c8dc`'s 0.799 and 458. Column-run splitting fails where letters touch.

**Per book is forced, not tidy.** X-heights run 10 to 18 px across these five and glyph pixel
sizes scale with them, so a pooled inventory would be a chimera of sizes.

## The shape

One inventory per book, from the same pinned inputs `typography-pgdp` takes, so provenance is the
existing discipline rather than a new one.

```text
glyphs-pgdp <corpus_root> --alignment a.json --profile p.json --out <dir>/
  manifest.json      pgdp-glyphs/v1: input hashes, method version, per-character
                     coverage, quality tallies
  glyphs.jsonl       one row per glyph: character, page, line ordinal, word ordinal,
                     glyph ordinal, source-frame box, quality flags
  atlas/U+0065.png   derived: every 'e' in the book on one grid
```

**Boxes are the contract; the atlas is a derived render.** Every other stage here emits a JSON
report with hashes and treats images as build artifacts, the Gate 4 sheets included. Boxes keep
the contract pure, re-cuttable and small; the atlas is regenerable when a self-contained artifact
is wanted.

**One atlas per character, not per glyph.** A file per glyph is 10,000 files a book and three
million across 286 projects. Per character is 50 to 90 files a book, and it is self-reviewing:
open `U+0065.png` and every `e` in the book is on one grid, where a bad cut is obvious. That is
the Gate 4 trick, built in rather than bolted on.

## Tasks

- [ ] **1. Cut glyphs from a reconciled word.** Given a word box and its transcription word, split
  by blank columns and emit one record per glyph when the counts agree. Emit nothing and record
  the reason when they do not.
- [ ] **2. Quality flags, recorded not enforced.** Whether the glyph's row extent agrees with the
  line's measured x-height, ascender and descender; whether it touches the **line** box edge;
  its ink density. Not the word box: a word box is tight to its own ink, so its tallest and
  lowest glyphs always touch it, which makes a word-box test meaningless.
- [ ] **3. The `pgdp-glyphs/v1` contract and its schema.** Input hashes, method version, per-
  character counts, quality tallies, and the per-glyph JSONL.
- [ ] **4. The `glyphs-pgdp` command.** Refuses a profile that does not hash to the alignment's
  recorded value, the same as `typography-pgdp`.
- [ ] **5. The per-character atlas renderer,** deterministic and regenerable from the JSONL alone.
- [ ] **6. Reviewed fixtures** covering a separable word, a touching word, and a word whose
  letters split into the wrong count.
- [ ] **7. Harvest all five books and measure every gate below.**

## Acceptance gates

Each carries its 2026-09-05 seed where one was measured.

1. **Determinism.** Two runs over identical inputs produce byte-identical JSONL and manifest.
   Uncalibrated.
2. **Provenance.** Every glyph row resolves to one page, line, word and ordinal, and the
   command refuses a profile that does not match the alignment's recorded hash. Uncalibrated,
   must be exact.
3. **Label correctness.** A reviewed sample of at least 200 glyphs across at least three books,
   rendered as atlas grids, at least 0.98 carrying the character the manifest claims. Higher than
   Gate 4's 0.95 because a mislabelled glyph poisons every page rendered from it. Uncalibrated.
4. **Lowercase coverage.** All 26 lowercase present in every book. Measured: true in all five.
5. **Yield floor.** At least 50 glyphs per accepted page. Measured 77 to 458, so the floor has
   margin, and the book that would fail it first is `projectID603d7d5e04ca0`.
6. **Atlas reproduction.** Re-rendering the atlas from the JSONL reproduces it byte for byte.
   Uncalibrated, must be exact.
7. **Latent discipline.** No key claims font identity, point size, advance, side bearing or
   tracking. The inventory records observed ink, never a typeface.

## Open decisions

**1. Does the atlas ship, or stay local?** Licensing is settled, so this is a repo-hygiene call
rather than a legal one. The committed-bytes rule was written for a reason and CT should set the
line. Recommendation: keep the JSONL as the committed contract and treat atlases as local build
artifacts, matching how the Gate 4 sheets are handled.

**2. Are digits worth harvesting from furniture?** They are absent from body prose, entirely so in
one book. Getting them means reversing an exclusion the pipeline makes deliberately.
Recommendation: do not. Record the gap in the manifest and let a consumer decide.

**3. Should a thin book refuse to emit?** Recommendation: emit and declare. A floor that silently
drops books hides what it dropped, which is the same reasoning Gate 6 was written under.

## What this does not do

It does not build a font. No outlines, no autotracing, no shaping tables. For synthesis you
compose at the measured size from samples taken at that size, and a traced outline would be
noisier than the bitmap it came from.

It does not render anything. Composing pages from an inventory is a later slice and needs its own
sampling rule, because reusing one exemplar per character would look mechanical in a way real
setting never does.

It does not fix separability. Connected-component labelling would rescue touching letters and
lift `projectID603d7d5e04ca0` most, but the column-run baseline is measured first so the
improvement can be scored against it.

It reaches only books with alignment reports: five of 286. Alignment is the bottleneck this sits
behind.

## Related

- [M15d font-free typographic observables](2026-09-02-pgdp-font-free-typographic-observables.md)
  — the word boxes this cuts from, and the latent discipline it inherits.
- [PGDP OCR witness for continuation fragments](2026-09-04-pgdp-ocr-witness-for-continuation-fragments.md)
  — the same provenance pattern, and the reason reconciliation is trustworthy.
- [What word reconciliation still misses](../research/2026-09-04-what-word-reconciliation-still-misses.md)
  — why a reconciled word is a safe place to cut from.
