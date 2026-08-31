"""Fit per-book page templates and classify pages against them.

A letterpress book is set once, so its text block holds the same position across
the volume. That makes a band's distance from the top of the page evidence for
what the band is: a running head sits where every page's first band sits, while
a chapter opening starts far below it.

Two classes named in the design are absent here on purpose. Front matter has no
measured discriminator, and one illustration is not enough to separate a plate
from a table with tall bands. Both fall to `unknown`, which suppresses nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pdomain_ocr_synth.pgdp.profile_models import PageMeasurement

PageClass = Literal[
    "normal_recto",
    "normal_verso",
    "chapter_opening",
    "unknown",
]

PAGE_TEMPLATE_METHOD = "first-band-templates/v1"

_HEAD_MAD_MAXIMUM_PX = 2
_CHAPTER_SINK_MINIMUM_PX = 150
# How steady a book's first band must be is a different question from how far a
# single page may sit from it. Running heads were measured 0 to 4px off their
# book's median, while the nearest page whose first band is genuine text sat
# 76px below. The window is flat between 4 and 20px on all three steady books,
# so 8 is double the observed spread and an order of magnitude clear of text.
_HEAD_WINDOW_MINIMUM_PX = 8
_HEAD_WINDOW_MAD_FACTOR = 3

_TRAILING_DIGITS = re.compile(r"(\d+)(?!.*\d)")


@dataclass(frozen=True, slots=True)
class PageTemplate:
    """One measured page shape a book repeats."""

    page_class: PageClass
    first_band_top_px: int
    text_left_px: int
    text_right_px: int
    band_count: int
    page_count: int
    page_share: float


@dataclass(frozen=True, slots=True)
class BookTemplates:
    """The page shapes fitted for one book, with the evidence for trusting them."""

    first_band_median_px: float | None
    first_band_mad_px: float | None
    head_window_px: float | None
    templates: tuple[PageTemplate, ...]
    classified_share: float

    @property
    def has_type_page(self) -> bool:
        """Whether the book's first band is steady enough to classify against."""

        return bool(self.templates)


@dataclass(frozen=True, slots=True)
class PageClassification:
    """One page's class and how far it sat from its template."""

    page_name: str
    page_class: PageClass
    template_residual_px: int | None
    furniture_band_ordinals: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _PageGeometry:
    page_name: str
    first_band_top: int
    text_left: int
    text_right: int
    band_count: int
    recto: bool


def fit_book_templates(pages: Sequence[PageMeasurement]) -> BookTemplates:
    """Fit the page shapes one book repeats, or none when it has no type page."""

    geometry = tuple(item for item in map(_page_geometry, pages) if item is not None)
    if not geometry:
        return BookTemplates(None, None, None, (), 0.0)

    tops = [item.first_band_top for item in geometry]
    center = float(median(tops))
    deviation = float(median(abs(top - center) for top in tops))
    if deviation > _HEAD_MAD_MAXIMUM_PX:
        # A book whose first band wanders has no single text block to describe.
        # Widening the window to fit it would classify everything and mean
        # nothing, so the book gets no templates at all.
        return BookTemplates(center, deviation, None, (), 0.0)

    window = max(float(_HEAD_WINDOW_MINIMUM_PX), _HEAD_WINDOW_MAD_FACTOR * deviation)
    normal = [item for item in geometry if abs(item.first_band_top - center) <= window]
    sunk = [item for item in geometry if item.first_band_top - center >= _CHAPTER_SINK_MINIMUM_PX]

    templates: list[PageTemplate] = []
    total = len(geometry)
    groups: tuple[tuple[PageClass, list[_PageGeometry]], ...] = (
        ("normal_recto", [item for item in normal if item.recto]),
        ("normal_verso", [item for item in normal if not item.recto]),
        ("chapter_opening", sunk),
    )
    for page_class, group in groups:
        template = _fit_template(page_class, group, total=total)
        if template is not None:
            templates.append(template)

    classified = sum(template.page_count for template in templates)
    return BookTemplates(
        first_band_median_px=center,
        first_band_mad_px=deviation,
        head_window_px=window,
        templates=tuple(templates),
        classified_share=classified / total if total else 0.0,
    )


def classify_pages(
    pages: Sequence[PageMeasurement], templates: BookTemplates
) -> tuple[PageClassification, ...]:
    """Classify each page and name the bands the aligner should ignore."""

    by_class: dict[PageClass, PageTemplate] = {
        template.page_class: template for template in templates.templates
    }
    results: list[PageClassification] = []
    for page in pages:
        geometry = _page_geometry(page)
        if geometry is None or not templates.has_type_page:
            results.append(PageClassification(page.page_name, "unknown", None, ()))
            continue
        results.append(_classify_page(geometry, templates=templates, by_class=by_class))
    return tuple(results)


def _classify_page(
    geometry: _PageGeometry,
    *,
    templates: BookTemplates,
    by_class: dict[PageClass, PageTemplate],
) -> PageClassification:
    center = templates.first_band_median_px
    window = templates.head_window_px
    if center is None or window is None:
        return PageClassification(geometry.page_name, "unknown", None, ())

    offset = geometry.first_band_top - center
    if abs(offset) <= window:
        page_class: PageClass = "normal_recto" if geometry.recto else "normal_verso"
        template = by_class.get(page_class)
        if template is None or abs(geometry.text_left - template.text_left_px) > window:
            return PageClassification(geometry.page_name, "unknown", None, ())
        # The first band of a normal page is the running head. It is printed but
        # deleted from F2, so the aligner must not match a source line to it.
        return PageClassification(
            geometry.page_name,
            page_class,
            int(abs(geometry.first_band_top - template.first_band_top_px)),
            (0,),
        )

    if offset >= _CHAPTER_SINK_MINIMUM_PX and "chapter_opening" in by_class:
        template = by_class["chapter_opening"]
        return PageClassification(
            geometry.page_name,
            "chapter_opening",
            int(abs(geometry.first_band_top - template.first_band_top_px)),
            (),
        )

    # Between the head window and the chapter sink the evidence is thin, so the
    # page is left unclassified rather than forced into a template.
    return PageClassification(geometry.page_name, "unknown", None, ())


def _fit_template(
    page_class: PageClass, group: Sequence[_PageGeometry], *, total: int
) -> PageTemplate | None:
    if not group:
        return None
    return PageTemplate(
        page_class=page_class,
        first_band_top_px=int(median(item.first_band_top for item in group)),
        text_left_px=int(median(item.text_left for item in group)),
        text_right_px=int(median(item.text_right for item in group)),
        band_count=int(median(item.band_count for item in group)),
        page_count=len(group),
        page_share=len(group) / total if total else 0.0,
    )


def _page_geometry(page: PageMeasurement) -> _PageGeometry | None:
    bounds = page.foreground_bounds
    if not page.ink_bands or bounds is None:
        return None
    return _PageGeometry(
        page_name=page.page_name,
        first_band_top=page.ink_bands[0].y_start,
        text_left=bounds[0],
        text_right=bounds[2],
        band_count=len(page.ink_bands),
        recto=_is_recto(page.page_name),
    )


def _is_recto(page_name: str) -> bool:
    """Guess the binding side from the page number in the file name.

    The folio sits on the outer edge, so the text block shifts between the two
    sides in books with a wide binding margin. A page with no number in its name
    is treated as recto, which only costs a template split.
    """

    match = _TRAILING_DIGITS.search(page_name)
    return bool(int(match.group(1)) % 2) if match else True
