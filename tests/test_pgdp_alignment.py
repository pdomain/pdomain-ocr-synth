"""Tests for snapshot-safe PGDP source-line alignment orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from pdomain_ocr_synth import __version__
from pdomain_ocr_synth.cli import main
from pdomain_ocr_synth.pgdp import alignment
from pdomain_ocr_synth.pgdp.alignment import build_alignment_report


def test_build_alignment_report_is_public() -> None:
    assert callable(build_alignment_report)


def _write_line_page(path: Path) -> None:
    image = Image.new("L", (120, 100), color=255)
    for row in (10, 30, 50, 70):
        for x in range(20, 100):
            for y in range(row, row + 5):
                image.putpixel((x, y), 0)
    image.save(path)


def _build_profile(corpus_root: Path, profile_path: Path) -> None:
    ranking_path = profile_path.with_name("ranking.json")
    assert (
        main(
            [
                "rank-pgdp",
                str(corpus_root),
                "--output",
                str(ranking_path),
                "--project-limit",
                "1",
                "--pages-per-project",
                "2",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "profile-pgdp",
                str(corpus_root),
                "--ranking",
                str(ranking_path),
                "--output",
                str(profile_path),
            ]
        )
        == 0
    )


def build_alignment_fixture(tmp_path: Path) -> tuple[Path, Path]:
    corpus_root = tmp_path / "corpus"
    project = corpus_root / "projectIDone"
    rounds = project / "rounds"
    rounds.mkdir(parents=True)
    (project / "project.json").write_text(
        json.dumps(
            {
                "projectid": "projectIDone",
                "title": "A book",
                "author": "An author",
                "genre": "Fiction",
                "pages_total": 2,
                "pg_ebook_number": 1,
            }
        ),
        encoding="utf-8",
    )
    (rounds / "F2.json").write_text(
        json.dumps(
            {
                "p10.png": "ten\nten\nten\nten",
                "p2.png": "two\ntwo\ntwo\ntwo",
            }
        ),
        encoding="utf-8",
    )
    _write_line_page(project / "p10.png")
    _write_line_page(project / "p2.png")
    profile_path = tmp_path / "profile.json"
    _build_profile(corpus_root, profile_path)
    return corpus_root, profile_path


def test_build_alignment_report_keeps_natural_page_order(tmp_path: Path) -> None:
    corpus_root, profile_path = build_alignment_fixture(tmp_path)

    report = build_alignment_report(corpus_root, profile_path, tool_version=__version__)

    assert [page.page_name for page in report.projects[0].pages] == ["p2.png", "p10.png"]
    assert report.profile_label == "profile.json"


def test_build_alignment_report_excludes_profile_scan_hash_mismatches(tmp_path: Path) -> None:
    corpus_root, profile_path = build_alignment_fixture(tmp_path)
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    payload["projects"][0]["pages"][0]["sha256"] = "0" * 64
    profile_path.write_text(json.dumps(payload), encoding="utf-8")

    report = build_alignment_report(corpus_root, profile_path, tool_version=__version__)

    page = report.projects[0].pages[0]
    assert page.exclusions == ("scan_hash_mismatch",)
    assert page.state == "excluded"


def test_build_alignment_report_discards_project_evidence_when_f2_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus_root, profile_path = build_alignment_fixture(tmp_path)
    original_read = alignment._read_f2_bytes
    reads = 0

    def read_then_change(path: Path) -> bytes:
        nonlocal reads
        reads += 1
        return original_read(path) if reads == 1 else b'{"p2.png":"changed"}'

    monkeypatch.setattr(alignment, "_read_f2_bytes", read_then_change)

    report = build_alignment_report(corpus_root, profile_path, tool_version=__version__)

    assert reads == 2
    assert all(page.exclusions == ("source_changed",) for page in report.projects[0].pages)
    assert all(not page.candidates and not page.operations for page in report.projects[0].pages)
