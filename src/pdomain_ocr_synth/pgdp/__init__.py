from __future__ import annotations

from pdomain_ocr_synth.pgdp.features import extract_page_features, score_page
from pdomain_ocr_synth.pgdp.models import (
    CorpusSummary,
    Diagnostic,
    PageFeatures,
    PageScore,
    RankedPage,
    RankedProject,
    RankingLimits,
    RankingReport,
)
from pdomain_ocr_synth.pgdp.ordering import natural_page_key
from pdomain_ocr_synth.pgdp.profile_models import (
    CoordinateFrame,
    Estimate,
    InkBand,
    PageMeasurement,
    ProfileDiagnostic,
    ProfileReport,
    ProjectProfile,
)
from pdomain_ocr_synth.pgdp.ranking import rank_corpus
from pdomain_ocr_synth.pgdp.report import write_report

__all__ = [
    "CoordinateFrame",
    "CorpusSummary",
    "Diagnostic",
    "Estimate",
    "InkBand",
    "PageFeatures",
    "PageMeasurement",
    "PageScore",
    "ProfileDiagnostic",
    "ProfileReport",
    "ProjectProfile",
    "RankedPage",
    "RankedProject",
    "RankingLimits",
    "RankingReport",
    "extract_page_features",
    "natural_page_key",
    "rank_corpus",
    "score_page",
    "write_report",
]
