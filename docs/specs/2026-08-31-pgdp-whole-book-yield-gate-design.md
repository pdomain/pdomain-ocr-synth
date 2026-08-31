# PGDP Whole-Book Yield Gate Design

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-08-31
- **Last verified:** 2026-08-31
- **Provenance:** measured on 2026-08-31 from five whole-book `pgdp-alignment/v3` runs over 1385
  pages, the M14 ranking feature table, the shipped review-gate code, and owner decisions in this
  session
- **Disposition:** Active design for the M15b acceptance gate replacement.
- **Read when:** changing the M15b review gate, judging whether a book is usable for synthesis, or
  interpreting eligible-page coverage.
- **Search terms:** PGDP, M15b, yield gate, per-book admission, eligible-page coverage, uniqueness
  margin, whole-book alignment.

A book now qualifies for synthesis by yielding at least 30 accepted pages, and corpus-wide
eligible-page coverage stops being a gate. Coverage remains measured and reported per book. The two
surviving corpus gates are 98 percent accepted-line precision and zero accepted declared-complex
pages.

## The gate splits into two evaluations

The single three-part gate splits into two evaluations that run on different reports.

The corpus gate keeps two of its three rules and loses the third. Accepted-line precision must reach
98 percent, and no declared-complex page may be accepted. Eligible-page coverage is removed as a
failure condition.

This gate still runs where it always ran, on the bounded review set. Precision exists only where a
human has recorded line decisions.

Book admission is the new rule and is not a gate. A book that yields at least 30 accepted pages is
admitted to synthesis. A book below that count is left out of the corpus. Nothing fails when a book
is not admitted, because a book that aligns badly is a corpus-selection outcome rather than a defect
in the extractor.

This evaluation runs on whole-book alignment reports, which carry no human line decisions and so can
never satisfy the precision gate.

Keeping the two evaluations apart is what makes each one measurable. Precision needs human review
and is affordable only on a bounded page set. Yield needs whole books and is meaningless on a
bounded one.

Eligible-page coverage stays in the report as a per-book statistic. Nothing fails because of it.

## Why the old gate measured the wrong pages

The 70 percent coverage gate was measured on the bounded 25-page review set, which M14 selects for
typographic interest rather than for being typical. Measuring yield on it understates what an
ordinary book returns.

Comparing the 25 selected pages against the other 1360 pages of the same five books shows the skew
directly.

| feature | selected 25 | rest of the same books |
|---|---|---|
| `table_like` | 0.200 | 0.046 |
| `poetry_like` | 0.200 | 0.027 |
| `aligned_fields` | 0.280 | 0.049 |
| `special_format` | 0.600 | 0.407 |
| median rank score | 21.0 | 4.0 |

Tables are over-represented 4.3 times, poetry 7.4 times, and aligned fields 5.7 times. The review
set exists to stress the extractor, and it does that well. It was never a sample from which to read
a yield figure.

## What whole books yield

Running the whole-book pipeline over all five review books gives 367 accepted pages from 971
eligible pages across 1385 pages, a corpus-wide coverage of 0.378. No book accepted a
declared-complex page.

| project | pages | eligible | accepted | coverage | admitted at 30 |
|---|---|---|---|---|---|
| `projectID609bfa0449bdf` | 312 | 248 | 226 | 0.911 | yes |
| `projectID64a479f51ce5b` | 237 | 133 | 75 | 0.564 | yes |
| `projectID603d7d5e04ca0` | 426 | 362 | 52 | 0.144 | yes |
| `projectID657550412c8dc` | 312 | 171 | 14 | 0.082 | no |
| `projectID67a80fde44d34` | 98 | 57 | 0 | 0.000 | no |

Whole-book alignment needs no new code. Rank the corpus with a page limit above the longest book,
cut the result down to one project, then profile and align that project.

```sh
pdomain-ocr-synth rank-pgdp "$CORPUS" --output ranking-full-allpages.json \
  --project-limit 285 --pages-per-project 5000
# Keep one project, setting project_limit to 1 and pages_per_project to that
# project's own page count.
python build_wholebook_ranking.py ranking-full-allpages.json "$ID" "ranking-wholebook-$ID.json"
pdomain-ocr-synth profile-pgdp "$CORPUS" --ranking "ranking-wholebook-$ID.json" \
  --output "profile-wholebook-$ID.json" --whole-book
pdomain-ocr-synth align-pgdp "$CORPUS" --profile "profile-wholebook-$ID.json" \
  --output "alignment-wholebook-$ID.json"
```

The `--whole-book` flag matters for the profile even when the ranking already lists every page,
because it pools book statistics and fits page templates over every measured page.

## Why a per-book count is the better criterion

Synthesis fits a book's typography from that book's correctly measured pages, so what matters is
whether a book supplies enough of them. The fraction of its pages that align is incidental.

The two readings disagree sharply on this evidence. Corpus coverage of 0.378 reads as a broadly
failing extractor. The per-book counts say something more useful and more accurate. Three books
supply 226, 75, and 52 aligned pages, which is ample for fitting a style, while two supply 14 and
0. Averaging those five books into one number hides the only distinction that changes what the
pipeline should do next, which is dropping the two weak books.

## What this gate does not settle

One acceptance criterion rejects almost everything, and its soundness is still unmeasured. Of the
604 eligible pages that were not accepted, 551 failed on uniqueness margin below the 0.15 minimum.
That is 91.2 percent of all rejections. Of those 604 pages, 576 reached the `proposed` state and 28
were excluded outright on line-count difference.

Two facts make that criterion the open risk. The first is that its rejections are not near misses:
in `projectID603d7d5e04ca0` the rejected margins have a median of 0.065, and in
`projectID67a80fde44d34` a median of 0.050. Lowering the cut to 0.05 would admit 188 and 28 more
pages whose correctness nobody has checked.

The second is that a high margin is not evidence of a correct alignment. Removing a spare candidate
can leave a single monotone assignment, which raises the margin whether or not that assignment is
right. The criterion behind 91.2 percent of rejections is one this project already declined to
trust as proof of correctness.

Only the confusion ledger can resolve this. Precision over the accepted pages says whether 0.15 is
too loose. Reviewing a sample of rejected pages says whether it is too strict. Neither question is
answerable from the counts above, so the 30-page threshold is provisional until precision is
measured.

## The threshold is a seed value

The 30-page minimum has no calibration behind it. Nothing downstream yet states how many pages a
per-book typography fit requires, because nothing fits typography from an aligned page today.

Thirty was chosen as a conservative seed on the same basis as the other M15b thresholds. It gives
enough pages to fit a style with redundancy, and it is roughly a tenth of a typical book in this
corpus.

Corpus review calibrates it once style fitting exists and can state its own requirement. Record the
measured per-book yields whenever the gate runs, so that calibration has evidence to work from.

## What changes in code

Both evaluations live in `src/pdomain_ocr_synth/pgdp/alignment_review.py`, which today pools every
selected page into one book-agnostic summary. That flat shape is why book admission cannot be
bolted onto the existing gate, and why the design adds a second evaluation rather than a fourth
threshold.

Removing the coverage failure is the smaller half.

- Drop `ELIGIBLE_PAGE_COVERAGE` from `ReviewGateFailure` and remove its comparison from
  `validate_review_gate`.
- Keep `eligible_page_coverage` on `ReviewSummary` as a reported statistic with no threshold.
- Move the existing 0.70 threshold tests onto the new admission rule.

Book admission is new and needs its own type, because `ReviewSummary` and `ReviewGateResult` carry
no project identity and so cannot name a book that falls short. The ledger already groups pages by
project through its `references`, which are `ReviewPage` values holding `project_id`, so the data is
present and only the result type is missing.

- Add `MINIMUM_ACCEPTED_PAGES_PER_BOOK`, set to 30.
- Add a per-book result carrying `project_id`, accepted pages, eligible pages, eligible-page
  coverage, and whether the book is admitted.
- Add a function that maps a report to one such result per project.

That function keeps the report's own project order rather than sorting again. Alignment reports
already validate that projects appear in natural order, so a second sort key could disagree with
the first and make replay depend on which one ran.

The wire format does not change. Both evaluations derive from fields the report already carries, so
the alignment schema version stays where it is.

## How to tell this shipped

- `validate_review_gate` no longer fails on eligible-page coverage at any value, and still fails on
  precision below 0.98, on precision that was never measured, and on any accepted declared-complex
  page.
- Book admission marks a book admitted at 30 or more accepted pages and not admitted below 30,
  without returning a pass or fail for the run.
- `eligible_page_coverage` still appears per book in the report.
- Replaying the five whole-book runs reproduces 226, 75, 52, 14, and 0 accepted pages, admitting
  three books and leaving out two.
- Whole-book reports carry no human line decisions, so they are never passed to
  `validate_review_gate`, which would fail them on unmeasured precision.
