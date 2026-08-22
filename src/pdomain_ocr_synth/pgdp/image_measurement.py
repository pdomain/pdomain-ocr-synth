"""Deterministic source-frame foreground measurements for PGDP scans."""

from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from pdomain_ocr_synth.pgdp.profile_models import CoordinateFrame

_EXIF_ORIENTATION_TAG = 274
_HASH_CHUNK_SIZE = 64 * 1024
_GRAYSCALE_LEVELS = 256


@dataclass(frozen=True, slots=True)
class ImageMeasurement:
    """Observed source-frame geometry for one decoded scan image."""

    sha256: str
    source_frame: CoordinateFrame
    image_mode: str
    exif_orientation: int | None
    grayscale_threshold: int
    foreground_pixels: int
    foreground_bounds: tuple[int, int, int, int] | None
    margins: tuple[int, int, int, int] | None


def measure_image(image_path: str | Path) -> ImageMeasurement:
    """Measure one stored raster without applying its EXIF orientation."""

    path = Path(image_path)
    file_sha256 = _sha256_file(path)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                source_frame = CoordinateFrame(width=image.width, height=image.height)
                image_mode = image.mode
                exif_orientation = _exif_orientation(image)
                with _source_grayscale(image) as grayscale_image:
                    grayscale = np.asarray(grayscale_image, dtype=np.uint8)
                    threshold = _otsu_threshold(_histogram(grayscale))
                    foreground = grayscale <= threshold
                    foreground_pixels = int(np.count_nonzero(foreground))
                    bounds = _foreground_bounds(foreground)
                    margins = _margins(bounds, source_frame)
                    del foreground
                    del grayscale
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError("Image rejected as a decompression bomb.") from error
    return ImageMeasurement(
        sha256=file_sha256,
        source_frame=source_frame,
        image_mode=image_mode,
        exif_orientation=exif_orientation,
        grayscale_threshold=threshold,
        foreground_pixels=foreground_pixels,
        foreground_bounds=bounds,
        margins=margins,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        while chunk := source_file.read(_HASH_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _exif_orientation(image: Image.Image) -> int | None:
    orientation = image.getexif().get(_EXIF_ORIENTATION_TAG)
    return (
        orientation if isinstance(orientation, int) and not isinstance(orientation, bool) else None
    )


def _source_grayscale(image: Image.Image) -> Image.Image:
    if image.mode in {"LA", "RGBA"} or "transparency" in image.info:
        with (
            image.convert("RGBA") as rgba,
            Image.new("RGBA", image.size, color=(255, 255, 255, 255)) as white,
            Image.alpha_composite(white, rgba) as composite,
        ):
            return composite.convert("L")
    return image.convert("L")


def _histogram(grayscale: np.ndarray[tuple[int, int], np.dtype[np.uint8]]) -> tuple[int, ...]:
    counts = np.bincount(grayscale.ravel(), minlength=_GRAYSCALE_LEVELS)
    return tuple(int(count) for count in counts[:_GRAYSCALE_LEVELS])


def _otsu_threshold(histogram: tuple[int, ...]) -> int:
    total = sum(histogram)
    weighted_total = sum(level * count for level, count in enumerate(histogram))
    background_count = 0
    background_total = 0
    best_threshold = 0
    best_numerator = 0
    best_denominator = 1
    for threshold, count in enumerate(histogram):
        background_count += count
        background_total += threshold * count
        foreground_count = total - background_count
        if background_count == 0 or foreground_count == 0:
            continue
        foreground_total = weighted_total - background_total
        difference = background_total * foreground_count - foreground_total * background_count
        numerator = difference * difference
        denominator = background_count * foreground_count
        if numerator * best_denominator > best_numerator * denominator:
            best_threshold = threshold
            best_numerator = numerator
            best_denominator = denominator
    return best_threshold


def _foreground_bounds(
    foreground: np.ndarray[tuple[int, int], np.dtype[np.bool]],
) -> tuple[int, int, int, int] | None:
    active_rows = foreground.any(axis=1)
    if not bool(active_rows.any()):
        return None
    active_columns = foreground.any(axis=0)
    return (
        int(active_columns.argmax()),
        int(active_rows.argmax()),
        int(active_columns.size - active_columns[::-1].argmax()),
        int(active_rows.size - active_rows[::-1].argmax()),
    )


def _margins(
    bounds: tuple[int, int, int, int] | None, source_frame: CoordinateFrame
) -> tuple[int, int, int, int] | None:
    if bounds is None:
        return None
    x_start, y_start, x_end, y_end = bounds
    return (x_start, y_start, source_frame.width - x_end, source_frame.height - y_end)
