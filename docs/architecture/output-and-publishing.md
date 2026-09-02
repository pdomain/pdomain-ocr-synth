# Output and publishing

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-07-14
- **Provenance:** verified from shipped output and publishing code, tests, and cited commits during the docgraph migration
- **Disposition:** Current truth promoted from implemented M07/M08 plans and specs 08/10.
- **Promotes:** implemented M07/M08 plans and specs 08/10.

Render output uses one versioned profile contract for recognition and
detection. Publishing stages that local output and uses the Hugging Face Hub
transport without changing the local training contract.

## Local output layouts

Recognition output contains `images/`, `labels.json`, `manifest.jsonl`,
`recipe.snapshot.yaml`, and `stats.json`. Labels map image names to ground-truth
text. The manifest carries per-sample rendering metadata, and the snapshot
captures the resolved recipe and input hashes.

Detection output uses the same top-level filenames. Its `labels.json` records
image size and doctr-compatible polygons for words and the available line and
paragraph collections. Page layouts produce fixed canvases; paragraph layouts
retain their rendered extents. Integration tests validate both layouts against
the trainer-facing profile shape.

## The trainer profile contract, captured

The layout above was harmonized against `pd-ocr-trainer`'s `dataset_store.py`, which is being
retired. These are the facts this repository's writer depends on, recorded here so they survive
that repository's removal. Measured from
`pd-ocr-trainer/src/pd_ocr_trainer/dataset_store.py` at commit `9a074050` on 2026-09-02.

The profile tree is `<split>/<profile>/<task>/`, with `task` one of `detection` or
`recognition`, and the base profile named `all`. An older layout used `base-ocr` for the same
profile and `dataset_store` migrated it forward.

Each task directory holds `images/` and a `labels.json` that is a flat JSON object mapping an
image filename to its ground-truth text. It is `labels.json`, not `labels.csv`. A directory
counts as a profile only if at least one task under it has a `labels.json`.

Two naming rules carry information in the filename rather than in a field.

A recognition crop's filename ends in four digit-only underscore-separated segments holding its
pixel coordinates. Stripping those four segments recovers the detection page filename it came
from. This is the only link between the two halves of a dataset.

A project identifier is recovered from an image stem by stripping trailing digit-only
underscore-separated segments. So a stem carries its project, then its page, then in the
recognition case its crop box, with nothing declaring which is which.

Both rules are positional and unversioned. Anything reading them is guessing structure from a
string, which is why `pdomain-ocr-training` supersedes this format rather than extending it.

## Determinism and safe continuation

Every sample derives its randomness from the run seed and stable sample index.
Changing worker count does not change current output bytes. Writers refuse to
overwrite an existing destination unless `--force` or `--resume` is selected;
those modes are mutually exclusive. Resume requires the stored recipe snapshot
to match and skips completed indices. This is a same-environment run contract,
not a guarantee of byte identity across future dependency, renderer, or
platform versions.

Stats summarize the run and manifest contents. The current files do not provide
complete per-sample corpus provenance or a full applied-degradation trace.
Those are deferred observability improvements rather than part of the v1
contract.

## Publishing flow

Recognition publishing builds an upload staging directory, dataset card, and
content digest from the local result. Detection publishing uses an ImageFolder
staging layout and includes its annotation metadata. Parquet generation and
500 MB sharding are not implemented.

Authentication resolves an explicit `--token` first, then environment or
cached Hugging Face login through the SDK. The orchestrator can create the
dataset repository, upload files, and create a requested tag. Content-hash
comparison makes a repeated unchanged publish a no-op unless the caller forces
the relevant operation. `--dry-run` performs preflight and reports the plan
without uploading; `--render-first` renders before staging.

The large-folder Hub API cannot honor the CLI's custom commit-message field, so
the command warns and the transport ignores that field. Repository and tag
validation otherwise follow the SDK. Most tests use a transport boundary; the
opt-in live-HF integration test is the evidence for the remote round trip.

## Implementation deviations and limits

The early recognition draft named `labels.csv`; the shipped writer and trainer
contract use `labels.json`. Detection likewise uses `labels.json`, not the
earlier `pages.json` wording. The runner uses a small internal progress reporter
instead of `tqdm`, and normal tests avoid importing the trainer because of its
intrusive import-time behavior.

Detection publishing shipped through ImageFolder and the existing Hub
transport rather than the proposed `datasets.push_to_hub` parquet path. A
byte-mutation idempotency test and a forced mid-upload interruption exercise
remain useful hardening. Glyph-annotation sidecars belong to open M12 and are
not part of shipped output.

## Evidence

- Code: `src/pdomain_ocr_synth/output/`, `src/pdomain_ocr_synth/render/run.py`,
  and `src/pdomain_ocr_synth/publish/`.
- Tests: `tests/test_output_recognition.py`, `tests/test_output_detection.py`,
  `tests/integration/test_trainer_dataset_contract.py`,
  `tests/test_publish_recognition.py`, `tests/test_publish_detection.py`,
  `tests/test_cli_publish_upload.py`, and
  `tests/integration/test_publish_live_hf.py`.
- Commits: `db867fa`, `0f9cb5f`, `ab9d1bf`, `72d3cd5`, `2be2145`,
  `2ee525b`, `540511d`, `200d5d5`, `5b84bf3`, `2d5ac0e`, and `e090040`.
- Verified: 2026-07-14 by repository inspection during the docgraph migration.
