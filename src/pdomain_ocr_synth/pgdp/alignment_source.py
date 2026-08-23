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


@dataclass(frozen=True, slots=True)
class _OpenStyle:
    kind: StyleKind
    byte_start: int
    normalized_start: int


def tokenize_source_page(page_name: str, source_text: str) -> TokenizedSourcePage:
    """Tokenize one F2 page without changing its source bytes."""

    source_utf8 = source_text.encode("utf-8")
    byte_offsets = _utf8_offsets(source_text)
    lexemes = _lex(source_text)
    diagnostics: list[SourceDiagnostic] = []
    deleted_controls, control_diagnostics = _valid_controls(
        page_name=page_name,
        lexemes=lexemes,
        byte_offsets=byte_offsets,
    )
    diagnostics.extend(control_diagnostics)
    operations: list[NormalizationOperation] = []
    style_runs: list[StyleRun] = []
    ineligible_ranges: list[tuple[int, int]] = [
        (diagnostic.byte_start, diagnostic.byte_end) for diagnostic in diagnostics
    ]
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
            operations.append(NormalizationOperation("delete_note", byte_start, byte_end, ""))
        elif lexeme.kind == "control":
            if lexeme.character_start in deleted_controls:
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
                operations.append(NormalizationOperation("delete_tag", byte_start, byte_end, ""))
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
                        ineligible_ranges=ineligible_ranges,
                        normalized_end=visible_length,
                    )
                else:
                    open_styles.append(_OpenStyle(tag_name, byte_end, visible_length))
            else:
                output = source_text[lexeme.character_start : lexeme.character_end]
                operations.append(
                    _copy_operation(
                        byte_offsets, lexeme.character_start, lexeme.character_end, output
                    )
                )
                visible_length += len(output)
                diagnostic = _diagnostic(
                    "unknown_tag",
                    f"Unknown F2 tag '{lexeme.name}'.",
                    page_name,
                    byte_start,
                    byte_end,
                )
                diagnostics.append(diagnostic)
                ineligible_ranges.append((byte_start, byte_end))
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
            ineligible_ranges.append((byte_start, byte_end))
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
        ineligible_ranges.append((open_style.byte_start, open_style.byte_start))

    visible_text = "".join(operation.output for operation in operations)
    lines = _source_lines(
        page_name=page_name,
        source_text=source_text,
        byte_offsets=byte_offsets,
        operations=operations,
        ineligible_ranges=ineligible_ranges,
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
    if attribute_text and not attribute_text[0].isspace():
        return _Lexeme("malformed", position, closing_bracket + 1)
    return _Lexeme("tag", position, closing_bracket + 1, name.lower(), closing)


def _valid_controls(
    *,
    page_name: str,
    lexemes: tuple[_Lexeme, ...],
    byte_offsets: tuple[int, ...],
) -> tuple[frozenset[int], tuple[SourceDiagnostic, ...]]:
    deleted: set[int] = set()
    diagnostics: list[SourceDiagnostic] = []
    open_control: _Lexeme | None = None
    open_control_is_valid = True
    for lexeme in lexemes:
        if lexeme.kind != "control" or lexeme.name is None:
            continue
        control = lexeme.name
        if control in _CONTROL_PAIRS:
            if open_control is None:
                open_control = lexeme
                open_control_is_valid = True
            else:
                open_control_is_valid = False
                diagnostics.append(
                    _diagnostic(
                        "malformed_control",
                        f"Nested or overlapping formatting control '{control}'.",
                        page_name,
                        byte_offsets[lexeme.character_start],
                        byte_offsets[lexeme.character_end],
                    )
                )
        elif open_control is not None and _CONTROL_PAIRS[open_control.name or ""] == control:
            if open_control_is_valid:
                deleted.add(open_control.character_start)
                deleted.add(lexeme.character_start)
            open_control = None
        else:
            if open_control is not None:
                open_control_is_valid = False
            diagnostics.append(
                _diagnostic(
                    "malformed_control",
                    f"Unmatched formatting control '{control}'.",
                    page_name,
                    byte_offsets[lexeme.character_start],
                    byte_offsets[lexeme.character_end],
                )
            )
    if open_control is not None:
        diagnostics.append(
            _diagnostic(
                "malformed_control",
                f"Unmatched formatting control '{open_control.name}'.",
                page_name,
                byte_offsets[open_control.character_start],
                byte_offsets[open_control.character_end],
            )
        )
    return frozenset(deleted), tuple(diagnostics)


def _copy_operation(
    byte_offsets: tuple[int, ...], character_start: int, character_end: int, output: str
) -> NormalizationOperation:
    return NormalizationOperation(
        "copy", byte_offsets[character_start], byte_offsets[character_end], output
    )


def _close_style(
    *,
    page_name: str,
    tag_name: StyleKind,
    byte_start: int,
    byte_end: int,
    open_styles: list[_OpenStyle],
    style_runs: list[StyleRun],
    diagnostics: list[SourceDiagnostic],
    ineligible_ranges: list[tuple[int, int]],
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
    ineligible_ranges.append((byte_start, byte_end))


def _source_lines(
    *,
    page_name: str,
    source_text: str,
    byte_offsets: tuple[int, ...],
    operations: list[NormalizationOperation],
    ineligible_ranges: list[tuple[int, int]],
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
                ineligible_ranges=ineligible_ranges,
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
            ineligible_ranges=ineligible_ranges,
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
    ineligible_ranges: list[tuple[int, int]],
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
    style_fitting_eligible = not any(
        start <= content_byte_end and end >= byte_start for start, end in ineligible_ranges
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
        style_fitting_eligible=style_fitting_eligible,
    )


def _diagnostic(
    code: str, message: str, page_name: str, byte_start: int, byte_end: int
) -> SourceDiagnostic:
    return SourceDiagnostic(code, message, page_name, byte_start, byte_end)
