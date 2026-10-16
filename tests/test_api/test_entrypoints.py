"""Unit tests verifying all API entrypoint shims and canonical app instances."""

from api import app as api_app
from api.main import app as api_main_app
from main import app as main_app
from src.api.app import app as canonical_app


def test_entrypoint_shims():
    """Verify that all entrypoint aliases expose the canonical FastAPI application."""
    assert api_app is canonical_app
    assert api_main_app is canonical_app
    assert main_app is canonical_app
