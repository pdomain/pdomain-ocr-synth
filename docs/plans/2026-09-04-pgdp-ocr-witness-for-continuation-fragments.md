---
Status: complete
Owner: CT
Created: 2026-09-04
Last verified: 2026-09-04
Kind: plan
---

# PGDP OCR Witness for Continuation Fragments

## Agent Index

- **Kind:** plan
- **Status:** complete
- **Owner:** CT
- **Created:** 2026-09-04
- **Last verified:** 2026-09-04
- **Provenance:** scoped on 2026-09-04 from the measured residual in
  [what word reconciliation still misses](../research/2026-09-04-what-word-reconciliation-still-misses.md),
  with feasibility measured against the existing `geometry-v1` doctr records for all five corpus
  books
- **Disposition:** Complete as of 2026-09-04. All seven tasks landed and all seven gates pass.
  Three of the four open decisions were taken as recommended; the confidence floor was left
  unset and is recorded as still unmeasured.
- **Read when:** implementing the OCR witness, or judging whether a line's leading ink run is a
  continuation fragment.
- **Search terms:** OCR witness, continuation fragment, doctr, geometry-v1, line-break hyphen,
  word reconciliation, M15e.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
  (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
  checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `typography-pgdp` mark a matched line whose leading ink run is a word fragment F2
does not carry, using an OCR record produced elsewhere, so the largest named cause of word-
reconciliation disagreement becomes visible to a consumer instead of only measured in a document.

## The scope collapsed once the workspace was checked

**This needs no OCR engine, no model, and no new dependency in this repo.** The witness data
already exists. `pdomain-source-data` runs the project's own fine-tuned doctr checkpoints over
PGDP projects and writes per-page records of recognized words with pixel boxes and confidences.
Those records are on disk at `/workspaces/pdomain-data/typography/geometry-v1/`, one JSONL per
book, 69 MB, covering all five corpus books at 98 to 426 pages each with zero recognition
failures.

So the work is to read a file and match boxes. `pdomain-ocr-synth` keeps its eight light
dependencies and stays torch-free, which is the same contract `pdomain-ocr-training` holds itself
to.

The producing half of the sidecar design is therefore already built by another repo. Only the
consuming half is left, and it is one optional input to an existing command.

## Why this is worth doing

Word-run over-split has two causes.
[The measurement](../research/2026-09-04-what-word-reconciliation-still-misses.md) puts F2's
silent rejoining of line-break hyphens at 3.3 to 6.8 percent of matched lines and 10 to 31 percent
of each book's remaining disagreement. F2 moves a word broken across two lines onto the line where
it started, so the next line's leading ink run has no F2 word to bind to and the run count comes
out one over.

That cause is not recoverable from F2 by any amount of parser care, because F2 has erased it. OCR
is the only witness to what ink is on the line.

## Feasibility, measured on 2026-09-04

Every check below ran against the real `geometry-v1` records and the real `alignment-t2-*`
reports. Nothing here is projected.

**The records pin to the same pages this repo already pins to.** All 155 accepted pages of
`projectID657550412c8dc` matched their alignment `scan_sha256` against the geometry record's
`image_sha256`, with no missing page and no mismatch.

**Matching the leading ink run to a recognized word is accurate.** On control lines, where the run
count already equals the word count and so the leading run *is* F2's first word, the matched OCR
text agrees with F2 in 0.955 to 0.994 of lines across the five books, on 629 to 3,887 lines each.
Under 1.2 percent of leading runs find no word at all.

| book | control lines | OCR agrees with F2 | fragment-labelled lines | OCR agrees |
| --- | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 3,887 | 0.994 | 686 | 0.627 |
| projectID64a479f51ce5b | 2,231 | 0.975 | 427 | 0.782 |
| projectID603d7d5e04ca0 | 2,441 | 0.955 | 1,071 | 0.855 |
| projectID657550412c8dc | 2,895 | 0.986 | 303 | 0.175 |
| projectID67a80fde44d34 | 629 | 0.976 | 132 | 0.599 |

**Two independent methods agree book by book.** The rate at which the witness disagrees with F2 on
over-split lines reproduces the leading-fragment share that the repair test derived from run
widths alone, within 0.016 to 0.089 in every book. Neither method can see the other's evidence:
one fits run widths against F2 character counts, the other reads the ink.

| book | witness disagrees | repair test says fragment | difference |
| --- | ---: | ---: | ---: |
| projectID609bfa0449bdf | 0.373 | 0.389 | -0.016 |
| projectID64a479f51ce5b | 0.218 | 0.236 | -0.019 |
| projectID603d7d5e04ca0 | 0.145 | 0.168 | -0.023 |
| projectID657550412c8dc | 0.825 | 0.736 | +0.089 |
| projectID67a80fde44d34 | 0.401 | 0.424 | -0.023 |

The reads are what the mechanism predicts. Against an F2 line beginning `of the rarest--but`, the
leading run reads `tunities`. Against `uncle, Robert Faunthorpe`, it reads `tionate`. Against
`indulged in personalities`, it reads `ment`.

## Tasks

- [x] **1. Read the geometry record.** A `pgdp-ocr-witness` reader parsing one book's JSONL into
  validated frozen records: page name, `image_sha256`, image size, recognizer identity, and words
  carrying pixel boxes and confidences. Reject an unknown `schema_version` rather than guessing at
  it. No torch, no doctr, no network.
- [x] **2. Verify provenance before use.** Each accepted page's `image_sha256` must equal the
  alignment report's `scan_sha256` for that page. A page that disagrees gets no witness and is
  recorded as such, on the same reasoning as `mask_mismatch`: a witness read from a different scan
  would be wrong in a way no later gate could see.
- [x] **3. Correspond runs to words.** Given a matched line's box and its ink runs, pick for each
  run the recognized word with the largest horizontal overlap whose box shares the line's row
  band. Emit the text and confidence, or nothing when no word overlaps.
- [x] **4. Decide `continuation_fragment`.** A line is flagged when its leading run's OCR text does
  not match F2's first word under alphanumeric-lowercase normalization. Record the two strings
  alongside the flag, so a reader can judge the call rather than trust it.
- [x] **5. Wire it as an optional input.** `typography-pgdp --geometry <book>.jsonl`. Without the
  flag the command behaves exactly as today. With it, each line row carries the flag and its
  evidence in `extensions`, each book carries the flagged count, and the report records the
  geometry file's own sha256 and the recognizer's name, version, and `config_sha256`.
- [x] **6. Report a second number, change no gate.** Add `reconciled_after_witness`, the share of
  measured lines that reconcile once a flagged line's leading run is discounted. Gate 6 keeps its
  definition and its value.
- [x] **7. Run the corpus and measure every gate below.**

## Acceptance gates

Each number is a pre-registered seed with its 2026-09-04 measurement beside it, so a failure can
be read as either a defect or a bad seed.

1. **Determinism.** Two runs with `--geometry` produce byte-identical JSON. Uncalibrated.
2. **No perturbation without the flag.** A run without `--geometry` is byte-identical to the
   committed v2 corpus reports. This is the gate that confines the change. Uncalibrated, and it
   must be exact.
3. **Page provenance.** Zero pages where the geometry `image_sha256` disagrees with the alignment
   `scan_sha256` across all five books. Measured 155 of 155 on one book; the other four are
   unmeasured.
4. **Control accuracy.** On lines whose run count already equals their word count, the witness
   agrees with F2's first word in at least 0.95 of lines per book. Measured 0.955 to 0.994.
5. **Agreement with the independent method.** Each book's flagged-fragment share lands within 0.10
   of the repair test's leading-fragment share. Measured 0.016 to 0.089.
6. **Gate 6 is unmoved.** Word reconciliation still reads 0.805, 0.742, 0.593, 0.800, 0.782.
7. **Latent discipline.** The denylist and estimate-shape check still passes with the new keys.

## Measured on 2026-09-04: every gate

Each book was run three times: twice with `--geometry` for determinism, and once without it to
check the change is confined. Evidence is in `/workspaces/pdomain/.m15d-evidence/`
(`witness-gates.json` and the fifteen reports).

| Gate | Result | Verdict |
| --- | --- | ---: |
| 1. Determinism | 5 of 5 books byte-identical across two runs | pass |
| 2. No perturbation without the flag | 5 of 5 byte-identical to the committed v2 reports | pass |
| 3. Page provenance | 0 `scan_hash_mismatch` pages; witness covers 0.998 to 1.000 of measured lines | pass |
| 4. Control accuracy | 0.970 to 0.990 against a 0.95 floor | pass |
| 5. Agreement with the repair test | 0.0006 to 0.0107 apart against a 0.10 ceiling | pass |
| 6. Gate 6 unmoved | 0.805, 0.742, 0.593, 0.800, 0.782, unchanged | pass |
| 7. Latent discipline | 0 violations across all 5 witness reports | pass |

**Gate 2 is the one that had to be exact, and is.** A run without `--geometry` reproduces the
committed v2 report byte for byte in every book, so the witness reaches nothing it was not given.

**Gate 5 is the interesting one.** Two methods that share no evidence agree on the fragment rate
to within 1.1 points. The repair test fits run widths against F2 character counts and never looks
at a pixel; the witness reads the ink and never looks at a run width.

| book | witness | repair test | difference |
| --- | ---: | ---: | ---: |
| projectID609bfa0449bdf | 0.0522 | 0.0528 | -0.0006 |
| projectID64a479f51ce5b | 0.0371 | 0.0332 | +0.0039 |
| projectID603d7d5e04ca0 | 0.0431 | 0.0396 | +0.0035 |
| projectID657550412c8dc | 0.0705 | 0.0597 | +0.0107 |
| projectID67a80fde44d34 | 0.0688 | 0.0676 | +0.0012 |

**What the witness is worth.** It flags 893 lines across the corpus, 3.7 to 7.1 percent of matched
lines. Discounting them lifts agreement with the transcription by 3.0 to 7.0 points.

| book | flagged lines | Gate 6 | reconciled after witness | gain |
| --- | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 264 | 0.805 | 0.860 | +5.5 |
| projectID64a479f51ce5b | 113 | 0.742 | 0.772 | +3.0 |
| projectID603d7d5e04ca0 | 196 | 0.593 | 0.632 | +3.9 |
| projectID657550412c8dc | 263 | 0.800 | 0.870 | +7.0 |
| projectID67a80fde44d34 | 57 | 0.782 | 0.847 | +6.5 |

## Decisions taken

Three of the four were taken as recommended on 2026-09-04. The fourth was not.

1. **Production stays where it is.** This consumes the records and records the recognizer's
   name, version, and `config_sha256` plus the file's own sha256, so a regeneration at another
   revision is visible rather than silent.
2. **Extensions, not a v2 contract.** `pgdp-typography/v1` and its schema are unchanged.
3. **`reconciled_after_witness` is reported, not gated.** Gate 6 keeps its definition and value.
4. **No confidence floor, and it is now measured rather than deferred.** Calibrated on
   2026-09-04: a floor would cost more than it saves. See below.

## Measured on 2026-09-04: a confidence floor is not warranted

**The witness only has to notice disagreement, which is a much easier job than reading the
word.** That is why confidence barely matters, and it is the reason a floor would hurt.

Control lines give ground truth for recognition: their run count already equals their word count,
so the first ink run *is* the transcription's first word and the read should match it. Bucketed by
the recognizer's own confidence over all five books:

| confidence | control lines | read matches F2 | flagged lines | flag explains the line |
| --- | ---: | ---: | ---: | ---: |
| 0.00-0.50 | 112 | 0.402 | 26 | 0.654 |
| 0.50-0.70 | 4,752 | 0.944 | 379 | 0.871 |
| 0.70-0.80 | 2,105 | 0.959 | 135 | 0.859 |
| 0.80-0.90 | 2,396 | 0.961 | 170 | 0.871 |
| 0.90-0.95 | 1,591 | 0.972 | 97 | 0.856 |
| 0.95-1.00 | 3,122 | 0.974 | 169 | 0.828 |

"Flag explains the line" is whether discounting the fragment leaves the run count equal to the
word count, which is what a correct flag should do.

Three things follow.

**Confidence predicts recognition only below 0.50.** Agreement collapses to 0.402 there and then
sits between 0.944 and 0.974 across every band above it. Between 0.50 and 1.00 the curve is flat.

**Confidence does not predict whether a flag is right, anywhere.** The explains rate is 0.83 to
0.87 in every band above 0.50, and the *highest* confidence band scores the lowest of them at
0.828. A garbled read of a real fragment still disagrees with the transcription, which is all the
flag needs.

**A floor at 0.50, the only defensible one, would make things slightly worse.** It would drop 26
of 976 flags, 2.7 percent, and 17 of those 26 look correct against 9 that do not. Any higher floor
is worse still: reads below 0.80 produce 49.5 to 67.2 percent of every book's flags.

So no floor ships, and the reason is a measurement rather than an omission. The per-word
confidence stays on every line row so a consumer that wants to weigh it can.

## Open decisions

**1. Who owns regenerating the geometry records.** They were produced by `pdomain-source-data` on
a cuda device at recognizer revision `8b7f9b31` and live outside every repo, in
`/workspaces/pdomain-data/`. This plan consumes them and does not reproduce them. If they are
regenerated at a different revision, every witness flag changes and the recorded
`config_sha256` is what makes that visible. Recommendation: consume, record the identity, and
leave production where it is.

**2. Extensions or a v2 contract.** Recommendation: extensions. `pgdp-typography/v1` already
carries free-form `extensions` on line and book records and its schema allows additional
properties, so the flag needs no contract change. Promote to v2 only when a consumer needs it
structurally.

**3. Whether `reconciled_after_witness` ever becomes a gate.** Recommendation: not yet. Gate 6 is
a tripwire for a broken detector. Redefining it to absorb a known cause would make it blind to
that cause returning.

**4. A confidence floor. Closed on 2026-09-04.** Measured and refused; see the section above. It
is kept here so a later reader sees the question was answered rather than dropped.

## What this does not do

It does not correct F2, rejoin anything, or change a word box. It marks a line and records why.

It does not touch the geometry estimator, the mask builder, or pooling. Gates 1 through 5 and 7 of
M15d must come back unchanged.

It does not address the other cause of over-split, a letter gap sitting a pixel over the
threshold. That one is at the noise floor of any single global threshold and is deliberately left
alone.

It says nothing about books outside the five with geometry records. A book without one runs
exactly as today.

## Related

- [What word reconciliation still misses](../research/2026-09-04-what-word-reconciliation-still-misses.md)
  — the measurement this plan acts on.
- [F2 silently rejoins line-break hyphens](../research/2026-09-03-pgdp-f2-line-break-hyphens.md)
  — the mechanism, and the OCR witness pass it first proposed.
- [M15d font-free typographic observables](2026-09-02-pgdp-font-free-typographic-observables.md)
  — the command this extends and the gates it must not move.
