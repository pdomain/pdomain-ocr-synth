from __future__ import annotations

from dataclasses import FrozenInstanceError
from itertools import pairwise

import pytest

from pdomain_ocr_synth.pgdp.alignment_source import tokenize_source_page


@pytest.mark.parametrize(
    ("source", "expected_lines", "expected_visible"),
    [
        ("plain text", ("plain text",), "plain text"),
        (
            "caf\u00e9\r\nnext\rfinal\n",
            ("caf\u00e9", "next", "final", ""),
            "caf\u00e9\nnext\nfinal\n",
        ),
        ("/* special */", (" special ",), " special "),
        ("[** proof note]word", ("word",), "word"),
    ],
)
def test_tokenize_source_preserves_visible_text_and_line_separators(
    source: str, expected_lines: tuple[str, ...], expected_visible: str
) -> None:
    tokenized = tokenize_source_page("001.png", source)

    assert tuple(line.visible_text for line in tokenized.lines) == expected_lines
    assert tokenized.visible_text == expected_visible
    assert tokenized.source_utf8 == source.encode("utf-8")


def test_tokenize_source_preserves_utf8_ranges_and_visible_case() -> None:
    source = "\u00c9ire\r\n<i>Mixed Case</i> [** proof note]\r"
    tokenized = tokenize_source_page("001.png", source)

    assert tuple(line.visible_text for line in tokenized.lines) == ("\u00c9ire", "Mixed Case ", "")
    assert tokenized.operations[0].byte_start == 0
    assert tokenized.operations[-1].byte_end == len(tokenized.source_utf8)
    assert all(left.byte_end == right.byte_start for left, right in pairwise(tokenized.operations))
    assert all(
        operation.output
        == tokenized.source_utf8[operation.byte_start : operation.byte_end].decode("utf-8")
        for operation in tokenized.operations
        if operation.kind == "copy"
    )
    assert "".join(operation.output for operation in tokenized.operations) == tokenized.visible_text


def test_tokenize_source_preserves_ligatures_punctuation_and_hyphenation() -> None:
    source = "\ufb02ower's well-\nknown co\u00f6peration"
    tokenized = tokenize_source_page("001.png", source)

    assert tokenized.visible_text == "\ufb02ower's well-\nknown co\u00f6peration"
    assert tuple(line.visible_text for line in tokenized.lines) == (
        "\ufb02ower's well-",
        "known co\u00f6peration",
    )


def test_tokenize_source_records_lines_with_half_open_utf8_spans() -> None:
    source = "\u00e9\r\nA\rB\n"
    tokenized = tokenize_source_page("001.png", source)

    assert [
        (
            line.ordinal,
            line.byte_start,
            line.byte_end,
            line.content_byte_start,
            line.content_byte_end,
            line.separator_byte_start,
            line.separator_byte_end,
            line.original_text,
        )
        for line in tokenized.lines
    ] == [
        (0, 0, 4, 0, 2, 2, 4, "\u00e9"),
        (1, 4, 6, 4, 5, 5, 6, "A"),
        (2, 6, 8, 6, 7, 7, 8, "B"),
        (3, 8, 8, 8, 8, 8, 8, ""),
    ]


def test_tokenize_source_deletes_recognized_tags_and_records_style_runs() -> None:
    source = "<i class='roman'>italics</i> <B>bold</b> <sc>CAPS</SC> <f x=1>font</f> <g>Greek</g>"
    tokenized = tokenize_source_page("001.png", source)

    assert tokenized.visible_text == "italics bold CAPS font Greek"
    assert [
        (run.kind, run.normalized_start, run.normalized_end) for run in tokenized.style_runs
    ] == [
        ("i", 0, 7),
        ("b", 8, 12),
        ("sc", 13, 17),
        ("f", 18, 22),
        ("g", 23, 28),
    ]
    assert [(run.byte_start, run.byte_end) for run in tokenized.style_runs] == [
        (17, 24),
        (32, 36),
        (45, 49),
        (62, 66),
        (74, 79),
    ]


def test_tokenize_source_records_standalone_tb_as_zero_width_style_run() -> None:
    tokenized = tokenize_source_page("001.png", "before <tb> after")

    assert tokenized.visible_text == "before  after"
    assert [
        (run.kind, run.normalized_start, run.normalized_end) for run in tokenized.style_runs
    ] == [("tb", 7, 7)]
    assert tokenized.lines[0].style_fitting_eligible is True


def test_tokenize_source_deletes_known_self_closing_tags() -> None:
    tokenized = tokenize_source_page("001.png", "<i/>visible<tb/> <u/>")

    assert tokenized.visible_text == "visible <u/>"
    assert [
        (run.kind, run.normalized_start, run.normalized_end) for run in tokenized.style_runs
    ] == [("tb", 7, 7)]
    assert [diagnostic.code for diagnostic in tokenized.diagnostics] == ["unknown_tag"]


def test_tokenize_source_keeps_unknown_tag_visible_and_marks_line_ineligible() -> None:
    tokenized = tokenize_source_page("001.png", "before <u>under</u> after")

    assert tokenized.visible_text == "before <u>under</u> after"
    assert [diagnostic.code for diagnostic in tokenized.diagnostics] == [
        "unknown_tag",
        "unknown_tag",
    ]
    assert tokenized.lines[0].matching_eligible is True
    assert tokenized.lines[0].style_fitting_eligible is False


@pytest.mark.parametrize(
    "source",
    [
        "[** note with /* unclosed control]",
        "<i data='/*'>visible</i>",
    ],
)
def test_tokenize_source_marks_raw_control_errors_ineligible_for_matching(source: str) -> None:
    tokenized = tokenize_source_page("001.png", source)

    assert "malformed_control" in [diagnostic.code for diagnostic in tokenized.diagnostics]
    assert tokenized.lines[0].matching_eligible is False
    assert tokenized.lines[0].style_fitting_eligible is False


def test_tokenize_source_marks_every_line_in_an_invalid_control_block_ineligible() -> None:
    source = "start /* outer\nmiddle /# nested\nend */ tail\noutside"

    tokenized = tokenize_source_page("001.png", source)

    assert [line.matching_eligible for line in tokenized.lines] == [False, False, False, True]
    assert [line.style_fitting_eligible for line in tokenized.lines] == [False, False, False, True]


def test_tokenize_source_marks_unclosed_control_through_page_end_ineligible() -> None:
    tokenized = tokenize_source_page("001.png", "start /# continued\nstill active\n")

    assert [line.matching_eligible for line in tokenized.lines[:2]] == [False, False]


def test_tokenize_source_splits_unknown_tags_around_valid_raw_controls() -> None:
    tokenized = tokenize_source_page("001.png", '<u data="/*">body*/</u>')

    assert tokenized.visible_text == '<u data="">body</u>'
    assert [operation.kind for operation in tokenized.operations] == [
        "copy",
        "delete_control",
        "copy",
        "copy",
        "delete_control",
        "copy",
    ]
    assert tokenized.lines[0].matching_eligible is True
    assert tokenized.lines[0].style_fitting_eligible is False


def test_tokenize_source_splits_proof_notes_around_valid_raw_controls() -> None:
    tokenized = tokenize_source_page("001.png", "[** note /* hidden */ text]")

    assert tokenized.visible_text == ""
    assert [operation.kind for operation in tokenized.operations] == [
        "delete_note",
        "delete_control",
        "delete_note",
        "delete_control",
        "delete_note",
    ]


def test_tokenize_source_splits_malformed_markup_around_valid_raw_controls() -> None:
    tokenized = tokenize_source_page("001.png", "<i broken /* body */")

    assert tokenized.visible_text == "<i broken  body "
    assert [operation.kind for operation in tokenized.operations] == [
        "copy",
        "delete_control",
        "copy",
        "delete_control",
    ]
    assert tokenized.lines[0].matching_eligible is True
    assert tokenized.lines[0].style_fitting_eligible is False


def test_tokenize_source_handles_a_large_control_rich_page_losslessly() -> None:
    source = "\n".join(f'<u data="/*">line {ordinal}*/</u>' for ordinal in range(256))

    tokenized = tokenize_source_page("001.png", source)

    assert len(tokenized.lines) == 256
    assert all(line.matching_eligible for line in tokenized.lines)
    assert all(not line.style_fitting_eligible for line in tokenized.lines)
    assert len(tokenized.operations) == 7 * 256 - 1
    assert "".join(operation.output for operation in tokenized.operations) == tokenized.visible_text


def test_tokenize_source_handles_tag_dense_single_line_input() -> None:
    source = "".join(f"<u data='{ordinal}'>" for ordinal in range(512))

    tokenized = tokenize_source_page("001.png", source)

    assert tokenized.visible_text == source
    assert len(tokenized.lines) == 1
    assert len(tokenized.operations) == 512
    assert len(tokenized.diagnostics) == 512


@pytest.mark.parametrize(
    "source",
    [
        "before <i broken",
        "before [** proof note",
        "before /* block",
        "before */ block",
    ],
)
def test_tokenize_source_preserves_malformed_markup(source: str) -> None:
    tokenized = tokenize_source_page("001.png", source)

    assert tokenized.visible_text == source
    assert tokenized.lines[0].style_fitting_eligible is False
    assert tokenized.diagnostics


def test_tokenize_source_preserves_all_controls_from_malformed_nested_block() -> None:
    source = "before /* outer /# inner */ after"

    tokenized = tokenize_source_page("001.png", source)

    assert tokenized.visible_text == source
    assert {operation.kind for operation in tokenized.operations} == {"copy"}
    assert tokenized.lines[0].style_fitting_eligible is False


def test_normalization_operations_are_a_complete_byte_partition() -> None:
    source = "a\u00e9\r\n<i>b</i>[** note]/* c */"
    tokenized = tokenize_source_page("001.png", source)

    assert [operation.byte_start for operation in tokenized.operations] == [
        0,
        3,
        5,
        8,
        9,
        13,
        22,
        24,
        27,
    ]
    assert [operation.byte_end for operation in tokenized.operations] == [
        3,
        5,
        8,
        9,
        13,
        22,
        24,
        27,
        29,
    ]
    assert [operation.kind for operation in tokenized.operations] == [
        "copy",
        "normalize_newline",
        "delete_tag",
        "copy",
        "delete_tag",
        "delete_note",
        "delete_control",
        "copy",
        "delete_control",
    ]


def test_source_records_are_immutable() -> None:
    tokenized = tokenize_source_page("001.png", "text")

    with pytest.raises(FrozenInstanceError):
        type(tokenized.lines[0]).__setattr__(tokenized.lines[0], "visible_text", "changed")
