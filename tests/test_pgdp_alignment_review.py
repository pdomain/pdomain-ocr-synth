"""Tests for review-only PGDP alignment overlays and ledger summaries."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from pdomain_ocr_synth import pgdp
from pdomain_ocr_synth.pgdp.alignment_models import (
    AlignmentOperation,
    PageAlignment,
    WireLineCandidate,
    WireSourceLine,
)
from pdomain_ocr_synth.pgdp.alignment_review import (
    ReviewCategory,
    ReviewedLine,
    classify_page,
    render_alignment_overlay,
    summarize_review,
)
from pdomain_ocr_synth.pgdp.profile_models import CoordinateFrame


def _sha256() -> str:
    return "a" * 64


def test_review_helpers_are_public() -> None:
    assert pgdp.render_alignment_overlay is render_alignment_overlay
    assert pgdp.summarize_review is summarize_review


def _page(
    *,
    accepted: bool = True,
    exclusions: tuple[str, ...] = (),
    normalized_cost: float = 0.1,
    mean_width_residual: float | None = 0.1,
    mean_indentation_residual: float | None = 0.2,
    uniqueness_margin: float = 0.3,
) -> PageAlignment:
    source_lines = (
        WireSourceLine(
            ordinal=0,
            byte_start=0,
            byte_end=2,
            content_byte_start=0,
            content_byte_end=1,
            separator_byte_start=1,
            separator_byte_end=2,
            original_text="a",
            separator_text="\n",
            visible_text="a",
            matching_eligible=True,
            style_fitting_eligible=True,
        ),
        WireSourceLine(
            ordinal=1,
            byte_start=2,
            byte_end=3,
            content_byte_start=2,
            content_byte_end=3,
            separator_byte_start=3,
            separator_byte_end=3,
            original_text="b",
            separator_text="",
            visible_text="b",
            matching_eligible=True,
            style_fitting_eligible=True,
        ),
    )
    candidates = (
        WireLineCandidate(
            ordinal=0,
            box=(20, 10, 60, 20),
            width=40,
            height=10,
            fill_ratio=0.2,
            component_count=1,
            foreground_pixels=80,
        ),
        WireLineCandidate(
            ordinal=1,
            box=(20, 30, 60, 40),
            width=40,
            height=10,
            fill_ratio=0.2,
            component_count=1,
            foreground_pixels=80,
        ),
    )
    state = "accepted" if accepted else "proposed"
    return PageAlignment(
        page_name="p1.png",
        f2_sha256=_sha256(),
        scan_sha256=_sha256(),
        source_frame=CoordinateFrame(width=80, height=60),
        source_lines=source_lines,
        formatting_spans=(),
        candidates=candidates,
        operations=(
            AlignmentOperation(kind="match", source_ordinal=0, candidate_ordinal=0, cost=0.1),
            AlignmentOperation(
                kind="skip_image", source_ordinal=None, candidate_ordinal=1, cost=1.0
            ),
            AlignmentOperation(
                kind="skip_text", source_ordinal=1, candidate_ordinal=None, cost=1.0
            ),
        ),
        total_cost=2.1,
        second_best_cost=None,
        normalized_cost=normalized_cost,
        matched_count=1,
        matched_ratio=0.5,
        uniqueness_margin=uniqueness_margin,
        mean_width_residual=mean_width_residual,
        mean_indentation_residual=mean_indentation_residual,
        state=state,
        accepted=accepted,
        exclusions=exclusions,
    )


def test_overlay_is_source_sized_and_report_is_unchanged(tmp_path: Path) -> None:
    scan_path = tmp_path / "scan.png"
    Image.new("L", (80, 60), color=255).save(scan_path)
    page = _page()
    before = page.to_dict()

    overlay = render_alignment_overlay(scan_path, page, tmp_path / "overlay.png")

    assert overlay.mode == "RGB"
    assert overlay.size == (80, 60)
    assert overlay.getpixel((20, 10)) == (0, 192, 0)
    assert overlay.getpixel((20, 30)) == (224, 0, 0)
    assert page.to_dict() == before
    assert (tmp_path / "overlay.png").is_file()
    assert any(overlay.getpixel((x, y)) != (255, 255, 255) for x in range(20) for y in range(60))


def test_overlay_marks_proposed_matches_amber(tmp_path: Path) -> None:
    scan_path = tmp_path / "scan.png"
    Image.new("RGB", (80, 60), color="white").save(scan_path)

    overlay = render_alignment_overlay(scan_path, _page(accepted=False), tmp_path / "overlay.png")

    assert overlay.getpixel((20, 10)) == (224, 160, 0)


def test_overlay_rejects_output_inside_supplied_corpus_root(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    scan_path = tmp_path / "scan.png"
    Image.new("RGB", (80, 60), color="white").save(scan_path)

    with pytest.raises(ValueError, match="outside the corpus root"):
        _ = render_alignment_overlay(
            scan_path,
            _page(),
            corpus_root / "overlay.png",
            corpus_root=corpus_root,
        )


def test_overlay_keeps_existing_output_when_atomic_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_path = tmp_path / "scan.png"
    output_path = tmp_path / "overlay.png"
    Image.new("RGB", (80, 60), color="white").save(scan_path)
    _ = output_path.write_bytes(b"previous overlay")

    def interrupted_replace(source: Path, destination: str | Path) -> Path:
        assert source != destination
        raise OSError("replace interrupted")

    monkeypatch.setattr(Path, "replace", interrupted_replace)

    with pytest.raises(OSError, match="replace interrupted"):
        _ = render_alignment_overlay(scan_path, _page(), output_path)

    assert output_path.read_bytes() == b"previous overlay"
    assert tuple(tmp_path.glob(".overlay.png.*.png")) == ()


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("probable_multi_column", ReviewCategory.DECLARED_COMPLEX),
        ("table_like", ReviewCategory.DECLARED_COMPLEX),
        ("illustration_marker", ReviewCategory.DECLARED_COMPLEX),
        ("border_dominated", ReviewCategory.DECLARED_COMPLEX),
        ("high_foreground_ratio", ReviewCategory.DECLARED_COMPLEX),
        ("f2_missing", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("f2_page_missing", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("page_missing", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("image_missing", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("image_unreadable", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("image_decode_failed", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("profile_page_missing", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("foreground_bounds_unavailable", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("insufficient_ink_bands", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("blank_page", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("fragmented_band", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("line_count_out_of_range", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("malformed_control", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("scan_hash_mismatch", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("inherited_profile_diagnostic", ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        ("source_changed", ReviewCategory.SOURCE_CHANGED),
        ("matched_ratio_below_minimum", ReviewCategory.ELIGIBLE),
        ("line_count_difference_exceeds_maximum", ReviewCategory.ELIGIBLE),
        ("normalized_cost_exceeds_maximum", ReviewCategory.ELIGIBLE),
        ("uniqueness_margin_below_minimum", ReviewCategory.ELIGIBLE),
        ("persistent_gutter", ReviewCategory.DECLARED_COMPLEX),
    ],
)
def test_classify_page_maps_each_known_exclusion_code(code: str, expected: ReviewCategory) -> None:
    assert classify_page(_page(accepted=False, exclusions=(code,))).category is expected


@pytest.mark.parametrize(
    ("codes", "expected"),
    [
        (("source_changed", "blank_page"), ReviewCategory.SOURCE_CHANGED),
        (("blank_page", "probable_multi_column"), ReviewCategory.UNAVAILABLE_OR_MALFORMED),
        (
            ("probable_multi_column", "normalized_cost_exceeds_maximum"),
            ReviewCategory.DECLARED_COMPLEX,
        ),
    ],
)
def test_classify_page_applies_priority_to_multiple_exclusions(
    codes: tuple[str, ...], expected: ReviewCategory
) -> None:
    assert classify_page(_page(accepted=False, exclusions=codes)).category is expected


def test_classify_page_rejects_unknown_m15b_code() -> None:
    with pytest.raises(ValueError, match="Unknown M15b exclusion code"):
        _ = classify_page(_page(accepted=False, exclusions=("unrecognized",)))


def test_review_summary_counts_disjoint_categories_and_preserves_null_residuals() -> None:
    pages = (
        replace(
            _page(),
            page_name="source-changed.png",
            accepted=False,
            state="excluded",
            exclusions=("source_changed",),
        ),
        replace(
            _page(),
            page_name="missing.png",
            accepted=False,
            state="excluded",
            exclusions=("blank_page",),
        ),
        replace(
            _page(),
            page_name="table.png",
            accepted=False,
            state="excluded",
            exclusions=("table_like",),
        ),
        replace(_page(), page_name="accepted.png"),
        replace(
            _page(),
            page_name="proposed.png",
            accepted=False,
            state="proposed",
            exclusions=("normalized_cost_exceeds_maximum",),
            normalized_cost=0.4,
            mean_width_residual=None,
            mean_indentation_residual=None,
            uniqueness_margin=0.0,
        ),
    )
    reviewed_lines = (
        ReviewedLine(0, 0, "match", "correct"),
        ReviewedLine(1, 1, "match", "incorrect"),
        ReviewedLine(2, None, "skip_text", "correct"),
    )

    summary = summarize_review(pages, reviewed_lines)

    assert summary.counts.selected_total == 5
    assert summary.counts.source_changed == 1
    assert summary.counts.unavailable_or_malformed == 1
    assert summary.counts.declared_complex == 1
    assert summary.counts.eligible == 2
    assert summary.accepted_line_precision == 0.5
    assert summary.eligible_page_coverage == 0.5
    assert summary.declared_complex_accepted == 0
    assert summary.normalized_costs == (0.1, 0.1, 0.1, 0.1, 0.4)
    assert summary.width_residuals == (0.1, 0.1, 0.1, 0.1, None)
    assert summary.indentation_residuals == (0.2, 0.2, 0.2, 0.2, None)
    assert summary.uniqueness_margins == (0.3, 0.3, 0.3, 0.3, 0.0)


def test_review_summary_handles_no_reviewed_matches_without_inventing_precision() -> None:
    summary = summarize_review((_page(),), ())

    assert summary.accepted_line_precision is None
    assert summary.confidence is None
    assert summary.confidence_kind == "uncalibrated"
