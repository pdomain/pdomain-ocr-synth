"""Tests for the per-book glyph inventory harvest.

The fixture draws pages whose ink is one 4 px bar per letter on an 8 px pitch, so a word's ink
runs and its transcription letters agree by construction. X-height letters run from 10 px below
the line top to the baseline 20 px lower, ascenders start 8 px higher, and descenders end 8 px
lower, so every asserted band flag below is that drawing read back.

A running head is drawn in the top margin and deliberately left out of the alignment's match
operations, which is what a real page's furniture looks like: PGDP strips it, so no matched line
box covers it and only an OCR record can label it.
"""

from __future__ import annotations

import copy
import itertools
import json
from hashlib import sha256
from pathlib import Path
from typing import NamedTuple

import pytest
from PIL import Image

from pdomain_ocr_synth.pgdp.alignment_image import extract_line_candidates
from pdomain_ocr_synth.pgdp.alignment_models import (
    AlignmentOperation,
    AlignmentReport,
    PageAlignment,
    ProjectAlignment,
    WireLineCandidate,
    WireSourceLine,
)
from pdomain_ocr_synth.pgdp.glyphs import build_glyph_inventory, write_glyph_inventory
from pdomain_ocr_synth.pgdp.image_measurement import open_image_snapshot
from pdomain_ocr_synth.pgdp.profile_models import ProfileReport
from pdomain_ocr_synth.pgdp.typography import ProvenanceError

TEXT_LEFT = 100
TEXT_RIGHT = 1000
LETTER_PITCH = 8
LETTER_WIDTH = 4
FIRST_LINE_TOP = 60
LINE_PITCH = 65
LINE_COUNT = 6
WORD_GAP_PX = 24
X_HEIGHT_TOP_OFFSET = 10
BASELINE_OFFSET = 30
ASCENDER_TOP_OFFSET = 2
DESCENDER_BOTTOM_OFFSET = 38
HEAD_TOP = 16
HEAD_TEXT = ("THE", "BOOK", "14")

_ASCENDERS = frozenset("bdfhklt")
_DESCENDERS = frozenset("gpqy")
_WORDS = ("nose", "shall", "adept", "quiet", "moral", "bring", "under", "waves", "light", "hopes")


class Fixture(NamedTuple):
    """A drawn corpus, a real profile, and a hand-built accepted alignment."""

    corpus_root: Path
    profile_path: Path
    alignment_path: Path
    geometry_path: Path
    line_texts: tuple[str, ...]


def _line_text(line: int) -> str:
    """Fill the measure with real words, staggered so no column is blank on every line."""

    words: list[str] = []
    x = TEXT_LEFT
    index = line
    while True:
        word = _WORDS[index % len(_WORDS)]
        width = len(word) * LETTER_PITCH - (LETTER_PITCH - LETTER_WIDTH)
        if x + width > TEXT_RIGHT:
            break
        words.append(word)
        x += width + WORD_GAP_PX
        index += 1
    return " ".join(words)


def _draw_word(image: Image.Image, word: str, *, x: int, top: int) -> int:
    for position, character in enumerate(word):
        y_start = top + (ASCENDER_TOP_OFFSET if character in _ASCENDERS else X_HEIGHT_TOP_OFFSET)
        y_end = top + (DESCENDER_BOTTOM_OFFSET if character in _DESCENDERS else BASELINE_OFFSET)
        left = x + position * LETTER_PITCH
        for column in range(left, left + LETTER_WIDTH):
            for row in range(y_start, y_end):
                image.putpixel((column, row), 0)
    return x + len(word) * LETTER_PITCH - (LETTER_PITCH - LETTER_WIDTH)


def _draw_line(image: Image.Image, text: str, *, top: int) -> None:
    x = TEXT_LEFT
    for word in text.split():
        x = _draw_word(image, word, x=x, top=top) + WORD_GAP_PX


def _draw_running_head(image: Image.Image) -> tuple[tuple[str, tuple[int, int, int, int]], ...]:
    boxes: list[tuple[str, tuple[int, int, int, int]]] = []
    x = 400
    for word in HEAD_TEXT:
        start = x
        x = _draw_word(image, word.lower(), x=x, top=HEAD_TOP)
        boxes.append((word, (start - 2, HEAD_TOP + 8, x + 2, HEAD_TOP + BASELINE_OFFSET + 2)))
        x += WORD_GAP_PX
    return tuple(boxes)


def _source_line(ordinal: int, text: str, byte_start: int) -> WireSourceLine:
    encoded = len(text.encode("utf-8"))
    content_end = byte_start + encoded
    return WireSourceLine(
        ordinal=ordinal,
        byte_start=byte_start,
        byte_end=content_end + 1,
        content_byte_start=byte_start,
        content_byte_end=content_end,
        separator_byte_start=content_end,
        separator_byte_end=content_end + 1,
        original_text=text,
        separator_text="\n",
        visible_text=text,
        matching_eligible=True,
        style_fitting_eligible=True,
    )


def build_glyph_fixture(tmp_path: Path) -> Fixture:
    """Draw two identical pages, profile them for real, and accept the body lines 1:1."""

    from pdomain_ocr_synth.cli import main

    corpus_root = tmp_path / "corpus"
    project = corpus_root / "projectIDone"
    (project / "rounds").mkdir(parents=True)
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
    line_texts = tuple(_line_text(line) for line in range(LINE_COUNT))
    image = Image.new("L", (1100, 460), color=255)
    head = _draw_running_head(image)
    for line, text in enumerate(line_texts):
        _draw_line(image, text, top=FIRST_LINE_TOP + line * LINE_PITCH)
    (project / "rounds" / "F2.json").write_text(
        json.dumps({"p2.png": "placeholder", "p10.png": "placeholder"}), encoding="utf-8"
    )
    for name in ("p2.png", "p10.png"):
        image.save(project / name)

    ranking_path = tmp_path / "ranking.json"
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
    profile_path = tmp_path / "profile.json"
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
    alignment_path = tmp_path / "alignment.json"
    scan_hashes = _write_accepted_alignment(
        corpus_root=corpus_root,
        profile_path=profile_path,
        alignment_path=alignment_path,
        line_texts=line_texts,
    )
    geometry_path = tmp_path / "geometry.jsonl"
    _write_geometry(geometry_path, head=head, scan_hashes=scan_hashes)
    return Fixture(corpus_root, profile_path, alignment_path, geometry_path, line_texts)


def _write_accepted_alignment(
    *,
    corpus_root: Path,
    profile_path: Path,
    alignment_path: Path,
    line_texts: tuple[str, ...],
) -> dict[str, str]:
    profile_bytes = profile_path.read_bytes()
    profile = ProfileReport.from_json(profile_bytes)
    project_profile = profile.projects[0]
    pages: list[PageAlignment] = []
    scan_hashes: dict[str, str] = {}
    for measurement in project_profile.pages:
        source_frame = measurement.source_frame
        bounds = measurement.foreground_bounds
        assert source_frame is not None
        assert bounds is not None
        scan_hashes[measurement.page_name] = measurement.sha256
        with open_image_snapshot(corpus_root / measurement.source_path) as snapshot:
            extraction = extract_line_candidates(
                snapshot,
                source_frame=source_frame,
                foreground_bounds=tuple(bounds),
                ink_bands=measurement.ink_bands,
                furniture_band_ordinals=measurement.furniture_band_ordinals,
            )
        candidates: list[WireLineCandidate] = []
        source_lines: list[WireSourceLine] = []
        operations: list[AlignmentOperation] = []
        byte_offset = 0
        for ordinal, candidate in enumerate(extraction.candidates):
            candidates.append(
                WireLineCandidate(
                    ordinal=ordinal,
                    box=candidate.box,
                    width=candidate.width,
                    height=candidate.height,
                    fill_ratio=candidate.fill_ratio,
                    component_count=candidate.component_count,
                    foreground_pixels=candidate.foreground_pixels,
                    band_ordinal=candidate.band_ordinal,
                    component_ordinal=candidate.component_ordinal,
                    horizontal_ink_profile=candidate.horizontal_ink_profile,
                )
            )
            line_index = round((candidate.box[1] - FIRST_LINE_TOP) / LINE_PITCH)
            if not 0 <= line_index < LINE_COUNT:
                continue
            text = line_texts[line_index]
            source_lines.append(_source_line(len(source_lines), text, byte_offset))
            byte_offset = source_lines[-1].byte_end
            operations.append(
                AlignmentOperation(
                    kind="match",
                    source_ordinal=source_lines[-1].ordinal,
                    candidate_ordinal=ordinal,
                    cost=0.0,
                )
            )
        pages.append(
            PageAlignment(
                page_name=measurement.page_name,
                f2_sha256="a" * 64,
                scan_sha256=measurement.sha256,
                source_frame=source_frame,
                source_lines=tuple(source_lines),
                formatting_spans=(),
                candidates=tuple(candidates),
                operations=tuple(operations),
                total_cost=0.0,
                second_best_cost=1.0,
                normalized_cost=0.0,
                matched_count=len(operations),
                matched_ratio=1.0,
                uniqueness_margin=1.0,
                mean_width_residual=0.0,
                mean_indentation_residual=0.0,
                state="accepted",
                accepted=True,
                exclusions=(),
            )
        )
    report = AlignmentReport(
        tool_version="0.0.0",
        profile_label=profile_path.name,
        profile_sha256=sha256(profile_bytes).hexdigest(),
        methods={},
        thresholds={},
        projects=(ProjectAlignment(project_id="projectIDone", pages=tuple(pages)),),
    )
    alignment_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return scan_hashes


def _write_geometry(
    path: Path,
    *,
    head: tuple[tuple[str, tuple[int, int, int, int]], ...],
    scan_hashes: dict[str, str],
) -> None:
    records = [
        json.dumps(
            {
                "schema_version": "1.0",
                "project_id": "projectIDone",
                "page_name": page_name,
                "image_sha256": scan_sha256,
                "image_width": 1100,
                "image_height": 460,
                "confidence_tier": "silver",
                "recognizer": {
                    "name": "pdomain-doctr-finetuned",
                    "version": "8b7f9b31",
                    "config_sha256": "b" * 64,
                },
                "words": [
                    {
                        "text": text,
                        "bbox": {
                            "top_left": {"x": box[0], "y": box[1], "is_normalized": False},
                            "bottom_right": {"x": box[2], "y": box[3], "is_normalized": False},
                            "is_normalized": False,
                        },
                        "confidence": 0.79,
                        "line_index": 0,
                        "word_index": index,
                    }
                    for index, (text, box) in enumerate(head)
                ],
            },
            sort_keys=True,
        )
        for page_name, scan_sha256 in sorted(scan_hashes.items())
    ]
    path.write_text("\n".join(records) + "\n", encoding="utf-8")


@pytest.fixture(scope="module")
def fixture(tmp_path_factory: pytest.TempPathFactory) -> Fixture:
    return build_glyph_fixture(tmp_path_factory.mktemp("glyphs"))


def _harvest(fixture: Fixture, *, geometry: bool = True) -> object:
    return build_glyph_inventory(
        fixture.corpus_root,
        fixture.alignment_path,
        fixture.profile_path,
        tool_version="0.0.0",
        geometry_path=fixture.geometry_path if geometry else None,
    )


def test_the_drawn_pages_yield_one_glyph_per_transcribed_letter(fixture: Fixture) -> None:
    harvest = _harvest(fixture, geometry=False)
    expected = 2 * sum(len(text.replace(" ", "")) for text in fixture.line_texts)
    transcribed = [row for row in harvest.rows if row.label_tier == "transcribed"]
    assert len(transcribed) == expected
    assert harvest.separable_word_count == harvest.reconciled_word_count


def test_every_glyph_carries_the_character_the_transcription_gave_it(fixture: Fixture) -> None:
    harvest = _harvest(fixture, geometry=False)
    page = min(row.page_name for row in harvest.rows)
    first_line = min(row.line_ordinal for row in harvest.rows if row.page_name == page)
    word = [
        row
        for row in harvest.rows
        if row.page_name == page and row.line_ordinal == first_line and row.word_ordinal == 0
    ]
    read_back = "".join(row.character for row in sorted(word, key=lambda row: row.glyph_ordinal))
    assert read_back == fixture.line_texts[0].split()[0]


def test_glyph_boxes_run_left_to_right_without_overlapping(fixture: Fixture) -> None:
    harvest = _harvest(fixture, geometry=False)
    page = min(row.page_name for row in harvest.rows)
    line = min(row.line_ordinal for row in harvest.rows if row.page_name == page)
    boxes = [
        row.box
        for row in sorted(
            (
                row
                for row in harvest.rows
                if row.page_name == page and row.line_ordinal == line and row.word_ordinal == 0
            ),
            key=lambda row: row.glyph_ordinal,
        )
    ]
    assert all(earlier[2] <= later[0] for earlier, later in itertools.pairwise(boxes))


def test_an_ascender_is_flagged_and_an_x_height_letter_is_not(fixture: Fixture) -> None:
    harvest = _harvest(fixture, geometry=False)
    ascenders = {row.character for row in harvest.rows if "ascends" in row.flags}
    plain = {row.character for row in harvest.rows if not row.flags}
    assert "h" in ascenders
    assert "o" in plain


def test_a_descender_is_flagged(fixture: Fixture) -> None:
    harvest = _harvest(fixture, geometry=False)
    assert "q" in {row.character for row in harvest.rows if "descends" in row.flags}


def test_the_running_head_is_harvested_as_the_recognized_tier(fixture: Fixture) -> None:
    harvest = _harvest(fixture)
    recognized = [row for row in harvest.rows if row.label_tier == "recognized"]
    assert "".join(sorted({row.character for row in recognized})) == "14BEHKOT"
    assert harvest.furniture_word_count == 2 * len(HEAD_TEXT)


def test_a_recognized_row_carries_the_reads_own_confidence(fixture: Fixture) -> None:
    harvest = _harvest(fixture)
    recognized = [row for row in harvest.rows if row.label_tier == "recognized"]
    assert {row.label_confidence for row in recognized} == {0.79}


def test_a_transcribed_row_never_carries_a_confidence(fixture: Fixture) -> None:
    harvest = _harvest(fixture)
    assert all(
        row.label_confidence is None for row in harvest.rows if row.label_tier == "transcribed"
    )


def test_a_recognized_glyph_records_no_band_offsets(fixture: Fixture) -> None:
    harvest = _harvest(fixture)
    recognized = [row for row in harvest.rows if row.label_tier == "recognized"]
    assert all(row.top_offset_px is None for row in recognized)


def test_without_a_geometry_record_no_furniture_is_harvested(fixture: Fixture) -> None:
    harvest = _harvest(fixture, geometry=False)
    assert all(row.label_tier == "transcribed" for row in harvest.rows)
    assert harvest.geometry_label is None
    assert harvest.furniture_word_count == 0


def test_the_harvest_is_byte_identical_across_two_runs(fixture: Fixture) -> None:
    assert _harvest(fixture).render() == _harvest(fixture).render()


def test_the_manifest_counts_agree_with_the_rows(fixture: Fixture) -> None:
    harvest = _harvest(fixture)
    manifest = harvest.manifest(rows_label="glyphs.jsonl", rows_sha256="a" * 64)
    assert manifest.glyph_count == len(harvest.rows)
    assert sum(row.glyph_count for row in manifest.coverage) == len(harvest.rows)
    assert manifest.ocr_recognizer is not None


def test_a_profile_that_does_not_hash_to_the_recorded_value_is_refused(
    fixture: Fixture, tmp_path: Path
) -> None:
    tampered = tmp_path / "profile.json"
    payload = json.loads(fixture.profile_path.read_text(encoding="utf-8"))
    payload["tool_version"] = "tampered"
    tampered.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ProvenanceError, match="does not match"):
        _ = build_glyph_inventory(
            fixture.corpus_root, fixture.alignment_path, tampered, tool_version="0.0.0"
        )


def test_an_alignment_covering_more_than_one_book_is_refused(
    fixture: Fixture, tmp_path: Path
) -> None:
    payload = json.loads(fixture.alignment_path.read_text(encoding="utf-8"))
    second = copy.deepcopy(payload["projects"][0])
    second["project_id"] = "projectIDtwo"
    payload["projects"] = [payload["projects"][0], second]
    path = tmp_path / "two-books.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one book"):
        _ = build_glyph_inventory(
            fixture.corpus_root, path, fixture.profile_path, tool_version="0.0.0"
        )


def test_writing_the_inventory_lands_both_files_and_a_nobackup_marker(
    fixture: Fixture, tmp_path: Path
) -> None:
    harvest = _harvest(fixture)
    directory = tmp_path / "inventory"
    manifest = write_glyph_inventory(harvest, directory, fixture.corpus_root)
    rendered = (directory / "glyphs.jsonl").read_bytes()
    assert sha256(rendered).hexdigest() == manifest.rows_sha256
    assert (directory / "manifest.json").is_file()
    assert (directory / ".nobackup").is_file()


def test_the_written_inventory_is_byte_identical_across_two_runs(
    fixture: Fixture, tmp_path: Path
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _ = write_glyph_inventory(_harvest(fixture), first, fixture.corpus_root)
    _ = write_glyph_inventory(_harvest(fixture), second, fixture.corpus_root)
    for name in ("glyphs.jsonl", "manifest.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_the_inventory_may_not_be_written_inside_the_corpus(fixture: Fixture) -> None:
    with pytest.raises(ValueError, match="outside the corpus root"):
        _ = write_glyph_inventory(
            _harvest(fixture), fixture.corpus_root / "inventory", fixture.corpus_root
        )
