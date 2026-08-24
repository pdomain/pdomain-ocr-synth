# PGDP observed geometry profiling

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Owner:** CT
- **Created:** 2026-08-24
- **Last verified:** 2026-08-24
- **Provenance:** verified from shipped code, schema, tests, commits, and corpus runs during the 2026-08-24 docgraph migration
- **Disposition:** Current truth promoted from the implemented first M15 observed-geometry profiling plan.
- **Promotes:** implemented `2026-08-22-pgdp-observed-geometry-profiler` plan.

`profile-pgdp` converts a `pgdp-rank/v1` review queue into a deterministic
`pgdp-profile/v1` report. It measures observed scan geometry in original raster
coordinates and keeps failures as evidence instead of numeric zeroes.

## Input validation preserves ranking and scan evidence

A strict Pydantic boundary validates the complete ranking report before corpus
work begins. Corpus references resolve only through safe relative paths. The
profiler snapshots and hashes the original ranking bytes and the original bytes
of each available selected scan. A missing scan has a `null` SHA-256 value.

The profiler handles one full-resolution page at a time. Before decoding, it
copies the source bytes into bounded temporary-file spooling. It does not apply
EXIF orientation. Dimensions, bounds, margins, and bands therefore use source
raster coordinates. Each successfully decoded page records its original-byte
hash, decoded dimensions, image mode, and orientation metadata when present.

Missing, corrupt, blank, or otherwise unusable scans retain page records and
diagnostics. A failed measurement never becomes a numeric zero.

## Foreground measurement is integer and deterministic

Each decoded image becomes 8-bit grayscale. A deterministic 256-bin integer
Otsu calculation chooses the lowest threshold among all maximizing thresholds.
Pixels at or below that threshold are foreground.

Foreground bounds use half-open coordinates. Four margins are derived from
those bounds in the same source frame. Blank pages have no bounds or margins.

The active-row threshold is the larger of two pixels and 0.5% of print width,
rounded up. Runs separated by at most one inactive row join. The profiler
discards joined runs shorter than two rows.

The report stores every retained raw ink band. It also derives median band
height and median pitch between successive band tops. A one-band page
contributes height but has no pitch sample.

## Exclusions keep observations while limiting estimates

Truth classes distinguish observed, derived, and pooled values. Every estimate
states its unit, coordinate frame, method, sample count, evidence, and
exclusions. Confidence is `null`, and `confidence_kind` is `uncalibrated`.

Project estimates pool eligible page values with the median and median absolute
deviation. Pooling does not remove outliers. Exclusions are metric-specific. A
page can contribute to one estimate while remaining ineligible for another.

Blank and corrupt pages contribute no numeric values to pooled estimates.
Blank pages can retain raw observations such as zero foreground pixels and a
threshold. One-band pages contribute band height but not pitch.
Border-dominated pages and pages with more than 60% foreground keep their raw
observations, but do not contribute margins, height, or pitch to project pooling.

A page is border-dominated when foreground occupies at least 50% of both
opposing outer strips on either axis. Each strip is the larger of one pixel and
1% of the corresponding dimension, rounded up.

## Report output separates measurement from ranking

The profile report is distinct from its ranking input. Serialization is
deterministic, uses atomic replacement, and requires output outside the corpus.
Invalid input exits with status 2. Completed measurement, including results
with diagnostics, exits with status 0. Output failures exit with status 6.

## Boundaries and limits

The profiler reports pixel observations in the unmodified source raster. It
does not rectify rotation, perspective, or page warp. It does not estimate
physical units or verified baselines.

The profiler does not detect columns, interpret semantics, measure text
alignment, infer fonts or styles, or choose renderer settings. Those tasks need
additional evidence and separate contracts.

## Evidence

- Code: `src/pdomain_ocr_synth/pgdp/profile_models.py`,
  `src/pdomain_ocr_synth/pgdp/profile_input.py`,
  `src/pdomain_ocr_synth/pgdp/paths.py`,
  `src/pdomain_ocr_synth/pgdp/image_measurement.py`,
  `src/pdomain_ocr_synth/pgdp/profiling.py`,
  `src/pdomain_ocr_synth/pgdp/report.py`, and
  `src/pdomain_ocr_synth/cli.py`.
- Schema: `schemas/pgdp-profile-v1.schema.json`.
- Tests: `tests/test_pgdp_profile_models.py`,
  `tests/test_pgdp_profile_input.py`,
  `tests/test_pgdp_image_measurement.py`, `tests/test_pgdp_profiling.py`,
  `tests/test_cli_profile_pgdp.py`, and
  `tests/test_pgdp_geometry_fixtures.py`.
- Commits: `c97b108`, `4b13fca`, `8f01f2a`, `895e355`, `83e0a09`,
  `ed86d52`, `f182774`, `5d0ea55`, `a7e5565`, `c058327`, `c9fadb5`,
  `a176747`, and `f29661f`.
- Corpus verification: two five-project, 60-page profiles were byte-identical,
  and all pages were measured. Three one-band pages were excluded only from
  pooled pitch. Ten reviewed overlays had no false bounds merge or split.
  Reviewed fixtures had zero bounds-edge error and mean band intersection over
  union of 1.0, with the expected border and blank exclusions.
- Verified: corpus results recorded in `docs/context/current-state.md`, then
  promoted on 2026-08-24 during the docgraph migration.
