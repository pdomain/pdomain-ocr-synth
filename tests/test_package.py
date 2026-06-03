"""Smoke tests for the package metadata."""

from __future__ import annotations

import importlib
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

import pdomain_ocr_synth


def test_version_matches_installed_metadata() -> None:
    try:
        metadata_version = version("pdomain-ocr-synth")
    except PackageNotFoundError:
        assert pdomain_ocr_synth.__version__ == "0.0.0+unknown"
        return

    assert pdomain_ocr_synth.__version__ == metadata_version


def test_version_falls_back_when_metadata_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    original_module = sys.modules.get("pdomain_ocr_synth")

    def missing_version(distribution_name: str) -> str:
        if distribution_name == "pdomain-ocr-synth":
            raise PackageNotFoundError
        return version(distribution_name)

    monkeypatch.setattr("importlib.metadata.version", missing_version)
    sys.modules.pop("pdomain_ocr_synth", None)
    try:
        imported = importlib.import_module("pdomain_ocr_synth")
        assert imported.__version__ == "0.0.0+unknown"
    finally:
        sys.modules.pop("pdomain_ocr_synth", None)
        if original_module is not None:
            sys.modules["pdomain_ocr_synth"] = original_module


def test_version_is_defined() -> None:
    assert pdomain_ocr_synth.__version__
    assert isinstance(pdomain_ocr_synth.__version__, str)


def test_public_api_exports_version() -> None:
    assert "__version__" in pdomain_ocr_synth.__all__
