"""Tests for font-free per-line typographic measurement.

Every fixture here is a synthetic block bitmap built from exact, known geometry -- vertical bars
standing in for glyph strokes, placed at exact rows for x-height bodies, ascenders, and
descenders. No font is opened or rendered, so these run on any machine with no fonts fetched.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pytest

from pdomain_ocr_synth.pgdp.typography_measure import (
    LineTypographyExclusion,
    LineTypographyMeasurement,
    measure_line_typography,
)

if TYPE_CHECKING:
    from pdomain_ocr_synth.pgdp.typography_measure import Bounds

# Every synthetic line spans this many columns, chosen so `max(200, width // 8)` divides it
# into exactly eight 200 px segments with no trailing remainder, keeping the segment-merge
# edge case out of the accuracy fixtures below (it gets its own focused test instead).
_TOTAL_WIDTH = 1600
_PADDING_ROWS = 30
# Larger than `1600/2 * tan(1deg) ~= 14`, the widest per-bar vertical shift any fixture here
# produces, so a shifted bar's ink never runs off the top or bottom of the canvas.


@dataclass(frozen=True, slots=True)
class _SyntheticLine:
    """A synthetic block bitmap plus the exact geometry used to build it."""

    mask: np.ndarray[tuple[int, int], np.dtype[np.bool]]
    box: Bounds
    baseline_row_px: int
    x_height_top_row_px: int
    stroke_width_px: int


def _build_synthetic_line(
    *, x_height_px: int, stroke_width_px: int, skew_degrees: float, gap_px: int
) -> _SyntheticLine:
    """Build one synthetic line of vertical-bar glyph stubs at exact known rows.

    Most bars span only the x-height body; every fifth bar also carries an ascender, and
    every seventh carries a descender, so the projection each segment sees is dominated by
    plain x-height ink, matching how a real line of type is dominated by lowercase letters.
    Skew shifts each bar vertically by its own column position times the true slope, which
    reproduces a skewed scan without rotating or resampling any pixel.
    """

    ascender_extent = x_height_px
    descender_extent = max(2, x_height_px // 2)
    x_height_top = _PADDING_ROWS + ascender_extent
    baseline = x_height_top + x_height_px - 1
    descender_bottom = baseline + descender_extent
    canvas_height = descender_bottom + 1 + _PADDING_ROWS
    canvas = np.zeros((canvas_height, _TOTAL_WIDTH), dtype=np.bool)

    true_slope = math.tan(math.radians(skew_degrees))
    stride = stroke_width_px + gap_px
    bar_index = 0
    position = 0
    while position + stroke_width_px <= _TOTAL_WIDTH:
        center_x = position + stroke_width_px / 2
        offset = round(true_slope * (center_x - _TOTAL_WIDTH / 2))
        if bar_index % 5 == 0:
            row_top, row_bottom = _PADDING_ROWS + offset, baseline + offset
        elif bar_index % 7 == 0:
            row_top, row_bottom = x_height_top + offset, descender_bottom + offset
        else:
            row_top, row_bottom = x_height_top + offset, baseline + offset
        canvas[row_top : row_bottom + 1, position : position + stroke_width_px] = True
        bar_index += 1
        position += stride

    rows_with_ink = np.flatnonzero(canvas.any(axis=1))
    columns_with_ink = np.flatnonzero(canvas.any(axis=0))
    box: Bounds = (
        int(np.min(columns_with_ink)),
        int(np.min(rows_with_ink)),
        int(np.max(columns_with_ink)) + 1,
        int(np.max(rows_with_ink)) + 1,
    )
    return _SyntheticLine(
        mask=canvas,
        box=box,
        baseline_row_px=baseline,
        x_height_top_row_px=x_height_top,
        stroke_width_px=stroke_width_px,
    )


def _fixture_cases() -> tuple[tuple[int, int, float, int], ...]:
    """Build the Gate 3 fixture sweep: `(x_height_px, stroke_width_px, skew_degrees, gap_px)`.

    A full cross of x-height and stroke at zero skew, then a dedicated skew sweep and a
    dedicated gap sweep held at mid-range x-height and stroke. Together they cover every edge
    the plan names: x-height 8 to 40, stroke 1 to 5, skew 0 and +/-0.5 and +/-1.0 degrees, and
    gaps 2 to 20, with no fixture repeated.
    """

    x_heights = (8, 14, 20, 28, 40)
    strokes = (1, 2, 3, 4, 5)
    skews_degrees = (0.5, -0.5, 1.0, -1.0)
    gaps = (2, 6, 10, 14, 20)

    cases: list[tuple[int, int, float, int]] = [
        (x_height, stroke, 0.0, 8) for x_height in x_heights for stroke in strokes
    ]
    cases.extend((20, 2, skew, 8) for skew in skews_degrees)
    cases.extend((20, 2, 0.0, gap) for gap in gaps)
    return tuple(cases)


_FIXTURE_CASES = _fixture_cases()


def test_fixture_sweep_covers_the_gate_3_parameter_space() -> None:
    assert len(_FIXTURE_CASES) >= 24
    assert len(set(_FIXTURE_CASES)) == len(_FIXTURE_CASES)
    x_heights = {case[0] for case in _FIXTURE_CASES}
    strokes = {case[1] for case in _FIXTURE_CASES}
    skews = {case[2] for case in _FIXTURE_CASES}
    gaps = {case[3] for case in _FIXTURE_CASES}
    assert min(x_heights) == 8
    assert max(x_heights) == 40
    assert min(strokes) == 1
    assert max(strokes) == 5
    assert skews >= {0.0, 0.5, -0.5, 1.0, -1.0}
    assert min(gaps) == 2
    assert max(gaps) == 20


@pytest.mark.parametrize(
    ("x_height_px", "stroke_width_px", "skew_degrees", "gap_px"),
    _FIXTURE_CASES,
    ids=[
        f"xh{x_height}-st{stroke}-sk{skew}-gap{gap}"
        for x_height, stroke, skew, gap in _FIXTURE_CASES
    ],
)
def test_recovers_known_geometry_within_one_pixel(
    x_height_px: int, stroke_width_px: int, skew_degrees: float, gap_px: int
) -> None:
    line = _build_synthetic_line(
        x_height_px=x_height_px,
        stroke_width_px=stroke_width_px,
        skew_degrees=skew_degrees,
        gap_px=gap_px,
    )

    measured = measure_line_typography(line.mask, line.box)

    assert isinstance(measured, LineTypographyMeasurement)
    assert abs(measured.baseline_row_px - line.baseline_row_px) <= 1
    assert abs(measured.x_height_top_row_px - line.x_height_top_row_px) <= 1
    assert abs(measured.stroke_width_px - line.stroke_width_px) <= 1
    assert measured.x_height_px == measured.baseline_row_px - measured.x_height_top_row_px
    assert measured.ascender_extent_px == measured.baseline_row_px - line.box[1]
    assert measured.descender_extent_px == line.box[3] - measured.baseline_row_px


def test_excludes_a_box_too_narrow_for_three_segments() -> None:
    line = _build_synthetic_line(x_height_px=20, stroke_width_px=2, skew_degrees=0.0, gap_px=8)
    narrow_box: Bounds = (line.box[0], line.box[1], line.box[0] + 150, line.box[3])

    measured = measure_line_typography(line.mask, narrow_box)

    assert isinstance(measured, LineTypographyExclusion)
    assert measured.reason == "insufficient_segments"
    assert measured.segment_count < 3
    assert measured.skew_slope is None


def test_excludes_a_line_past_the_skew_backstop() -> None:
    line = _build_synthetic_line(x_height_px=20, stroke_width_px=2, skew_degrees=5.0, gap_px=8)

    measured = measure_line_typography(line.mask, line.box)

    assert isinstance(measured, LineTypographyExclusion)
    assert measured.reason == "skew_exceeds_maximum"
    assert measured.skew_slope is not None
    assert abs(measured.skew_slope) > 0.02


def test_measurement_rejects_an_inconsistent_x_height() -> None:
    with pytest.raises(ValueError, match="x_height_px"):
        _ = LineTypographyMeasurement(
            baseline_row_px=100,
            x_height_top_row_px=80,
            x_height_px=19,
            ascender_extent_px=100,
            descender_extent_px=10,
            stroke_width_px=2.0,
            skew_slope=0.0,
            segment_count=8,
        )


def test_exclusion_requires_a_slope_only_for_the_skew_reason() -> None:
    with pytest.raises(ValueError, match="skew_exceeds_maximum"):
        _ = LineTypographyExclusion(reason="skew_exceeds_maximum", segment_count=3, skew_slope=None)
    with pytest.raises(ValueError, match="insufficient_segments"):
        _ = LineTypographyExclusion(
            reason="insufficient_segments", segment_count=1, skew_slope=0.01
        )
