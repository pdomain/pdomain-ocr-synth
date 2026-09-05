"""Harvest one book's glyph inventory from its own scans.

`build_glyph_inventory` reads a shipped `pgdp-alignment/v3` report together with the
`pgdp-profile/v2` profile alignment recorded, rebuilds each accepted page's ink mask, and cuts
glyphs from two places. Words on a line reconciled against F2 give the `transcribed` tier, where
the character is a human proofer's. Words a `geometry-v1` record read outside every matched line
give the `recognized` tier, where PGDP carries no text at all and a DocTR read is the only label
there is. Nothing here runs OCR, opens a font, renders text, or leaves the `source` frame.

The command refuses to start unless the profile hashes to the value the alignment report recorded,
and it refuses an alignment covering more than one book: an inventory is per book because
x-heights run 10 to 18 px across the five corpus books, so a pooled one would be a chimera of
sizes.
"""

from __future__ import annotations

import os
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from pdomain_ocr_synth.pgdp.alignment_image import build_candidate_mask
from pdomain_ocr_synth.pgdp.alignment_models import AlignmentReport
from pdomain_ocr_synth.pgdp.glyph_atlas import render_atlas, write_atlas
from pdomain_ocr_synth.pgdp.glyph_cut import (
    GLYPH_CUT_METHODS,
    crop_to_ink,
    cut_word_glyphs,
)
from pdomain_ocr_synth.pgdp.glyph_furniture import (
    FURNITURE_METHODS,
    page_furniture_words,
    witness_matches_scan,
)
from pdomain_ocr_synth.pgdp.glyph_models import (
    GLYPHS_ALGORITHM_VERSION,
    GLYPHS_MANIFEST_FILENAME,
    GLYPHS_ROWS_FILENAME,
    AtlasSheet,
    CharacterCoverage,
    GlyphManifest,
    GlyphPage,
    GlyphRow,
    render_rows,
)
from pdomain_ocr_synth.pgdp.glyph_quality import (
    GLYPH_QUALITY_METHODS,
    LineBand,
    measure_glyph_quality,
)
from pdomain_ocr_synth.pgdp.glyph_style import (
    GLYPH_STYLE_METHODS,
    BookStyle,
    read_alignment_style,
    styles_for_word,
)
from pdomain_ocr_synth.pgdp.image_measurement import (
    measure_image_snapshot,
    open_image_snapshot,
)
from pdomain_ocr_synth.pgdp.ocr_witness import BookWitness, read_book_witness
from pdomain_ocr_synth.pgdp.ordering import natural_page_key
from pdomain_ocr_synth.pgdp.paths import (
    corpus_relative_path,
    require_canonical_relative_reference,
    resolve_image_candidate,
)
from pdomain_ocr_synth.pgdp.profile_models import ProfileReport
from pdomain_ocr_synth.pgdp.report import write_report
from pdomain_ocr_synth.pgdp.typography import (
    ProvenanceError,
    book_word_gap_threshold,
    matched_lines,
)
from pdomain_ocr_synth.pgdp.typography_measure import (
    TYPOGRAPHY_MEASURE_METHODS,
    WORD_SEGMENTATION_METHODS,
    LineTypographyMeasurement,
    measure_line_typography,
    measure_line_words,
    x_height_gap_threshold,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pdomain_ocr_synth.pgdp.alignment_models import (
        PageAlignment,
        ProjectAlignment,
        WireLineCandidate,
    )
    from pdomain_ocr_synth.pgdp.glyph_furniture import FurnitureWord
    from pdomain_ocr_synth.pgdp.ocr_witness import PageWitness
    from pdomain_ocr_synth.pgdp.profile_models import PageMeasurement, ProjectProfile
    from pdomain_ocr_synth.pgdp.typography_measure import WordGapThreshold

Bounds = tuple[int, int, int, int]
Mask = np.ndarray[tuple[int, int], np.dtype[np.bool]]


@dataclass(frozen=True, slots=True)
class _PageHarvest:
    """One page's rows and tallies, or the reason it yielded none."""

    rows: tuple[GlyphRow, ...] = ()
    reconciled_words: int = 0
    separable_words: int = 0
    furniture_words: int = 0
    word_rejects: Mapping[str, int] = field(default_factory=dict)
    exclusion: str | None = None
    source_path: str | None = None
    furniture_skipped: bool = False


@dataclass(frozen=True, slots=True)
class GlyphHarvest:
    """One book's cut glyphs and everything the manifest needs to describe them."""

    project_id: str
    tool_version: str
    alignment_label: str
    alignment_sha256: str
    profile_label: str
    profile_sha256: str
    methods: Mapping[str, object]
    thresholds: Mapping[str, object]
    rows: tuple[GlyphRow, ...] = ()
    pages: tuple[GlyphPage, ...] = ()
    accepted_page_count: int = 0
    harvested_page_count: int = 0
    reconciled_word_count: int = 0
    separable_word_count: int = 0
    furniture_word_count: int = 0
    quality_flag_counts: Mapping[str, int] = field(default_factory=dict)
    word_reject_counts: Mapping[str, int] = field(default_factory=dict)
    page_exclusion_counts: Mapping[str, int] = field(default_factory=dict)
    geometry_label: str | None = None
    geometry_sha256: str | None = None
    ocr_recognizer: Mapping[str, str] | None = None
    styled_line_count: int = 0
    furniture_skipped_page_count: int = 0

    def render(self) -> str:
        return render_rows(self.rows)

    def manifest(
        self,
        *,
        rows_label: str,
        rows_sha256: str,
        atlas: Sequence[AtlasSheet] = (),
    ) -> GlyphManifest:
        """The manifest describing this harvest, once its rows have been written and hashed."""

        counts: Counter[tuple[str, str | None, str]] = Counter()
        for row in self.rows:
            counts[row.label_tier, row.label_style, row.character] += 1
        by_tier: Counter[str] = Counter()
        by_style: Counter[str] = Counter()
        for (tier, style, _), count in counts.items():
            by_tier[tier] += count
            by_style[style or "unknown"] += count
        return GlyphManifest(
            tool_version=self.tool_version,
            project_id=self.project_id,
            alignment_label=self.alignment_label,
            alignment_sha256=self.alignment_sha256,
            profile_label=self.profile_label,
            profile_sha256=self.profile_sha256,
            rows_label=rows_label,
            rows_sha256=rows_sha256,
            methods=self.methods,
            thresholds=self.thresholds,
            accepted_page_count=self.accepted_page_count,
            harvested_page_count=self.harvested_page_count,
            reconciled_word_count=self.reconciled_word_count,
            separable_word_count=self.separable_word_count,
            furniture_word_count=self.furniture_word_count,
            glyph_count_by_tier=dict(by_tier),
            coverage=tuple(
                CharacterCoverage(
                    character=character,
                    label_tier="recognized" if tier == "recognized" else "transcribed",
                    glyph_count=count,
                    label_style=style,
                )
                for (tier, style, character), count in counts.items()
            ),
            quality_flag_counts=self.quality_flag_counts,
            word_reject_counts=self.word_reject_counts,
            page_exclusion_counts=self.page_exclusion_counts,
            pages=self.pages,
            atlas=tuple(atlas),
            geometry_label=self.geometry_label,
            geometry_sha256=self.geometry_sha256,
            ocr_recognizer=self.ocr_recognizer,
            extensions={
                "furniture_skipped_page_count": self.furniture_skipped_page_count,
                "glyph_count_by_style": dict(sorted(by_style.items())),
                "styled_line_count": self.styled_line_count,
            },
        )


def build_glyph_inventory(
    corpus_root: str | Path,
    alignment_path: str | Path,
    profile_path: str | Path,
    *,
    tool_version: str,
    geometry_path: str | Path | None = None,
) -> GlyphHarvest:
    """Cut every glyph one book's accepted pages yield, on both label tiers."""

    root = Path(corpus_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Corpus root is not a directory: {root}")

    alignment_file = Path(alignment_path).expanduser()
    alignment_bytes = _read_bytes(alignment_file, label="alignment report")
    alignment = AlignmentReport.from_json(alignment_bytes)
    if len(alignment.projects) != 1:
        raise ValueError("A glyph inventory covers exactly one book.")
    project = alignment.projects[0]

    profile_file = Path(profile_path).expanduser()
    profile_bytes = _read_bytes(profile_file, label="profile")
    profile_sha256 = sha256(profile_bytes).hexdigest()
    if profile_sha256 != alignment.profile_sha256:
        raise ProvenanceError(
            "Profile does not match the alignment report's recorded profile_sha256: "
            f"{profile_sha256} != {alignment.profile_sha256}."
        )
    profile = ProfileReport.from_json(profile_bytes)
    project_profile = next(
        (candidate for candidate in profile.projects if candidate.project_id == project.project_id),
        None,
    )
    if project_profile is None:
        raise ValueError(f"Profile carries no project {project.project_id!r}.")

    witness = (
        None
        if geometry_path is None
        else read_book_witness(geometry_path, project_id=project.project_id)
    )
    book_style = read_alignment_style(project)
    gap = book_word_gap_threshold(project)
    return _harvest_project(
        root,
        project=project,
        project_profile=project_profile,
        witness=witness,
        book_style=book_style,
        gap=gap,
        tool_version=tool_version,
        alignment_label=alignment_file.name,
        alignment_sha256=sha256(alignment_bytes).hexdigest(),
        profile_label=alignment.profile_label,
        profile_sha256=profile_sha256,
    )


def _harvest_project(
    root: Path,
    *,
    project: ProjectAlignment,
    project_profile: ProjectProfile,
    witness: BookWitness | None,
    book_style: BookStyle,
    gap: WordGapThreshold,
    tool_version: str,
    alignment_label: str,
    alignment_sha256: str,
    profile_label: str,
    profile_sha256: str,
) -> GlyphHarvest:
    measurements = {page.page_name: page for page in project_profile.pages}
    rows: list[GlyphRow] = []
    pages: list[GlyphPage] = []
    word_rejects: Counter[str] = Counter()
    exclusions: Counter[str] = Counter()
    accepted = harvested = reconciled = separable = furniture = furniture_skipped = 0
    for page in sorted(project.pages, key=lambda page: natural_page_key(page.page_name)):
        if not page.accepted:
            continue
        accepted += 1
        harvest = _harvest_page(
            root,
            project_id=project.project_id,
            page=page,
            measurement=measurements.get(page.page_name),
            gap=gap,
            page_witness=None if witness is None else witness.page(page.page_name),
            book_style=book_style,
        )
        word_rejects.update(harvest.word_rejects)
        reconciled += harvest.reconciled_words
        separable += harvest.separable_words
        furniture += harvest.furniture_words
        furniture_skipped += int(harvest.furniture_skipped)
        if harvest.exclusion is not None:
            exclusions[harvest.exclusion] += 1
            continue
        harvested += 1
        rows.extend(harvest.rows)
        if harvest.source_path is not None and page.scan_sha256 is not None:
            pages.append(
                GlyphPage(
                    page_name=page.page_name,
                    scan_sha256=page.scan_sha256,
                    source_path=harvest.source_path,
                    glyph_count=len(harvest.rows),
                )
            )
    flags: Counter[str] = Counter()
    for row in rows:
        flags.update(row.flags)
    return GlyphHarvest(
        project_id=project.project_id,
        tool_version=tool_version,
        alignment_label=alignment_label,
        alignment_sha256=alignment_sha256,
        profile_label=profile_label,
        profile_sha256=profile_sha256,
        methods=_methods(witness=witness),
        thresholds=_thresholds(gap, witness=witness),
        rows=tuple(rows),
        pages=tuple(pages),
        accepted_page_count=accepted,
        harvested_page_count=harvested,
        reconciled_word_count=reconciled,
        separable_word_count=separable,
        furniture_word_count=furniture,
        quality_flag_counts=dict(flags),
        word_reject_counts=dict(word_rejects),
        page_exclusion_counts=dict(exclusions),
        geometry_label=None if witness is None else witness.label,
        geometry_sha256=None if witness is None else witness.sha256,
        ocr_recognizer=None if witness is None else witness.recognizer.to_dict(),
        styled_line_count=book_style.styled_line_count,
        furniture_skipped_page_count=furniture_skipped,
    )


def _methods(*, witness: BookWitness | None) -> dict[str, object]:
    methods: dict[str, object] = {
        "algorithm_version": GLYPHS_ALGORITHM_VERSION,
        "line_measurement": TYPOGRAPHY_MEASURE_METHODS["algorithm"],
        "word_segmentation": WORD_SEGMENTATION_METHODS["algorithm"],
        "glyph_cut": GLYPH_CUT_METHODS["algorithm"],
        "glyph_quality": GLYPH_QUALITY_METHODS["algorithm"],
    }
    if witness is not None:
        methods["furniture_selection"] = FURNITURE_METHODS["algorithm"]
    methods["glyph_style"] = GLYPH_STYLE_METHODS["algorithm"]
    return methods


def _thresholds(gap: WordGapThreshold, *, witness: BookWitness | None) -> dict[str, object]:
    sources = [
        TYPOGRAPHY_MEASURE_METHODS,
        WORD_SEGMENTATION_METHODS,
        GLYPH_CUT_METHODS,
        GLYPH_QUALITY_METHODS,
    ]
    if witness is not None:
        sources.append(FURNITURE_METHODS)
    thresholds: dict[str, object] = {
        name: value for source in sources for name, value in source.items() if name != "algorithm"
    }
    thresholds["word_gap_threshold_px"] = gap.threshold_px
    thresholds["word_gap_threshold_rule"] = gap.rule
    return thresholds


def _harvest_page(
    root: Path,
    *,
    project_id: str,
    page: PageAlignment,
    measurement: PageMeasurement | None,
    gap: WordGapThreshold,
    page_witness: PageWitness | None,
    book_style: BookStyle | None,
) -> _PageHarvest:
    if measurement is None:
        return _PageHarvest(exclusion="profile_page_missing")
    source_frame = page.source_frame
    bounds = _foreground_bounds(measurement)
    if source_frame is None or bounds is None:
        return _PageHarvest(exclusion="foreground_bounds_unavailable")
    image_path = _resolve_scan(root, project_id=project_id, measurement=measurement)
    if image_path is None:
        return _PageHarvest(exclusion="image_missing")

    try:
        with open_image_snapshot(image_path) as snapshot:
            if snapshot.sha256 != page.scan_sha256:
                return _PageHarvest(exclusion="scan_hash_mismatch")
            if (
                measure_image_snapshot(snapshot).grayscale_threshold
                != measurement.grayscale_threshold
            ):
                return _PageHarvest(exclusion="mask_mismatch")
            mask, _rejected = build_candidate_mask(
                snapshot, source_frame=source_frame, foreground_bounds=bounds
            )
    except (OSError, ValueError, RuntimeError):
        return _PageHarvest(exclusion="image_unreadable")

    matched = matched_lines(page)
    if _mask_disagrees(mask, matched):
        return _PageHarvest(exclusion="mask_mismatch")

    rows: list[GlyphRow] = []
    rejects: Counter[str] = Counter()
    reconciled = separable = 0
    line_boxes: list[Bounds] = []
    for candidate_ordinal, source_ordinal, candidate, visible_text in matched:
        box = _box(candidate.box)
        line_boxes.append(box)
        measured = measure_line_typography(mask, box)
        if not isinstance(measured, LineTypographyMeasurement):
            continue
        threshold = (
            x_height_gap_threshold(measured.x_height_px)
            if gap.threshold_px is None
            else gap.threshold_px
        )
        words = measure_line_words(
            mask, box, candidate.horizontal_ink_profile, visible_text, threshold
        )
        if not words.words_reconciled:
            continue
        band = LineBand(
            box=box,
            baseline_row_px=measured.baseline_row_px,
            x_height_top_row_px=measured.x_height_top_row_px,
        )
        for word_ordinal, (word, text) in enumerate(
            zip(words.words, visible_text.split(), strict=True)
        ):
            reconciled += 1
            cut = cut_word_glyphs(mask, box=word.box, text=text)
            if cut.reason is not None:
                rejects[f"transcribed:{cut.reason}"] += 1
                continue
            separable += 1
            styles = styles_for_word(
                book_style,
                page_name=page.page_name,
                source_ordinal=source_ordinal,
                visible_text=visible_text,
                word_ordinal=word_ordinal,
                positions=[glyph.ordinal for glyph in cut.glyphs],
            )
            rows.extend(
                _glyph_row(
                    mask,
                    page_name=page.page_name,
                    label_tier="transcribed",
                    line_ordinal=candidate_ordinal,
                    word_ordinal=word_ordinal,
                    character=glyph.character,
                    glyph_ordinal=glyph.ordinal,
                    box=glyph.box,
                    band=band,
                    label_confidence=None,
                    label_style=style,
                    source_line_ordinal=source_ordinal,
                )
                for glyph, style in zip(cut.glyphs, styles, strict=True)
            )

    furniture_rows, furniture_words, furniture_skipped = _harvest_furniture(
        mask,
        page_name=page.page_name,
        scan_sha256=page.scan_sha256,
        page_witness=page_witness,
        matched_line_boxes=line_boxes,
        rejects=rejects,
    )
    rows.extend(furniture_rows)
    return _PageHarvest(
        rows=tuple(rows),
        reconciled_words=reconciled,
        separable_words=separable,
        furniture_words=furniture_words,
        word_rejects=dict(rejects),
        source_path=measurement.source_path,
        furniture_skipped=furniture_skipped,
    )


def _harvest_furniture(
    mask: Mask,
    *,
    page_name: str,
    scan_sha256: str | None,
    page_witness: PageWitness | None,
    matched_line_boxes: Sequence[Bounds],
    rejects: Counter[str],
) -> tuple[tuple[GlyphRow, ...], int, bool]:
    """Cut the running head and the folio, whose only label is the recognizer's read."""

    if page_witness is None or scan_sha256 is None:
        return (), 0, False
    if not witness_matches_scan(page_witness, scan_sha256=scan_sha256):
        return (), 0, True
    words = page_furniture_words(
        page_witness, scan_sha256=scan_sha256, matched_line_boxes=matched_line_boxes
    )
    rows: list[GlyphRow] = []
    for word in words:
        rows.extend(_furniture_rows(mask, page_name=page_name, word=word, rejects=rejects))
    return tuple(rows), len(words), False


def _furniture_rows(
    mask: Mask, *, page_name: str, word: FurnitureWord, rejects: Counter[str]
) -> tuple[GlyphRow, ...]:
    box = _clip(word.box, mask)
    tightened = None if box is None else crop_to_ink(mask, box=box)
    if tightened is None:
        rejects["recognized:no_ink"] += 1
        return ()
    cut = cut_word_glyphs(mask, box=tightened, text=word.text)
    if cut.reason is not None:
        rejects[f"recognized:{cut.reason}"] += 1
        return ()
    return tuple(
        _glyph_row(
            mask,
            page_name=page_name,
            label_tier="recognized",
            line_ordinal=word.line_index,
            word_ordinal=word.word_index,
            character=glyph.character,
            glyph_ordinal=glyph.ordinal,
            box=glyph.box,
            band=None,
            label_confidence=word.confidence,
        )
        for glyph in cut.glyphs
    )


def _glyph_row(
    mask: Mask,
    *,
    page_name: str,
    label_tier: str,
    line_ordinal: int,
    word_ordinal: int,
    character: str,
    glyph_ordinal: int,
    box: Bounds,
    band: LineBand | None,
    label_confidence: float | None,
    label_style: str | None = None,
    source_line_ordinal: int | None = None,
) -> GlyphRow:
    quality = measure_glyph_quality(mask, box=box, line=band)
    return GlyphRow(
        character=character,
        label_tier="recognized" if label_tier == "recognized" else "transcribed",
        page_name=page_name,
        line_ordinal=line_ordinal,
        word_ordinal=word_ordinal,
        glyph_ordinal=glyph_ordinal,
        box=box,
        ink_density=quality.ink_density,
        row_extent_px=quality.row_extent_px,
        top_offset_px=quality.top_offset_px,
        bottom_offset_px=quality.bottom_offset_px,
        flags=quality.flags,
        label_confidence=label_confidence,
        label_style=label_style,
        source_line_ordinal=source_line_ordinal,
    )


def _clip(box: Bounds, mask: Mask) -> Bounds | None:
    """A recognized box clipped to the page, which the recognizer's frame does not guarantee."""

    height, width = mask.shape
    x_start, y_start, x_end, y_end = box
    clipped = (max(0, x_start), max(0, y_start), min(width, x_end), min(height, y_end))
    if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
        return None
    return clipped


def _mask_disagrees(mask: Mask, matched: Sequence[tuple[int, int, WireLineCandidate, str]]) -> bool:
    """Whether the rebuilt mask fails to reproduce any matched candidate's recorded ink.

    The same check `typography.py` makes, for the same reason: a mask that has drifted would place
    every glyph box on ink the alignment stage never saw.
    """

    for _ordinal, _source_ordinal, candidate, _text in matched:
        x_start, y_start, x_end, y_end = _box(candidate.box)
        if int(np.count_nonzero(mask[y_start:y_end, x_start:x_end])) != candidate.foreground_pixels:
            return True
    return False


def _box(value: Sequence[int]) -> Bounds:
    x_start, y_start, x_end, y_end = value
    return x_start, y_start, x_end, y_end


def _foreground_bounds(measurement: PageMeasurement) -> Bounds | None:
    bounds = measurement.foreground_bounds
    if bounds is None or len(bounds) != 4:
        return None
    return _box(bounds)


def _resolve_scan(root: Path, *, project_id: str, measurement: PageMeasurement) -> Path | None:
    try:
        reference = require_canonical_relative_reference(
            value=measurement.source_path, label="source_path"
        )
        path = (root / reference).resolve()
        if not path.is_file() or not path.is_relative_to(root):
            return None
        project_reference = require_canonical_relative_reference(
            value=project_id, label="project reference", direct_child=True
        )
        project_directory = (root / project_reference).resolve()
        if not project_directory.is_dir():
            return None
        resolution = resolve_image_candidate(
            project_directory=project_directory,
            page_name=measurement.page_name,
            corpus_root=root,
        )
        if resolution.image_path is None:
            return None
        expected = corpus_relative_path(path=resolution.image_path, corpus_root=root)
    except (OSError, RuntimeError, ValueError):
        return None
    if measurement.source_path != expected:
        return None
    return resolution.image_path


def _read_bytes(path: Path, *, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise ValueError(f"Could not read the {label}: {path}") from error


def write_glyph_inventory(
    harvest: GlyphHarvest,
    output_dir: str | Path,
    corpus_root: str | Path,
    *,
    atlas: bool = True,
) -> GlyphManifest:
    """Write `glyphs.jsonl`, the per-character atlas, and `manifest.json` into one directory.

    The rows are written first and hashed, so the manifest records the bytes on disk rather than a
    hash of something that was rendered again. The atlas is rendered from those same rows, which
    is what makes re-rendering it a check rather than a repetition.
    """

    directory = Path(output_dir).expanduser().resolve()
    root = Path(corpus_root).expanduser().resolve()
    if directory.is_relative_to(root):
        raise ValueError("Inventory output must be outside the corpus root.")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / ".nobackup").touch()

    rendered = harvest.render().encode("utf-8")
    _write_bytes(directory / GLYPHS_ROWS_FILENAME, rendered)
    sheets = (
        write_atlas(render_atlas(harvest.rows, corpus_root=root, pages=harvest.pages), directory)
        if atlas
        else ()
    )
    manifest = harvest.manifest(
        rows_label=GLYPHS_ROWS_FILENAME,
        rows_sha256=sha256(rendered).hexdigest(),
        atlas=sheets,
    )
    write_report(manifest, directory / GLYPHS_MANIFEST_FILENAME, root)
    return manifest


def _write_bytes(path: Path, payload: bytes) -> None:
    """Write one file atomically, so a killed run leaves no half-written inventory."""

    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            _ = temporary_file.write(payload)
            temporary_file.flush()
            _ = os.fsync(temporary_file.fileno())
        _ = temporary_path.replace(path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
