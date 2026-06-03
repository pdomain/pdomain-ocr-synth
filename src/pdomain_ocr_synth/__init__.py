"""pdomain-ocr-synth: synthetic OCR training-data generator (recipe-driven)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pdomain-ocr-synth")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
