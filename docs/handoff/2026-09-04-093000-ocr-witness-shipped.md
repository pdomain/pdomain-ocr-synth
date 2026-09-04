---
kind: handoff
status: "active"
created: "2026-09-04"
created_at: "2026-09-04T09:30:00Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "2311ba8"
supersedes: "2026-09-04-014500-m15d-word-gap-v2-complete.md"
handoff_reason: milestone_complete
host: claude-code
---

# The OCR witness ships, and it needed no OCR engine

## What changed

`typography-pgdp` takes an optional `--geometry` record and marks a matched line
whose first ink run is a word fragment the transcription does not carry. That was
the largest named cause of what word reconciliation still misses, at 10 to 31
percent of each book's disagreement.

All seven gates of
[the plan](../plans/2026-09-04-pgdp-ocr-witness-for-continuation-fragments.md)
pass, so it moves from `proposed` to `complete`.

## The scope collapsed once the workspace was checked

**This repo runs no OCR, opens no model, and gained no dependency.** The first
design was tesseract via subprocess. Checking the workspace first showed that
`pdomain-ocr-training` and `pdomain-book-tools` both use python-doctr, and that
`pdomain-source-data` already runs the project's own fine-tuned DocTR checkpoints
over PGDP projects. Its output was sitting at
`/workspaces/pdomain-data/typography/geometry-v1/`: one JSONL per book, 69 MB,
all five corpus books, 98 to 426 pages each, zero recognition failures.

So the work became reading a file and matching boxes. The base install keeps its
eight light dependencies and stays torch-free, which is the same contract
`pdomain-ocr-training` holds itself to.

CT's suggestion to use DocTR rather than tesseract is what surfaced this. It did
not swap one engine for another; it removed the engine.

## Three commits, each gated on `make ci AI=1`

| commit | what |
| --- | --- |
| `cb6da30` | the reader, the correspondence rule, and 21 tests |
| `3eae7ca` | `--geometry`, the line and book rollups, and 11 more tests |
| `2311ba8` | the corpus run, every gate, and the docs |

## Every gate, measured

Each book ran three times: twice with `--geometry` for determinism, once without
it to check the change is confined. Evidence is in
`/workspaces/pdomain/.m15d-evidence/` (`witness-gates.json` and fifteen reports).

| Gate | Result | Verdict |
| --- | --- | ---: |
| 1. Determinism | 5 of 5 books byte-identical across two runs | pass |
| 2. No perturbation without the flag | 5 of 5 byte-identical to the committed v2 reports | pass |
| 3. Page provenance | 0 `scan_hash_mismatch`; witness covers 0.998 to 1.000 of measured lines | pass |
| 4. Control accuracy | 0.970 to 0.990 against a 0.95 floor | pass |
| 5. Agreement with the repair test | 0.0006 to 0.0107 apart against a 0.10 ceiling | pass |
| 6. Gate 6 unmoved | 0.805, 0.742, 0.593, 0.800, 0.782, unchanged | pass |
| 7. Latent discipline | 0 violations across all 5 witness reports | pass |

**Gate 2 is the one that had to be exact, and is.** A run without `--geometry`
reproduces the committed v2 report byte for byte in every book.

**Gate 5 is the interesting one.** Two methods that share no evidence agree on
the fragment rate to within 1.1 points. The repair test fits run widths against
F2 character counts and never looks at a pixel; the witness reads the ink and
never looks at a run width.

**What the witness is worth.** It flags 893 lines, 3.7 to 7.1 percent of matched
lines. Discounting them lifts agreement with the transcription by 3.0 to 7.0
points.

| book | flagged | Gate 6 | after witness | gain |
| --- | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 264 | 0.805 | 0.860 | +5.5 |
| projectID64a479f51ce5b | 113 | 0.742 | 0.772 | +3.0 |
| projectID603d7d5e04ca0 | 196 | 0.593 | 0.632 | +3.9 |
| projectID657550412c8dc | 263 | 0.800 | 0.870 | +7.0 |
| projectID67a80fde44d34 | 57 | 0.782 | 0.847 | +6.5 |

## What did not change

The wire contract. `pgdp-typography/v1` and its schema are exactly as they were;
the witness lives in `extensions`, which the contract already allowed. `make
schema` regenerates no diff.

Gate 6. `reconciled_after_witness` is reported beside it and does not replace it.
Gate 6 is a tripwire for a broken detector, and folding a known cause into it
would make it blind to that cause returning.

The geometry estimator and word segmentation. Gate 2 is the proof.

## Decisions taken, and one deliberately not

Three of the plan's four open decisions were taken as recommended: production of
the geometry records stays in `pdomain-source-data`, the flag lives in
`extensions` rather than a v2 contract, and `reconciled_after_witness` is
reported rather than gated.

**The fourth was measured rather than taken.** A confidence floor is not
warranted. Confidence predicts recognition only below 0.50, where control-line
agreement collapses to 0.402; above it the curve is flat at 0.944 to 0.974. And
confidence does not predict whether a flag is right anywhere, with the explains
rate sitting at 0.83 to 0.87 in every band above 0.50 and the *highest*
confidence band scoring lowest. A floor at 0.50 would drop 26 of 976 flags and
17 of those look correct. The witness only has to notice disagreement, which is
an easier job than reading the word, so a garbled read of a real fragment still
works. No floor ships, and the per-word confidence stays on every line row.

## One process failure worth recording

A commit landed on a red gate. The command was
`make ci AI=1 2>&1 | tail -4 && git commit`, and a pipeline's exit status is the
last command's, so `tail` returned 0 and the `&&` never guarded anything. The
failure was a real one: a test requires every CLI flag to appear in the usage
doc's flag table, and `--geometry` did not. It was caught on the next look, fixed,
and the commit amended before any push, so the remote never saw it. Use
`set -o pipefail` when gating on a piped command.

## Still open

**The other cause of over-split** is untouched and deliberately so: a letter gap
sitting a pixel over the threshold, which is at the noise floor of any single
global threshold. Moving the threshold trades one error for another.

**Gate 4 of M15d is still model-reviewed.** Whether the 210 sheets in
`.m15d-evidence/gate4-sheets/` want a human pass is the one item that needs CT
rather than more measurement.

**Books outside the five** have no geometry record and run exactly as today.

## Still not implemented

Font candidates, inverse rendering, typeface ranking, rectification, rectified
frames, change-point detection over page index, and any point-size or leading
claim. None of it is started.

## Two corrections a later reader still needs

**Use the `alignment-t2-*` reports, not `alignment-wholebook-*`.** Only the t2 set
carries the page-classification fixes; it accepts 665 pages against 367.

**Background corpus runs get killed in this container, and a Bash call is capped
at ten minutes.** A book with `--geometry` takes 130 to 240 seconds per run, so
run at most two per call.

## Resume steps

1. Decide whether Gate 4 wants a human pass. This is the one item that needs you
   rather than more measurement.
2. If word-box quality is reported to a consumer, report it per gap. The detector
   gets 91.5 to 97 percent of individual word gaps right against the 59 to 81
   percent of lines Gate 6 reports.

## Pointers

- [the OCR witness plan](../plans/2026-09-04-pgdp-ocr-witness-for-continuation-fragments.md)
- [the M15d plan](../plans/2026-09-02-pgdp-font-free-typographic-observables.md)
- [What word reconciliation still misses](../research/2026-09-04-what-word-reconciliation-still-misses.md)
- [F2 line-break hyphens](../research/2026-09-03-pgdp-f2-line-break-hyphens.md)
- [Word-gap threshold is too low](../research/2026-09-03-word-gap-threshold-is-too-low.md)
- [previous handoff](2026-09-04-014500-m15d-word-gap-v2-complete.md)
- `/workspaces/pdomain/.m15d-evidence/witness-gates.json` — every witness gate number
- `/workspaces/pdomain/.m15d-evidence/confidence-floor.json` — why no floor ships
- `/workspaces/pdomain/.m15d-evidence/gates.json` — the M15d v2 gate numbers
