"""Smoke tests for the package metadata."""

from pdomain_ocr_synth import __all__, __version__


def test_version_is_defined() -> None:
    assert __version__
    assert isinstance(__version__, str)
    assert __version__ != "0.0.1"


def test_public_api_exports_version() -> None:
    assert "__version__" in __all__
