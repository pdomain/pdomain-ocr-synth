"""Tests for recording a cut glyph against its line's measured bands.

Every mask here is built inline. Nothing reads the corpus or opens an image.
"""

from __future__ import annotations

import numpy as np
import pytest

from pdomain_ocr_synth.pgdp.glyph_quality import (
    GlyphQuality,
    LineBand,
    measure_glyph_quality,
)

_LINE = LineBand(box=(0, 10, 100, 30), baseline_row_px=24, x_height_top_row_px=16)


def _mask_with_ink(
    box: tuple[int, int, int, int],
) -> np.ndarray[tuple[int, int], np.dtype[np.bool]]:
    page = np.zeros((40, 100), dtype=np.bool_)
    x_start, y_start, x_end, y_end = box
    page[y_start:y_end, x_start:x_end] = True
    return page


def test_a_glyph_sitting_in_the_x_height_band_raises_no_band_flag() -> None:
    quality = measure_glyph_quality(
        _mask_with_ink((20, 16, 26, 25)), box=(20, 16, 26, 25), line=_LINE
    )
    assert quality.flags == ()
    assert (quality.top_offset_px, quality.bottom_offset_px) == (0, 0)


def test_an_ascender_is_flagged_as_ascending() -> None:
    quality = measure_glyph_quality(
        _mask_with_ink((20, 11, 26, 25)), box=(20, 11, 26, 25), line=_LINE
    )
    assert "ascends" in quality.flags
    assert quality.top_offset_px == -5


def test_a_descender_is_flagged_as_descending() -> None:
    quality = measure_glyph_quality(
        _mask_with_ink((20, 16, 26, 29)), box=(20, 16, 26, 29), line=_LINE
    )
    assert "descends" in quality.flags
    assert quality.bottom_offset_px == 4


def test_a_glyph_that_never_reaches_the_baseline_is_flagged() -> None:
    quality = measure_glyph_quality(
        _mask_with_ink((20, 16, 26, 20)), box=(20, 16, 26, 20), line=_LINE
    )
    assert "short_of_baseline" in quality.flags


def test_a_glyph_one_pixel_outside_a_band_is_within_tolerance() -> None:
    quality = measure_glyph_quality(
        _mask_with_ink((20, 15, 26, 26)), box=(20, 15, 26, 26), line=_LINE
    )
    assert quality.flags == ()


def test_a_glyph_reaching_the_line_box_top_is_flagged() -> None:
    quality = measure_glyph_quality(
        _mask_with_ink((20, 10, 26, 25)), box=(20, 10, 26, 25), line=_LINE
    )
    assert "touches_line_top" in quality.flags


def test_a_glyph_reaching_the_line_box_bottom_is_flagged() -> None:
    quality = measure_glyph_quality(
        _mask_with_ink((20, 16, 26, 30)), box=(20, 16, 26, 30), line=_LINE
    )
    assert "touches_line_bottom" in quality.flags


def test_a_full_box_of_ink_reads_a_density_of_one() -> None:
    quality = measure_glyph_quality(
        _mask_with_ink((20, 16, 26, 25)), box=(20, 16, 26, 25), line=_LINE
    )
    assert quality.ink_density == 1.0
    assert quality.row_extent_px == 9


def test_a_nearly_empty_box_is_flagged_as_sparse() -> None:
    page = np.zeros((40, 100), dtype=np.bool_)
    page[16, 20] = True
    quality = measure_glyph_quality(page, box=(20, 16, 30, 25), line=_LINE)
    assert "sparse_ink" in quality.flags
    assert quality.ink_density < 0.15


def test_a_glyph_with_no_line_records_density_alone() -> None:
    quality = measure_glyph_quality(_mask_with_ink((20, 2, 26, 8)), box=(20, 2, 26, 8), line=None)
    assert quality.top_offset_px is None
    assert quality.bottom_offset_px is None
    assert quality.flags == ()


def test_flags_come_back_sorted_and_deduplicated() -> None:
    quality = GlyphQuality(
        ink_density=0.5,
        row_extent_px=4,
        top_offset_px=0,
        bottom_offset_px=0,
        flags=("descends", "ascends", "ascends"),
    )
    assert quality.flags == ("ascends", "descends")


def test_the_two_band_offsets_are_recorded_together_or_not_at_all() -> None:
    with pytest.raises(ValueError, match="together or not at all"):
        _ = GlyphQuality(ink_density=0.5, row_extent_px=4, top_offset_px=0)


def test_a_line_band_may_not_place_its_x_height_top_below_its_baseline() -> None:
    with pytest.raises(ValueError, match="at or above its baseline"):
        _ = LineBand(box=(0, 10, 100, 30), baseline_row_px=16, x_height_top_row_px=24)


def test_an_empty_glyph_box_is_refused() -> None:
    with pytest.raises(ValueError, match="positive width and height"):
        _ = measure_glyph_quality(
            np.zeros((40, 100), dtype=np.bool_), box=(20, 16, 20, 25), line=None
        )
