"""Record what one cut glyph looks like against its line's measured bands.

Three things are recorded and none is enforced: where the glyph's rows sit against the line's
x-height top and baseline, whether the glyph reaches the line box's own top or bottom row, and how
much of its box is ink. A consumer picking exemplars for synthesis wants all three; a gate that
dropped glyphs on any of them would hide the shape of what the corpus actually yields.

The reference is the **line** box, never the word box. A word box is tight to that word's own ink,
so its tallest glyph always touches its top row and its lowest always touches its bottom row. An
earlier check made against the word box read 0.69 to 0.84 of glyphs as clipped across the five
books, which measured nothing but that definition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

import numpy as np

Bounds = tuple[int, int, int, int]
GlyphQualityFlag = Literal[
    "ascends",
    "descends",
    "short_of_baseline",
    "sparse_ink",
    "touches_line_bottom",
    "touches_line_top",
]

GLYPH_QUALITY_METHODS: dict[str, float | int | str] = {
    "algorithm": "line-band-agreement/v1",
    "row_extent_tolerance_px": 1,
    "sparse_ink_density_maximum": 0.15,
}

_ROW_EXTENT_TOLERANCE_PX: Final = 1
"""How far a glyph's rows may sit outside a band before the band flag is raised.

One pixel, because the line's baseline and x-height top are medians over column segments and a
round-half-up of a median lands on either side of a true edge by up to a pixel on its own.
"""

_SPARSE_INK_DENSITY_MAXIMUM: Final = 0.15
"""Below this share of ink in its own box, a cut is more likely a speck than a letter."""


@dataclass(frozen=True, slots=True)
class LineBand:
    """The line measurements a glyph's rows are read against, in the `source` frame."""

    box: Bounds
    baseline_row_px: int
    x_height_top_row_px: int

    def __post_init__(self) -> None:
        _, y_start, _, y_end = self.box
        if y_end <= y_start:
            raise ValueError("A line box must have positive height.")
        if self.x_height_top_row_px > self.baseline_row_px:
            raise ValueError("A line's x-height top must sit at or above its baseline.")


@dataclass(frozen=True, slots=True)
class GlyphQuality:
    """One glyph's recorded quality, with the two offsets the band flags were read from.

    `top_offset_px` is the glyph's first ink row minus the line's x-height top row, so it is
    negative for an ascender. `bottom_offset_px` is the glyph's last ink row minus the baseline
    row, so it is positive for a descender. Both are `None` for a glyph with no line measurement,
    which is every glyph on the `recognized` tier.
    """

    ink_density: float
    row_extent_px: int
    top_offset_px: int | None = None
    bottom_offset_px: int | None = None
    flags: tuple[GlyphQualityFlag, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.ink_density <= 1.0:
            raise ValueError("ink_density must be a share between zero and one.")
        if self.row_extent_px <= 0:
            raise ValueError("row_extent_px must be positive.")
        object.__setattr__(self, "flags", tuple(sorted(set(self.flags))))
        if (self.top_offset_px is None) != (self.bottom_offset_px is None):
            raise ValueError("A glyph's two band offsets are recorded together or not at all.")


def measure_glyph_quality(
    mask: np.ndarray[tuple[int, int], np.dtype[np.bool]],
    *,
    box: Bounds,
    line: LineBand | None,
) -> GlyphQuality:
    """Measure one glyph box against the page ink mask and its line's bands.

    `line` is `None` for a glyph cut from a recognized word, which sits outside every matched line
    and so has no measured baseline to be read against.
    """

    x_start, y_start, x_end, y_end = box
    if x_end <= x_start or y_end <= y_start:
        raise ValueError("A glyph box must have positive width and height.")
    cropped = mask[y_start:y_end, x_start:x_end]
    ink_pixels = int(np.count_nonzero(cropped))
    density = ink_pixels / ((x_end - x_start) * (y_end - y_start))
    flags: list[GlyphQualityFlag] = []
    if density < _SPARSE_INK_DENSITY_MAXIMUM:
        flags.append("sparse_ink")
    if line is None:
        return GlyphQuality(ink_density=density, row_extent_px=y_end - y_start, flags=tuple(flags))

    _, line_y_start, _, line_y_end = line.box
    top_offset = y_start - line.x_height_top_row_px
    bottom_offset = (y_end - 1) - line.baseline_row_px
    if top_offset < -_ROW_EXTENT_TOLERANCE_PX:
        flags.append("ascends")
    if bottom_offset > _ROW_EXTENT_TOLERANCE_PX:
        flags.append("descends")
    if bottom_offset < -_ROW_EXTENT_TOLERANCE_PX:
        flags.append("short_of_baseline")
    if y_start <= line_y_start:
        flags.append("touches_line_top")
    if y_end >= line_y_end:
        flags.append("touches_line_bottom")
    return GlyphQuality(
        ink_density=density,
        row_extent_px=y_end - y_start,
        top_offset_px=top_offset,
        bottom_offset_px=bottom_offset,
        flags=tuple(flags),
    )
