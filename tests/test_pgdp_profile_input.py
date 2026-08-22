from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdomain_ocr_synth.pgdp.profile_input import load_profile_input


def _write_ranking(
    path: Path,
    *,
    schema_version: object = 1,
    algorithm_version: object = "pgdp-rank/v1",
    projects: object = (),
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "algorithm_version": algorithm_version,
                "projects": projects,
            }
        ),
        encoding="utf-8",
    )


def _project(project_id: str, page_names: tuple[str, ...]) -> dict[str, object]:
    return {
        "project_id": project_id,
        "title": f"Title {project_id}",
        "author": "Author",
        "genre": "Fiction",
        "pages": [{"name": page_name} for page_name in page_names],
    }


def _make_project(corpus_root: Path, project_id: str) -> Path:
    project_directory = corpus_root / project_id
    project_directory.mkdir(parents=True)
    return project_directory


def test_profile_input_preserves_report_order_and_records_root_image_path(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    project_b = _make_project(corpus_root, "projectIDb")
    project_a = _make_project(corpus_root, "projectIDa")
    (project_b / "p2.png").touch()
    (project_b / "p1.png").touch()
    (project_a / "p3.png").touch()
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(
        ranking_path,
        projects=(
            _project("projectIDb", ("p2.png", "p1.png")),
            _project("projectIDa", ("p3.png",)),
        ),
    )

    ranking_input = load_profile_input(ranking_path, corpus_root=corpus_root)

    assert [project.project_id for project in ranking_input.projects] == [
        "projectIDb",
        "projectIDa",
    ]
    assert [page.name for page in ranking_input.projects[0].pages] == ["p2.png", "p1.png"]
    page = ranking_input.projects[0].pages[0]
    assert page.source_path == "projectIDb/p2.png"
    assert page.image_path == project_b / "p2.png"


def test_profile_input_rejects_unknown_algorithm(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(ranking_path, algorithm_version="pgdp-rank/v2")

    with pytest.raises(ValueError, match="pgdp-rank/v1"):
        _ = load_profile_input(ranking_path, corpus_root=corpus_root)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("[1]", "valid ranking JSON"),
        ("{", "valid ranking JSON"),
        (
            json.dumps(
                {"schema_version": "1", "algorithm_version": "pgdp-rank/v1", "projects": []}
            ),
            "valid ranking JSON",
        ),
    ],
)
def test_profile_input_rejects_malformed_ranking_json(
    tmp_path: Path, payload: str, message: str
) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    ranking_path = tmp_path / "ranking.json"
    ranking_path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        _ = load_profile_input(ranking_path, corpus_root=corpus_root)


def test_profile_input_rejects_unknown_schema_version(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(ranking_path, schema_version=2)

    with pytest.raises(ValueError, match="schema version 1"):
        _ = load_profile_input(ranking_path, corpus_root=corpus_root)


def test_profile_input_rejects_duplicate_project_ids(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    _make_project(corpus_root, "projectIDone")
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(
        ranking_path,
        projects=(
            _project("projectIDone", ()),
            _project("projectIDone", ()),
        ),
    )

    with pytest.raises(ValueError, match="Duplicate project_id"):
        _ = load_profile_input(ranking_path, corpus_root=corpus_root)


def test_profile_input_rejects_duplicate_page_names(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    _make_project(corpus_root, "projectIDone")
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(ranking_path, projects=(_project("projectIDone", ("p1.png", "p1.png")),))

    with pytest.raises(ValueError, match="Duplicate page name"):
        _ = load_profile_input(ranking_path, corpus_root=corpus_root)


def test_profile_input_rejects_a_missing_project_directory(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(ranking_path, projects=(_project("projectIDmissing", ()),))

    with pytest.raises(ValueError, match="does not exist"):
        _ = load_profile_input(ranking_path, corpus_root=corpus_root)


@pytest.mark.parametrize("project_id", ["/absolute", "../traversal", "projectID\x00bad"])
def test_profile_input_rejects_unsafe_project_references(tmp_path: Path, project_id: str) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(ranking_path, projects=(_project(project_id, ()),))

    with pytest.raises(ValueError, match=r"(?i)unsafe"):
        _ = load_profile_input(ranking_path, corpus_root=corpus_root)


@pytest.mark.parametrize("page_name", ["/absolute.png", "../traversal.png", "p1\x00.png"])
def test_profile_input_rejects_unsafe_page_references(tmp_path: Path, page_name: str) -> None:
    corpus_root = tmp_path / "corpus"
    _make_project(corpus_root, "projectIDone")
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(ranking_path, projects=(_project("projectIDone", (page_name,)),))

    with pytest.raises(ValueError, match=r"(?i)unsafe"):
        _ = load_profile_input(ranking_path, corpus_root=corpus_root)


def test_profile_input_rejects_symlink_escape(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    project_directory = _make_project(corpus_root, "projectIDone")
    outside = tmp_path / "outside.png"
    outside.touch()
    try:
        (project_directory / "p1.png").symlink_to(outside)
    except OSError as error:
        pytest.skip(f"Symlinks are unavailable: {error}")
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(ranking_path, projects=(_project("projectIDone", ("p1.png",)),))

    with pytest.raises(ValueError, match="escapes"):
        _ = load_profile_input(ranking_path, corpus_root=corpus_root)


def test_profile_input_uses_root_precedence_when_root_and_images_candidates_exist(
    tmp_path: Path,
) -> None:
    corpus_root = tmp_path / "corpus"
    project_directory = _make_project(corpus_root, "projectIDone")
    root_image = project_directory / "p1.png"
    root_image.touch()
    images_image = project_directory / "images" / "p1.png"
    images_image.parent.mkdir()
    images_image.touch()
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(ranking_path, projects=(_project("projectIDone", ("p1.png",)),))

    ranking_input = load_profile_input(ranking_path, corpus_root=corpus_root)

    page = ranking_input.projects[0].pages[0]
    assert page.image_path == root_image
    assert page.source_path == "projectIDone/p1.png"


def test_profile_input_keeps_missing_image_page_for_later_measurement_diagnostics(
    tmp_path: Path,
) -> None:
    corpus_root = tmp_path / "corpus"
    _make_project(corpus_root, "projectIDone")
    ranking_path = tmp_path / "ranking.json"
    _write_ranking(ranking_path, projects=(_project("projectIDone", ("missing.png",)),))

    ranking_input = load_profile_input(ranking_path, corpus_root=corpus_root)

    page = ranking_input.projects[0].pages[0]
    assert page.image_path is None
    assert page.source_path is None
