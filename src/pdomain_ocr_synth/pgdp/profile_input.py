from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import TypeAdapter, ValidationError

from pdomain_ocr_synth.pgdp.models import RankingReportData
from pdomain_ocr_synth.pgdp.paths import (
    UnsafePathError,
    corpus_relative_path,
    require_canonical_relative_reference,
    resolve_image_candidate,
    resolve_project_directory,
)

if TYPE_CHECKING:
    from pdomain_ocr_synth.pgdp.models import RankedPageData

_SCHEMA_VERSION = 1
_ALGORITHM_VERSION = "pgdp-rank/v1"
_RANKING_REPORT_ADAPTER = TypeAdapter(RankingReportData)


@dataclass(frozen=True, slots=True)
class ProfileInputPage:
    """One selected page with its current safe image resolution."""

    name: str
    image_path: Path | None
    source_path: str | None


@dataclass(frozen=True, slots=True)
class ProfileInputProject:
    """One selected report project in report order."""

    project_id: str
    title: str | None
    author: str | None
    genre: str | None
    pages: tuple[ProfileInputPage, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "pages", tuple(self.pages))


@dataclass(frozen=True, slots=True)
class ProfileInput:
    """Validated ranking selection ready for scan measurement."""

    projects: tuple[ProfileInputProject, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "projects", tuple(self.projects))


def load_profile_input(ranking_path: str | Path, *, corpus_root: str | Path) -> ProfileInput:
    """Validate an M14 report and resolve its selected images safely."""

    payload = _load_ranking_payload(Path(ranking_path))
    _validate_version(payload)
    root = Path(corpus_root)
    project_ids: set[str] = set()
    projects: list[ProfileInputProject] = []
    for project_payload in payload["projects"]:
        project_id = project_payload["project_id"]
        if project_id in project_ids:
            raise ValueError(f"Duplicate project_id in ranking report: {project_id!r}.")
        project_ids.add(project_id)
        project_directory = resolve_project_directory(corpus_root=root, project_id=project_id)
        pages = _load_project_pages(
            project_id=project_id,
            page_payloads=project_payload["pages"],
            project_directory=project_directory,
            corpus_root=root,
        )
        projects.append(
            ProfileInputProject(
                project_id=project_id,
                title=project_payload["title"],
                author=project_payload["author"],
                genre=project_payload["genre"],
                pages=pages,
            )
        )
    return ProfileInput(projects=tuple(projects))


def _load_ranking_payload(path: Path) -> RankingReportData:
    try:
        return _RANKING_REPORT_ADAPTER.validate_json(path.read_text(encoding="utf-8"), strict=True)
    except (OSError, UnicodeDecodeError, ValidationError) as error:
        raise ValueError("Ranking report must be valid ranking JSON.") from error


def _validate_version(payload: RankingReportData) -> None:
    if payload["schema_version"] != _SCHEMA_VERSION:
        raise ValueError("Ranking report must use schema version 1.")
    if payload["algorithm_version"] != _ALGORITHM_VERSION:
        raise ValueError("Ranking report must use algorithm pgdp-rank/v1.")


def _load_project_pages(
    *,
    project_id: str,
    page_payloads: list[RankedPageData],
    project_directory: Path,
    corpus_root: Path,
) -> tuple[ProfileInputPage, ...]:
    page_names: set[str] = set()
    pages: list[ProfileInputPage] = []
    for page_payload in page_payloads:
        page_name = page_payload["name"]
        _ = require_canonical_relative_reference(value=page_name, label="page reference")
        if page_name in page_names:
            raise ValueError(f"Duplicate page name for project {project_id!r}: {page_name!r}.")
        page_names.add(page_name)
        resolution = resolve_image_candidate(
            project_directory=project_directory,
            page_name=page_name,
            corpus_root=corpus_root,
        )
        if resolution.unsafe_candidate:
            raise UnsafePathError(
                f"Page image candidate escapes the project or corpus: {page_name!r}."
            )
        source_path = (
            corpus_relative_path(path=resolution.image_path, corpus_root=corpus_root)
            if resolution.image_path is not None
            else None
        )
        pages.append(
            ProfileInputPage(
                name=page_name,
                image_path=resolution.image_path,
                source_path=source_path,
            )
        )
    return tuple(pages)
