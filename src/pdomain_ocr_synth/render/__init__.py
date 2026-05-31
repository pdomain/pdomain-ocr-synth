"""Render layer — turns text + recipe knobs into images + ground truth.

Public surface:

- ``RenderContext`` — opened font cache + per-run RNG.
- ``RenderedSample`` — image + ground-truth metadata produced per call.
- ``render_word_crop`` — render one ``word_crops``-mode sample.
- ``sample_value`` — draw a value from a recipe scalar / range /
  weighted-choice field.
- ``run_recipe`` (M07) — full dataset loop into the
  ``pdomain-ocr-training/v1`` recognition layout.
- ``plan_recipe`` — dry-run summary of what ``run_recipe`` would do.
"""

from __future__ import annotations

from pdomain_ocr_synth.render.context import RenderContext, branched_seed
from pdomain_ocr_synth.render.line import render_line
from pdomain_ocr_synth.render.page import render_page
from pdomain_ocr_synth.render.paragraph import render_paragraph
from pdomain_ocr_synth.render.run import RunPlan, RunResult, plan_recipe, run_recipe
from pdomain_ocr_synth.render.sample import (
    GlyphRun,
    LineBox,
    ParagraphBox,
    RenderedSample,
    WordBox,
)
from pdomain_ocr_synth.render.sampling import sample_color, sample_value, weighted_choice
from pdomain_ocr_synth.render.word_crop import (
    MissingGlyphError,
    RenderError,
    render_word_crop,
)
from pdomain_ocr_synth.render.wrap import fit_lines

__all__ = [
    "GlyphRun",
    "LineBox",
    "MissingGlyphError",
    "ParagraphBox",
    "RenderContext",
    "RenderError",
    "RenderedSample",
    "RunPlan",
    "RunResult",
    "WordBox",
    "branched_seed",
    "fit_lines",
    "plan_recipe",
    "render_line",
    "render_page",
    "render_paragraph",
    "render_word_crop",
    "run_recipe",
    "sample_color",
    "sample_value",
    "weighted_choice",
]
