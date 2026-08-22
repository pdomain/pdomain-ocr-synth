from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdomain_ocr_synth.pgdp import RankingReport, natural_page_key, rank_corpus


def _project(
    root: Path,
    project_id: str,
    *,
    pages: dict[str, str] | None = None,
    metadata: object | None = None,
    transcriptions: object | None = None,
    images: tuple[str, ...] = (),
) -> Path:
    project = root / project_id
    project.mkdir()
    project_metadata = {
        "projectid": project_id,
        "title": f"Title {project_id}",
        "author": "Author",
        "genre": "Fiction",
        "pages_total": 12,
        "pg_ebook_number": 99,
    }
    (project / "project.json").write_text(
        json.dumps(project_metadata if metadata is None else metadata), encoding="utf-8"
    )
    if pages is not None:
        rounds = project / "rounds"
        rounds.mkdir()
        (rounds / "F2.json").write_text(json.dumps(pages), encoding="utf-8")
    if transcriptions is not None:
        (project / "pages.json").write_text(json.dumps(transcriptions), encoding="utf-8")
    for image in images:
        image_path = project / image
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.touch()
    return project


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


def test_rank_corpus_counts_missing_f2_project_and_excludes_it(tmp_path: Path) -> None:
    _project(tmp_path, "projectIDmissing")
    _project(
        tmp_path,
        "projectIDranked",
        pages={"p1.png": "/* <i>text</i> */"},
        transcriptions={"p1.png": "text"},
    )

    report = rank_corpus(tmp_path)

    assert report.corpus.projects_seen == 2
    assert [project.project_id for project in report.projects] == ["projectIDranked"]
    assert [(diagnostic.code, diagnostic.project_id) for diagnostic in report.diagnostics] == [
        ("missing_f2", "projectIDmissing")
    ]


def test_rank_corpus_continues_after_malformed_project_metadata(tmp_path: Path) -> None:
    _project(
        tmp_path,
        "projectIDbroken",
        pages={"p1.png": "/* <i>text</i> */"},
        metadata={"projectid": 5},
    )
    _project(
        tmp_path,
        "projectIDvalid",
        pages={"p1.png": "/* <i>text</i> */"},
        transcriptions={"p1.png": "text"},
    )

    report = rank_corpus(tmp_path)

    assert [project.project_id for project in report.projects] == ["projectIDvalid"]
    assert [(diagnostic.code, diagnostic.project_id) for diagnostic in report.diagnostics] == [
        ("malformed_project_metadata", "projectIDbroken")
    ]


def test_rank_corpus_excludes_project_with_mismatched_metadata_id(tmp_path: Path) -> None:
    _project(
        tmp_path,
        "projectIDdirectory",
        pages={"p1.png": "/* <i>text</i> */"},
        metadata={"projectid": "projectIDpayload"},
    )

    report = rank_corpus(tmp_path)

    assert report.corpus.projects_ranked == 0
    assert [(diagnostic.code, diagnostic.project_id) for diagnostic in report.diagnostics] == [
        ("project_id_mismatch", "projectIDdirectory")
    ]


def test_rank_corpus_reports_malformed_pages_json_and_keeps_project(tmp_path: Path) -> None:
    _project(
        tmp_path,
        "projectIDone",
        pages={"p1.png": "/* <i>text</i> */"},
        transcriptions={"p1.png": 1},
    )

    report = rank_corpus(tmp_path)

    assert report.projects[0].pages[0].transcription_available is False
    assert [(diagnostic.code, diagnostic.project_id) for diagnostic in report.diagnostics] == [
        ("malformed_pages_json", "projectIDone")
    ]


def test_rank_corpus_scores_top_ten_pages_and_distinct_groups(tmp_path: Path) -> None:
    pages = {
        f"p{index}.png": "/* <i>a</i><i>b</i><i>c</i><i>d</i><i>e</i><i>f</i> */"
        for index in range(1, 12)
    }
    pages["p11L.png"] = "/* <i>a</i><i>b</i><i>c</i><i>d</i><i>e</i><i>f</i> */"
    _project(tmp_path, "projectIDone", pages=pages)

    report = rank_corpus(tmp_path, pages_per_project=1)

    project = report.projects[0]
    assert project.score_components == {"top_ten_page_scores": 116, "group_bonus": 40}
    assert project.score == 156


def test_rank_corpus_sorts_projects_by_score_then_project_id(tmp_path: Path) -> None:
    _project(tmp_path, "projectIDb", pages={"p1.png": "plain"})
    _project(tmp_path, "projectIDa", pages={"p1.png": "plain"})
    _project(tmp_path, "projectIDz", pages={"p1.png": "/* <i>text</i> */"})

    report = rank_corpus(tmp_path)

    assert [project.project_id for project in report.projects] == [
        "projectIDz",
        "projectIDa",
        "projectIDb",
    ]


def test_rank_corpus_sorts_pages_by_score_then_natural_name(tmp_path: Path) -> None:
    _project(
        tmp_path,
        "projectIDone",
        pages={
            "p10.png": "/* <i>text</i> */",
            "p002.png": "/* <i>text</i> */",
            "p2.png": "/* <i>text</i> */",
        },
    )

    report = rank_corpus(tmp_path, pages_per_project=3)

    assert [page.name for page in report.projects[0].pages] == ["p2.png", "p002.png", "p10.png"]


def test_rank_corpus_selects_each_group_before_high_score_fill(tmp_path: Path) -> None:
    _project(
        tmp_path,
        "projectIDone",
        pages={
            "p1.png": "/* <i>many</i><i>tags</i> */",
            "p2.png": "/* one   two\nthree   four\nfive   six */",
            "p3.png": "long normal prose line\n" * 5 + "/* a\nbb\nccc\ndddd */",
            "p4.png": '/* "one"\n"two"\n"three"\n"four" */',
            "p5L.png": "/* plain */",
            "p6.png": "/* <i>more</i><i>style</i><i>tags</i> */",
        },
    )

    report = rank_corpus(tmp_path, pages_per_project=5)

    assert [page.name for page in report.projects[0].pages] == [
        "p6.png",
        "p2.png",
        "p3.png",
        "p4.png",
        "p5L.png",
    ]


def test_rank_corpus_uses_one_slot_for_page_matching_multiple_groups(tmp_path: Path) -> None:
    _project(
        tmp_path,
        "projectIDone",
        pages={
            "p1L.png": "/* <i>styled</i> */",
            "p2.png": "/* one   two\nthree   four\nfive   six */",
        },
    )

    report = rank_corpus(tmp_path, pages_per_project=2)

    assert [page.name for page in report.projects[0].pages] == ["p1L.png", "p2.png"]
    assert report.projects[0].pages[0].matched_groups == (
        "mixed_typography",
        "multipart_layout",
    )


def test_rank_corpus_marks_missing_image_unavailable_without_dropping_page(tmp_path: Path) -> None:
    _project(tmp_path, "projectIDone", pages={"nested/p1.png": "/* <i>text</i> */"})

    report = rank_corpus(tmp_path)

    assert report.projects[0].pages[0].name == "nested/p1.png"
    assert report.projects[0].pages[0].image_available is False


@pytest.mark.parametrize(("project_limit", "pages_per_project"), [(0, 1), (1, 0), (-1, 1)])
def test_rank_corpus_requires_positive_limits(
    tmp_path: Path, project_limit: int, pages_per_project: int
) -> None:
    with pytest.raises(ValueError, match="positive"):
        _ = rank_corpus(tmp_path, project_limit=project_limit, pages_per_project=pages_per_project)


def test_rank_corpus_enforces_project_and_page_caps(tmp_path: Path) -> None:
    _project(
        tmp_path,
        "projectIDhigh",
        pages={
            "p1.png": "/* <i>one</i> */",
            "p2.png": "/* <i>two</i> */",
        },
    )
    _project(tmp_path, "projectIDlow", pages={"p1.png": "plain"})

    report = rank_corpus(tmp_path, project_limit=1, pages_per_project=1)

    assert report.corpus.projects_ranked == 2
    assert [project.project_id for project in report.projects] == ["projectIDhigh"]
    assert [page.name for page in report.projects[0].pages] == ["p1.png"]


def test_rank_corpus_returns_an_equal_report_for_repeated_runs(tmp_path: Path) -> None:
    _project(
        tmp_path,
        "projectIDone",
        pages={"p2.png": "/* <i>text</i> */", "p1.png": "plain"},
        transcriptions={"p1.png": "plain"},
        images=("p2.png",),
    )

    assert rank_corpus(tmp_path) == rank_corpus(tmp_path)
