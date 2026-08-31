"""Extract conservative source-frame scan line candidates for PGDP alignment."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from statistics import median
from typing import TYPE_CHECKING, Literal

import numpy as np
from PIL import Image

from pdomain_ocr_synth.pgdp.image_measurement import SnapshotReplayFile, measure_image_snapshot

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pdomain_ocr_synth.pgdp.image_measurement import ImageSnapshot
    from pdomain_ocr_synth.pgdp.profile_models import CoordinateFrame, InkBand, ProfileDiagnostic


Bounds = tuple[int, int, int, int]
RejectionReason = Literal[
    "empty_band",
    "fragmented_band",
    "long_horizontal_rule",
    "minor_ink_cluster",
    "page_border",
]

ALIGNMENT_IMAGE_METHODS: dict[str, float | int | str] = {
    "algorithm": "source-frame-components/v2",
    "connectivity": 8,
    "minimum_ink_bands": 2,
    "page_border_edges": 3,
    "long_rule_minimum_width_ratio": 0.8,
    "long_rule_maximum_height_ratio": 0.02,
    "join_minimum_vertical_overlap_ratio": 0.4,
    "join_maximum_vertical_center_distance_ratio": 0.6,
    "join_maximum_horizontal_gap_median_height_ratio": 2.0,
    "merge_horizontally_overlapping_clusters": True,
    "fragmented_band_minor_ink_share": 0.02,
    "fragmented_band_maximum_rate": 0.35,
    "gutter_minimum_width_ratio": 0.03,
    "gutter_minimum_vertical_coverage_ratio": 0.6,
}

_MINIMUM_INK_BANDS = 2
_PAGE_BORDER_EDGES = 3
_LONG_RULE_MINIMUM_WIDTH_PERCENT = 80
_LONG_RULE_MAXIMUM_HEIGHT_PERCENT = 2
_JOIN_MINIMUM_VERTICAL_OVERLAP_PERCENT = 40
_JOIN_MAXIMUM_CENTER_DISTANCE_TENTHS = 12
_JOIN_MAXIMUM_HORIZONTAL_GAP_MEDIAN_HEIGHT_FACTOR = 2
_FRAGMENTED_BAND_MINOR_INK_PERCENT = 2
_FRAGMENTED_BAND_MAXIMUM_RATE_PERCENT = 35
_GUTTER_MINIMUM_WIDTH_PERCENT = 3
_GUTTER_MINIMUM_VERTICAL_COVERAGE_TENTHS = 6
_PASSTHROUGH_DIAGNOSTICS = frozenset(
    {
        "blank_page",
        "border_dominated",
        "foreground_bounds_unavailable",
        "high_foreground_ratio",
        "image_decode_failed",
        "image_missing",
        "image_unreadable",
    }
)


@dataclass(frozen=True, slots=True)
class LineCandidate:
    """One conservative source-frame visual-line candidate."""

    band_ordinal: int
    box: Bounds
    component_ordinal: int
    component_count: int
    foreground_pixels: int
    width: int
    height: int
    fill_ratio: float
    horizontal_ink_profile: tuple[float, ...]

    def __post_init__(self) -> None:
        _require_nonnegative_integer(self.band_ordinal, name="band_ordinal")
        _require_nonnegative_integer(self.component_ordinal, name="component_ordinal")
        _require_box(self.box, allow_empty=False)
        _require_nonnegative_integer(self.component_count, name="component_count")
        if self.component_count == 0:
            raise ValueError("Line candidates require at least one component.")
        _require_nonnegative_integer(self.foreground_pixels, name="foreground_pixels")
        if self.foreground_pixels == 0:
            raise ValueError("Line candidates require foreground pixels.")
        if self.width != self.box[2] - self.box[0] or self.height != self.box[3] - self.box[1]:
            raise ValueError("Line candidate dimensions must match its box.")
        if not math.isfinite(self.fill_ratio) or not 0.0 < self.fill_ratio <= 1.0:
            raise ValueError("Line candidate fill_ratio must be in (0, 1].")
        if len(self.horizontal_ink_profile) != self.width:
            raise ValueError("Line candidate profile length must match its width.")
        if any(not math.isfinite(value) or value < 0.0 for value in self.horizontal_ink_profile):
            raise ValueError("Line candidate profile values must be finite and nonnegative.")
        if not math.isclose(sum(self.horizontal_ink_profile), 1.0, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Line candidate profile must sum to one.")


@dataclass(frozen=True, slots=True)
class RejectedComponent:
    """A component or cluster withheld from alignment candidate output."""

    reason: RejectionReason
    box: Bounds
    foreground_pixels: int
    band_ordinal: int | None = None
    component_ordinal: int | None = None

    def __post_init__(self) -> None:
        _require_box(self.box, allow_empty=True)
        _require_nonnegative_integer(self.foreground_pixels, name="foreground_pixels")
        if self.band_ordinal is not None:
            _require_nonnegative_integer(self.band_ordinal, name="band_ordinal")
        if self.component_ordinal is not None:
            _require_nonnegative_integer(self.component_ordinal, name="component_ordinal")


@dataclass(frozen=True, slots=True)
class Gutter:
    """One persistent vertical whitespace interval within candidate evidence."""

    box: Bounds
    vertical_coverage: float

    def __post_init__(self) -> None:
        _require_box(self.box, allow_empty=False)
        if not math.isfinite(self.vertical_coverage) or not 0.0 <= self.vertical_coverage <= 1.0:
            raise ValueError("Gutter vertical_coverage must be in [0, 1].")


@dataclass(frozen=True, slots=True)
class CandidateExtraction:
    """Candidates, exclusions, and raw rejection evidence for one scan snapshot."""

    source_sha256: str
    source_frame: CoordinateFrame
    candidates: tuple[LineCandidate, ...] = ()
    rejected: tuple[RejectedComponent, ...] = ()
    gutter: Gutter | None = None
    probable_multi_column: bool = False
    exclusions: tuple[str, ...] = ()
    inherited_diagnostics: tuple[ProfileDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        if len(self.source_sha256) != 64:
            raise ValueError("source_sha256 must be a SHA-256 digest.")
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "rejected", tuple(self.rejected))
        object.__setattr__(self, "exclusions", tuple(self.exclusions))
        object.__setattr__(self, "inherited_diagnostics", tuple(self.inherited_diagnostics))
        if self.probable_multi_column != (self.gutter is not None):
            raise ValueError("A probable multi-column result requires exactly one gutter record.")


@dataclass(frozen=True, slots=True)
class _Run:
    """A half-open foreground run in one raster row."""

    y: int
    x_start: int
    x_end: int
    label: int


@dataclass(frozen=True, slots=True)
class Component:
    """A labeled connected component backed by source-mask runs."""

    ordinal: int
    label: int
    box: Bounds
    foreground_pixels: int

    @property
    def width(self) -> int:
        return self.box[2] - self.box[0]

    @property
    def height(self) -> int:
        return self.box[3] - self.box[1]


@dataclass(frozen=True, slots=True)
class _LabeledComponents:
    """Components and the source runs needed to clear selected labels."""

    components: tuple[Component, ...]
    runs: tuple[_Run, ...]


@dataclass(frozen=True, slots=True)
class _BandCounts:
    """How many bands were measurable, and how many of those stayed fragmented."""

    measured: int
    fragmented: int

    @property
    def exceeds_maximum_rate(self) -> bool:
        """Whether the fragmented share is past the version 2 page limit.

        A page with no measurable band has no rate. It is excluded by the
        `insufficient_ink_bands` and `empty_band` paths instead.
        """

        if self.measured == 0:
            return False
        return self.fragmented * 100 > self.measured * _FRAGMENTED_BAND_MAXIMUM_RATE_PERCENT


@dataclass(frozen=True, slots=True)
class _Cluster:
    """One join-compatible cluster within an M15a ink band."""

    box: Bounds
    component_ordinal: int
    component_count: int
    foreground_pixels: int


class _DisjointSet:
    """Small deterministic union-find used to join components into line clusters."""

    def __init__(self) -> None:
        self._parents: list[int] = []

    def add(self) -> int:
        label = len(self._parents)
        self._parents.append(label)
        return label

    def find(self, label: int) -> int:
        parent = self._parents[label]
        while parent != self._parents[parent]:
            parent = self._parents[parent]
        while label != parent:
            next_label = self._parents[label]
            self._parents[label] = parent
            label = next_label
        return parent

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            self._parents[right_root] = left_root
        else:
            self._parents[left_root] = right_root


def extract_line_candidates(
    snapshot: ImageSnapshot,
    *,
    source_frame: CoordinateFrame,
    foreground_bounds: Bounds | None,
    ink_bands: Sequence[InkBand] | None,
    diagnostics: Sequence[ProfileDiagnostic] = (),
) -> CandidateExtraction:
    """Extract conservative line candidates from one immutable scan snapshot.

    The source frame, bounds, bands, and diagnostics are the M15a evidence for this
    same page. The caller owns the live-file rehash after this snapshot closes.
    """

    inherited_diagnostics = tuple(diagnostics)
    inherited_exclusions = _inherited_exclusions(inherited_diagnostics)
    if inherited_exclusions:
        return _empty_extraction(
            snapshot=snapshot,
            source_frame=source_frame,
            exclusions=inherited_exclusions,
            inherited_diagnostics=inherited_diagnostics,
        )
    if foreground_bounds is None or not _is_valid_box(foreground_bounds, source_frame):
        return _empty_extraction(
            snapshot=snapshot,
            source_frame=source_frame,
            exclusions=("foreground_bounds_unavailable",),
            inherited_diagnostics=inherited_diagnostics,
        )
    retained_bands = tuple(ink_bands or ())
    if len(retained_bands) < _MINIMUM_INK_BANDS:
        return _empty_extraction(
            snapshot=snapshot,
            source_frame=source_frame,
            exclusions=("insufficient_ink_bands",),
            inherited_diagnostics=inherited_diagnostics,
        )

    foreground = _foreground_mask(snapshot, source_frame)
    if not bool(foreground.any()):
        return _empty_extraction(
            snapshot=snapshot,
            source_frame=source_frame,
            exclusions=("blank_page",),
            inherited_diagnostics=inherited_diagnostics,
        )
    rejected: list[RejectedComponent] = []
    _remove_page_borders(foreground, rejected)
    _remove_long_rules(foreground, foreground_bounds, rejected)
    candidates, band_rejections, clusters, band_counts = _extract_band_candidates(
        foreground,
        retained_bands,
        source_frame=source_frame,
        foreground_bounds=foreground_bounds,
    )
    rejected.extend(band_rejections)
    gutter = _find_gutter(foreground, foreground_bounds, clusters)
    exclusions: list[str] = []
    if band_counts.exceeds_maximum_rate:
        exclusions.append("fragmented_band")
        candidates = ()
    if gutter is not None:
        exclusions.append("probable_multi_column")
    rejected.sort(
        key=lambda item: (item.reason, item.band_ordinal is None, item.band_ordinal, item.box)
    )
    return CandidateExtraction(
        source_sha256=snapshot.sha256,
        source_frame=source_frame,
        candidates=tuple(candidates),
        rejected=tuple(rejected),
        gutter=gutter,
        probable_multi_column=gutter is not None,
        exclusions=tuple(exclusions),
        inherited_diagnostics=inherited_diagnostics,
    )


def _empty_extraction(
    *,
    snapshot: ImageSnapshot,
    source_frame: CoordinateFrame,
    exclusions: tuple[str, ...],
    inherited_diagnostics: tuple[ProfileDiagnostic, ...],
) -> CandidateExtraction:
    return CandidateExtraction(
        source_sha256=snapshot.sha256,
        source_frame=source_frame,
        exclusions=exclusions,
        inherited_diagnostics=inherited_diagnostics,
    )


def _inherited_exclusions(diagnostics: Sequence[ProfileDiagnostic]) -> tuple[str, ...]:
    mapped: list[str] = []
    for diagnostic in diagnostics:
        if diagnostic.code in {"one_ink_band", "no_ink_bands"}:
            code = "insufficient_ink_bands"
        elif diagnostic.code in _PASSTHROUGH_DIAGNOSTICS:
            code = diagnostic.code
        else:
            code = "inherited_profile_diagnostic"
        if code not in mapped:
            mapped.append(code)
    return tuple(mapped)


def _foreground_mask(
    snapshot: ImageSnapshot, source_frame: CoordinateFrame
) -> np.ndarray[tuple[int, int], np.dtype[np.bool]]:
    measured = measure_image_snapshot(snapshot)
    if (
        measured.source_frame.width != source_frame.width
        or measured.source_frame.height != source_frame.height
    ):
        raise ValueError("Snapshot dimensions do not match the M15a source frame.")
    source_file = SnapshotReplayFile(snapshot.source_file)
    _ = source_file.seek(0)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source_file) as image, _candidate_grayscale(image) as grayscale_image:
                grayscale = np.asarray(grayscale_image, dtype=np.uint8)
                return grayscale <= measured.grayscale_threshold
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError("Image rejected as a decompression bomb.") from error


def _candidate_grayscale(image: Image.Image) -> Image.Image:
    if image.mode in {"LA", "RGBA"} or "transparency" in image.info:
        with (
            image.convert("RGBA") as rgba,
            Image.new("RGBA", image.size, color=(255, 255, 255, 255)) as white,
            Image.alpha_composite(white, rgba) as composite,
        ):
            return composite.convert("L")
    return image.convert("L")


def _remove_page_borders(
    foreground: np.ndarray[tuple[int, int], np.dtype[np.bool]], rejected: list[RejectedComponent]
) -> None:
    labeled = _label_components(foreground)
    height, width = foreground.shape
    labels_to_clear: set[int] = set()
    for component in labeled.components:
        edge_count = sum(
            (
                component.box[0] == 0,
                component.box[1] == 0,
                component.box[2] == width,
                component.box[3] == height,
            )
        )
        if edge_count >= _PAGE_BORDER_EDGES:
            labels_to_clear.add(component.label)
            rejected.append(
                RejectedComponent(
                    reason="page_border",
                    box=component.box,
                    foreground_pixels=component.foreground_pixels,
                    component_ordinal=component.ordinal,
                )
            )
    _clear_labels(foreground, labeled.runs, labels_to_clear)


def _remove_long_rules(
    foreground: np.ndarray[tuple[int, int], np.dtype[np.bool]],
    foreground_bounds: Bounds,
    rejected: list[RejectedComponent],
) -> None:
    labeled = _label_components(foreground)
    foreground_width = foreground_bounds[2] - foreground_bounds[0]
    foreground_height = foreground_bounds[3] - foreground_bounds[1]
    labels_to_clear: set[int] = set()
    for component in labeled.components:
        if (
            component.width * 100 > foreground_width * _LONG_RULE_MINIMUM_WIDTH_PERCENT
            and component.height * 100 < foreground_height * _LONG_RULE_MAXIMUM_HEIGHT_PERCENT
        ):
            labels_to_clear.add(component.label)
            rejected.append(
                RejectedComponent(
                    reason="long_horizontal_rule",
                    box=component.box,
                    foreground_pixels=component.foreground_pixels,
                    component_ordinal=component.ordinal,
                )
            )
    _clear_labels(foreground, labeled.runs, labels_to_clear)


def _extract_band_candidates(
    foreground: np.ndarray[tuple[int, int], np.dtype[np.bool]],
    ink_bands: Sequence[InkBand],
    *,
    source_frame: CoordinateFrame,
    foreground_bounds: Bounds,
) -> tuple[list[LineCandidate], list[RejectedComponent], tuple[_Cluster, ...], _BandCounts]:
    candidates: list[LineCandidate] = []
    rejected: list[RejectedComponent] = []
    all_clusters: list[_Cluster] = []
    measured_bands = 0
    fragmented_bands = 0
    for band_ordinal, band in enumerate(ink_bands):
        if band.y_start < 0 or band.y_end > source_frame.height:
            return (
                [],
                [
                    RejectedComponent(
                        reason="empty_band",
                        box=(foreground_bounds[0], band.y_start, foreground_bounds[0], band.y_end),
                        foreground_pixels=0,
                        band_ordinal=band_ordinal,
                    )
                ],
                (),
                _BandCounts(measured=0, fragmented=0),
            )
        band_mask = foreground[band.y_start : band.y_end].copy()
        labeled = _label_components(band_mask)
        if not labeled.components:
            rejected.append(
                RejectedComponent(
                    reason="empty_band",
                    box=(foreground_bounds[0], band.y_start, foreground_bounds[0], band.y_end),
                    foreground_pixels=0,
                    band_ordinal=band_ordinal,
                )
            )
            continue
        components = tuple(
            Component(
                ordinal=component.ordinal,
                label=component.label,
                box=(
                    component.box[0],
                    component.box[1] + band.y_start,
                    component.box[2],
                    component.box[3] + band.y_start,
                ),
                foreground_pixels=component.foreground_pixels,
            )
            for component in labeled.components
        )
        clusters = merge_horizontally_overlapping_clusters(join_components(components))
        counted, minor = drop_minor_ink_clusters(clusters)
        all_clusters.extend(counted)
        rejected.extend(
            RejectedComponent(
                reason="minor_ink_cluster",
                box=cluster.box,
                foreground_pixels=cluster.foreground_pixels,
                band_ordinal=band_ordinal,
                component_ordinal=cluster.component_ordinal,
            )
            for cluster in minor
        )
        measured_bands += 1
        if len(counted) != 1:
            fragmented_bands += 1
            rejected.extend(
                RejectedComponent(
                    reason="fragmented_band",
                    box=cluster.box,
                    foreground_pixels=cluster.foreground_pixels,
                    band_ordinal=band_ordinal,
                    component_ordinal=cluster.component_ordinal,
                )
                for cluster in counted
            )
        cluster = max(counted, key=lambda item: (item.foreground_pixels, -item.component_ordinal))
        candidate_mask = foreground[
            cluster.box[1] : cluster.box[3], cluster.box[0] : cluster.box[2]
        ]
        column_counts = tuple(
            int(np.count_nonzero(candidate_mask[:, column_index]))
            for column_index in range(cluster.box[2] - cluster.box[0])
        )
        candidates.append(
            LineCandidate(
                band_ordinal=band_ordinal,
                box=cluster.box,
                component_ordinal=cluster.component_ordinal,
                component_count=cluster.component_count,
                foreground_pixels=cluster.foreground_pixels,
                width=cluster.box[2] - cluster.box[0],
                height=cluster.box[3] - cluster.box[1],
                fill_ratio=cluster.foreground_pixels
                / ((cluster.box[2] - cluster.box[0]) * (cluster.box[3] - cluster.box[1])),
                horizontal_ink_profile=tuple(
                    int(count) / cluster.foreground_pixels for count in column_counts
                ),
            )
        )
    candidates.sort(key=lambda item: (item.band_ordinal, item.box, item.component_ordinal))
    return (
        candidates,
        rejected,
        tuple(all_clusters),
        _BandCounts(measured=measured_bands, fragmented=fragmented_bands),
    )


def join_components(components: Sequence[Component]) -> tuple[_Cluster, ...]:
    if not components:
        return ()
    ordered = tuple(sorted(components, key=lambda item: (item.box, item.ordinal)))
    median_height = median(component.height for component in ordered)
    maximum_gap = _JOIN_MAXIMUM_HORIZONTAL_GAP_MEDIAN_HEIGHT_FACTOR * median_height
    joined = _DisjointSet()
    labels = [joined.add() for _ in ordered]
    for index, component in enumerate(ordered):
        for later_index in range(index + 1, len(ordered)):
            later = ordered[later_index]
            if later.box[0] - component.box[2] > maximum_gap:
                break
            if _components_are_joinable(component, later, maximum_gap=maximum_gap):
                joined.union(labels[index], labels[later_index])
    grouped: dict[int, list[Component]] = {}
    for label, component in zip(labels, ordered, strict=True):
        grouped.setdefault(joined.find(label), []).append(component)
    clusters = tuple(_cluster(group) for _, group in sorted(grouped.items()))
    return tuple(sorted(clusters, key=lambda item: (item.box, item.component_ordinal)))


def merge_horizontally_overlapping_clusters(
    clusters: Sequence[_Cluster],
) -> tuple[_Cluster, ...]:
    """Union clusters whose horizontal ranges overlap.

    Clusters that overlap in x cannot be separate columns or separate words, so a
    band that splits them apart split one visual line. Overlap is transitive here:
    a chain of overlapping clusters becomes one cluster even when its ends do not
    overlap each other.
    """

    if not clusters:
        return ()
    ordered = tuple(sorted(clusters, key=lambda item: (item.box, item.component_ordinal)))
    merged = _DisjointSet()
    labels = [merged.add() for _ in ordered]
    for index, cluster in enumerate(ordered):
        for later_index in range(index + 1, len(ordered)):
            later = ordered[later_index]
            if later.box[0] >= cluster.box[2]:
                break
            merged.union(labels[index], labels[later_index])
    grouped: dict[int, list[_Cluster]] = {}
    for label, cluster in zip(labels, ordered, strict=True):
        grouped.setdefault(merged.find(label), []).append(cluster)
    return tuple(
        sorted(
            (_merge_clusters(group) for _, group in sorted(grouped.items())),
            key=lambda item: (item.box, item.component_ordinal),
        )
    )


def drop_minor_ink_clusters(
    clusters: Sequence[_Cluster],
) -> tuple[tuple[_Cluster, ...], tuple[_Cluster, ...]]:
    """Split clusters into the ones that count and the negligible-ink ones.

    A comma, an accent, a speck of dust, or a broken serif can miss the join rule
    and stand alone. Counting it as a second cluster would fragment an ordinary
    text row, so it is set aside. It is returned rather than discarded, and the
    caller records it as evidence. When every cluster falls below the share, the
    band keeps all of them: that band really is fragmented.
    """

    ordered = tuple(clusters)
    total = sum(cluster.foreground_pixels for cluster in ordered)
    if total <= 0:
        return ordered, ()
    counted = tuple(
        cluster
        for cluster in ordered
        if cluster.foreground_pixels * 100 >= total * _FRAGMENTED_BAND_MINOR_INK_PERCENT
    )
    if not counted:
        return ordered, ()
    minor = tuple(cluster for cluster in ordered if cluster not in counted)
    return counted, minor


def _merge_clusters(clusters: Sequence[_Cluster]) -> _Cluster:
    if len(clusters) == 1:
        return clusters[0]
    return _Cluster(
        box=(
            min(cluster.box[0] for cluster in clusters),
            min(cluster.box[1] for cluster in clusters),
            max(cluster.box[2] for cluster in clusters),
            max(cluster.box[3] for cluster in clusters),
        ),
        component_ordinal=min(cluster.component_ordinal for cluster in clusters),
        component_count=sum(cluster.component_count for cluster in clusters),
        foreground_pixels=sum(cluster.foreground_pixels for cluster in clusters),
    )


def _components_are_joinable(left: Component, right: Component, *, maximum_gap: float) -> bool:
    vertical_overlap = max(0, min(left.box[3], right.box[3]) - max(left.box[1], right.box[1]))
    smaller_height = min(left.height, right.height)
    if vertical_overlap * 100 < smaller_height * _JOIN_MINIMUM_VERTICAL_OVERLAP_PERCENT:
        return False
    center_distance_twice = abs((left.box[1] + left.box[3]) - (right.box[1] + right.box[3]))
    if (
        center_distance_twice * 10
        > max(left.height, right.height) * _JOIN_MAXIMUM_CENTER_DISTANCE_TENTHS
    ):
        return False
    horizontal_gap = max(0, right.box[0] - left.box[2], left.box[0] - right.box[2])
    return horizontal_gap <= maximum_gap


def _cluster(components: Sequence[Component]) -> _Cluster:
    return _Cluster(
        box=(
            min(component.box[0] for component in components),
            min(component.box[1] for component in components),
            max(component.box[2] for component in components),
            max(component.box[3] for component in components),
        ),
        component_ordinal=min(component.ordinal for component in components),
        component_count=len(components),
        foreground_pixels=sum(component.foreground_pixels for component in components),
    )


def _find_gutter(
    foreground: np.ndarray[tuple[int, int], np.dtype[np.bool]],
    foreground_bounds: Bounds,
    clusters: Sequence[_Cluster],
) -> Gutter | None:
    if not clusters:
        return None
    y_start = min(cluster.box[1] for cluster in clusters)
    y_end = max(cluster.box[3] for cluster in clusters)
    extent_height = y_end - y_start
    if extent_height == 0:
        return None
    x_start, _, x_end, _ = foreground_bounds
    interior = foreground[y_start:y_end, x_start:x_end]
    active_rows = interior.any(axis=1)
    active_height = int(np.count_nonzero(active_rows))
    if active_height == 0:
        return None
    occupied_rows = interior[active_rows]
    empty_columns = tuple(
        int(np.count_nonzero(~occupied_rows[:, column_index])) * 10
        >= active_height * _GUTTER_MINIMUM_VERTICAL_COVERAGE_TENTHS
        for column_index in range(x_end - x_start)
    )
    minimum_width = math.ceil((x_end - x_start) * _GUTTER_MINIMUM_WIDTH_PERCENT / 100)
    gutters: list[Gutter] = []
    run_start: int | None = None
    for index, is_empty in enumerate(empty_columns):
        if bool(is_empty) and run_start is None:
            run_start = index
        if not bool(is_empty) and run_start is not None:
            _append_gutter(
                gutters,
                interior,
                x_start=x_start,
                y_start=y_start,
                y_end=y_end,
                run_start=run_start,
                run_end=index,
                minimum_width=minimum_width,
            )
            run_start = None
    if run_start is not None:
        _append_gutter(
            gutters,
            interior,
            x_start=x_start,
            y_start=y_start,
            y_end=y_end,
            run_start=run_start,
            run_end=len(empty_columns),
            minimum_width=minimum_width,
        )
    if not gutters:
        return None
    return min(gutters, key=lambda item: (-(item.box[2] - item.box[0]), item.box))


def _append_gutter(
    gutters: list[Gutter],
    interior: np.ndarray[tuple[int, int], np.dtype[np.bool]],
    *,
    x_start: int,
    y_start: int,
    y_end: int,
    run_start: int,
    run_end: int,
    minimum_width: int,
) -> None:
    if run_start == 0 or run_end == interior.shape[1] or run_end - run_start < minimum_width:
        return
    empty_pixels = int(np.count_nonzero(~interior[:, run_start:run_end]))
    area = (y_end - y_start) * (run_end - run_start)
    gutters.append(
        Gutter(
            box=(x_start + run_start, y_start, x_start + run_end, y_end),
            vertical_coverage=empty_pixels / area,
        )
    )


def _label_components(
    foreground: np.ndarray[tuple[int, int], np.dtype[np.bool]],
) -> _LabeledComponents:
    labels = _DisjointSet()
    runs: list[_Run] = []
    previous_runs: list[_Run] = []
    for y_index in range(foreground.shape[0]):
        row_runs: list[_Run] = []
        run_start: int | None = None
        for x_index in range(foreground.shape[1] + 1):
            is_foreground = x_index < foreground.shape[1] and bool(foreground[y_index, x_index])
            if is_foreground and run_start is None:
                run_start = x_index
                continue
            if is_foreground or run_start is None:
                continue
            label = labels.add()
            run = _Run(y=y_index, x_start=run_start, x_end=x_index, label=label)
            row_runs.append(run)
            run_start = None
        previous_index = 0
        for run in row_runs:
            while (
                previous_index < len(previous_runs)
                and previous_runs[previous_index].x_end < run.x_start
            ):
                previous_index += 1
            overlap_index = previous_index
            while (
                overlap_index < len(previous_runs)
                and previous_runs[overlap_index].x_start <= run.x_end
            ):
                labels.union(run.label, previous_runs[overlap_index].label)
                overlap_index += 1
        runs.extend(row_runs)
        previous_runs = row_runs
    grouped: dict[int, list[_Run]] = {}
    for run in runs:
        grouped.setdefault(labels.find(run.label), []).append(run)
    unordered = [
        (
            label,
            (
                min(run.x_start for run in group),
                min(run.y for run in group),
                max(run.x_end for run in group),
                max(run.y for run in group) + 1,
            ),
            sum(run.x_end - run.x_start for run in group),
        )
        for label, group in grouped.items()
    ]
    unordered.sort(key=lambda item: (item[1], item[0]))
    return _LabeledComponents(
        components=tuple(
            Component(
                ordinal=ordinal,
                label=label,
                box=box,
                foreground_pixels=foreground_pixels,
            )
            for ordinal, (label, box, foreground_pixels) in enumerate(unordered)
        ),
        runs=tuple(
            _Run(y=run.y, x_start=run.x_start, x_end=run.x_end, label=labels.find(run.label))
            for run in runs
        ),
    )


def _clear_labels(
    foreground: np.ndarray[tuple[int, int], np.dtype[np.bool]],
    runs: Sequence[_Run],
    labels_to_clear: set[int],
) -> None:
    if not labels_to_clear:
        return
    for run in runs:
        if run.label in labels_to_clear:
            foreground[run.y, run.x_start : run.x_end] = False


def _is_valid_box(box: Bounds, source_frame: CoordinateFrame) -> bool:
    if any(value < 0 for value in box):
        return False
    if box[2] <= box[0] or box[3] <= box[1]:
        return False
    return box[2] <= source_frame.width and box[3] <= source_frame.height


def _require_box(box: Bounds, *, allow_empty: bool) -> None:
    for value in box:
        _require_nonnegative_integer(value, name="box coordinate")
    if box[2] < box[0] or box[3] < box[1]:
        raise ValueError("Boxes must use non-inverted half-open coordinates.")
    if not allow_empty and (box[2] == box[0] or box[3] == box[1]):
        raise ValueError("Boxes must be nonempty.")


def _require_nonnegative_integer(value: int, *, name: str) -> None:
    if isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer.")
