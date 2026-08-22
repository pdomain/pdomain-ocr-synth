"""Tests for deterministic source-frame scan measurements."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from pdomain_ocr_synth.pgdp import image_measurement
from pdomain_ocr_synth.pgdp.image_measurement import measure_image


def test_blank_white_image_has_no_foreground_geometry(tmp_path: Path) -> None:
    image_path = tmp_path / "blank.png"
    Image.new("L", (12, 9), color=255).save(image_path)

    result = measure_image(image_path)

    assert result.source_frame.width == 12
    assert result.source_frame.height == 9
    assert result.image_mode == "L"
    assert result.grayscale_threshold == 0
    assert result.foreground_pixels == 0
    assert result.foreground_bounds is None
    assert result.margins is None


def test_solid_black_image_uses_the_whole_source_frame(tmp_path: Path) -> None:
    image_path = tmp_path / "solid.png"
    Image.new("L", (7, 5), color=0).save(image_path)

    result = measure_image(image_path)

    assert result.grayscale_threshold == 0
    assert result.foreground_pixels == 35
    assert result.foreground_bounds == (0, 0, 7, 5)
    assert result.margins == (0, 0, 0, 0)


def test_grayscale_image_hashes_original_bytes_and_uses_otsu_threshold(tmp_path: Path) -> None:
    image_path = tmp_path / "gray.png"
    image = Image.new("L", (6, 4), color=255)
    ImageDraw.Draw(image).rectangle((2, 1, 3, 2), fill=0)
    image.save(image_path)

    result = measure_image(image_path)

    assert result.sha256 == sha256(image_path.read_bytes()).hexdigest()
    assert result.grayscale_threshold == 0
    assert result.foreground_pixels == 4
    assert result.foreground_bounds == (2, 1, 4, 3)
    assert result.margins == (2, 1, 2, 1)


def test_rgb_image_uses_luminance_foreground_in_raw_coordinates(tmp_path: Path) -> None:
    image_path = tmp_path / "rgb.png"
    image = Image.new("RGB", (9, 7), color=(255, 255, 255))
    ImageDraw.Draw(image).rectangle((4, 2, 6, 4), fill=(0, 0, 0))
    image.save(image_path)

    result = measure_image(image_path)

    assert result.image_mode == "RGB"
    assert result.foreground_pixels == 9
    assert result.foreground_bounds == (4, 2, 7, 5)


def test_rgba_image_composites_transparency_over_white(tmp_path: Path) -> None:
    image_path = tmp_path / "rgba.png"
    image = Image.new("RGBA", (8, 6), color=(0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((1, 2, 2, 3), fill=(0, 0, 0, 128))
    image.save(image_path)

    result = measure_image(image_path)

    assert result.image_mode == "RGBA"
    assert result.foreground_pixels == 4
    assert result.foreground_bounds == (1, 2, 3, 4)


def test_palette_image_preserves_mode_and_measures_palette_ink(tmp_path: Path) -> None:
    image_path = tmp_path / "palette.png"
    image = Image.new("P", (8, 6), color=0)
    image.putpalette([255, 255, 255, 0, 0, 0] + [0] * 762)
    ImageDraw.Draw(image).rectangle((3, 1, 4, 4), fill=1)
    image.save(image_path)

    result = measure_image(image_path)

    assert result.image_mode == "P"
    assert result.foreground_pixels == 8
    assert result.foreground_bounds == (3, 1, 5, 5)


def test_two_rectangles_report_half_open_tight_source_bounds(tmp_path: Path) -> None:
    image_path = tmp_path / "rectangles.png"
    image = Image.new("L", (40, 30), color=255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((5, 4, 12, 10), fill=0)
    draw.rectangle((25, 18, 34, 25), fill=0)
    image.save(image_path)

    result = measure_image(image_path)

    assert result.foreground_pixels == 136
    assert result.foreground_bounds == (5, 4, 35, 26)
    assert result.margins == (5, 4, 5, 4)


def test_bounds_avoid_full_page_coordinate_index_arrays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "dense.png"
    Image.new("L", (20, 10), color=0).save(image_path)

    def fail_nonzero(*args: object, **kwargs: object) -> None:
        raise AssertionError("Foreground bounds must not materialize pixel coordinate arrays.")

    monkeypatch.setattr(image_measurement.np, "nonzero", fail_nonzero)

    result = measure_image(image_path)

    assert result.foreground_bounds == (0, 0, 20, 10)


def test_exif_orientation_is_metadata_and_does_not_rotate_source_coordinates(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "oriented.jpg"
    image = Image.new("L", (12, 8), color=255)
    ImageDraw.Draw(image).rectangle((1, 2, 3, 4), fill=0)
    exif = Image.Exif()
    exif[274] = 6
    image.save(image_path, exif=exif, quality=100, subsampling=0)

    result = measure_image(image_path)

    assert result.source_frame.width == 12
    assert result.source_frame.height == 8
    assert result.exif_orientation == 6
    assert result.foreground_bounds == (1, 2, 4, 5)


def test_decompression_bomb_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    image_path = tmp_path / "small.png"
    Image.new("L", (2, 2), color=255).save(image_path)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)

    with pytest.raises(ValueError, match="decompression bomb"):
        _ = measure_image(image_path)
