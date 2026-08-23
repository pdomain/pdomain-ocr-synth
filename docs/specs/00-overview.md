# 00 — Overview

## Agent Index

- **Kind:** spec
- **Status:** partial
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-07-14
- **Provenance:** agent-verified from repository evidence during the 2026-07-14 docgraph migration
- **Disposition:** Retained because shipped behavior and unresolved intent both remain.

## Purpose

Generate labeled synthetic images for OCR training of historical and specialty
typography. Output drops directly into a `pd-ocr-trainer` profile.

## Current implementation status

The recipe-driven CLI, HarfBuzz rendering, local/web/Wikisource corpus inputs,
recognition and detection outputs, and Hugging Face publishing are shipped.
See `src/pdomain_ocr_synth/` and the integration tests under `tests/`.

Hugging Face corpus input, Internet Archive, Gutenberg, `web_list`, the M11
browser UI, and M12 semantic glyph annotations are not shipped. Current
`glyph_runs` describe rendering geometry; they are not the planned semantic
annotation side channel.

## Goals

1. **Recipe-driven.** A YAML file fully describes a synthetic dataset:
   text source, transforms, fonts, layout, degradation, output target.
2. **Web-aware corpora.** Recipes can pull text from URLs, Wikisource, the
   Internet Archive, or Hugging Face datasets, with on-disk caching.
3. **CLI-first.** `pdomain-ocr-synth render <recipe.yaml>` produces a dataset.
   Other subcommands handle scaffolding, validation, preview, and corpus
   fetching.
4. **Pluggable seams.** Corpus provider, text transform, and degradation
   stages are extension points so new scripts can be added without forking.
5. **Concrete first.** Gaelic is the first recipe; abstractions are
   extracted only when a second recipe (Fraktur, blackletter, etc.) makes
   the seams obvious.

## Non-goals

- **Not a model trainer.** That's `pd-ocr-trainer`.
- **Not a labeler / corrector.** That's `pd-ocr-labeler`.
- **Not a full layout simulator.** Page-level synthesis is a stretch goal;
  the v1 emphasis is recognition data (word/line crops) plus simple
  paragraph layouts for detection.
- **Not a font ingestion tool.** Fonts must be present on disk and licensed
  by the user. The recipe references them.

## Workspace integration

| Direction | Touchpoint |
|-----------|-----------|
| Inbound (text) | Local files, URLs, Wikisource, CELT, HF datasets, Internet Archive |
| Inbound (fonts) | User-provided font files referenced by absolute or recipe-relative paths |
| Outbound (local) | A `pd-ocr-trainer` profile directory (recognition or detection layout) |
| Outbound (HF) | Optional Hugging Face dataset repo via `pdomain-ocr-synth publish` (see [Output and publishing](../architecture/output-and-publishing.md) and the workspace-level filesystem path `DATASETS.md`, which is outside this governed Markdown graph) |

The outbound contract is defined by `pd-ocr-trainer`'s `dataset_store.py`. See
[Output and publishing](../architecture/output-and-publishing.md) for the layout this project must
match.

## First recipe: Gaelic

`recipes/gaelic.yaml` targets Cló Gaelach (insular Irish typography) plus the
orthographic features of pre-reform Irish text:

- Punctum delens (`ḃ ċ ḋ ḟ ġ ṁ ṗ ṡ ṫ`) — replaces modern `bh ch dh fh gh
  mh ph sh th`
- Tironian et (`⁊`) for "agus" / "and"
- Long s (`ſ`) in word-medial position
- Insular letterforms via Cló Gaelach fonts (Bunchló, Seanchló, Duibhlinn)

## Future recipes (sketches, not committed)

- **Fraktur** — German blackletter, long-s rules, ß handling
- **Early-modern English** — long-s, ligatures (ct, st), interchange of u/v
  and i/j, italic catchwords
- **Greek** — polytonic accents, breathings
- **Cyrillic Old Slavonic** — titlos, abbreviations, archaic letterforms

Each becomes a YAML recipe plus optionally a small Python module of
script-specific transforms.

## Scan-derived typography and structure

The active [PGDP typography and page-structure design](2026-08-22-pgdp-typography-structure-synthesis-design.md)
extends the original recognition-first scope. It defines a measurement-first program for learning
book styles from PGDP scans and generating structured pages with mixed typography.

The active [PGDP source-line alignment design](2026-08-23-pgdp-source-line-alignment-design.md)
defines M15b. It conservatively aligns byte-preserved F2 lines with source-frame image candidates
on eligible single-column pages. Rectification remains a separate M15c milestone.

## Open questions

These are flagged here so the spec doesn't pretend they're settled.

1. **Font licensing — resolved.** This is a non-commercial project, so
   all four font families used by `recipes/gaelic.yaml` (Gaelchló,
   Gadelica, Gaedhilge, Cló Tuamach) are free to *use*. Gaelchló forbids
   redistribution and the other non-OFL families have unclear
   redistribution terms, so none are bundled in the repo. See
   [`fonts-gaelic.md`](fonts-gaelic.md) for download instructions. The
   OFL-licensed Gaedhilge is the candidate for a future CI/test fallback.
2. **Scope of the first recipe.** Pure Irish-language text vs. mixed-script
   pages (English grammar of Irish, dictionaries) is a layout question that
   may justify a second recipe rather than complicating the first.
3. **Detection vs. recognition first.** Recognition word-crops are the
   easier and higher-volume path; detection requires plausible page layouts.
   v1 focuses on recognition.
4. **Glyph-level ground truth.** For ligatures and insular forms, the
   character a reader perceives may not match the codepoint string. We
   record the codepoint string as ground truth and let the trainer's vocab
   handle the rest; this matches `pd-ocr-trainer`'s current behavior.

## Adversarial Review

- **Stage and source:** Migration-time post-implementation review of the document, repository
  history, code, tests, and linked plans. Evidence included 852c878, fd9fe7c, CLAUDE.md,
  README.md, recipes/gaelic.yaml, src/pdomain_ocr_synth/cli.py.
- **Accepted findings:** The core recipe-driven OCR synthesizer, Gaelic recipe, CLI, extensible
  registries, corpus cache, recognition/detection output, and publishing path shipped across
  M00-M10, so most of the overview describes real product direction. It remains the repository's
  architecture pointer and still contains live M11/M12 intent, so it is neither fully
  implemented nor disposable.
- **Effect on this document:** Status: `partial`. Retained for unresolved intent; the original
  design is not fully shipped truth.
- **Implementation deviations:** The document promises broad web-aware corpus coverage, but only
  local, web, and Wikisource providers are registered; Hugging Face input, Internet Archive,
  Gutenberg, and web_list remain deferred. The CLI table elsewhere includes preview, but the
  planned M11 browser preview UI is not shipped. Glyph-level ground truth is deferred to M12;
  current glyph_runs are rendering geometry, not the planned semantic ligature/long-s annotation
  side channel. The outbound trainer name and repository-wide command names were renamed after
  the original design.
- **Residual risks:** Ship M11 preview UI. Ship M12 semantic glyph annotations. Retain the
  explicit non-goals, font-licensing boundary, trainer output contract, and concrete-first
  abstraction rule as durable rationale. Decide whether the sketched non-Gaelic recipes and
  deferred corpus providers remain roadmap bets.
