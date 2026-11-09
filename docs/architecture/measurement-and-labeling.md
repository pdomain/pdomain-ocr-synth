# Measurement and labeling live in other repositories

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Owner:** CT
- **Created:** 2026-11-06
- **Last verified:** 2026-11-07
- **Provenance:** verified 2026-11-06 by inspection of this repository and of the sibling packages named below. Tests
  were read, not re-run. Region editing and layout-training status rechecked against current sibling code on 2026-11-07.
- **Disposition:** Current truth for the 2026-09-07 measurement cutover and for the labeling work whose plans lived here
  and whose code landed elsewhere.
- **Promotes:** the measurement extraction plan, the annotation vocabulary and preconditions plans, the region store,
  route, page-kind, geometry, and region-review plans, and the furniture-gap issue.

This repository renders synthetic OCR training pairs from recipes. It does not measure scans. It does not label pages.
Those two jobs have their own packages.

The recipe and output contracts this package ships are in
[Development and recipe system](development-and-recipe-system.md) and [Output and publishing](output-and-publishing.md).

## Measurement lives in pdomain-pgdp-measure

`pdomain-ocr-synth` has no measurement library and no runtime dependency on `pdomain-pgdp-measure`.

The cutover on 2026-09-07 was one step.

Callers use `pgdp-measure` with the subcommands `rank`, `profile`, `align`, `typography`, and `glyphs`.

The wire strings did not change: `pgdp-rank/v1`, `pgdp-profile/v2`, `pgdp-alignment/v3`, `pgdp-typography/v1`, and
`pgdp-glyphs/v1`.

The architecture for those commands sits beside that code, in `pdomain-pgdp-measure/docs/architecture/`.

This repository does not keep a second copy.

On 2026-09-07 the extraction compared 927 report files across five books with the baseline at `f9fdfef`. The recorded
result was `BYTE IDENTICAL — EXTRACTION IS CLEAN` after normalizing only `tool_version` and `alignment_sha256`.

That comparison was not re-run on 2026-11-06.

The move from 665 accepted pages to 713 is older. It is the alignment those files already held on 2026-09-06. The
extraction did not find that difference.

### Evidence for the cutover

- Code: no `src/pdomain_ocr_synth/pgdp/` directory. `pyproject.toml` dependencies do not name `pdomain-pgdp-measure`.
  `src/pdomain_ocr_synth/cli.py` has no `*-pgdp` subcommand. Sibling command registration is
  `pdomain-pgdp-measure/src/pdomain_pgdp_measure/cli.py`.
- Tests: `tests/test_cli.py::test_pgdp_subcommands_are_gone`. A search of `src/` and `tests/` for `pdomain_pgdp_measure`
  returns nothing.
- Verified: 2026-11-06 by file inspection and `git log` of the cutover. The 927-file result is the plan's 2026-09-07
  record, after those two fields were normalized. The 665-to-713 count is the plan's 2026-09-06 record. Neither was
  re-run.

## Shared annotation vocabulary

`pdomain-book-contracts` is the shared authority for what a person or a model asserted about a page.

`RegionRole` has 34 values. Twenty of those roles already shipped on `Block`. Fourteen are additions.

`PageKind` is a separate enum from the measurement package's page class. It is also separate from the packager's page
type.

Provenance enums live in `annotation/provenance.py`. They are still re-exported from typography labels.

`ReviewMetadata` carries a source and a state. The state defaults to unknown.

A mapping translates a detector region type into `RegionRole`. The twenty roles that already shipped on `Block` are
already `RegionRole` values.

### Evidence for the vocabulary

- Code: `pdomain-book-contracts/pdomain_book_contracts/annotation/roles.py`, `page_kind.py`, `provenance.py`,
  `mappings.py`, and `pdomain_book_contracts/ocr/review.py`.
- Tests: `tests/test_annotation_vocabularies.py` has 13 tests, including the twenty original roles and fourteen
  additions. Also `tests/test_annotation_mappings.py` and `tests/test_review_metadata_provenance.py`.
- Verified: 2026-11-06 by reading those files. This pass did not execute the tests.

## Annotation preconditions

Four checks landed under the labeling work, outside this repository.

A reorganize step can report a word the pipeline duplicated. In strict mode, it can refuse the page. A dropped word is
not reported as a duplicate.

A detector label `page_number` stays a page number. It is not folded into the footer. The block role for that region is
`page number`.

Page templates record the spread of the group they were fitted from. That spread survives a profile round trip.

Block role labels accept the same 34 roles as `RegionRole`.

### Evidence for the preconditions

- Code: `pdomain-book-tools/pdomain_book_tools/ocr/reorganize_page_utils.py` and `pdomain-pgdp-measure` page-template
  code exercised by the tests below.
- Tests: `pdomain-book-tools/tests/ocr/test_word_duplication.py`, `tests/layout/test_page_number_mapping.py`, and
  `tests/ocr/test_block_role_vocabulary.py`. `pdomain-pgdp-measure/tests/test_pgdp_page_templates.py` includes
  `test_a_template_records_the_spread_of_its_own_group`, `test_a_single_page_group_has_zero_spread`,
  `test_the_spread_reaches_the_serialized_profile`, and `test_the_spread_survives_a_profile_round_trip`.
- Verified: 2026-11-06 by reading the test names and confirming the files exist. This pass did not execute the tests.

## Region stores and routes

In `pdomain-ocr-labeler-spa`, confirmed regions are `Block` objects in the page.

Proposals and decisions are append-only JSONL journals under the project's `.pd-pages/` directory. A proposal is not
written into the page blob.

`resolve_regions` is the read path that joins the page, the proposal log, and the decision log.

The region API always speaks source pixels: proposal boxes, request bodies, and served
`RegionView.box`. A confirmed region's stored `Block.bounding_box` follows the page's own word-box
convention, normalized 0-to-1 or pixel-space. Boxes convert at the boundary in the labeler's
`core/regions/coordinates.py`, the same rule `_bbox_to_model` applies to words.

The region routes do this work:

- They create, edit, and delete a region.
- They set word membership.
- They list proposals.
- They accept, reject, and unreject.
- They start a book-scoped proposal run.

A golden fixture pins `block_role_labels` and `override_page_sort_order` through `Block` round trip.

The canvas draws confirmed regions and proposals on separate layers, `regions-confirmed` and `regions-proposed`.

### Evidence for the stores and routes

- Code: `pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/regions/models.py`, `proposal_log.py`, and
  `resolver.py`. `api/regions.py` includes `create_region`, `edit_region`, `delete_region`,
  `set_region_word_membership`, `list_region_proposals`, `accept_region_proposal`, `reject_region_proposal`,
  `unreject_region_proposal`, and `start_region_proposal_run`. Also `frontend/src/components/BBoxOverlay.tsx`.
- Tests: `tests/unit/core/regions/test_region_models.py`, `test_proposal_log.py`, `test_decision_log.py`,
  `test_resolver.py`, `test_block_adapter.py`, `tests/integration/test_regions_router.py`,
  `test_region_proposals_router.py`, `tests/conformance/test_region_block_round_trip.py`, and
  `tests/e2e/test_region_layer_visibility.py`.
- Verified: 2026-11-06 by reading those paths. This pass did not execute the suites.

## Page kind

The book-scoped job `propose_page_kinds` measures the book. It proposes a page kind. A person confirms it.

`PagePayload` carries `page_kind` and `page_kind_reviewed`.

A reviewed-marker store records the confirmation.

The marker must reach durable storage. The confirm route requires the event store.

### Evidence for page kind

- Code: `pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_page_kinds.py`,
  `core/page_kind/reviewed_store.py`, and `api/pages.py`.
- Tests: `tests/unit/core/jobs/test_propose_page_kinds_handler.py`, `tests/unit/core/page_kind/test_reviewed_store.py`,
  `test_page_kind_models.py`, `test_proposal_log.py`, `tests/unit/api/test_propose_page_kinds_endpoint.py`,
  `test_page_kind_endpoint.py`, and `pdomain-book-tools/tests/ocr/test_page_kind.py`.
- Verified: 2026-11-06 by confirming those files exist. This pass did not execute the suites.

## Region review

A person selects a region or a proposal on the canvas. The person decides it from a panel or from the keyboard.

`n` and `p` move through undecided proposals. Enter accepts. `x` rejects.

One shared mutation key stops a second decision from being sent while the first is in flight.

A repeat reject writes nothing new.

Changing page clears a region selection so a key cannot apply the previous page's proposal id.

The UI also supports drawing a confirmed region, resizing its box, and editing its member words.
The canvas captures the box; `RegionDetail` selects its role and creates it through `useCreateRegion`.
Resize handles submit through `useEditRegion`, and member-word changes use `set_region_word_membership`.
This does not implement the separate proposal-to-region matcher or the planned sibling-membership invariant.

### Evidence for region review

- Code: `pdomain-ocr-labeler-spa/frontend/src/hooks/useRegionMutations.ts` and `useRegionReviewHotkeys.ts`.
- Tests: `frontend/src/hooks/useRegionMutations.test.tsx`, `useRegionReviewHotkeys.test.tsx`,
  `useRegionReviewHotkeys.crossInstance.test.tsx`, and `tests/e2e/test_region_review_loop.py`.
  Drawing and resizing are covered by `frontend/src/components/PageImageCanvas.test.tsx`,
  `components/right-panel/RegionDetail.test.tsx`, and `lib/region-geometry.test.ts` under the same frontend source root.
- Verified: 2026-11-06 by reading the hook comments and confirming the test files exist. This pass did not execute the
  suites. The plan records the merge as `pdomain-ocr-labeler-spa` `b8c2cd7` on 2026-09-17.
- Verified editing behavior: 2026-11-07 by reading `PageImageCanvas.tsx`, `RegionDetail.tsx`, and the region mutation hooks
  at labeler `5b0a624c`. The sibling frontend suite was not rerun in this audit.

## Layout training

`pdomain-ocr-training` loads confirmed regions from the labeler's `regions/labels.json` export.
The loader validates the export and pairs each page with its detection image, mapping roles to `RegionRole` class indices.

`train_layout_from_config` runs training and validation batches through a caller-supplied `LayoutModel`,
emits progress, and asks that model to save a checkpoint. `LocalTrainingRunner.train_layout` exposes this loop.
There is no default model: omitting it raises an error instead of downloading weights.
This is partial slice 7 plumbing, not a completed layout-model backend or book-scoped classifier.

### Evidence for layout training

- Code: `pdomain-ocr-training/pdomain_ocr_training/layout_regions.py`, `layout.py`, `local.py`, and `protocols.py`.
- Tests: `pdomain-ocr-training/tests/test_layout_regions.py` covers export loading, injected-model training,
  finite-loss checks, and refusal without a model. These tests use an injected model;
  they do not establish trained-model quality.
- Verified: 2026-11-07 by source and test inspection at training `1fb52d5`. The sibling suite was not rerun here.

## Furniture proposals

The default region detector is a composite of `FurnitureDetector` and `PoetryDetector`.

`FurnitureDetector` proposes a page header and a page number from the top furniture bands.

`fit` pools in-band word gaps. It splits them with Otsu. It places the threshold at the midpoint of that valley.

Each proposal records `gap_threshold_source` as `book_fit` or `fixed_share`.

The fixed share is 10 percent of text width.

The plain function `furniture_region_detector` always uses that fixed share.

The fit falls back to that share when any of these is true:

- Text width is missing.
- Fewer than 8 gaps were pooled.
- Either Otsu class has fewer than 2 members.
- The fitted threshold is outside 2 to 40 percent of text width.

A book-fitted run can also peel a digits-only folio, or a short digit lookalike such as `IO`, off the edge of a head.
That peel is off when the fit fell back.

A roman numeral stays on the head.

### Evidence for furniture proposals

- Code: `pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/regions/furniture.py` contains `FurnitureDetector`,
  `_fit_gap_threshold_px`, `FOLIO_GAP_SHARE_OF_TEXT_WIDTH`, and `_MIN_POOLED_GAPS`. Also `core/regions/poetry.py`.
  `bootstrap.py` sets `region_detector` to `CompositeDetector((FurnitureDetector(), PoetryDetector()))`.
- Tests: `tests/unit/core/regions/test_furniture.py`. `test_the_evidence_names_the_fixed_share_threshold_source` expects
  `fixed_share` from `furniture_region_detector`. The motivating-book test expects `book_fit` from
  `FurnitureDetector.fit`. It expects the fixed detector to join head and folio on a page where 10 percent of a 1596 px
  text width is about 160 px. The head-folio gaps on that page are 135 to 150 px.
- Verified: 2026-11-06 by reading `furniture.py` and those tests. This pass did not execute the suite. The plan records
  the first merge as `0e35a06`. It records the fit as `6ed5156`. The narrow-valley follow-up is in `86105eb`. All three
  are on 2026-09-17.
