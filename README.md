# pdomain-ocr-synth

## Agent Index

- **Kind:** process
- **Document role:** usage
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-11-07
- **Provenance:** rechecked 2026-11-07 against pyproject.toml, the CLI, recipe and render modules,
  output writers, and tests. Partial milestones and deferred UI/annotation scope remain in the plans index.
- **Disposition:** Retained as the project entry point.

Synthetic OCR training-data generator. Produces labeled image+text pairs for
historical and specialty typography (first target: Cló Gaelach / early Irish
typography), in the format `pdomain-ocr-training` reads as its profile
directories.

**Status:** M00–M10 substantially shipped, with residual work in M00, M03–M06, M09, and M10.
M11 (preview UI) and M12 (glyph annotations) remain unbuilt. See the [remaining work](docs/plans/README.md).
The architecture notes describe current behavior; specs preserve partial and deferred designs.
The [roadmap](docs/plans/README.md) is the sole schedule.
See the [documentation map](docs/README.md) for current documentation and
[`AGENTS.md`](AGENTS.md) for contributor and agent guidance.

## Why

Real labeled data for historical scripts is scarce. The standard playbook for
training an OCR model on uncommon typography is:

1. Generate a large synthetic corpus (this project)
2. Pretrain on it
3. Fine-tune on a small set of real labeled pages from `pd-ocr-labeler`

This project covers step 1. It is recipe-driven so adding a new script
(Fraktur, blackletter, early-modern English with long-s, Greek, etc.) is a
matter of writing a YAML file plus optional custom transforms.

## How it fits the workspace

```
[ pdomain-ocr-synth ]  →  recognition crops + detection pages
        │
        ▼
[ pdomain-ocr-training ]  reads new profile (e.g. `gaelic`)
        │
        ▼
[ pdomain-ocr-cli ]  uses fine-tuned model on real scans
```

The output adapter writes directly into the directory layout
`pdomain-ocr-training` reads, verified against its
`RecognitionDataset` / `DetectionDataset` construction in
`pdomain_ocr_training/recog.py` and `detect.py`. That layout was
originally harmonized against the now-retired `pd-ocr-trainer`'s
`dataset_store.py`; see [Output and
publishing](docs/architecture/output-and-publishing.md) for the
captured contract.

## Getting started

Start with the architecture and usage references for shipped behavior. The specs retain partial or deferred design.
The [roadmap](docs/plans/README.md) is the sole schedule.

| # | Documentation | What it covers |
|---|------|----------------|
| 00 | [Overview](docs/specs/00-overview.md) | Goals, non-goals, integration |
| 01 | [Development and recipe system](docs/architecture/development-and-recipe-system.md) | CLI and recipe architecture |
| 02 | [Recipe format](docs/specs/02-recipe-format.md) | YAML schema reference |
| 03 | [Recipe workflow](docs/usage/recipe-workflow.md) | Create, validate, render, and publish a recipe |
| 04 | [Corpus providers](docs/specs/04-corpus-providers.md) | Local, web, Wikisource; HF datasets remain unimplemented |
| 05 | [Text transforms](docs/specs/05-text-transforms.md) | Lenition, long-s, Tironian et |
| 06 | [Rendering](docs/specs/06-rendering.md) | Fonts, shaping, layouts |
| 07 | [Degradation](docs/specs/07-degradation.md) | Augmentation pipeline |
| 08 | [Output and publishing](docs/architecture/output-and-publishing.md) | Trainer layouts and publishing |
| 09 | [Extending](docs/specs/09-extending.md) | Adding providers / transforms / degradations |
| 10 | [Output and publishing](docs/architecture/output-and-publishing.md) | Push rendered datasets to Hugging Face |
| 11 | [Preview UI](docs/specs/11-preview-ui.md) | Unbuilt visual recipe tuning; the earlier NiceGUI design is superseded in part |
| 12 | [Glyph annotations emission](docs/specs/12-glyph-annotations-emission.md) | Per-word ligature / long-s side channel |
| 13 | [Dev-local mode and deps](docs/specs/13-dev-local-mode-and-deps.md) | `upgrade-deps` must not silently revert dev-local venvs |

A full worked recipe lives at the filesystem path `recipes/gaelic.yaml`. It is
not part of the governed Markdown graph.

## Implementation roadmap

Specs describe the destination; the [implementation roadmap](docs/plans/README.md)
tracks milestone status and the path to implementation.
