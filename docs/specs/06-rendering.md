# 06 — Rendering

## Agent Index

- **Kind:** spec
- **Status:** partial
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-11-07
- **Provenance:** rechecked 2026-11-07 against render/, recipe/models.py, validation.py,
  output writers, and tests/test_render*.py. YAML examples were checked against the current recipe models.
- **Disposition:** Retained because shipped behavior and unresolved intent both remain.

Rendering turns transformed text + a chosen font into a clean (un-degraded)
image plus per-glyph ground-truth metadata. Degradation runs after, on the
clean output.

## Current implementation status

HarfBuzz word, line, paragraph, and page rendering ships in
`src/pdomain_ocr_synth/render/`, with deterministic layout and geometry covered
by `tests/test_render*.py`. Current glyph runs provide cluster geometry.

Pillow rendering is schema-accepted but rejected by validation. `subpixel` is
not a recipe field; headings and drop caps remain deferred; page indentation
uses `paragraph_indent_px`. Semantic ligature, long-s, and swash annotations
belong to unbuilt M12 and must not be inferred from current glyph runs.

## Shaping engine

The design catalog describes two engines, but only HarfBuzz is supported now:

| Engine | Use when |
|--------|----------|
| `harfbuzz` (default) | Scripts with shaping rules: ligatures, contextual forms, mark positioning |
| `pillow` | Plain Latin without shaping; faster but no `liga`/`calt` support |

Cló Gaelach uses HarfBuzz. So does anything with marks (Greek polytonic,
Arabic, Devanagari, Gaelic dotted forms when stored as base + combining
mark rather than precomposed).

The HarfBuzz path uses `uharfbuzz` for shaping and `freetype-py` for
rasterization. Anti-aliasing is on; disabling it is rejected. The earlier `subpixel: false`
proposal is not a recipe field.

## Font selection

```yaml
fonts:
  - path: ./fonts/Bunchlo-GC.otf
    weight: 0.4
  - path: ./fonts/Seanchlo-GC.otf
    weight: 0.4
  - path: ./fonts/Duibhlinn.ttf
    weight: 0.2
    features:
      liga: true
      calt: true
```

For each sample, a font is drawn by weight. `features` overrides OpenType features for the renderer.
The renderer explicitly enables `liga` and `calt` by default. HarfBuzz controls other default features;
they are not all disabled.

The validator inspects each font on disk and surfaces these issues at
`pdomain-ocr-synth validate` time:

| Code | When |
|------|------|
| `font_missing` (error) | Required font file does not exist |
| `optional_font_missing` (warning) | `optional: true` font file does not exist; will be skipped at render |
| `font_unreadable` (error) | freetype-py can't open the file |
| `font_empty` (error) | Font reports zero glyphs or an empty cmap |

Glyph coverage is checked **at render time**, not at validate time:
each sample whose token requires a codepoint the chosen font does not
cover raises `MissingGlyphError` and the preview / render writer
records `missing_glyph` as the manifest skip reason (with the missing
codepoints listed). A pre-render corpus-vs-font coverage report and
inspection of `liga`/`calt` GSUB feature presence are deferred — see
[M05's font-validation closeout](../plans/05-rendering.md#font-validation).

## Size, color, DPI

```yaml
rendering:
  font_size_pt: { min: 10, max: 22 }
  dpi: { min: 200, max: 400 }
  ink_color:
    r: { min: 5, max: 50 }
    g: { min: 5, max: 50 }
    b: { min: 5, max: 50 }
  background_color:
    r: { min: 215, max: 250 }
    g: { min: 210, max: 245 }
    b: { min: 195, max: 235 }
  antialiasing: true
```

Per-sample, each value is drawn from its distribution. Independent draws
across R/G/B let you sample warm cream backgrounds and cool ink without
correlation matrices.

## Layout modes

`layout.mode` selects the geometry of each rendered sample.

### `word_crops`

The default for recognition training. Each sample is a single word.

```yaml
layout:
  mode: word_crops
  padding_px: { min: 4, max: 14 }
```

Output: tight image around the word; ground truth = the word string.

`baseline_jitter_px` is accepted by the model but no current renderer applies it.

### `lines`

Each sample is one line of text (multiple words on a baseline).

```yaml
layout:
  mode: lines
  max_width_px: 800
  padding_px: { min: 4, max: 12 }
```

Output: image of N words on one baseline; ground truth = the line.

The earlier `word_spacing` control is not a recipe field. Spaces use the font's shaped advances.
The line renderer also ignores `baseline_jitter_px`.

### `paragraphs`

Wrapped multi-line block.

```yaml
layout:
  mode: paragraphs
  max_width_px: 800
  line_spacing: { min: 1.1, max: 1.5 }
  paragraph_alignment: justify   # left | right | center | justify
```

Output: image of a paragraph; ground truth = paragraph text plus per-line
bounding boxes (used by detection mode in spec 08).

`max_lines`, `alignment`, and `paragraph_indent_em` were earlier proposals, not accepted recipe keys.
The current alignment key is `paragraph_alignment`. Pixel indentation uses `paragraph_indent_px` in pages mode.

### `pages`

Multi-paragraph page synthesis supports one column with sampled padding, paragraph spacing, and
first-line indentation. Headings, drop caps, and multiple columns remain deferred.

```yaml
layout:
  mode: pages
  page_size_px: [1200, 1800]
  max_width_px: 1000
  padding_px: { min: 60, max: 140 }
  paragraph_spacing: { min: 0.8, max: 1.2 }
  paragraph_indent_px: 24
```

Output: page image + per-paragraph + per-line + per-word bounding boxes.

The earlier `margins_px`, `paragraphs_per_page`, `heading_probability`, and `drop_cap_probability`
controls are not recipe fields.

`page_size_px` is optional. When unset, the page canvas is auto-sized
to the natural extent of the composed paragraphs plus padding. When
set to `[width, height]`, the renderer emits an image of *exactly*
that size: content is composed at its natural extent and placed at
the top-left, and the remainder of the canvas is padded with the
sampled `background_color`. If the natural content is larger than the
requested size in either dimension, the renderer raises
`RenderError` — silent truncation would corrupt the per-word/per-line
annotations the detection trainer consumes. Bbox annotations are
emitted in the natural-content rectangle, never extending into the
padded margin.

## Ground truth captured per sample

Regardless of layout mode, each rendered sample emits:

| Field | Meaning |
|-------|---------|
| `text` | Codepoint string of the rendered text |
| `font_path` | Resolved font path |
| `font_size_pt` | Drawn size |
| `dpi` | Drawn DPI |
| `bbox` | Tight bounding box of the inked region (px) |
| `glyph_runs` | Per-glyph (or per-cluster) bbox + cluster index, when shaping_engine = harfbuzz |
| `line_boxes` | Per-line bbox + text in paragraphs/pages; empty for word crops and single-line samples |
| `word_boxes` | Per-word bbox + text in lines/paragraphs/pages; empty for word crops |
| `paragraph_boxes` | Per-paragraph bbox + text in paragraphs/pages; empty for word crops and lines |

The writers persist selected metadata, not the whole `RenderedSample`. Recognition manifests retain
`word_boxes` when present; detection labels group word boxes under `lines` and retain `paragraphs` when present.
Neither writer persists `glyph_runs`. Detection-mode output
uses these boxes to write `labels.json`-compatible records (an
earlier draft of spec 08 called this file `pages.json`; the trainer's
`DetectionDataset` reader is the canonical contract).

## Rendering pitfalls

- **Mark stacking.** Gaelic dotted consonants stored as base + combining
  mark may render with the dot misaligned if the font's mark positioning
  is bad. Validate visually; prefer precomposed codepoints when both forms
  exist.
- **Tofu / .notdef.** A square box means the font doesn't have that glyph.
  Coverage is checked at render time; the renderer skips and records missing codepoints.
- **Hinting.** TrueType vs CFF/PostScript fonts hint differently at small
  sizes — let DPI variation cover this rather than sweeping hint settings.
- **Italic fonts at low DPI.** Glyphs touch and confuse the model. Use
  italics sparingly and at higher DPI.

## Adversarial Review

- **Stage and source:** Migration-time post-implementation review of the document, repository
  history, code, tests, and linked plans. Evidence included 7776904, eaf961b, 861ae8b, ee54805,
  f7b59e4, 4a6b199.
- **Accepted findings:** HarfBuzz word, line, paragraph, and page rendering; weighted fonts;
  deterministic draws; fixed page canvases; and bbox/glyph-run geometry shipped with extensive
  tests. Pillow rendering, some advertised layout controls, and the semantic glyph-annotation
  objective remain unbuilt or deliberately changed, so the design is partial.
- **Effect on this document:** Status: `partial`. Retained for unresolved intent; the original
  design is not fully shipped truth.
- **Implementation deviations:** pillow is schema-accepted but validation rejects it; only
  HarfBuzz rendering ships. subpixel is documented but absent from the recipe model. OpenType
  feature toggles are modeled on fonts but the promised general feature behavior is not fully
  established by the renderer/tests. paragraph_indent_em became paragraph_indent_px and is
  meaningful for pages; paragraph alignment support evolved separately. heading_probability and
  drop_cap_probability are advertised but deferred. Glyph runs provide cluster geometry today,
  while M12's semantic ligature/long-s/swash annotations are not started. The prose says the
  validator should catch tofu, but coverage is intentionally render-time.
- **Residual risks:** Complete or remove Pillow/antialiasing/subpixel and font-feature promises.
  Adjudicate page headings/drop caps and deferred font coverage/GSUB reports. Ship M12 semantic
  glyph annotations without confusing them with existing geometric glyph_runs. Promote the
  shipped HarfBuzz/layout/bbox invariants to architecture when open rendering intent is
  separated.
