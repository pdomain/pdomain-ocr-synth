from __future__ import annotations

from pdomain_ocr_synth.pgdp import RankingReport, natural_page_key


def test_ranking_report_serializes_without_runtime_paths() -> None:
    report = RankingReport.empty(project_limit=50, pages_per_project=12)

    assert report.to_dict() == {
        "schema_version": 1,
        "algorithm_version": "pgdp-rank/v1",
        "limits": {"projects": 50, "pages_per_project": 12},
        "corpus": {"projects_seen": 0, "projects_ranked": 0},
        "diagnostics": [],
        "projects": [],
    }


def test_natural_page_key_orders_numeric_runs_by_value_then_width() -> None:
    names = ["p10.png", "p002.png", "p2.png", "P02.png", "p1.png"]

    assert sorted(names, key=natural_page_key) == [
        "p1.png",
        "p2.png",
        "P02.png",
        "p002.png",
        "p10.png",
    ]


def test_natural_page_key_uses_original_name_after_casefolded_parts() -> None:
    names = ["p02.png", "P02.png"]

    assert sorted(names, key=natural_page_key) == ["P02.png", "p02.png"]
