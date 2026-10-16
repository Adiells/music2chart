"""Entrypoint alias for uvicorn api.main:app."""

from src.api.app import app

__all__ = ["app"]
