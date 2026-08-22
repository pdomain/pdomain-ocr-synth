from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from pdomain_ocr_synth.pgdp.profile_models import (
    ALGORITHM_VERSION,
    SCHEMA_VERSION,
    CoordinateFrame,
    Estimate,
    InkBand,
    PageMeasurement,
    ProfileReport,
    ProjectProfile,
    profile_schema_json,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ARTIFACT = REPO_ROOT / "schemas" / "pgdp-profile-v1.schema.json"


def _page(
    *, foreground_bounds: tuple[int, int, int, int] | None = (10, 20, 90, 180)
) -> PageMeasurement:
    return PageMeasurement(
        page_name="001.png",
        source_path="projectID1/001.png",
        sha256="a" * 64,
        source_frame=CoordinateFrame(width=100, height=200),
        image_mode="L",
        grayscale_threshold=127,
        foreground_pixels=1000,
        foreground_bounds=foreground_bounds,
        margins=(10, 20, 10, 20),
        ink_bands=(InkBand(y_start=20, y_end=40), InkBand(y_start=55, y_end=78)),
        derived_estimates=(
            Estimate(
                name="median_ink_band_height",
                value=21.5,
                unit="px",
                truth_class="derived",
                method="pgdp-profile/v1/row-projection",
                sample_count=1,
                evidence_pages=("001.png",),
            ),
        ),
    )


def _report() -> ProfileReport:
    page = _page()
    project = ProjectProfile(
        project_id="projectID1",
        title="A book",
        author="An author",
        genre="Poetry",
        pages=(page,),
        pooled_estimates=(
            Estimate(
                name="median_margin_left",
                value=10.0,
                unit="px",
                truth_class="pooled",
                method="pgdp-profile/v1/median",
                sample_count=1,
                evidence_pages=("001.png",),
            ),
        ),
    )
    return ProfileReport(
        source_ranking={"algorithm_version": "pgdp-rank/v1", "sha256": "b" * 64},
        methods={"ink_geometry": "pgdp-profile/v1/row-projection"},
        projects=(project,),
    )


def test_profile_report_serializes_deterministically_with_normalized_tuples() -> None:
    report = _report()

    assert report.schema_version == SCHEMA_VERSION
    assert report.algorithm_version == ALGORITHM_VERSION
    assert report.projects == tuple(report.projects)
    assert report.to_json() == report.to_json()
    assert report.to_dict()["projects"][0]["pages"][0]["observations"]["ink_bands"] == [
        {"y_start": 20, "y_end": 40},
        {"y_start": 55, "y_end": 78},
    ]


def test_absent_bounds_do_not_become_zero() -> None:
    page = _page(foreground_bounds=None)

    assert page.to_dict()["observations"]["foreground_bounds"] is None


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: CoordinateFrame(width=-1, height=2), "nonnegative"),
        (lambda: InkBand(y_start=3, y_end=2), "half-open"),
        (
            lambda: Estimate(
                name="x",
                value=math.nan,
                unit="px",
                truth_class="observed",
                method="method",
                sample_count=0,
            ),
            "finite",
        ),
        (
            lambda: Estimate(
                name="x",
                value=1.0,
                unit="px",
                truth_class="observed",
                method="method",
                sample_count=2,
                evidence_pages=("001",),
            ),
            "sample_count",
        ),
        (
            lambda: Estimate(
                name="x",
                value=1.0,
                unit="px",
                truth_class="observed",
                method="method",
                sample_count=2,
                evidence_pages=("001", "001"),
            ),
            "duplicate",
        ),
    ],
)
def test_profile_records_reject_invalid_values(factory: object, message: str) -> None:
    if not callable(factory):
        raise AssertionError("test factory must be callable")

    with pytest.raises(ValueError, match=message):
        _ = factory()


def test_profile_report_round_trips_through_typed_wire_json() -> None:
    report = _report()

    reloaded = ProfileReport.from_json(report.to_json())

    assert reloaded.to_dict() == report.to_dict()


def test_profile_reader_preserves_unknown_v1_fields_in_extensions() -> None:
    payload = _report().to_dict()
    payload["future_report_field"] = {"switch": [1, True, None]}
    projects = payload["projects"]
    assert isinstance(projects, list)
    projects[0]["future_project_field"] = "kept"

    reloaded = ProfileReport.from_dict(payload)
    written = reloaded.to_dict()

    assert written["future_report_field"] == {"switch": [1, True, None]}
    assert written["projects"][0]["future_project_field"] == "kept"


def test_profile_reader_preserves_unknown_v1_fields_at_nested_boundaries() -> None:
    payload = _report().to_dict()
    projects = payload["projects"]
    assert isinstance(projects, list)
    pages = projects[0]["pages"]
    assert isinstance(pages, list)
    page = pages[0]
    page["future_page_field"] = {"valid": True}
    page["source_frame"]["future_frame_field"] = 1
    page["image"]["future_image_field"] = "kept"
    observations = page["observations"]
    observations["future_observation_field"] = ["kept"]
    observations["margins"]["future_margin_field"] = None
    bands = observations["ink_bands"]
    assert isinstance(bands, list)
    bands[0]["future_band_field"] = False
    estimates = page["derived_estimates"]
    assert isinstance(estimates, list)
    estimates[0]["future_estimate_field"] = {"kept": 1}

    written = ProfileReport.from_dict(payload).to_dict()
    written_page = written["projects"][0]["pages"][0]

    assert written_page["future_page_field"] == {"valid": True}
    assert written_page["source_frame"]["future_frame_field"] == 1
    assert written_page["image"]["future_image_field"] == "kept"
    assert written_page["observations"]["future_observation_field"] == ["kept"]
    assert written_page["observations"]["margins"]["future_margin_field"] is None
    assert written_page["observations"]["ink_bands"][0]["future_band_field"] is False
    assert written_page["derived_estimates"][0]["future_estimate_field"] == {"kept": 1}


def test_profile_records_reject_nonfinite_extension_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        _ = ProfileReport(
            source_ranking={"ranking_score": math.inf},
            methods={},
        )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("schema_version", True),
        ("schema_version", 1.0),
    ],
)
def test_profile_reader_rejects_coerced_schema_versions(key: str, value: object) -> None:
    payload = _report().to_dict()
    payload[key] = value

    with pytest.raises(ValueError, match="schema_version"):
        _ = ProfileReport.from_dict(payload)


def test_profile_extensions_are_deeply_immutable() -> None:
    nested = {"value": [1, {"two": 2}]}
    report = ProfileReport(source_ranking={"details": nested}, methods={})
    nested["value"][1]["two"] = 3

    assert report.to_dict()["source_ranking"] == {"details": {"value": [1, {"two": 2}]}}


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("schema_version", 2, "schema_version"),
        ("algorithm_version", "pgdp-profile/v2", "algorithm_version"),
    ],
)
def test_profile_reader_rejects_unknown_major_versions(
    key: str, value: object, message: str
) -> None:
    payload = _report().to_dict()
    payload[key] = value

    with pytest.raises(ValueError, match=message):
        _ = ProfileReport.from_dict(payload)


def test_profile_schema_artifact_matches_fresh_generation() -> None:
    assert SCHEMA_ARTIFACT.read_text(encoding="utf-8") == profile_schema_json()


def test_profile_schema_declares_the_top_level_contract() -> None:
    payload = json.loads(SCHEMA_ARTIFACT.read_text(encoding="utf-8"))

    assert payload["properties"].keys() >= {
        "schema_version",
        "algorithm_version",
        "source_ranking",
        "methods",
        "projects",
        "diagnostics",
    }
