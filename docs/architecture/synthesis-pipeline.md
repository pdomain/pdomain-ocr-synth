# Synthesis pipeline

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Owner:** CT
- **Created:** 2026-11-12
- **Last verified:** 2026-11-12
- **Provenance:** written 2026-11-12 from `corpus/`, `text_transforms/`, `render/run.py`,
  `degradation/`, and the output writers. Tests named below were not re-run.
- **Disposition:** Current truth for how a recipe becomes images. Recipe loading and the
  output contract live in the sibling architecture notes.
- **Promotes:** the shipped parts of specs 04, 05, 06, and 07 and plans 03, 05, and 06.

A render walks one recipe from text to a degraded image.

Loading, validation, and the files on disk are in
[Development and recipe system](development-and-recipe-system.md) and
[Output and publishing](output-and-publishing.md).

## Steps, resume, and workers

`run_recipe` in `src/pdomain_ocr_synth/render/run.py` does five things.

1. It collects corpus text and runs the recipe text transforms.
2. It tokenizes that text for the layout mode.
3. It draws `count` tokens with replacement from `Random(effective_seed ^ 0xC0FFEE)`.
   The sample index does not choose the token.
4. It renders each sample, then degrades it. The sample index reseeds that work through
   `branched_seed`.
5. It writes recognition or detection output.

Resume is off unless the caller asks for it.

- A non-empty destination without `--force` or `--resume` raises
  `DestinationNotEmptyError`.
- `--force` and `--resume` together are rejected.
- `--force` wipes the destination.
- `--resume` with no snapshot raises `SnapshotMismatchError`, including on an empty
  directory.
- Invalid `labels.json` raises `SnapshotMismatchError`.
- Resume also raises `SnapshotMismatchError` unless the tool version, seed, input
  hashes, and recipe match.

`output.count` may grow. Resume keeps indexes that already have a successful manifest
row and renders the rest.

Worker count does not change the image, the label, or the manifest payload. Wall time
and audit timestamps do change between runs.

## Corpus providers and names that are not registered

Three providers are registered: `local`, `web`, and `wikisource`.

`run_providers` walks `recipe.corpus` in order. Each entry can filter its text.

`local` reads files from disk. `web` and `wikisource` use the on-disk cache unless the
entry sets `cache: false` or the caller passes `no_cache`.

`pdomain-ocr-synth fetch` warms that cache. The render path uses the same providers.

Wikisource title fetch works.

Fetch or render raises `ProviderError` for a category lookup. The model accepts
`category`. Validation does not flag it.

A third-party provider can register on the entry-point group
`pdomain_ocr_synth.corpus_providers`. A broken plugin does not stop validation of a
recipe that does not use it.

`hf_dataset` is a recipe-model type and is not registered. Validation reports
`corpus_provider_not_implemented` for it.

`web_list`, `internet_archive`, and `gutenberg` are names in spec 04. They are not
recipe-model types, and they are not registered providers.

## Text joining and transforms

Non-empty provider texts are joined with `\n\n`. The transforms then run with the
recipe seed. Tokenization runs on that transformed text.

Wikisource text and filtered text already end in a newline, so the boundary can be
three newlines. `normalize_whitespace` collapses a run of three or more consecutive
newlines to two.

The page split on three newlines applies only in pages mode, and only when that run
is still present.

The registered callables are `normalize_whitespace`, `lowercase`, `uppercase`,
`strip_punctuation`, `nfc`, `nfd`, `nfkc`, `nfkd`, `regex_replace`, `keep_only`,
`min_token_length`, `max_token_length`, `apply_lenition_dots`, `seimhiu_to_dot`,
`dot_to_seimhiu`, `tironian_et`, and `long_s_medial`.

The Gaelic recipe uses `normalize_whitespace`, `keep_only`, `apply_lenition_dots`,
`tironian_et`, and `long_s_medial`.

`u_v_swap`, `i_j_swap`, and `ct_st_ligature_marker` are described in spec 05 and are
not registered. Validation rejects them.

## Layouts and sample drawing

The renderer shapes with HarfBuzz (`uharfbuzz`) and rasterizes with `freetype-py`.

`rendering.antialiasing` defaults to true. `false` is rejected as
`antialiasing_disable_not_implemented`. The rasterizer always uses `FT_LOAD_RENDER`
and does not read the flag.

The recipe field `subpixel` does not exist.

The schema accepts a Pillow engine, and validation rejects it.

Four layouts ship:

| `output.mode` | `layout.mode` | One sample is |
| --- | --- | --- |
| recognition | `word_crops` | one word |
| recognition | `lines` | one line, with per-word boxes in the manifest |
| detection | `paragraphs` | one paragraph |
| detection | `pages` | one page of paragraphs |

Paragraph tokens split on `\n\s*\n+`, so a space-only blank line still splits.

Page tokens split on `\n\s*\n\s*\n+`. Each page then splits on the paragraph
boundary, and those paragraphs wrap on their own.

Hard newlines stay line breaks.

Unset `max_width_px` does not wrap.

Paragraphs and pages use `line_spacing`, default 1.2 nominal line heights. They also
use `paragraph_alignment`: `left`, `center`, `right`, or `justify`.

`center` and `right` align every line. Under `justify`, the last line and any
single-word line stay left.

Pages also use `paragraph_spacing`, default 1.0 line heights, and first-line
`paragraph_indent_px`. That indent also shrinks the first line's wrap budget.

On pages, `page_size_px` pads smaller content to that size at the top left and does
not shift boxes. Content larger in either dimension raises `RenderError`.

Other modes warn `layout_key_unused` and ignore the key.

Each sample draws one font by weight.

Shaping starts from `liga` and `calt` on. `font.features` overrides that map.
Features left unset stay at HarfBuzz defaults.

`glyph_runs` are cluster geometry from that shaping. They are not semantic glyph
annotations. Nothing in `src/` writes `glyph_annotations`.

A missing codepoint raises `MissingGlyphError`. Preview and render record
`missing_glyph` and the missing codepoints.

Validate does not preflight a corpus against a font.

Headings and drop caps are not layout features.

## Degradation stages

Stages run in recipe order. The runner does not reorder them.

Each stage applies with its `probability`. A skip leaves the sample unchanged.

Pixel stages are `blur`, `noise`, `brightness`, `contrast`, `gamma`, `ink_bleed`,
`ink_thin`, `paper_texture`, `foxing`, `jpeg`, `webp`, and `grayscale`. They use
Pillow and NumPy. They do not move boxes.

`skew` is the only geometry stage. It rotates around the image center, expands the
canvas, and updates the boxes and glyph runs. The output stays RGB.

`perspective`, `scale`, `bleed_through`, `scratches`, `fold_line`, and `binarize`
are catalog names. Validation rejects them.

The manifest field `degradations_applied` lists the configured kind, probability, and
optional `name`. It does not list which probability rolls fired, and it does not list
the sampled option values.

There is no public plugin registry for stages. Built-ins register into a module dict
at import.

## Code and tests read for this note

- Code: `src/pdomain_ocr_synth/corpus/registry.py`, `corpus/runner.py`,
  `text_transforms/builtins.py`, `render/run.py`, `degradation/pipeline.py`, and
  `degradation/builtins.py`. The manifest records are written in
  `output/recognition.py` and `output/detection.py`.
- Tests: `tests/test_corpus_local.py`, `tests/test_corpus_web.py`,
  `tests/test_corpus_wikisource.py`, `tests/test_corpus_runner.py`,
  `tests/test_text_transforms.py`, `tests/test_render.py`, `tests/test_render_line.py`,
  `tests/test_render_paragraph.py`, `tests/test_render_page.py`,
  `tests/test_degradation.py`, `tests/test_cli_render.py`,
  `tests/test_cli_render_lines.py`, `tests/test_cli_render_paragraphs.py`, and
  `tests/test_cli_render_pages.py`.
- Verified: 2026-11-12 by reading those modules. The suites were not re-run for this note.
