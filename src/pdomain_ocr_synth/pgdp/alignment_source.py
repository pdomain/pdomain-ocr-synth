from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NormalizationKind = Literal[
    "copy",
    "delete_control",
    "delete_tag",
    "delete_note",
    "normalize_newline",
]
StyleKind = Literal["i", "b", "sc", "f", "g", "tb"]

_CONTROL_PAIRS = {"/*": "*/", "/#": "#/"}
_CONTROL_CLOSERS = frozenset(_CONTROL_PAIRS.values())


@dataclass(frozen=True, slots=True)
class NormalizationOperation:
    """One source range and its normalized visible output."""

    kind: NormalizationKind
    byte_start: int
    byte_end: int
    output: str


@dataclass(frozen=True, slots=True)
class StyleRun:
    """A recognized style body in normalized and source coordinates."""

    kind: StyleKind
    normalized_start: int
    normalized_end: int
    byte_start: int
    byte_end: int


@dataclass(frozen=True, slots=True)
class SourceDiagnostic:
    """A recoverable source-tokenization issue with byte evidence."""

    code: str
    message: str
    page_name: str
    byte_start: int
    byte_end: int


@dataclass(frozen=True, slots=True)
class SourceLine:
    """One original source line and its visible normalized form."""

    page_name: str
    ordinal: int
    byte_start: int
    byte_end: int
    content_byte_start: int
    content_byte_end: int
    separator_byte_start: int
    separator_byte_end: int
    original_text: str
    visible_text: str
    operation_ordinals: tuple[int, ...]
    formatting_span_ids: tuple[str, ...]
    continued_block_ids: tuple[str, ...]
    matching_eligible: bool
    style_fitting_eligible: bool


@dataclass(frozen=True, slots=True)
class TokenizedSourcePage:
    """Lossless source bytes and their visible normalization view."""

    page_name: str
    source_utf8: bytes
    visible_text: str
    lines: tuple[SourceLine, ...]
    operations: tuple[NormalizationOperation, ...]
    style_runs: tuple[StyleRun, ...]
    diagnostics: tuple[SourceDiagnostic, ...]


@dataclass(frozen=True, slots=True)
class _Lexeme:
    kind: Literal["tag", "note", "control", "newline", "malformed"]
    character_start: int
    character_end: int
    name: str | None = None
    closing: bool = False
    self_closing: bool = False


@dataclass(frozen=True, slots=True)
class _OpenStyle:
    kind: StyleKind
    byte_start: int
    normalized_start: int


@dataclass(frozen=True, slots=True)
class _ControlParseResult:
    deleted_starts: frozenset[int]
    diagnostics: tuple[SourceDiagnostic, ...]
    invalid_byte_ranges: tuple[tuple[int, int], ...]


def tokenize_source_page(page_name: str, source_text: str) -> TokenizedSourcePage:
    """Tokenize one F2 page without changing its source bytes."""

    source_utf8 = source_text.encode("utf-8")
    byte_offsets = _utf8_offsets(source_text)
    lexemes = _lex(source_text)
    diagnostics: list[SourceDiagnostic] = []
    control_result = _valid_controls(
        page_name=page_name,
        raw_controls=_raw_controls(source_text),
        byte_offsets=byte_offsets,
    )
    diagnostics.extend(control_result.diagnostics)
    operations: list[NormalizationOperation] = []
    style_runs: list[StyleRun] = []
    matching_ineligible_ranges = list(control_result.invalid_byte_ranges)
    style_ineligible_ranges = list(matching_ineligible_ranges)
    open_styles: list[_OpenStyle] = []
    visible_length = 0
    position = 0

    for lexeme in lexemes:
        if position < lexeme.character_start:
            output = source_text[position : lexeme.character_start]
            operation = _copy_operation(byte_offsets, position, lexeme.character_start, output)
            operations.append(operation)
            visible_length += len(output)

        byte_start = byte_offsets[lexeme.character_start]
        byte_end = byte_offsets[lexeme.character_end]
        if lexeme.kind == "newline":
            operations.append(
                NormalizationOperation("normalize_newline", byte_start, byte_end, "\n")
            )
            visible_length += 1
        elif lexeme.kind == "note":
            visible_length += _append_fragmented_operation(
                source_text=source_text,
                byte_offsets=byte_offsets,
                lexeme=lexeme,
                outer_kind="delete_note",
                deleted_control_starts=control_result.deleted_starts,
                operations=operations,
            )
        elif lexeme.kind == "control":
            if lexeme.character_start in control_result.deleted_starts:
                operations.append(
                    NormalizationOperation("delete_control", byte_start, byte_end, "")
                )
            else:
                output = source_text[lexeme.character_start : lexeme.character_end]
                operations.append(
                    _copy_operation(
                        byte_offsets, lexeme.character_start, lexeme.character_end, output
                    )
                )
                visible_length += len(output)
        elif lexeme.kind == "tag":
            tag_name = _style_kind(lexeme.name)
            if tag_name is not None:
                visible_length += _append_fragmented_operation(
                    source_text=source_text,
                    byte_offsets=byte_offsets,
                    lexeme=lexeme,
                    outer_kind="delete_tag",
                    deleted_control_starts=control_result.deleted_starts,
                    operations=operations,
                )
                if tag_name == "tb":
                    style_runs.append(
                        StyleRun("tb", visible_length, visible_length, byte_end, byte_end)
                    )
                elif lexeme.closing:
                    _close_style(
                        page_name=page_name,
                        tag_name=tag_name,
                        byte_start=byte_start,
                        byte_end=byte_end,
                        open_styles=open_styles,
                        style_runs=style_runs,
                        diagnostics=diagnostics,
                        style_ineligible_ranges=style_ineligible_ranges,
                        normalized_end=visible_length,
                    )
                elif not lexeme.self_closing:
                    open_styles.append(_OpenStyle(tag_name, byte_end, visible_length))
            else:
                visible_length += _append_fragmented_operation(
                    source_text=source_text,
                    byte_offsets=byte_offsets,
                    lexeme=lexeme,
                    outer_kind="copy",
                    deleted_control_starts=control_result.deleted_starts,
                    operations=operations,
                )
                diagnostic = _diagnostic(
                    "unknown_tag",
                    f"Unknown F2 tag '{lexeme.name}'.",
                    page_name,
                    byte_start,
                    byte_end,
                )
                diagnostics.append(diagnostic)
                style_ineligible_ranges.append((byte_start, byte_end))
        else:
            output = source_text[lexeme.character_start : lexeme.character_end]
            operations.append(
                _copy_operation(byte_offsets, lexeme.character_start, lexeme.character_end, output)
            )
            visible_length += len(output)
            diagnostic = _diagnostic(
                "malformed_markup",
                "Malformed F2 markup remains visible.",
                page_name,
                byte_start,
                byte_end,
            )
            diagnostics.append(diagnostic)
            style_ineligible_ranges.append((byte_start, byte_end))
        position = lexeme.character_end

    if position < len(source_text):
        output = source_text[position:]
        operations.append(_copy_operation(byte_offsets, position, len(source_text), output))
        visible_length += len(output)

    for open_style in open_styles:
        diagnostic = _diagnostic(
            "unmatched_style_tag",
            f"Unmatched opening F2 tag '{open_style.kind}'.",
            page_name,
            open_style.byte_start,
            open_style.byte_start,
        )
        diagnostics.append(diagnostic)
        style_ineligible_ranges.append((open_style.byte_start, open_style.byte_start))

    visible_text = "".join(operation.output for operation in operations)
    lines = _source_lines(
        page_name=page_name,
        source_text=source_text,
        byte_offsets=byte_offsets,
        operations=operations,
        matching_ineligible_ranges=matching_ineligible_ranges,
        style_ineligible_ranges=style_ineligible_ranges,
    )
    return TokenizedSourcePage(
        page_name=page_name,
        source_utf8=source_utf8,
        visible_text=visible_text,
        lines=lines,
        operations=tuple(operations),
        style_runs=tuple(style_runs),
        diagnostics=tuple(diagnostics),
    )


def _utf8_offsets(source_text: str) -> tuple[int, ...]:
    offsets = [0]
    for character in source_text:
        offsets.append(offsets[-1] + len(character.encode("utf-8")))
    return tuple(offsets)


def _style_kind(name: str | None) -> StyleKind | None:
    match name:
        case "i":
            return "i"
        case "b":
            return "b"
        case "sc":
            return "sc"
        case "f":
            return "f"
        case "g":
            return "g"
        case "tb":
            return "tb"
        case _:
            return None


def _lex(source_text: str) -> tuple[_Lexeme, ...]:
    lexemes: list[_Lexeme] = []
    position = 0
    while position < len(source_text):
        newline_end = _newline_end(source_text, position)
        if newline_end is not None:
            lexemes.append(_Lexeme("newline", position, newline_end))
            position = newline_end
            continue
        control = source_text[position : position + 2]
        if control in _CONTROL_PAIRS or control in _CONTROL_CLOSERS:
            lexemes.append(_Lexeme("control", position, position + 2, control))
            position += 2
            continue
        if source_text.startswith("[**", position):
            note_end = _proof_note_end(source_text, position)
            if note_end is None:
                lexemes.append(_Lexeme("malformed", position, _line_end(source_text, position)))
                position = _line_end(source_text, position)
            else:
                lexemes.append(_Lexeme("note", position, note_end))
                position = note_end
            continue
        if source_text[position] == "<":
            tag = _tag_lexeme(source_text, position)
            if tag is not None:
                lexemes.append(tag)
                position = tag.character_end
                continue
        position += 1
    return tuple(lexemes)


def _raw_controls(source_text: str) -> tuple[_Lexeme, ...]:
    controls: list[_Lexeme] = []
    position = 0
    while position < len(source_text):
        control = source_text[position : position + 2]
        if control in _CONTROL_PAIRS or control in _CONTROL_CLOSERS:
            controls.append(_Lexeme("control", position, position + 2, control))
            position += 2
        else:
            position += 1
    return tuple(controls)


def _newline_end(source_text: str, position: int) -> int | None:
    character = source_text[position]
    if character == "\n":
        return position + 1
    if character == "\r":
        return position + 2 if source_text[position + 1 : position + 2] == "\n" else position + 1
    return None


def _proof_note_end(source_text: str, position: int) -> int | None:
    line_end = _line_end(source_text, position)
    closing = source_text.find("]", position + 3, line_end)
    return None if closing == -1 else closing + 1


def _line_end(source_text: str, position: int) -> int:
    candidates = [
        candidate
        for candidate in (source_text.find("\n", position), source_text.find("\r", position))
        if candidate != -1
    ]
    return min(candidates) if candidates else len(source_text)


def _tag_lexeme(source_text: str, position: int) -> _Lexeme | None:
    line_end = _line_end(source_text, position)
    closing_bracket = source_text.find(">", position + 1, line_end)
    if closing_bracket == -1:
        remainder = source_text[position + 1 : line_end].lstrip()
        if remainder.startswith("/"):
            remainder = remainder[1:].lstrip()
        if remainder[:1].isalpha() and remainder[:1].isascii():
            return _Lexeme("malformed", position, line_end)
        return None
    body = source_text[position + 1 : closing_bracket].strip()
    closing = body.startswith("/")
    if closing:
        body = body[1:].lstrip()
    if not body or not body[0].isalpha() or not body[0].isascii():
        return _Lexeme("malformed", position, closing_bracket + 1)
    name_end = 1
    while name_end < len(body) and (body[name_end].isalnum() or body[name_end] in "_:-"):
        name_end += 1
    name = body[:name_end]
    attribute_text = body[name_end:]
    self_closing = not closing and attribute_text.rstrip().endswith("/")
    if self_closing:
        attribute_text = attribute_text.rstrip()[:-1]
    if attribute_text and not attribute_text[0].isspace():
        return _Lexeme("malformed", position, closing_bracket + 1)
    return _Lexeme(
        "tag",
        position,
        closing_bracket + 1,
        name.lower(),
        closing,
        self_closing,
    )


def _valid_controls(
    *,
    page_name: str,
    raw_controls: tuple[_Lexeme, ...],
    byte_offsets: tuple[int, ...],
) -> _ControlParseResult:
    deleted: set[int] = set()
    diagnostics: list[SourceDiagnostic] = []
    invalid_byte_ranges: list[tuple[int, int]] = []
    open_control: _Lexeme | None = None
    open_control_is_valid = True
    for control_lexeme in raw_controls:
        if control_lexeme.name is None:
            continue
        control = control_lexeme.name
        if control in _CONTROL_PAIRS:
            if open_control is None:
                open_control = control_lexeme
                open_control_is_valid = True
            else:
                open_control_is_valid = False
                diagnostics.append(
                    _diagnostic(
                        "malformed_control",
                        f"Nested or overlapping formatting control '{control}'.",
                        page_name,
                        byte_offsets[control_lexeme.character_start],
                        byte_offsets[control_lexeme.character_end],
                    )
                )
        elif open_control is not None and _CONTROL_PAIRS[open_control.name or ""] == control:
            if open_control_is_valid:
                deleted.add(open_control.character_start)
                deleted.add(control_lexeme.character_start)
            else:
                invalid_byte_ranges.append(
                    (
                        byte_offsets[open_control.character_start],
                        byte_offsets[control_lexeme.character_end],
                    )
                )
            open_control = None
        else:
            if open_control is not None:
                open_control_is_valid = False
            else:
                invalid_byte_ranges.append(
                    (
                        byte_offsets[control_lexeme.character_start],
                        byte_offsets[control_lexeme.character_end],
                    )
                )
            diagnostics.append(
                _diagnostic(
                    "malformed_control",
                    f"Unmatched formatting control '{control}'.",
                    page_name,
                    byte_offsets[control_lexeme.character_start],
                    byte_offsets[control_lexeme.character_end],
                )
            )
    if open_control is not None:
        invalid_byte_ranges.append((byte_offsets[open_control.character_start], byte_offsets[-1]))
        diagnostics.append(
            _diagnostic(
                "malformed_control",
                f"Unmatched formatting control '{open_control.name}'.",
                page_name,
                byte_offsets[open_control.character_start],
                byte_offsets[open_control.character_end],
            )
        )
    return _ControlParseResult(
        deleted_starts=frozenset(deleted),
        diagnostics=tuple(diagnostics),
        invalid_byte_ranges=tuple(invalid_byte_ranges),
    )


def _copy_operation(
    byte_offsets: tuple[int, ...], character_start: int, character_end: int, output: str
) -> NormalizationOperation:
    return NormalizationOperation(
        "copy", byte_offsets[character_start], byte_offsets[character_end], output
    )


def _append_fragmented_operation(
    *,
    source_text: str,
    byte_offsets: tuple[int, ...],
    lexeme: _Lexeme,
    outer_kind: NormalizationKind,
    deleted_control_starts: frozenset[int],
    operations: list[NormalizationOperation],
) -> int:
    visible_length = 0
    position = lexeme.character_start
    control_starts = tuple(
        control_start
        for control_start in sorted(deleted_control_starts)
        if lexeme.character_start <= control_start and control_start + 2 <= lexeme.character_end
    )
    for control_start in control_starts:
        visible_length += _append_outer_operation(
            source_text=source_text,
            byte_offsets=byte_offsets,
            character_start=position,
            character_end=control_start,
            kind=outer_kind,
            operations=operations,
        )
        operations.append(
            NormalizationOperation(
                "delete_control",
                byte_offsets[control_start],
                byte_offsets[control_start + 2],
                "",
            )
        )
        position = control_start + 2
    visible_length += _append_outer_operation(
        source_text=source_text,
        byte_offsets=byte_offsets,
        character_start=position,
        character_end=lexeme.character_end,
        kind=outer_kind,
        operations=operations,
    )
    return visible_length


def _append_outer_operation(
    *,
    source_text: str,
    byte_offsets: tuple[int, ...],
    character_start: int,
    character_end: int,
    kind: NormalizationKind,
    operations: list[NormalizationOperation],
) -> int:
    if character_start == character_end:
        return 0
    output = source_text[character_start:character_end] if kind == "copy" else ""
    operations.append(
        NormalizationOperation(
            kind,
            byte_offsets[character_start],
            byte_offsets[character_end],
            output,
        )
    )
    return len(output)


def _close_style(
    *,
    page_name: str,
    tag_name: StyleKind,
    byte_start: int,
    byte_end: int,
    open_styles: list[_OpenStyle],
    style_runs: list[StyleRun],
    diagnostics: list[SourceDiagnostic],
    style_ineligible_ranges: list[tuple[int, int]],
    normalized_end: int,
) -> None:
    if open_styles and open_styles[-1].kind == tag_name:
        open_style = open_styles.pop()
        style_runs.append(
            StyleRun(
                tag_name,
                open_style.normalized_start,
                normalized_end,
                open_style.byte_start,
                byte_start,
            )
        )
        return
    diagnostic = _diagnostic(
        "unmatched_style_tag",
        f"Unmatched closing F2 tag '{tag_name}'.",
        page_name,
        byte_start,
        byte_end,
    )
    diagnostics.append(diagnostic)
    style_ineligible_ranges.append((byte_start, byte_end))


def _source_lines(
    *,
    page_name: str,
    source_text: str,
    byte_offsets: tuple[int, ...],
    operations: list[NormalizationOperation],
    matching_ineligible_ranges: list[tuple[int, int]],
    style_ineligible_ranges: list[tuple[int, int]],
) -> tuple[SourceLine, ...]:
    lines: list[SourceLine] = []
    content_start = 0
    ordinal = 0
    position = 0
    while position < len(source_text):
        newline_end = _newline_end(source_text, position)
        if newline_end is None:
            position += 1
            continue
        lines.append(
            _make_line(
                page_name=page_name,
                ordinal=ordinal,
                source_text=source_text,
                byte_offsets=byte_offsets,
                content_start=content_start,
                content_end=position,
                separator_end=newline_end,
                operations=operations,
                matching_ineligible_ranges=matching_ineligible_ranges,
                style_ineligible_ranges=style_ineligible_ranges,
            )
        )
        ordinal += 1
        content_start = newline_end
        position = newline_end
    lines.append(
        _make_line(
            page_name=page_name,
            ordinal=ordinal,
            source_text=source_text,
            byte_offsets=byte_offsets,
            content_start=content_start,
            content_end=len(source_text),
            separator_end=len(source_text),
            operations=operations,
            matching_ineligible_ranges=matching_ineligible_ranges,
            style_ineligible_ranges=style_ineligible_ranges,
        )
    )
    return tuple(lines)


def _make_line(
    *,
    page_name: str,
    ordinal: int,
    source_text: str,
    byte_offsets: tuple[int, ...],
    content_start: int,
    content_end: int,
    separator_end: int,
    operations: list[NormalizationOperation],
    matching_ineligible_ranges: list[tuple[int, int]],
    style_ineligible_ranges: list[tuple[int, int]],
) -> SourceLine:
    byte_start = byte_offsets[content_start]
    content_byte_end = byte_offsets[content_end]
    byte_end = byte_offsets[separator_end]
    operation_ordinals = tuple(
        ordinal
        for ordinal, operation in enumerate(operations)
        if operation.byte_start >= byte_start and operation.byte_end <= byte_end
    )
    visible_text = "".join(
        operations[index].output
        for index in operation_ordinals
        if operations[index].byte_end <= content_byte_end
    )
    matching_eligible = not _overlaps_ranges(
        byte_start, content_byte_end, matching_ineligible_ranges
    )
    style_fitting_eligible = not _overlaps_ranges(
        byte_start, content_byte_end, style_ineligible_ranges
    )
    return SourceLine(
        page_name=page_name,
        ordinal=ordinal,
        byte_start=byte_start,
        byte_end=byte_end,
        content_byte_start=byte_start,
        content_byte_end=content_byte_end,
        separator_byte_start=content_byte_end,
        separator_byte_end=byte_end,
        original_text=source_text[content_start:content_end],
        visible_text=visible_text,
        operation_ordinals=operation_ordinals,
        formatting_span_ids=(),
        continued_block_ids=(),
        matching_eligible=matching_eligible,
        style_fitting_eligible=style_fitting_eligible,
    )


def _diagnostic(
    code: str, message: str, page_name: str, byte_start: int, byte_end: int
) -> SourceDiagnostic:
    return SourceDiagnostic(code, message, page_name, byte_start, byte_end)


def _overlaps_ranges(byte_start: int, byte_end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(
        (start < byte_end and byte_start < end)
        or (start == end and byte_start <= start <= byte_end)
        for start, end in ranges
    )
