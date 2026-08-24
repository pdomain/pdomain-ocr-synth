"""Review-only overlays and summaries for PGDP source-line alignment."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pdomain_ocr_synth.pgdp.alignment_models import PageAlignment


class ReviewCategory(StrEnum):
    """One disjoint page category for a bounded alignment review."""

    DECLARED_COMPLEX = "declared_complex"
    UNAVAILABLE_OR_MALFORMED = "unavailable_or_malformed"
    SOURCE_CHANGED = "source_changed"
    ELIGIBLE = "eligible"


_DECLARED_COMPLEX_CODES = frozenset(
    {
        "probable_multi_column",
        "persistent_gutter",
        "table_like",
        "illustration_marker",
        "border_dominated",
        "high_foreground_ratio",
    }
)
_UNAVAILABLE_OR_MALFORMED_CODES = frozenset(
    {
        "f2_missing",
        "f2_page_missing",
        "page_missing",
        "image_missing",
        "image_unreadable",
        "image_decode_failed",
        "profile_page_missing",
        "foreground_bounds_unavailable",
        "insufficient_ink_bands",
        "blank_page",
        "fragmented_band",
        "line_count_out_of_range",
        "malformed_control",
        "scan_hash_mismatch",
        "inherited_profile_diagnostic",
    }
)
_SOURCE_CHANGED_CODE = "source_changed"
_ALIGNMENT_QUALITY_CODES = frozenset(
    {
        "matched_ratio_below_minimum",
        "line_count_difference_exceeds_maximum",
        "normalized_cost_exceeds_maximum",
        "uniqueness_margin_below_minimum",
    }
)
_KNOWN_EXCLUSION_CODES = (
    _DECLARED_COMPLEX_CODES
    | _UNAVAILABLE_OR_MALFORMED_CODES
    | _ALIGNMENT_QUALITY_CODES
    | {_SOURCE_CHANGED_CODE}
)

_ACCEPTED_MATCH_COLOR = (0, 192, 0)
_REJECTED_MATCH_COLOR = (224, 160, 0)
_SKIPPED_CANDIDATE_COLOR = (224, 0, 0)

ObservedOperation = Literal["match", "skip_image", "skip_text"]
ReviewerDecision = Literal["correct", "incorrect"]


@dataclass(frozen=True, slots=True)
class PageClassification:
    """The category assigned to one selected page."""

    category: ReviewCategory
    exclusions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewedLine:
    """One human-reviewed expected mapping and observed operation."""

    expected_source_ordinal: int | None
    expected_candidate_ordinal: int | None
    observed_operation: ObservedOperation
    reviewer_decision: ReviewerDecision

    def __post_init__(self) -> None:
        _validate_ordinal(self.expected_source_ordinal, name="expected_source_ordinal")
        _validate_ordinal(self.expected_candidate_ordinal, name="expected_candidate_ordinal")
        if self.observed_operation == "match":
            if self.expected_source_ordinal is None or self.expected_candidate_ordinal is None:
                raise ValueError("Match review rows require source and candidate ordinals.")
        elif self.observed_operation == "skip_image":
            if self.expected_source_ordinal is not None or self.expected_candidate_ordinal is None:
                raise ValueError("skip_image review rows require only a candidate ordinal.")
        elif self.observed_operation == "skip_text":
            if self.expected_source_ordinal is None or self.expected_candidate_ordinal is not None:
                raise ValueError("skip_text review rows require only a source ordinal.")
        else:
            raise ValueError("Observed review operation is unsupported.")
        if self.reviewer_decision not in {"correct", "incorrect"}:
            raise ValueError("Reviewer decision is unsupported.")


@dataclass(frozen=True, slots=True)
class ReviewCounts:
    """The four exhaustive counts for a selected page set."""

    selected_total: int
    declared_complex: int
    unavailable_or_malformed: int
    source_changed: int
    eligible: int

    def __post_init__(self) -> None:
        values = (
            self.selected_total,
            self.declared_complex,
            self.unavailable_or_malformed,
            self.source_changed,
            self.eligible,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ):
            raise ValueError("Review counts must be nonnegative integers.")
        if self.selected_total != sum(values[1:]):
            raise ValueError("selected_total must equal the four disjoint review counts.")


@dataclass(frozen=True, slots=True)
class ReviewLedger:
    """Typed page classifications and human-reviewed line decisions."""

    classifications: tuple[PageClassification, ...]
    reviewed_lines: tuple[ReviewedLine, ...]

    @classmethod
    def from_pages(
        cls,
        pages: Sequence[PageAlignment],
        reviewed_lines: Sequence[ReviewedLine] = (),
    ) -> ReviewLedger:
        """Build the complete ledger for selected alignment pages."""

        return cls(
            classifications=tuple(classify_page(page) for page in pages),
            reviewed_lines=tuple(reviewed_lines),
        )

    @property
    def counts(self) -> ReviewCounts:
        """Return exhaustive category counts for selected pages."""

        return ReviewCounts(
            selected_total=len(self.classifications),
            declared_complex=sum(
                item.category is ReviewCategory.DECLARED_COMPLEX for item in self.classifications
            ),
            unavailable_or_malformed=sum(
                item.category is ReviewCategory.UNAVAILABLE_OR_MALFORMED
                for item in self.classifications
            ),
            source_changed=sum(
                item.category is ReviewCategory.SOURCE_CHANGED for item in self.classifications
            ),
            eligible=sum(item.category is ReviewCategory.ELIGIBLE for item in self.classifications),
        )

    @property
    def accepted_line_precision(self) -> float | None:
        """Return correct reviewed matches divided by all reviewed matches."""

        reviewed_matches = tuple(
            item for item in self.reviewed_lines if item.observed_operation == "match"
        )
        if not reviewed_matches:
            return None
        return sum(item.reviewer_decision == "correct" for item in reviewed_matches) / len(
            reviewed_matches
        )


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    """Review metrics that preserve page-level null residual evidence."""

    counts: ReviewCounts
    accepted_line_precision: float | None
    eligible_page_coverage: float | None
    declared_complex_accepted: int
    normalized_costs: tuple[float, ...]
    width_residuals: tuple[float | None, ...]
    indentation_residuals: tuple[float | None, ...]
    uniqueness_margins: tuple[float, ...]
    confidence: None = None
    confidence_kind: Literal["uncalibrated"] = "uncalibrated"


def classify_page(page: PageAlignment) -> PageClassification:
    """Map one page to its one review category using fixed priority."""

    unknown_codes = set(page.exclusions) - _KNOWN_EXCLUSION_CODES
    if unknown_codes:
        codes = ", ".join(sorted(unknown_codes))
        raise ValueError(f"Unknown M15b exclusion code: {codes}.")
    exclusions = tuple(page.exclusions)
    if _SOURCE_CHANGED_CODE in exclusions:
        category = ReviewCategory.SOURCE_CHANGED
    elif set(exclusions) & _UNAVAILABLE_OR_MALFORMED_CODES:
        category = ReviewCategory.UNAVAILABLE_OR_MALFORMED
    elif set(exclusions) & _DECLARED_COMPLEX_CODES:
        category = ReviewCategory.DECLARED_COMPLEX
    else:
        category = ReviewCategory.ELIGIBLE
    return PageClassification(category=category, exclusions=exclusions)


def summarize_review(
    pages: Sequence[PageAlignment], reviewed_lines: Sequence[ReviewedLine] = ()
) -> ReviewSummary:
    """Summarize a selected review set without collapsing null residuals."""

    selected_pages = tuple(pages)
    ledger = ReviewLedger.from_pages(selected_pages, reviewed_lines)
    counts = ledger.counts
    eligible_pages = tuple(
        page
        for page, classification in zip(selected_pages, ledger.classifications, strict=True)
        if classification.category is ReviewCategory.ELIGIBLE
    )
    eligible_page_coverage = (
        None
        if not eligible_pages
        else sum(page.accepted for page in eligible_pages) / len(eligible_pages)
    )
    declared_complex_accepted = sum(
        page.accepted
        for page, classification in zip(selected_pages, ledger.classifications, strict=True)
        if classification.category is ReviewCategory.DECLARED_COMPLEX
    )
    return ReviewSummary(
        counts=counts,
        accepted_line_precision=ledger.accepted_line_precision,
        eligible_page_coverage=eligible_page_coverage,
        declared_complex_accepted=declared_complex_accepted,
        normalized_costs=tuple(page.normalized_cost for page in selected_pages),
        width_residuals=tuple(page.mean_width_residual for page in selected_pages),
        indentation_residuals=tuple(page.mean_indentation_residual for page in selected_pages),
        uniqueness_margins=tuple(page.uniqueness_margin for page in selected_pages),
    )


def render_alignment_overlay(
    scan_path: str | Path,
    page_alignment: PageAlignment,
    output_path: str | Path,
    *,
    corpus_root: str | Path | None = None,
) -> Image.Image:
    """Render one immutable page alignment as a source-sized RGB PNG overlay."""

    scan = Path(scan_path).resolve(strict=True)
    if not scan.is_file():
        raise ValueError(f"Overlay scan path must name a regular file: {scan!s}.")
    output = _validated_output_path(output_path, corpus_root=corpus_root)
    with Image.open(scan) as source:
        overlay = source.convert("RGB")
    if page_alignment.source_frame is not None and overlay.size != (
        page_alignment.source_frame.width,
        page_alignment.source_frame.height,
    ):
        overlay.close()
        raise ValueError("Overlay scan dimensions must match the alignment source frame.")

    matched_sources = {
        operation.candidate_ordinal: operation.source_ordinal
        for operation in page_alignment.operations
        if operation.kind == "match"
    }
    draw = ImageDraw.Draw(overlay)
    for candidate in page_alignment.candidates:
        source_ordinal = matched_sources.get(candidate.ordinal)
        color = _candidate_color(source_ordinal, accepted=page_alignment.accepted)
        x_start, y_start, x_end, y_end = candidate.box
        draw.rectangle((x_start, y_start, x_end - 1, y_end - 1), outline=color, width=1)
        if source_ordinal is not None:
            draw.text((0, y_start), str(source_ordinal), fill=color)
    _write_overlay_atomic(overlay, output)
    return overlay


def _validate_ordinal(value: int | None, *, name: str) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError(f"{name} must be a nonnegative integer or null.")


def _candidate_color(source_ordinal: int | None, *, accepted: bool) -> tuple[int, int, int]:
    if source_ordinal is None:
        return _SKIPPED_CANDIDATE_COLOR
    return _ACCEPTED_MATCH_COLOR if accepted else _REJECTED_MATCH_COLOR


def _validated_output_path(output_path: str | Path, *, corpus_root: str | Path | None) -> Path:
    output = Path(output_path).resolve()
    if corpus_root is not None:
        root = Path(corpus_root).resolve()
        if output == root or output.is_relative_to(root):
            raise ValueError("Overlay output must be outside the corpus root.")
    if not output.parent.is_dir():
        raise ValueError(f"Overlay output directory does not exist: {output.parent!s}.")
    return output


def _write_overlay_atomic(overlay: Image.Image, output: Path) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".png",
    )
    temporary_path = Path(temporary_name)
    try:
        os.close(descriptor)
        overlay.save(temporary_path, format="PNG")
        temporary_descriptor = os.open(temporary_path, os.O_RDONLY)
        try:
            _ = os.fsync(temporary_descriptor)
        finally:
            os.close(temporary_descriptor)
        _ = temporary_path.replace(output)
    except Exception as write_error:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as cleanup_error:
            raise ExceptionGroup(
                "Writing the overlay and removing its temporary file both failed.",
                [write_error, cleanup_error],
            ) from None
        raise
    directory_descriptor = os.open(output.parent, os.O_RDONLY)
    try:
        _ = os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)
