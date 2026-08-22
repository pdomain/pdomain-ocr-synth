"""Versioned, evidence-preserving PGDP source-geometry profile records."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictInt,
    TypeAdapter,
    ValidationError,
    field_validator,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


SCHEMA_VERSION = 1
ALGORITHM_VERSION = "pgdp-profile/v1"
SOURCE_FRAME = "source"
UNCALIBRATED_CONFIDENCE_KIND = "uncalibrated"

TruthClass = Literal["observed", "derived", "pooled"]
ConfidenceKind = Literal["uncalibrated"]
Bounds = tuple[int, int, int, int] | list[int]
Margins = tuple[int | None, int | None, int | None, int | None] | list[int | None]

_JSON_OBJECT_ADAPTER = TypeAdapter(dict[str, JsonValue])


def _require_nonnegative_integer(value: int, *, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer.")


def _require_finite(value: float, *, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number.")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")


def _deep_freeze_json_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        _require_finite(value, name="JSON value")
        return value
    if isinstance(value, list):
        return tuple(_deep_freeze_json_value(item) for item in value)
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _deep_freeze_json_value(item) for key, item in sorted(value.items())}
        )
    raise ValueError("Extension values must be JSON-native.")


def _thaw_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        _require_finite(value, name="JSON value")
        return value
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    if isinstance(value, MappingProxyType):
        thawed: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("Stored extension object keys must be strings.")
            thawed[key] = _thaw_json_value(item)
        return thawed
    raise ValueError("Stored extension value is not JSON-native.")


def _normalized_extensions(values: Mapping[str, object]) -> Mapping[str, object]:
    validated = _JSON_OBJECT_ADAPTER.validate_python(dict(values))
    return MappingProxyType(
        {key: _deep_freeze_json_value(value) for key, value in sorted(validated.items())}
    )


def _extensions_dict(values: Mapping[str, object]) -> dict[str, JsonValue]:
    return {key: _thaw_json_value(value) for key, value in sorted(values.items())}


def _merged_payload(
    payload: dict[str, JsonValue], extensions: Mapping[str, object]
) -> dict[str, JsonValue]:
    overlap = set(payload) & set(extensions)
    if overlap:
        joined = ", ".join(sorted(overlap))
        raise ValueError(f"extensions cannot replace defined fields: {joined}.")
    payload.update(_extensions_dict(extensions))
    return payload


@dataclass(frozen=True, slots=True)
class CoordinateFrame:
    """The dimensions of the source-image coordinate frame."""

    width: int
    height: int
    name: Literal["source"] = SOURCE_FRAME
    extensions: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.name != SOURCE_FRAME:
            raise ValueError(f"Coordinate frame must be {SOURCE_FRAME!r} in profile version 1.")
        _require_nonnegative_integer(self.width, name="width")
        _require_nonnegative_integer(self.height, name="height")
        object.__setattr__(self, "extensions", _normalized_extensions(self.extensions))

    def to_dict(self) -> dict[str, JsonValue]:
        return _merged_payload(
            {"name": self.name, "width": self.width, "height": self.height}, self.extensions
        )


@dataclass(frozen=True, slots=True)
class InkBand:
    """A half-open horizontal row-projection ink interval."""

    y_start: int
    y_end: int
    extensions: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonnegative_integer(self.y_start, name="y_start")
        _require_nonnegative_integer(self.y_end, name="y_end")
        if self.y_end < self.y_start:
            raise ValueError("Ink band must have non-inverted half-open bounds.")
        object.__setattr__(self, "extensions", _normalized_extensions(self.extensions))

    def to_dict(self) -> dict[str, JsonValue]:
        return _merged_payload({"y_start": self.y_start, "y_end": self.y_end}, self.extensions)


@dataclass(frozen=True, slots=True)
class Estimate:
    """One measured, derived, or pooled value with page-level evidence."""

    name: str
    value: float | None
    unit: str
    truth_class: TruthClass
    method: str
    sample_count: int
    evidence_pages: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    frame: Literal["source"] = SOURCE_FRAME
    confidence: None = None
    confidence_kind: ConfidenceKind = UNCALIBRATED_CONFIDENCE_KIND
    extensions: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Estimate name must not be empty.")
        if not self.unit:
            raise ValueError("Estimate unit must not be empty.")
        if not self.method:
            raise ValueError("Estimate method must not be empty.")
        if self.truth_class not in {"observed", "derived", "pooled"}:
            raise ValueError("Estimate truth_class is unsupported.")
        if self.frame != SOURCE_FRAME:
            raise ValueError(f"Estimate frame must be {SOURCE_FRAME!r} in profile version 1.")
        if self.confidence is not None:
            raise ValueError("Profile version 1 confidence must be null.")
        if self.confidence_kind != UNCALIBRATED_CONFIDENCE_KIND:
            raise ValueError("Profile version 1 confidence_kind must be 'uncalibrated'.")
        _require_nonnegative_integer(self.sample_count, name="sample_count")
        if self.value is not None:
            _require_finite(self.value, name="Estimate value")
        object.__setattr__(self, "evidence_pages", tuple(self.evidence_pages))
        object.__setattr__(self, "exclusions", tuple(self.exclusions))
        if len(set(self.evidence_pages)) != len(self.evidence_pages):
            raise ValueError("Estimate evidence_pages contains duplicate pages.")
        if self.sample_count != len(self.evidence_pages):
            raise ValueError("Estimate sample_count must match evidence_pages.")
        if self.value is not None and self.sample_count == 0:
            raise ValueError("A numeric estimate requires page evidence.")
        object.__setattr__(self, "extensions", _normalized_extensions(self.extensions))

    def to_dict(self) -> dict[str, JsonValue]:
        return _merged_payload(
            {
                "name": self.name,
                "value": self.value,
                "unit": self.unit,
                "truth_class": self.truth_class,
                "frame": self.frame,
                "method": self.method,
                "sample_count": self.sample_count,
                "evidence_pages": list(self.evidence_pages),
                "exclusions": list(self.exclusions),
                "confidence": self.confidence,
                "confidence_kind": self.confidence_kind,
            },
            self.extensions,
        )


@dataclass(frozen=True, slots=True)
class ProfileDiagnostic:
    """A non-fatal issue collected while creating a geometry profile."""

    code: str
    message: str
    project_id: str | None = None
    page_name: str | None = None
    extensions: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "extensions", _normalized_extensions(self.extensions))

    def to_dict(self) -> dict[str, JsonValue]:
        return _merged_payload(
            {
                "code": self.code,
                "message": self.message,
                "project_id": self.project_id,
                "page_name": self.page_name,
            },
            self.extensions,
        )


@dataclass(frozen=True, slots=True)
class PageMeasurement:
    """The source-frame geometry observed and derived for one scan."""

    page_name: str
    source_path: str
    sha256: str
    source_frame: CoordinateFrame
    image_mode: str
    grayscale_threshold: int | None
    foreground_pixels: int | None
    foreground_bounds: Bounds | None
    margins: Margins | None
    ink_bands: tuple[InkBand, ...] | None = ()
    derived_estimates: tuple[Estimate, ...] = ()
    exclusions: tuple[str, ...] = ()
    diagnostics: tuple[ProfileDiagnostic, ...] = ()
    extensions: Mapping[str, object] = field(default_factory=dict)
    image_extensions: Mapping[str, object] = field(default_factory=dict)
    observation_extensions: Mapping[str, object] = field(default_factory=dict)
    margin_extensions: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.page_name:
            raise ValueError("Page name must not be empty.")
        if not self.source_path:
            raise ValueError("Source path must not be empty.")
        if not self.sha256:
            raise ValueError("SHA-256 must not be empty.")
        if not self.image_mode:
            raise ValueError("Image mode must not be empty.")
        if self.grayscale_threshold is not None:
            _require_nonnegative_integer(self.grayscale_threshold, name="grayscale_threshold")
        self._normalize_geometry()
        if self.foreground_pixels is not None:
            _require_nonnegative_integer(self.foreground_pixels, name="foreground_pixels")
        self._validate_bounds()
        self._validate_margins()
        object.__setattr__(self, "derived_estimates", tuple(self.derived_estimates))
        object.__setattr__(self, "exclusions", tuple(self.exclusions))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "extensions", _normalized_extensions(self.extensions))
        object.__setattr__(self, "image_extensions", _normalized_extensions(self.image_extensions))
        object.__setattr__(
            self, "observation_extensions", _normalized_extensions(self.observation_extensions)
        )
        object.__setattr__(
            self, "margin_extensions", _normalized_extensions(self.margin_extensions)
        )
        self._validate_foreground_coherence()
        if any(estimate.truth_class != "derived" for estimate in self.derived_estimates):
            raise ValueError("Page derived_estimates must use the derived truth_class.")

    def _normalize_geometry(self) -> None:
        if self.foreground_bounds is not None:
            normalized_bounds = tuple(self.foreground_bounds)
            if len(normalized_bounds) != 4:
                raise ValueError("Foreground bounds must contain four coordinates.")
            object.__setattr__(self, "foreground_bounds", normalized_bounds)
        if self.margins is not None:
            normalized_margins = tuple(self.margins)
            if len(normalized_margins) != 4:
                raise ValueError("Margins must contain left, top, right, and bottom values.")
            object.__setattr__(self, "margins", normalized_margins)
        if self.ink_bands is not None:
            object.__setattr__(self, "ink_bands", tuple(self.ink_bands))

    def _validate_foreground_coherence(self) -> None:
        if self.foreground_pixels is None:
            if (
                self.foreground_bounds is not None
                or self.margins is not None
                or self.ink_bands is not None
            ):
                raise ValueError(
                    "Unavailable foreground measurements must have unavailable geometry."
                )
            return
        if self.foreground_pixels == 0:
            if self.foreground_bounds is not None or self.margins is not None:
                raise ValueError("A blank page must not have foreground bounds or margins.")
            if self.ink_bands not in (None, ()):
                raise ValueError("A blank page must not have ink bands.")
            return
        if self.foreground_bounds is None or self.margins is None or self.ink_bands is None:
            raise ValueError("Measured foreground pixels require bounds, margins, and ink bands.")

    def _validate_bounds(self) -> None:
        if self.foreground_bounds is None:
            return
        x_start, y_start, x_end, y_end = self.foreground_bounds
        for name, value in (
            ("foreground_bounds.x_start", x_start),
            ("foreground_bounds.y_start", y_start),
            ("foreground_bounds.x_end", x_end),
            ("foreground_bounds.y_end", y_end),
        ):
            _require_nonnegative_integer(value, name=name)
        if x_end < x_start or y_end < y_start:
            raise ValueError("Foreground bounds must be non-inverted half-open bounds.")
        if x_end > self.source_frame.width or y_end > self.source_frame.height:
            raise ValueError("Foreground bounds must stay inside the source frame.")

    def _validate_margins(self) -> None:
        if self.margins is None:
            return
        if len(self.margins) != 4:
            raise ValueError("Margins must contain left, top, right, and bottom values.")
        for margin in self.margins:
            if margin is not None:
                _require_nonnegative_integer(margin, name="margin")

    def to_dict(self) -> dict[str, JsonValue]:
        foreground_bounds: list[JsonValue] | None = (
            None if self.foreground_bounds is None else list(self.foreground_bounds)
        )
        margins: dict[str, JsonValue] | None
        if self.margins is None:
            margins = None
        else:
            margins = _merged_payload(
                {
                    "left": self.margins[0],
                    "top": self.margins[1],
                    "right": self.margins[2],
                    "bottom": self.margins[3],
                },
                self.margin_extensions,
            )
        ink_bands: list[JsonValue] | None = (
            None
            if self.ink_bands is None
            else list[JsonValue](band.to_dict() for band in self.ink_bands)
        )
        observations = _merged_payload(
            {
                "grayscale_threshold": self.grayscale_threshold,
                "foreground_pixels": self.foreground_pixels,
                "foreground_bounds": foreground_bounds,
                "margins": margins,
                "ink_bands": ink_bands,
            },
            self.observation_extensions,
        )
        return _merged_payload(
            {
                "page_name": self.page_name,
                "source_path": self.source_path,
                "sha256": self.sha256,
                "source_frame": self.source_frame.to_dict(),
                "image": _merged_payload({"mode": self.image_mode}, self.image_extensions),
                "observations": observations,
                "derived_estimates": [estimate.to_dict() for estimate in self.derived_estimates],
                "exclusions": list(self.exclusions),
                "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            },
            self.extensions,
        )


@dataclass(frozen=True, slots=True)
class ProjectProfile:
    """Ordered page observations and pooled estimates for one PGDP project."""

    project_id: str
    title: str | None
    author: str | None
    genre: str | None
    pages: tuple[PageMeasurement, ...] = ()
    pooled_estimates: tuple[Estimate, ...] = ()
    exclusions: tuple[str, ...] = ()
    diagnostics: tuple[ProfileDiagnostic, ...] = ()
    extensions: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValueError("Project ID must not be empty.")
        object.__setattr__(self, "pages", tuple(self.pages))
        object.__setattr__(self, "pooled_estimates", tuple(self.pooled_estimates))
        object.__setattr__(self, "exclusions", tuple(self.exclusions))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "extensions", _normalized_extensions(self.extensions))
        page_names = tuple(page.page_name for page in self.pages)
        if len(set(page_names)) != len(page_names):
            raise ValueError("Project profile contains duplicate page names.")
        if any(estimate.truth_class != "pooled" for estimate in self.pooled_estimates):
            raise ValueError("Project pooled_estimates must use the pooled truth_class.")

    def to_dict(self) -> dict[str, JsonValue]:
        return _merged_payload(
            {
                "project_id": self.project_id,
                "title": self.title,
                "author": self.author,
                "genre": self.genre,
                "pages": [page.to_dict() for page in self.pages],
                "pooled_estimates": [estimate.to_dict() for estimate in self.pooled_estimates],
                "exclusions": list(self.exclusions),
                "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            },
            self.extensions,
        )


@dataclass(frozen=True, slots=True)
class ProfileReport:
    """Stable JSON-safe output from a local PGDP geometry-profile run."""

    source_ranking: Mapping[str, object]
    methods: Mapping[str, object]
    projects: tuple[ProjectProfile, ...] = ()
    diagnostics: tuple[ProfileDiagnostic, ...] = ()
    schema_version: int = SCHEMA_VERSION
    algorithm_version: str = ALGORITHM_VERSION
    extensions: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ValueError(f"Unsupported schema_version {self.schema_version!r}.")
        if self.algorithm_version != ALGORITHM_VERSION:
            raise ValueError(f"Unsupported algorithm_version {self.algorithm_version!r}.")
        object.__setattr__(self, "source_ranking", _normalized_extensions(self.source_ranking))
        object.__setattr__(self, "methods", _normalized_extensions(self.methods))
        object.__setattr__(self, "projects", tuple(self.projects))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "extensions", _normalized_extensions(self.extensions))
        project_ids = tuple(project.project_id for project in self.projects)
        if len(set(project_ids)) != len(project_ids):
            raise ValueError("Profile report contains duplicate project IDs.")

    def to_dict(self) -> dict[str, JsonValue]:
        return _merged_payload(
            {
                "schema_version": self.schema_version,
                "algorithm_version": self.algorithm_version,
                "source_ranking": _extensions_dict(self.source_ranking),
                "methods": _extensions_dict(self.methods),
                "projects": [project.to_dict() for project in self.projects],
                "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            },
            self.extensions,
        )

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_dict(cls, payload: object) -> ProfileReport:
        try:
            return ProfileReportWire.model_validate(payload).to_domain()
        except ValidationError as error:
            raise ValueError(f"Invalid PGDP geometry profile: {error}") from error

    @classmethod
    def from_json(cls, payload: str | bytes | bytearray) -> ProfileReport:
        try:
            return ProfileReportWire.model_validate_json(payload).to_domain()
        except ValidationError as error:
            raise ValueError(f"Invalid PGDP geometry profile: {error}") from error


class _WireModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


def _wire_extensions(model: _WireModel) -> dict[str, JsonValue]:
    extras = model.model_extra
    if extras is None:
        return {}
    return _JSON_OBJECT_ADAPTER.validate_python(extras)


class CoordinateFrameWire(_WireModel):
    name: Literal["source"] = SOURCE_FRAME
    width: StrictInt = Field(ge=0)
    height: StrictInt = Field(ge=0)

    def to_domain(self) -> CoordinateFrame:
        return CoordinateFrame(
            name=self.name,
            width=self.width,
            height=self.height,
            extensions=_wire_extensions(self),
        )


class InkBandWire(_WireModel):
    y_start: StrictInt = Field(ge=0)
    y_end: StrictInt = Field(ge=0)

    def to_domain(self) -> InkBand:
        return InkBand(y_start=self.y_start, y_end=self.y_end, extensions=_wire_extensions(self))


class EstimateWire(_WireModel):
    name: str = Field(min_length=1)
    value: float | None = None
    unit: str = Field(min_length=1)
    truth_class: Literal["observed", "derived", "pooled"]
    frame: Literal["source"] = SOURCE_FRAME
    method: str = Field(min_length=1)
    sample_count: StrictInt = Field(ge=0)
    evidence_pages: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    confidence: None
    confidence_kind: Literal["uncalibrated"]

    @field_validator("value", mode="before")
    @classmethod
    def _validate_numeric_value(cls, value: object) -> object:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError("Estimate value must be a JSON number or null.")
        return value

    def to_domain(self) -> Estimate:
        return Estimate(
            name=self.name,
            value=self.value,
            unit=self.unit,
            truth_class=self.truth_class,
            frame=self.frame,
            method=self.method,
            sample_count=self.sample_count,
            evidence_pages=self.evidence_pages,
            exclusions=self.exclusions,
            confidence=self.confidence,
            confidence_kind=self.confidence_kind,
            extensions=_wire_extensions(self),
        )


class ProfileDiagnosticWire(_WireModel):
    code: str
    message: str
    project_id: str | None = None
    page_name: str | None = None

    def to_domain(self) -> ProfileDiagnostic:
        return ProfileDiagnostic(
            code=self.code,
            message=self.message,
            project_id=self.project_id,
            page_name=self.page_name,
            extensions=_wire_extensions(self),
        )


class ImageMetadataWire(_WireModel):
    mode: str = Field(min_length=1)


class MarginsWire(_WireModel):
    left: StrictInt | None = Field(default=None, ge=0)
    top: StrictInt | None = Field(default=None, ge=0)
    right: StrictInt | None = Field(default=None, ge=0)
    bottom: StrictInt | None = Field(default=None, ge=0)


class ObservationsWire(_WireModel):
    grayscale_threshold: StrictInt | None = Field(default=None, ge=0)
    foreground_pixels: StrictInt | None = Field(ge=0)
    foreground_bounds: tuple[StrictInt, StrictInt, StrictInt, StrictInt] | None
    margins: MarginsWire | None
    ink_bands: tuple[InkBandWire, ...] | None


class PageMeasurementWire(_WireModel):
    page_name: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    sha256: str = Field(min_length=1)
    source_frame: CoordinateFrameWire
    image: ImageMetadataWire
    observations: ObservationsWire
    derived_estimates: tuple[EstimateWire, ...] = ()
    exclusions: tuple[str, ...] = ()
    diagnostics: tuple[ProfileDiagnosticWire, ...] = ()

    @field_validator("derived_estimates")
    @classmethod
    def _validate_derived_estimates(
        cls, estimates: tuple[EstimateWire, ...]
    ) -> tuple[EstimateWire, ...]:
        if any(estimate.truth_class != "derived" for estimate in estimates):
            raise ValueError("Page derived_estimates must use the derived truth_class.")
        return estimates

    def to_domain(self) -> PageMeasurement:
        observations = self.observations
        margins = observations.margins
        page_margins: tuple[int | None, int | None, int | None, int | None] | None
        margin_extensions: dict[str, JsonValue]
        if margins is None:
            page_margins = None
            margin_extensions = {}
        else:
            page_margins = (margins.left, margins.top, margins.right, margins.bottom)
            margin_extensions = _wire_extensions(margins)
        return PageMeasurement(
            page_name=self.page_name,
            source_path=self.source_path,
            sha256=self.sha256,
            source_frame=self.source_frame.to_domain(),
            image_mode=self.image.mode,
            grayscale_threshold=observations.grayscale_threshold,
            foreground_pixels=observations.foreground_pixels,
            foreground_bounds=observations.foreground_bounds,
            margins=page_margins,
            ink_bands=(
                None
                if observations.ink_bands is None
                else tuple(band.to_domain() for band in observations.ink_bands)
            ),
            derived_estimates=tuple(estimate.to_domain() for estimate in self.derived_estimates),
            exclusions=self.exclusions,
            diagnostics=tuple(diagnostic.to_domain() for diagnostic in self.diagnostics),
            extensions=_wire_extensions(self),
            image_extensions=_wire_extensions(self.image),
            observation_extensions=_wire_extensions(observations),
            margin_extensions=margin_extensions,
        )


class ProjectProfileWire(_WireModel):
    project_id: str = Field(min_length=1)
    title: str | None = None
    author: str | None = None
    genre: str | None = None
    pages: tuple[PageMeasurementWire, ...] = ()
    pooled_estimates: tuple[EstimateWire, ...] = ()
    exclusions: tuple[str, ...] = ()
    diagnostics: tuple[ProfileDiagnosticWire, ...] = ()

    @field_validator("pooled_estimates")
    @classmethod
    def _validate_pooled_estimates(
        cls, estimates: tuple[EstimateWire, ...]
    ) -> tuple[EstimateWire, ...]:
        if any(estimate.truth_class != "pooled" for estimate in estimates):
            raise ValueError("Project pooled_estimates must use the pooled truth_class.")
        return estimates

    def to_domain(self) -> ProjectProfile:
        return ProjectProfile(
            project_id=self.project_id,
            title=self.title,
            author=self.author,
            genre=self.genre,
            pages=tuple(page.to_domain() for page in self.pages),
            pooled_estimates=tuple(estimate.to_domain() for estimate in self.pooled_estimates),
            exclusions=self.exclusions,
            diagnostics=tuple(diagnostic.to_domain() for diagnostic in self.diagnostics),
            extensions=_wire_extensions(self),
        )


class ProfileReportWire(_WireModel):
    schema_version: Literal[1]
    algorithm_version: Literal["pgdp-profile/v1"]
    source_ranking: dict[str, JsonValue]
    methods: dict[str, JsonValue]
    projects: tuple[ProjectProfileWire, ...] = ()
    diagnostics: tuple[ProfileDiagnosticWire, ...] = ()

    @field_validator("schema_version", mode="before")
    @classmethod
    def _validate_schema_version(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int) or value != SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version {value!r}.")
        return value

    @field_validator("algorithm_version")
    @classmethod
    def _validate_algorithm_version(cls, value: Literal["pgdp-profile/v1"]) -> str:
        if value != ALGORITHM_VERSION:
            raise ValueError(f"Unsupported algorithm_version {value!r}.")
        return value

    @classmethod
    def from_domain(cls, report: ProfileReport) -> ProfileReportWire:
        return cls.model_validate(report.to_dict())

    def to_domain(self) -> ProfileReport:
        return ProfileReport(
            schema_version=self.schema_version,
            algorithm_version=self.algorithm_version,
            source_ranking=self.source_ranking,
            methods=self.methods,
            projects=tuple(project.to_domain() for project in self.projects),
            diagnostics=tuple(diagnostic.to_domain() for diagnostic in self.diagnostics),
            extensions=_wire_extensions(self),
        )


def profile_schema_json() -> str:
    """Generate the canonical version-1 JSON Schema artifact."""

    return json.dumps(ProfileReportWire.model_json_schema(), indent=2, sort_keys=False) + "\n"
