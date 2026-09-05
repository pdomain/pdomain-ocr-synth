"""Resolve what face each cut glyph was printed in, from PGDP's own F2 markup.

A per-character inventory that mixes faces is not one inventory. PGDP transcribes small capitals
in mixed case, so `<sc>Lowther Street</sc>` yields the letters `Lowther Street` and a capital `O`
lands in the lowercase `o` bucket carrying a lowercase label. Nothing that compares a label to a
character can see that, because the character is right and only the letterform is wrong. Italic is
the same problem one degree milder.

The markup is already in the corpus and the tokenizer already parses it: `alignment_source`
produces a `StyleRun` per `<i>`, `<b>` and `<sc>` span with offsets into the page's visible text.
This module reads the same `rounds/F2.json` the alignment read, refuses it unless it hashes to the
`f2_sha256` that alignment recorded, re-derives those runs, and checks every line it uses against
the alignment's own recorded `visible_text` before trusting an offset from it.

`None` and `"roman"` are different answers. `"roman"` means the transcription marks no style on
that glyph. `None` means no style source could be trusted for it, which is every glyph on the
`recognized` tier and every glyph on a page whose lines did not verify.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from pdomain_ocr_synth.pgdp.alignment_source import tokenize_source_page
from pdomain_ocr_synth.pgdp.f2 import load_f2
from pdomain_ocr_synth.pgdp.paths import resolve_project_directory

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

GLYPH_STYLE_METHODS: dict[str, float | int | str] = {
    "algorithm": "f2-style-runs/v1",
    "style_source": "pgdp-f2-markup",
}

ROMAN: Final = "roman"
"""The transcription marks no style on this glyph. Not the same as an unknown style."""

STYLE_NAMES: Final = MappingProxyType(
    {
        "i": "italic",
        "b": "bold",
        "sc": "small_caps",
        "g": "gesperrt",
        "f": "f",
        "tb": "thought_break",
    }
)
"""F2 tag names spelled out. `gesperrt` is letter-spaced setting, which PGDP marks as `<g>`."""

F2_RELATIVE_PATH: Final = "rounds/F2.json"


class GlyphStyleError(ValueError):
    """The F2 source handed to this stage is not the one the alignment report recorded."""


@dataclass(frozen=True, slots=True)
class BookStyle:
    """One book's F2 style spans, keyed by page name and source-line ordinal.

    Spans are half-open character ranges relative to the start of that line's visible text, which
    is the same string the alignment report carries for the line.
    """

    project_id: str
    label: str
    sha256: str
    spans: Mapping[tuple[str, int], tuple[tuple[int, int, str], ...]]
    visible: Mapping[tuple[str, int], str]

    def line_agrees(self, page_name: str, ordinal: int, visible_text: str) -> bool:
        """Whether the re-derived line is the one the alignment report recorded."""

        return self.visible.get((page_name, ordinal)) == visible_text

    def style_at(self, page_name: str, ordinal: int, *, character_offset: int) -> str:
        """The style covering one character of one line, or `roman` when none does."""

        kinds = sorted(
            {
                STYLE_NAMES.get(kind, kind)
                for start, end, kind in self.spans.get((page_name, ordinal), ())
                if start <= character_offset < end
            }
        )
        return "+".join(kinds) if kinds else ROMAN


def read_book_style(corpus_root: str | Path, *, project_id: str, f2_sha256: str) -> BookStyle:
    """Read one book's F2 markup, refusing any file that is not the aligned one.

    The hash is the whole `rounds/F2.json` file's, which is exactly what `alignment.py` records on
    every page of the book, so a changed transcription cannot silently restyle an inventory.
    """

    root = Path(corpus_root).expanduser().resolve()
    project_directory = resolve_project_directory(corpus_root=root, project_id=project_id)
    source = project_directory / F2_RELATIVE_PATH
    try:
        payload = source.read_bytes()
    except OSError as error:
        raise GlyphStyleError(f"Could not read the F2 source: {source}") from error
    digest = sha256(payload).hexdigest()
    if digest != f2_sha256:
        wrong = f"hashes to {digest}, not the aligned {f2_sha256}"
        raise GlyphStyleError(f"F2 source {source.name} {wrong}.")

    parsed = load_f2(source)
    spans: dict[tuple[str, int], tuple[tuple[int, int, str], ...]] = {}
    visible: dict[tuple[str, int], str] = {}
    for parsed_page in parsed.pages:
        page = tokenize_source_page(parsed_page.name, parsed_page.source_text)
        page_name = parsed_page.name
        offsets = _operation_offsets(tuple(len(op.output) for op in page.operations))
        for line in page.lines:
            if not line.operation_ordinals:
                continue
            start = offsets[line.operation_ordinals[0]]
            end = start + len(line.visible_text)
            visible[page_name, line.ordinal] = line.visible_text
            covering = tuple(
                (
                    max(0, run.normalized_start - start),
                    min(end, run.normalized_end) - start,
                    run.kind,
                )
                for run in page.style_runs
                if run.normalized_start < end and run.normalized_end > start
            )
            if covering:
                spans[page_name, line.ordinal] = covering
    return BookStyle(
        project_id=project_id,
        label=source.name,
        sha256=digest,
        spans=MappingProxyType(spans),
        visible=MappingProxyType(visible),
    )


def word_character_offsets(visible_text: str) -> tuple[int, ...]:
    """Where each whitespace-split word starts in the line's own visible text.

    `str.split()` collapses whitespace runs and drops the edges, so the offsets cannot be found by
    counting separators; they are walked instead. The order matches `visible_text.split()`, which
    is the order the word boxes are reconciled in.
    """

    offsets: list[int] = []
    inside = False
    for index, character in enumerate(visible_text):
        if character.isspace():
            inside = False
        elif not inside:
            offsets.append(index)
            inside = True
    return tuple(offsets)


def styles_for_word(
    book_style: BookStyle | None,
    *,
    page_name: str,
    source_ordinal: int,
    visible_text: str,
    word_ordinal: int,
    positions: Sequence[int],
) -> tuple[str | None, ...]:
    """One style per printing-character position of a reconciled word.

    `positions` are the offsets, inside the word, of the characters that were cut. Returns `None`
    for every position when no trusted style source covers this line, so a caller can tell "no
    style marked" from "no style known".
    """

    if book_style is None or not book_style.line_agrees(page_name, source_ordinal, visible_text):
        return tuple(None for _ in positions)
    starts = word_character_offsets(visible_text)
    if word_ordinal >= len(starts):
        return tuple(None for _ in positions)
    word_start = starts[word_ordinal]
    return tuple(
        book_style.style_at(page_name, source_ordinal, character_offset=word_start + position)
        for position in positions
    )


def _operation_offsets(lengths: tuple[int, ...]) -> tuple[int, ...]:
    offsets = [0]
    for length in lengths:
        offsets.append(offsets[-1] + length)
    return tuple(offsets)
