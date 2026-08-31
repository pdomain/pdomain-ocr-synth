# PGDP Fragmented-Band Correction Design

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-08-31
- **Last verified:** 2026-08-31
- **Provenance:** measured on 2026-08-31 from the reproduced fixed 25-page M15b review set, the v1
  extractor code, and owner design approval in this session
- **Disposition:** Active design for the M15b fragmented-band extractor correction.
- **Read when:** implementing or reviewing the `pgdp-alignment/v2` line-candidate extractor.
- **Search terms:** PGDP, M15b, fragmented band, line candidate, cluster join, extractor v2.

Version 2 stops rejecting a whole page because one ink band splits into several clusters. It merges
clusters that overlap horizontally, ignores clusters holding almost no ink when it counts
fragmentation, and excludes a page only when a large share of its bands stay fragmented.

## What the correction must achieve

Admit the ordinary single-column text pages that version 1 rejects, without admitting the
multi-column, tabular, and malformed pages it correctly rejects.

## Why version 1 rejects readable pages

Version 1 excludes a page when any single ink band yields more than one cluster. One band out of
forty-four is enough to reject the page. That rule, not the join threshold, is the main defect.

The clusters it splits apart are usually not separated by space. On 12 of the 23 rejected pages the
median horizontal gap between adjacent clusters is zero, which means the clusters overlap
horizontally. Nothing that overlaps in x can be two columns or two words.

What actually splits them is ink too small to matter. Across the 325 fragmented bands in the review
set, 138 hold all their minor clusters below 2 percent of the band's ink. These are commas,
accents, dust, and broken serifs that fail the join rule's vertical-overlap and center-distance
tests and become clusters of their own.

Improving the join rule alone cannot fix this. Three bounded join corrections were simulated
against the review set. The best cut `p006.png` from 27 fragmented bands to 9, but no option
brought any page to zero. As long as a single fragmented band rejects the page, the gates stay
unreachable.

Only 13 of the 23 rejected pages depend on this correction. The other 10 also carry `table_like`,
`probable_multi_column`, `persistent_gutter`, `malformed_control`, or `line_count_out_of_range`
exclusions, and stay excluded whatever the extractor does.

## What version 2 does instead

The extractor keeps the version 1 component join, then applies three new steps per band:

1. Merge clusters whose horizontal ranges overlap, repeating until no pair overlaps. Overlapping
   clusters cannot be separate columns.
2. Ignore clusters holding less than 2 percent of the band's ink when deciding whether the band is
   fragmented. Record them as rejected-component evidence rather than discarding them silently.
3. Emit one line candidate per band, taken from the surviving cluster with the most ink.

A band counts as fragmented when more than one cluster survives steps 1 and 2. The page is excluded
as `fragmented_band` only when the fragmented share of its measured bands exceeds 0.35.

A measured band is one that lies inside the source frame and yields at least one component. Bands
rejected as `empty_band` are not measured and stay out of both sides of the ratio. A page with no
measured bands has no rate, and is excluded by the existing `insufficient_ink_bands` and
`empty_band` paths rather than by this rule.

```text
per band:
  clusters = join_components(components)      # unchanged from v1
  clusters = merge_x_overlapping(clusters)    # new, to a fixpoint
  counted  = drop_minor_ink(clusters)         # new, below 2% of band ink
  candidate = max(counted, key=ink)           # dominant cluster
  fragmented = len(counted) != 1

per page:
  exclude as fragmented_band when
    fragmented_bands / measured_bands > 0.35
```

## Why the threshold is 0.35

The threshold separates the two populations in the review set with margin on both sides. Every one
of the 12 text pages lands at or below 0.2955, and every clearly complex page lands at or above
0.4375.

| Page group | Fragmented-band rate |
|---|---|
| 12 text pages | 0.0 to 0.2955 (highest: `p008.png`) |
| `053.png` | 0.129 |
| Clearly complex pages | 0.4375 to 0.7647 (`w0030`, `006`, `p092`, `w0390`, `005`) |
| Complex pages with independent exclusions | 0.1429 to 0.3182 (`p090`, `w0050`, `p055`, `w0070`, `a0090`) |

Ignoring minor ink is what buys the margin. It lowers the text pages, moving `089.png` from 0.278
to 0.167 and `p148.png` from 0.32 to 0.28. It lowers two complex pages as well, moving `p092.png`
from 0.6667 to 0.5 and `p055.png` from 0.2917 to 0.25, and leaves every other complex page
unchanged. Neither move costs anything: `p092.png` stays far above the threshold, and `p055.png`
carries an independent `malformed_control` exclusion.

## Known risk: one page will be admitted that should not be

`053.png` has a fragmented-band rate of 0.129, below 7 of the 12 text pages. No threshold can admit
the 12 and exclude it, so version 2 makes 13 pages eligible where review found 12 alignable.

The downstream alignment gates are the remaining defense. If they reject `053.png`, eligible-page
coverage is 12 of 13, or 92 percent, comfortably above the 70 percent gate. If they accept it with
wrong lines, accepted-line precision falls and this design needs another pass. The implementation
run measures which happens; this design does not assume either.

## How the algorithm version changes

The report algorithm becomes `pgdp-alignment/v2` and the candidate method becomes
`source-frame-components/v2`. The design for version 1 requires a new algorithm version whenever a
constant or method changes, and this correction changes both.

Version 1 stays reproducible through git history and its retained schema file, not through the
version 2 reader. `schemas/pgdp-alignment-v1.schema.json` is kept unchanged, and checking out the
commit before the version 2 bump reproduces version 1 bytes exactly.

Loading a stored version 1 report with version 2 code fails validation, by design. The M15b design
requires an unknown major algorithm version to be rejected rather than guessed at.

Version 2 adds three constants to the serialized method block:

- `merge_horizontally_overlapping_clusters: true`
- `fragmented_band_minor_ink_share: 0.02`
- `fragmented_band_maximum_rate: 0.35`

Version 2 also adds `minor_ink_cluster` to the rejection reasons, so a cluster ignored by the
minor-ink filter is still recorded as evidence rather than dropped.

## What does not change

The three quality gates stay exactly as they are: at least 98 percent accepted-line precision, at
least 70 percent eligible-page coverage, and zero accepted declared-complex pages. The alignment
thresholds stay at 90 percent matched lines, cost at most 0.22, and uniqueness margin at least
0.15. Confidence stays null with `confidence_kind` set to `uncalibrated`.

The fixed 25-page selection stays fixed, and replay stays deterministic.

## Non-goals

- This design does not rectify, rotate, or dewarp scans.
- It does not infer baselines, reading order across columns, typography, or font identity.
- It does not weaken any gate to make the review pass.
- It does not calibrate confidence.
- It does not begin M15c or any later typography, semantic, or compositor work.

## Adversarial Review

- **Stage and source:** One read-only reviewer checked this design and its implementation plan
  against the version 1 design, the extractor code, the existing tests, and the measurement data in
  `/workspaces/pdomain/.m15b-evidence/`.
- **Accepted findings:** The minor-ink filter also lowers `p092.png` and `p055.png`, so the claim
  that every complex page's rate is unchanged was wrong. `053.png` sits below 7 of the 12 text
  pages, not 9. A sentence promised two new constants and listed three. The plan cited four line
  numbers for three assertions. The 0.35 denominator never defined a measured band or the zero-band
  case. The minor-ink filter had no rejection reason it could record under, so version 2 adds
  `minor_ink_cluster`.
- **Effect on this document:** Every accepted finding was corrected here or in the plan before
  implementation began.
- **Residual risks:** `053.png` becomes eligible although review found it not alignable. The
  implementation run confirmed the alignment quality gates reject it, so no declared-complex or
  unalignable page was accepted. A second defect surfaced in that run: the uniqueness margin is an
  unnormalized absolute cost difference, and it rejects eight otherwise fully matched text pages.
  That threshold is outside this design and needs a separate owner decision.
- **Superseded diagnosis:** the low uniqueness margins were later traced to running heads and page
  numbers being emitted as line candidates with no F2 source line. The correction is designed in
  [the whole-book page template design](2026-08-31-pgdp-whole-book-page-templates-design.md).

## Where the measurements come from

Measurements come from the fixed 25-page review set reproduced on 2026-08-31. That reproduction
holds 25 pages, 1,681 source lines, 1,107 operation rows, and 23 `fragmented_band` exclusions, and
matches every count recorded for the original review. Two runs were byte-identical.

The reproduced reports, the rebuilt ranking and profile, and the four read-only diagnostic scripts
are kept in `/workspaces/pdomain/.m15b-evidence/`, outside `/tmp`, because the original review
artifacts were lost from `/tmp` between sessions.
