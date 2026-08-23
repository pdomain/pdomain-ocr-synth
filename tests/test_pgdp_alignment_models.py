from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdomain_ocr_synth.pgdp.alignment_models import (
    ALIGNMENT_ALGORITHM_VERSION,
    ALIGNMENT_SCHEMA_VERSION,
    AlignmentDiagnostic,
    AlignmentOperation,
    AlignmentReport,
    PageAlignment,
    ProjectAlignment,
    WireFormattingSpan,
    WireLineCandidate,
    WireSourceLine,
    WireStyleRun,
)
from pdomain_ocr_synth.pgdp.profile_models import CoordinateFrame


def _sha256() -> str:
    return "a" * 64


def make_report() -> AlignmentReport:
    page = PageAlignment(
        page_name="p2.png",
        f2_sha256=_sha256(),
        scan_sha256=_sha256(),
        source_frame=CoordinateFrame(width=100, height=200),
        source_lines=(
            WireSourceLine(
                ordinal=0,
                byte_start=0,
                byte_end=5,
                content_byte_start=0,
                content_byte_end=5,
                separator_byte_start=5,
                separator_byte_end=5,
                original_text="\u00c9ire",
                separator_text="",
                visible_text="\u00c9ire",
                matching_eligible=True,
                style_fitting_eligible=True,
                formatting_span_ids=("local:p2.png:0:p2.png:5",),
                continued_block_ids=(),
            ),
        ),
        formatting_spans=(
            WireFormattingSpan(
                opening_id="local:p2.png:0",
                block_id="local:p2.png:0:p2.png:5",
                kind="local",
                byte_start=0,
                byte_end=5,
                closed=True,
            ),
        ),
        candidates=(
            WireLineCandidate(
                ordinal=0,
                box=(1, 2, 90, 12),
                width=89,
                height=10,
                fill_ratio=0.25,
                component_count=2,
                foreground_pixels=100,
            ),
        ),
        operations=(
            AlignmentOperation(kind="match", source_ordinal=0, candidate_ordinal=0, cost=0.1),
        ),
        total_cost=0.1,
        second_best_cost=0.4,
        normalized_cost=0.1,
        matched_count=1,
        matched_ratio=1.0,
        uniqueness_margin=0.3,
        mean_width_residual=0.1,
        mean_indentation_residual=0.0,
        state="accepted",
        accepted=True,
        exclusions=(),
    )
    project = ProjectAlignment(project_id="book", pages=(page,))
    return AlignmentReport(
        tool_version="0.1.0",
        profile_label="profile.json",
        profile_sha256=_sha256(),
        methods={"z": "last", "a": "first"},
        thresholds={"max_cost": 0.22},
        projects=(project,),
    )


def test_alignment_report_keeps_uncalibrated_confidence_and_sorted_mappings() -> None:
    payload = make_report().to_dict()

    page = payload["projects"][0]["pages"][0]
    assert page["confidence"] is None
    assert page["confidence_kind"] == "uncalibrated"
    assert payload["schema_version"] == ALIGNMENT_SCHEMA_VERSION == 1
    assert payload["algorithm_version"] == ALIGNMENT_ALGORITHM_VERSION == "pgdp-alignment/v1"
    assert list(payload["methods"]) == ["a", "z"]
    assert page["source_frame"] == {"name": "source", "width": 100, "height": 200}


def test_alignment_report_round_trips_additive_v1_values_without_inventing_defaults() -> None:
    payload = make_report().to_dict()
    payload["future_report"] = {"array": [1, {"nested": True}]}
    payload["projects"][0]["future_project"] = {"value": None}
    payload["projects"][0]["pages"][0]["future_page"] = ["kept", {"also": "kept"}]

    rewritten = AlignmentReport.from_dict(payload).to_dict()

    assert rewritten["future_report"] == payload["future_report"]
    assert rewritten["projects"][0]["future_project"] == payload["projects"][0]["future_project"]
    assert (
        rewritten["projects"][0]["pages"][0]["future_page"]
        == payload["projects"][0]["pages"][0]["future_page"]
    )
    assert json.dumps(rewritten, ensure_ascii=False, sort_keys=True) == json.dumps(
        AlignmentReport.from_json(json.dumps(payload)).to_dict(), ensure_ascii=False, sort_keys=True
    )


@pytest.mark.parametrize(
    ("payload_update", "message"),
    [
        ({"schema_version": 2}, "schema_version"),
        ({"algorithm_version": "pgdp-alignment/v2"}, "algorithm_version"),
        ({"profile_label": "../profile.json"}, "profile_label"),
    ],
)
def test_alignment_report_rejects_unknown_versions_and_unsafe_profile_labels(
    payload_update: dict[str, object], message: str
) -> None:
    payload = make_report().to_dict()
    payload.update(payload_update)

    with pytest.raises(ValueError, match=message):
        _ = AlignmentReport.from_dict(payload)


@pytest.mark.parametrize("invalid_version", [True, 1.0])
def test_alignment_report_rejects_boolean_and_float_schema_versions(
    invalid_version: bool | float,
) -> None:
    payload = make_report().to_dict()
    payload["schema_version"] = invalid_version

    with pytest.raises(ValueError, match="schema_version"):
        _ = AlignmentReport.from_dict(payload)


def test_direct_construction_rejects_coercible_primitive_values() -> None:
    with pytest.raises(TypeError):
        _ = AlignmentDiagnostic(code=True, message="diagnostic")
    with pytest.raises(TypeError):
        _ = WireSourceLine(
            ordinal=0,
            byte_start=0,
            byte_end=5,
            content_byte_start=0,
            content_byte_end=5,
            separator_byte_start=5,
            separator_byte_end=5,
            original_text="\u00c9ire",
            separator_text="",
            visible_text=1,
            matching_eligible=True,
            style_fitting_eligible=True,
        )
    with pytest.raises(TypeError):
        _ = PageAlignment(
            page_name="p2.png",
            f2_sha256=_sha256(),
            scan_sha256=_sha256(),
            source_frame=CoordinateFrame(width=100, height=200),
            source_lines=(),
            formatting_spans=(),
            candidates=(),
            operations=(),
            total_cost=0.0,
            second_best_cost=None,
            normalized_cost=0.0,
            matched_count=0,
            matched_ratio=0.0,
            uniqueness_margin=0.0,
            mean_width_residual=None,
            mean_indentation_residual=None,
            state="proposed",
            accepted=0,
            exclusions=(),
        )


def test_wire_source_line_requires_complete_utf8_span_evidence() -> None:
    payload = make_report().to_dict()
    source_line = payload["projects"][0]["pages"][0]["source_lines"][0]
    source_line.pop("original_text")

    with pytest.raises(ValueError, match="original_text"):
        _ = AlignmentReport.from_dict(payload)


def test_wire_source_line_keeps_content_and_separator_byte_partition() -> None:
    line = WireSourceLine(
        ordinal=0,
        byte_start=0,
        byte_end=6,
        content_byte_start=0,
        content_byte_end=5,
        separator_byte_start=5,
        separator_byte_end=6,
        original_text="\u00c9ire",
        separator_text="\r",
        visible_text="\u00c9ire",
        matching_eligible=True,
        style_fitting_eligible=True,
    )

    assert line.to_dict()["separator_byte_end"] == 6


def test_wire_style_run_has_closed_kind_and_complete_spans() -> None:
    style_run = WireStyleRun(
        kind="italic",
        normalized_start=0,
        normalized_end=4,
        byte_start=0,
        byte_end=4,
    )

    assert style_run.to_dict() == {
        "kind": "italic",
        "normalized_start": 0,
        "normalized_end": 4,
        "byte_start": 0,
        "byte_end": 4,
    }


@pytest.mark.parametrize(
    ("kind", "normalized_start", "normalized_end", "byte_start", "byte_end"),
    [
        ("underline", 0, 1, 0, 1),
        ("bold", 2, 1, 0, 1),
        ("bold", 0, 1, 2, 1),
    ],
)
def test_wire_style_run_rejects_unknown_or_inverted_spans(
    kind: str,
    normalized_start: int,
    normalized_end: int,
    byte_start: int,
    byte_end: int,
) -> None:
    with pytest.raises(ValueError):
        _ = WireStyleRun(
            kind=kind,
            normalized_start=normalized_start,
            normalized_end=normalized_end,
            byte_start=byte_start,
            byte_end=byte_end,
        )


def test_wire_read_rejects_unknown_style_run_kind_and_missing_separator_text() -> None:
    payload = make_report().to_dict()
    page = payload["projects"][0]["pages"][0]
    page["style_runs"] = [
        {
            "kind": "underline",
            "normalized_start": 0,
            "normalized_end": 1,
            "byte_start": 0,
            "byte_end": 1,
        }
    ]

    with pytest.raises(ValueError, match="style_runs"):
        _ = AlignmentReport.from_dict(payload)

    page["style_runs"] = []
    page["source_lines"][0].pop("separator_text")
    with pytest.raises(ValueError, match="separator_text"):
        _ = AlignmentReport.from_dict(payload)


@pytest.mark.parametrize("separator_text", ["\r", "\n", "\r\n"])
def test_source_line_preserves_exact_separator_text(separator_text: str) -> None:
    content = "a"
    separator_end = len(content.encode("utf-8")) + len(separator_text.encode("utf-8"))
    line = WireSourceLine(
        ordinal=0,
        byte_start=0,
        byte_end=separator_end,
        content_byte_start=0,
        content_byte_end=1,
        separator_byte_start=1,
        separator_byte_end=separator_end,
        original_text=content,
        separator_text=separator_text,
        visible_text=content,
        matching_eligible=True,
        style_fitting_eligible=True,
    )

    assert line.to_dict()["separator_text"] == separator_text


def test_page_rejects_noncontiguous_source_line_byte_evidence() -> None:
    first = WireSourceLine(
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
    )
    second = WireSourceLine(
        ordinal=1,
        byte_start=3,
        byte_end=4,
        content_byte_start=3,
        content_byte_end=4,
        separator_byte_start=4,
        separator_byte_end=4,
        original_text="b",
        separator_text="",
        visible_text="b",
        matching_eligible=True,
        style_fitting_eligible=True,
    )

    with pytest.raises(ValueError, match="contiguous"):
        _ = PageAlignment(
            page_name="p2.png",
            f2_sha256=_sha256(),
            scan_sha256=None,
            source_frame=None,
            source_lines=(first, second),
            formatting_spans=(),
            candidates=(),
            operations=(),
            total_cost=0.0,
            second_best_cost=None,
            normalized_cost=0.0,
            matched_count=0,
            matched_ratio=0.0,
            uniqueness_margin=0.0,
            mean_width_residual=None,
            mean_indentation_residual=None,
            state="proposed",
            accepted=False,
            exclusions=(),
        )


def test_page_rejects_source_line_evidence_not_starting_at_zero() -> None:
    line = WireSourceLine(
        ordinal=0,
        byte_start=1,
        byte_end=2,
        content_byte_start=1,
        content_byte_end=2,
        separator_byte_start=2,
        separator_byte_end=2,
        original_text="a",
        separator_text="",
        visible_text="a",
        matching_eligible=True,
        style_fitting_eligible=True,
    )

    with pytest.raises(ValueError, match="contiguous"):
        _ = PageAlignment(
            page_name="p2.png",
            f2_sha256=_sha256(),
            scan_sha256=None,
            source_frame=None,
            source_lines=(line,),
            formatting_spans=(),
            candidates=(),
            operations=(),
            total_cost=0.0,
            second_best_cost=None,
            normalized_cost=0.0,
            matched_count=0,
            matched_ratio=0.0,
            uniqueness_margin=0.0,
            mean_width_residual=None,
            mean_indentation_residual=None,
            state="proposed",
            accepted=False,
            exclusions=(),
        )


def test_direct_report_output_round_trips_through_strict_reader() -> None:
    report = make_report()

    assert AlignmentReport.from_dict(report.to_dict()).to_dict() == report.to_dict()


def test_wire_source_line_rejects_inverted_utf8_span() -> None:
    with pytest.raises(ValueError):
        _ = WireSourceLine(
            ordinal=0,
            byte_start=2,
            byte_end=1,
            content_byte_start=2,
            content_byte_end=1,
            separator_byte_start=1,
            separator_byte_end=1,
            original_text="",
            separator_text="",
            visible_text="bad",
            matching_eligible=True,
            style_fitting_eligible=True,
        )


def test_wire_candidate_rejects_inverted_source_frame_box() -> None:
    with pytest.raises(ValueError):
        _ = WireLineCandidate(
            ordinal=0,
            box=(1, 1, 0, 2),
            width=-1,
            height=1,
            fill_ratio=0.2,
            component_count=1,
            foreground_pixels=1,
        )


def test_alignment_operation_rejects_incomplete_match() -> None:
    with pytest.raises(ValueError):
        _ = AlignmentOperation(kind="match", source_ordinal=None, candidate_ordinal=0, cost=0.0)


def test_schema_is_generated_from_alignment_report_input() -> None:
    schema_path = Path("schemas/pgdp-alignment-v1.schema.json")
    assert schema_path.read_text(encoding="utf-8") == AlignmentReport.json_schema()
