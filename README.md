# pdomain-ocr-synth

## Agent Index

- **Kind:** usage
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-07-14
- **Provenance:** agent-verified from repository evidence during the 2026-07-14 docgraph migration
- **Disposition:** Retained as the project entry point.

Synthetic OCR training-data generator. Produces labeled image+text pairs for
historical and specialty typography (first target: Cló Gaelach / early Irish
typography), in the format consumed by `pd-ocr-trainer` profiles.

**Status:** M00–M10 substantially shipped. M11 (preview UI) and M12 (glyph annotations) remain.
The `docs/specs/` set is the authoritative design reference; `docs/plans/` tracks milestone progress.
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
[ pd-ocr-trainer ]  reads new profile (e.g. `gaelic`)
        │
        ▼
[ pdomain-ocr-cli ]  uses fine-tuned model on real scans
```

The output adapter writes directly into the directory layout
`pd-ocr-trainer` already understands.

## Getting started

Read the specs in order:

| # | Spec | What it covers |
|---|------|----------------|
| 00 | [Overview](docs/specs/00-overview.md) | Goals, non-goals, integration |
| 01 | [Development and recipe system](docs/architecture/development-and-recipe-system.md) | CLI and recipe architecture |
| 02 | [Recipe format](docs/specs/02-recipe-format.md) | YAML schema reference |
| 03 | [Recipe workflow](docs/usage/recipe-workflow.md) | Create, validate, render, and publish a recipe |
| 04 | [Corpus providers](docs/specs/04-corpus-providers.md) | Local, web, Wikisource, HF datasets |
| 05 | [Text transforms](docs/specs/05-text-transforms.md) | Lenition, long-s, Tironian et |
| 06 | [Rendering](docs/specs/06-rendering.md) | Fonts, shaping, layouts |
| 07 | [Degradation](docs/specs/07-degradation.md) | Augmentation pipeline |
| 08 | [Output and publishing](docs/architecture/output-and-publishing.md) | Trainer layouts and publishing |
| 09 | [Extending](docs/specs/09-extending.md) | Adding providers / transforms / degradations |
| 10 | [Output and publishing](docs/architecture/output-and-publishing.md) | Push rendered datasets to Hugging Face |
| 11 | [Preview UI](docs/specs/11-preview-ui.md) | NiceGUI for visual recipe tuning with explicit create/save actions |
| 12 | [Glyph annotations emission](docs/specs/12-glyph-annotations-emission.md) | Per-word ligature / long-s side channel |
| 13 | [Dev-local mode and deps](docs/specs/13-dev-local-mode-and-deps.md) | `upgrade-deps` must not silently revert dev-local venvs |

A full worked recipe lives at the filesystem path `recipes/gaelic.yaml`. It is
not part of the governed Markdown graph.

## Implementation roadmap

Specs describe the destination; the [implementation roadmap](docs/plans/README.md)
tracks milestone status and the path to implementation.
