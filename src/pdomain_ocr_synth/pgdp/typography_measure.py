"""Measure per-line vertical extents, stroke width, and skew, font-free.

Given the page ink mask `alignment_image.build_candidate_mask` builds and one matched
candidate's source-frame box, `measure_line_typography` estimates where the baseline and
x-height top sit, how thick strokes run, and how much the line skews -- all without opening a
font, rendering text, or leaving the `source` coordinate frame.

The estimator is local by design. A whole-line vertical projection smears under skew: at a
half-degree tilt a 1500 px line smears its baseline by `1500 * tan(0.5deg) ~= 13.1` px, which
swallows a 20 px x-height whole. Splitting the box into `max(200, width // 8)` px column
segments and projecting each one separately cuts that smear by the width ratio, to about
1.75 px for a 200 px segment at the same tilt. Taking the median baseline across segments then
recovers the line's typical geometry despite the smear each segment still carries. This is a
local estimator, not a rectification: it never builds a rotated frame or a resampled image.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median
from typing import Literal

import numpy as np

Bounds = tuple[int, int, int, int]
LineExclusionReason = Literal["insufficient_segments", "skew_exceeds_maximum"]

TYPOGRAPHY_MEASURE_METHODS: dict[str, float | int | str] = {
    "algorithm": "segment-vertical-projection/v1",
    "segment_minimum_width_px": 200,
    "segment_width_divisor": 8,
    "minimum_usable_segments": 3,
    "maximum_skew_slope": 0.02,
}

_SEGMENT_MINIMUM_WIDTH_PX = 200
_SEGMENT_WIDTH_DIVISOR = 8
_MINIMUM_USABLE_SEGMENTS = 3
_MAXIMUM_SKEW_SLOPE = 0.02


@dataclass(frozen=True, slots=True)
class LineTypographyMeasurement:
    """One matched line's font-free vertical extents, stroke width, and skew.

    Every field is a pixel count or a dimensionless slope in the `source` frame. Rows are
    box-relative half-open coordinates translated back into the page's absolute frame:
    `baseline_row_px` and `x_height_top_row_px` are absolute row indices, not offsets.
    """

    baseline_row_px: int
    x_height_top_row_px: int
    x_height_px: int
    ascender_extent_px: int
    descender_extent_px: int
    stroke_width_px: float
    skew_slope: float
    segment_count: int

    def __post_init__(self) -> None:
        for name, value in (
            ("baseline_row_px", self.baseline_row_px),
            ("x_height_top_row_px", self.x_height_top_row_px),
            ("ascender_extent_px", self.ascender_extent_px),
            ("descender_extent_px", self.descender_extent_px),
        ):
            if value < 0:
                raise ValueError(f"{name} must be nonnegative.")
        if self.x_height_px != self.baseline_row_px - self.x_height_top_row_px:
            raise ValueError("x_height_px must equal baseline_row_px minus x_height_top_row_px.")
        if self.x_height_px < 0:
            raise ValueError("x_height_px must be nonnegative.")
        if not math.isfinite(self.stroke_width_px) or self.stroke_width_px < 0:
            raise ValueError("stroke_width_px must be a nonnegative finite number.")
        if not math.isfinite(self.skew_slope):
            raise ValueError("skew_slope must be finite.")
        if self.segment_count < _MINIMUM_USABLE_SEGMENTS:
            raise ValueError("A measurement requires the minimum usable segment count.")


@dataclass(frozen=True, slots=True)
class LineTypographyExclusion:
    """Why one matched line's box could not be measured."""

    reason: LineExclusionReason
    segment_count: int
    skew_slope: float | None = None

    def __post_init__(self) -> None:
        if self.segment_count < 0:
            raise ValueError("segment_count must be nonnegative.")
        if self.reason == "skew_exceeds_maximum" and self.skew_slope is None:
            raise ValueError("A skew_exceeds_maximum exclusion requires the measured slope.")
        if self.reason == "insufficient_segments" and self.skew_slope is not None:
            raise ValueError("An insufficient_segments exclusion has no measured slope.")
        if self.skew_slope is not None and not math.isfinite(self.skew_slope):
            raise ValueError("skew_slope must be finite.")


@dataclass(frozen=True, slots=True)
class _SegmentEstimate:
    """One column segment's local baseline and x-height-top row, before pooling."""

    center_x: float
    baseline_row: int
    x_height_top_row: int


def measure_line_typography(
    mask: np.ndarray[tuple[int, int], np.dtype[np.bool]],
    box: Bounds,
) -> LineTypographyMeasurement | LineTypographyExclusion:
    """Measure one matched candidate's box against the page ink mask that produced it.

    `mask` is the full-page boolean ink mask `alignment_image.build_candidate_mask` returns;
    `box` is the candidate's half-open source-frame box. The caller owns rebuilding that mask
    and verifying it reproduces the candidate's recorded evidence before calling this.
    """

    x_start, y_start, x_end, y_end = box
    width = x_end - x_start
    line_mask = mask[y_start:y_end, x_start:x_end]
    segment_width = max(_SEGMENT_MINIMUM_WIDTH_PX, width // _SEGMENT_WIDTH_DIVISOR)
    segments = tuple(
        _measure_segment(line_mask, segment_start, segment_end)
        for segment_start, segment_end in _segment_bounds(width, segment_width)
    )
    usable = tuple(segment for segment in segments if segment is not None)
    if len(usable) < _MINIMUM_USABLE_SEGMENTS:
        return LineTypographyExclusion(reason="insufficient_segments", segment_count=len(usable))

    skew_slope = _fit_skew_slope(usable)
    if abs(skew_slope) > _MAXIMUM_SKEW_SLOPE:
        return LineTypographyExclusion(
            reason="skew_exceeds_maximum", segment_count=len(usable), skew_slope=skew_slope
        )

    baseline_row_local = _round_half_up(median(segment.baseline_row for segment in usable))
    x_height_top_row_local = _round_half_up(median(segment.x_height_top_row for segment in usable))
    baseline_row_px = y_start + baseline_row_local
    x_height_top_row_px = y_start + x_height_top_row_local
    return LineTypographyMeasurement(
        baseline_row_px=baseline_row_px,
        x_height_top_row_px=x_height_top_row_px,
        x_height_px=baseline_row_px - x_height_top_row_px,
        ascender_extent_px=baseline_row_px - y_start,
        descender_extent_px=y_end - baseline_row_px,
        stroke_width_px=_median_stroke_width(line_mask, x_height_top_row_local, baseline_row_local),
        skew_slope=skew_slope,
        segment_count=len(usable),
    )


def _segment_bounds(width: int, segment_width: int) -> tuple[tuple[int, int], ...]:
    """Split `[0, width)` into `segment_width`-wide column ranges.

    A trailing remainder narrower than half a segment is folded into the previous segment
    rather than kept as its own, so a short leftover column strip never stands alone as a
    segment too thin to carry a reliable projection.
    """

    bounds: list[tuple[int, int]] = []
    start = 0
    while start < width:
        end = min(start + segment_width, width)
        bounds.append((start, end))
        start = end
    if len(bounds) >= 2:
        last_start, last_end = bounds[-1]
        if (last_end - last_start) * 2 < segment_width:
            previous_start, _ = bounds[-2]
            bounds[-2] = (previous_start, last_end)
            _ = bounds.pop()
    return tuple(bounds)


def _measure_segment(
    line_mask: np.ndarray[tuple[int, int], np.dtype[np.bool]],
    segment_start: int,
    segment_end: int,
) -> _SegmentEstimate | None:
    """Estimate one segment's local baseline and x-height-top row, or `None` if unusable.

    The baseline is the sharpest downward drop in the lower half of the segment's vertical
    ink projection; the x-height top is the sharpest upward rise in the upper half. "Half" is
    taken over the rows where *this segment* actually carries ink, not over the matched box's
    full row range: under skew, one segment's ink can sit rows away from another's, and a box
    tall enough to hold an extreme ascender or descender at one edge would otherwise push a
    distant segment's own content out of a box-wide half-window entirely. A segment with no
    ink, or no clear drop or rise -- typically one that fell in a between-word gap -- is
    unusable and excluded from the line's pooled estimate rather than forced to report a value.
    """

    profile = line_mask[:, segment_start:segment_end].sum(axis=1)
    ink_rows = np.flatnonzero(profile)
    if ink_rows.size == 0:
        return None
    support_top = int(np.min(ink_rows))
    support_bottom = int(np.max(ink_rows))
    midpoint = (support_top + support_bottom) // 2

    if midpoint >= support_bottom:
        return None
    drops = profile[midpoint:support_bottom] - profile[midpoint + 1 : support_bottom + 1]
    drop_index = int(np.argmax(drops))
    if drops[drop_index] <= 0:
        return None
    baseline_row = midpoint + drop_index

    if support_top >= midpoint:
        return None
    rises = profile[support_top + 1 : midpoint + 1] - profile[support_top:midpoint]
    rise_index = int(np.argmax(rises))
    if rises[rise_index] <= 0:
        return None
    x_height_top_row = support_top + rise_index + 1

    return _SegmentEstimate(
        center_x=(segment_start + segment_end) / 2,
        baseline_row=baseline_row,
        x_height_top_row=x_height_top_row,
    )


def _fit_skew_slope(segments: tuple[_SegmentEstimate, ...]) -> float:
    """Least-squares slope of segment baseline row against segment center column."""

    mean_x = sum(segment.center_x for segment in segments) / len(segments)
    mean_y = sum(segment.baseline_row for segment in segments) / len(segments)
    numerator = sum(
        (segment.center_x - mean_x) * (segment.baseline_row - mean_y) for segment in segments
    )
    denominator = sum((segment.center_x - mean_x) ** 2 for segment in segments)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _median_stroke_width(
    line_mask: np.ndarray[tuple[int, int], np.dtype[np.bool]],
    x_height_top_row_local: int,
    baseline_row_local: int,
) -> float:
    """Median horizontal ink run length across rows between the x-height top and baseline."""

    row_start = min(x_height_top_row_local, baseline_row_local)
    row_end = max(x_height_top_row_local, baseline_row_local)
    run_lengths = np.concatenate(
        [_run_lengths(line_mask[row, :]) for row in range(row_start, row_end + 1)]
    )
    if run_lengths.size == 0:
        return 0.0
    return float(np.median(run_lengths))


def _run_lengths(
    row: np.ndarray[tuple[int, ...], np.dtype[np.bool]],
) -> np.ndarray[tuple[int, ...], np.dtype[np.signedinteger]]:
    """Lengths of every contiguous `True` run in one boolean row, left to right."""

    padded = np.concatenate((np.zeros(1, dtype=np.bool), row, np.zeros(1, dtype=np.bool)))
    later = padded[1:]
    earlier = padded[:-1]
    starts = np.flatnonzero(later & ~earlier)
    ends = np.flatnonzero(earlier & ~later)
    return ends - starts


def _round_half_up(value: float) -> int:
    return math.floor(value + 0.5)
