"""Tests for deterministic PGDP source-frame line candidate extraction."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PIL import Image, ImageDraw

from pdomain_ocr_synth.pgdp.image_measurement import open_image_snapshot
from pdomain_ocr_synth.pgdp.profile_models import CoordinateFrame, InkBand, ProfileDiagnostic

if TYPE_CHECKING:
    from pdomain_ocr_synth.pgdp.alignment_candidates import CandidateExtraction


_SOURCE_FRAME = CoordinateFrame(width=100, height=80)
_FOREGROUND_BOUNDS = (10, 10, 90, 70)
_ROW_BANDS = (
    InkBand(y_start=20, y_end=25),
    InkBand(y_start=35, y_end=40),
    InkBand(y_start=50, y_end=55),
)


def _extract(
    image_path: Path, *, diagnostics: tuple[ProfileDiagnostic, ...] = ()
) -> CandidateExtraction:
    from pdomain_ocr_synth.pgdp.alignment_candidates import extract_line_candidates

    with open_image_snapshot(image_path) as snapshot:
        return extract_line_candidates(
            snapshot,
            source_frame=_SOURCE_FRAME,
            foreground_bounds=_FOREGROUND_BOUNDS,
            ink_bands=_ROW_BANDS,
            diagnostics=diagnostics,
        )


def _page_with_rows(*, border: bool = False, rule: bool = False) -> Image.Image:
    image = Image.new("L", (100, 80), color=255)
    draw = ImageDraw.Draw(image)
    if border:
        draw.rectangle((0, 0, 99, 79), outline=0, width=1)
    for y_start, y_end, first_end, second_start, second_end in (
        (20, 24, 28, 32, 55),
        (35, 39, 31, 35, 58),
        (50, 54, 34, 40, 62),
    ):
        draw.rectangle((20, y_start, first_end, y_end), fill=0)
        draw.rectangle((second_start, y_start, second_end, y_end), fill=0)
    if rule:
        draw.line((10, 60, 89, 60), fill=0, width=1)
    return image


def test_extract_candidates_removes_border_and_long_rule(tmp_path: Path) -> None:
    image_path = tmp_path / "rows.png"
    _page_with_rows(border=True, rule=True).save(image_path)

    result = _extract(image_path)

    assert [candidate.box for candidate in result.candidates] == [
        (20, 20, 56, 25),
        (20, 35, 59, 40),
        (20, 50, 63, 55),
    ]
    assert [candidate.band_ordinal for candidate in result.candidates] == [0, 1, 2]
    assert [(item.reason, item.box) for item in result.rejected] == [
        ("long_horizontal_rule", (10, 60, 90, 61)),
        ("page_border", (0, 0, 100, 80)),
    ]
    assert result.probable_multi_column is False
    assert result.gutter is None
    assert result.exclusions == ()


def test_candidate_records_component_measurements_and_normalized_profile(tmp_path: Path) -> None:
    image_path = tmp_path / "rows.png"
    _page_with_rows().save(image_path)

    result = _extract(image_path)

    candidate = result.candidates[0]
    assert candidate.component_count == 2
    assert candidate.foreground_pixels == 165
    assert candidate.width == 36
    assert candidate.height == 5
    assert candidate.fill_ratio == pytest.approx(165 / 180)
    assert len(candidate.horizontal_ink_profile) == candidate.width
    assert sum(candidate.horizontal_ink_profile) == pytest.approx(1.0)
    assert candidate.horizontal_ink_profile[:9] == pytest.approx((1 / 33,) * 9)


def test_extract_candidates_excludes_fragmented_band_in_stable_order(tmp_path: Path) -> None:
    image_path = tmp_path / "fragmented.png"
    image = _page_with_rows()
    draw = ImageDraw.Draw(image)
    draw.rectangle((70, 35, 78, 39), fill=0)
    image.save(image_path)

    result = _extract(image_path)

    assert result.candidates == ()
    assert result.exclusions == ("fragmented_band",)
    assert [(item.reason, item.band_ordinal, item.box) for item in result.rejected] == [
        ("fragmented_band", 1, (20, 35, 59, 40)),
        ("fragmented_band", 1, (70, 35, 79, 40)),
    ]


def test_extract_candidates_detects_persistent_vertical_gutter(tmp_path: Path) -> None:
    image_path = tmp_path / "columns.png"
    image = Image.new("L", (100, 80), color=255)
    draw = ImageDraw.Draw(image)
    for y_start, y_end in ((20, 24), (35, 39), (50, 54)):
        draw.rectangle((10, y_start, 38, y_end), fill=0)
        draw.rectangle((61, y_start, 89, y_end), fill=0)
    image.save(image_path)

    result = _extract(image_path)

    assert result.probable_multi_column is True
    assert result.gutter is not None
    assert result.gutter.box == (39, 20, 61, 55)
    assert result.exclusions == ("fragmented_band", "probable_multi_column")


@pytest.mark.parametrize(
    ("inherited_code", "expected_exclusion"),
    [
        ("blank_page", "blank_page"),
        ("one_ink_band", "insufficient_ink_bands"),
        ("no_ink_bands", "insufficient_ink_bands"),
        ("border_dominated", "border_dominated"),
        ("high_foreground_ratio", "high_foreground_ratio"),
        ("image_missing", "image_missing"),
        ("image_unreadable", "image_unreadable"),
        ("image_decode_failed", "image_decode_failed"),
        ("foreground_bounds_unavailable", "foreground_bounds_unavailable"),
        ("", "inherited_profile_diagnostic"),
        ("future_code", "inherited_profile_diagnostic"),
    ],
)
def test_extract_candidates_maps_inherited_profile_diagnostics(
    tmp_path: Path, inherited_code: str, expected_exclusion: str
) -> None:
    image_path = tmp_path / "rows.png"
    _page_with_rows().save(image_path)
    diagnostic = ProfileDiagnostic(code=inherited_code, message="retained evidence")

    result = _extract(image_path, diagnostics=(diagnostic,))

    assert result.candidates == ()
    assert result.exclusions == (expected_exclusion,)
    assert result.inherited_diagnostics == (diagnostic,)


def test_extract_candidates_excludes_missing_bounds_or_insufficient_bands(tmp_path: Path) -> None:
    image_path = tmp_path / "rows.png"
    _page_with_rows().save(image_path)

    from pdomain_ocr_synth.pgdp.alignment_candidates import extract_line_candidates

    with open_image_snapshot(image_path) as snapshot:
        no_bounds = extract_line_candidates(
            snapshot,
            source_frame=_SOURCE_FRAME,
            foreground_bounds=None,
            ink_bands=_ROW_BANDS,
        )
        too_few_bands = extract_line_candidates(
            snapshot,
            source_frame=_SOURCE_FRAME,
            foreground_bounds=_FOREGROUND_BOUNDS,
            ink_bands=_ROW_BANDS[:1],
        )

    assert no_bounds.exclusions == ("foreground_bounds_unavailable",)
    assert too_few_bands.exclusions == ("insufficient_ink_bands",)


def test_extract_candidates_excludes_negative_foreground_bounds(tmp_path: Path) -> None:
    image_path = tmp_path / "rows.png"
    _page_with_rows().save(image_path)

    from pdomain_ocr_synth.pgdp.alignment_candidates import extract_line_candidates

    with open_image_snapshot(image_path) as snapshot:
        result = extract_line_candidates(
            snapshot,
            source_frame=_SOURCE_FRAME,
            foreground_bounds=(-1, 10, 90, 70),
            ink_bands=_ROW_BANDS,
        )

    assert result.candidates == ()
    assert result.exclusions == ("foreground_bounds_unavailable",)


def test_extract_candidates_uses_snapshot_bytes_after_live_image_mutates(tmp_path: Path) -> None:
    image_path = tmp_path / "changing.png"
    _page_with_rows().save(image_path)
    original_bytes = image_path.read_bytes()
    replacement = Image.new("L", (100, 80), color=255)
    replacement_path = tmp_path / "replacement.png"
    replacement.save(replacement_path)

    from pdomain_ocr_synth.pgdp.alignment_candidates import extract_line_candidates

    _ = image_path.write_bytes(original_bytes)
    with open_image_snapshot(image_path) as snapshot:
        _ = image_path.write_bytes(replacement_path.read_bytes())
        result = extract_line_candidates(
            snapshot,
            source_frame=_SOURCE_FRAME,
            foreground_bounds=_FOREGROUND_BOUNDS,
            ink_bands=_ROW_BANDS,
        )

    assert result.source_sha256 == sha256(original_bytes).hexdigest()
    assert [candidate.box for candidate in result.candidates] == [
        (20, 20, 56, 25),
        (20, 35, 59, 40),
        (20, 50, 63, 55),
    ]


def test_extract_candidates_accepts_additive_source_frame_evidence(tmp_path: Path) -> None:
    image_path = tmp_path / "rows.png"
    _page_with_rows().save(image_path)

    from pdomain_ocr_synth.pgdp.alignment_candidates import extract_line_candidates

    with open_image_snapshot(image_path) as snapshot:
        result = extract_line_candidates(
            snapshot,
            source_frame=CoordinateFrame(
                width=100,
                height=80,
                extensions={"future_measurement": "retained"},
            ),
            foreground_bounds=_FOREGROUND_BOUNDS,
            ink_bands=_ROW_BANDS,
        )

    assert len(result.candidates) == 3


def test_alignment_image_methods_expose_all_fixed_thresholds() -> None:
    from pdomain_ocr_synth.pgdp.alignment_candidates import ALIGNMENT_IMAGE_METHODS

    assert ALIGNMENT_IMAGE_METHODS == {
        "algorithm": "source-frame-components/v1",
        "connectivity": 8,
        "minimum_ink_bands": 2,
        "page_border_edges": 3,
        "long_rule_minimum_width_ratio": 0.8,
        "long_rule_maximum_height_ratio": 0.02,
        "join_minimum_vertical_overlap_ratio": 0.4,
        "join_maximum_vertical_center_distance_ratio": 0.6,
        "join_maximum_horizontal_gap_median_height_ratio": 2.0,
        "gutter_minimum_width_ratio": 0.03,
        "gutter_minimum_vertical_coverage_ratio": 0.6,
    }


def test_component_join_uses_the_band_median_height_for_horizontal_gaps(tmp_path: Path) -> None:
    image_path = tmp_path / "median-gap.png"
    image = Image.new("L", (100, 80), color=255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 20, 12, 21), fill=0)
    draw.rectangle((22, 20, 31, 29), fill=0)
    draw.rectangle((40, 20, 49, 29), fill=0)
    draw.rectangle((20, 40, 49, 44), fill=0)
    image.save(image_path)

    from pdomain_ocr_synth.pgdp.alignment_candidates import extract_line_candidates

    with open_image_snapshot(image_path) as snapshot:
        result = extract_line_candidates(
            snapshot,
            source_frame=_SOURCE_FRAME,
            foreground_bounds=(10, 20, 50, 45),
            ink_bands=(InkBand(y_start=20, y_end=30), InkBand(y_start=40, y_end=45)),
        )

    assert [(candidate.box, candidate.component_count) for candidate in result.candidates] == [
        ((10, 20, 50, 30), 3),
        ((20, 40, 50, 45), 1),
    ]
