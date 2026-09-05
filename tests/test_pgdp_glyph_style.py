"""Tests for resolving a cut glyph's face from PGDP's own F2 markup."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from pdomain_ocr_synth.pgdp.glyph_style import (
    ROMAN,
    GlyphStyleError,
    read_book_style,
    styles_for_word,
    word_character_offsets,
)

_PAGE = "p001.png"


def _corpus(tmp_path: Path, pages: dict[str, str]) -> tuple[Path, str]:
    project = tmp_path / "corpus" / "projectIDone"
    (project / "rounds").mkdir(parents=True)
    payload = json.dumps(pages)
    (project / "rounds" / "F2.json").write_text(payload, encoding="utf-8")
    digest = sha256((project / "rounds" / "F2.json").read_bytes()).hexdigest()
    return tmp_path / "corpus", digest


def test_word_offsets_survive_collapsed_whitespace() -> None:
    assert word_character_offsets("  one   two three ") == (2, 8, 12)
    assert word_character_offsets("") == ()
    assert word_character_offsets("   ") == ()


def test_an_unmarked_line_reads_roman(tmp_path: Path) -> None:
    root, digest = _corpus(tmp_path, {_PAGE: "plain words here\n"})
    style = read_book_style(root, project_id="projectIDone", f2_sha256=digest)
    assert (
        styles_for_word(
            style,
            page_name=_PAGE,
            source_ordinal=0,
            visible_text="plain words here",
            word_ordinal=1,
            positions=[0, 1, 2, 3, 4],
        )
        == (ROMAN,) * 5
    )


def test_an_italic_word_reads_italic(tmp_path: Path) -> None:
    root, digest = _corpus(tmp_path, {_PAGE: "plain <i>words</i> here\n"})
    style = read_book_style(root, project_id="projectIDone", f2_sha256=digest)
    assert (
        styles_for_word(
            style,
            page_name=_PAGE,
            source_ordinal=0,
            visible_text="plain words here",
            word_ordinal=1,
            positions=[0, 1, 2, 3, 4],
        )
        == ("italic",) * 5
    )


def test_small_caps_are_named_rather_than_folded_into_roman(tmp_path: Path) -> None:
    root, digest = _corpus(tmp_path, {_PAGE: "<sc>Lowther Street</sc>, November\n"})
    style = read_book_style(root, project_id="projectIDone", f2_sha256=digest)
    visible = "Lowther Street, November"
    assert (
        styles_for_word(
            style,
            page_name=_PAGE,
            source_ordinal=0,
            visible_text=visible,
            word_ordinal=0,
            positions=[0, 1, 2],
        )
        == ("small_caps",) * 3
    )
    assert styles_for_word(
        style,
        page_name=_PAGE,
        source_ordinal=0,
        visible_text=visible,
        word_ordinal=2,
        positions=[0],
    ) == (ROMAN,)


def test_a_style_ending_mid_word_only_covers_its_own_characters(tmp_path: Path) -> None:
    root, digest = _corpus(tmp_path, {_PAGE: "<i>ab</i>cd\n"})
    style = read_book_style(root, project_id="projectIDone", f2_sha256=digest)
    assert styles_for_word(
        style,
        page_name=_PAGE,
        source_ordinal=0,
        visible_text="abcd",
        word_ordinal=0,
        positions=[0, 1, 2, 3],
    ) == ("italic", "italic", ROMAN, ROMAN)


def test_nested_styles_are_reported_together(tmp_path: Path) -> None:
    root, digest = _corpus(tmp_path, {_PAGE: "<sc><i>both</i></sc>\n"})
    style = read_book_style(root, project_id="projectIDone", f2_sha256=digest)
    assert styles_for_word(
        style,
        page_name=_PAGE,
        source_ordinal=0,
        visible_text="both",
        word_ordinal=0,
        positions=[0],
    ) == ("italic+small_caps",)


def test_a_proofer_note_mentioning_a_tag_is_not_a_tag(tmp_path: Path) -> None:
    """The `<sc>` inside a proofer's query is text, and the note never reaches the visible line."""

    root, digest = _corpus(tmp_path, {_PAGE: "Lowther Street[**mark place in <sc>?], November\n"})
    style = read_book_style(root, project_id="projectIDone", f2_sha256=digest)
    visible = "Lowther Street, November"
    assert style.line_agrees(_PAGE, 0, visible)
    assert (
        styles_for_word(
            style,
            page_name=_PAGE,
            source_ordinal=0,
            visible_text=visible,
            word_ordinal=0,
            positions=[0, 1, 2],
        )
        == (ROMAN,) * 3
    )


def test_a_line_that_does_not_match_the_alignment_yields_no_style(tmp_path: Path) -> None:
    root, digest = _corpus(tmp_path, {_PAGE: "plain <i>words</i> here\n"})
    style = read_book_style(root, project_id="projectIDone", f2_sha256=digest)
    assert styles_for_word(
        style,
        page_name=_PAGE,
        source_ordinal=0,
        visible_text="something else entirely",
        word_ordinal=0,
        positions=[0],
    ) == (None,)


def test_no_style_source_yields_none_rather_than_roman() -> None:
    assert styles_for_word(
        None,
        page_name=_PAGE,
        source_ordinal=0,
        visible_text="a b",
        word_ordinal=0,
        positions=[0],
    ) == (None,)


def test_a_word_ordinal_past_the_line_yields_no_style(tmp_path: Path) -> None:
    root, digest = _corpus(tmp_path, {_PAGE: "two words\n"})
    style = read_book_style(root, project_id="projectIDone", f2_sha256=digest)
    assert styles_for_word(
        style,
        page_name=_PAGE,
        source_ordinal=0,
        visible_text="two words",
        word_ordinal=9,
        positions=[0],
    ) == (None,)


def test_an_f2_that_does_not_hash_to_the_recorded_value_is_refused(tmp_path: Path) -> None:
    root, _digest = _corpus(tmp_path, {_PAGE: "plain words\n"})
    with pytest.raises(GlyphStyleError, match="not the aligned"):
        _ = read_book_style(root, project_id="projectIDone", f2_sha256="c" * 64)


def test_a_missing_f2_is_refused(tmp_path: Path) -> None:
    project = tmp_path / "corpus" / "projectIDone"
    (project / "rounds").mkdir(parents=True)
    with pytest.raises(GlyphStyleError, match="Could not read the F2 source"):
        _ = read_book_style(tmp_path / "corpus", project_id="projectIDone", f2_sha256="c" * 64)


def test_the_book_records_the_file_it_read(tmp_path: Path) -> None:
    root, digest = _corpus(tmp_path, {_PAGE: "plain words\n"})
    style = read_book_style(root, project_id="projectIDone", f2_sha256=digest)
    assert (style.label, style.sha256, style.project_id) == ("F2.json", digest, "projectIDone")
