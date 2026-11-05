"""Persistence for chart feedback in Supabase."""

from typing import Any

import httpx

from config.settings import get_settings


class FeedbackStorageError(RuntimeError):
    """Raised when feedback cannot be persisted to the configured store."""


async def store_chart_feedback(record: dict[str, Any]) -> None:
    """Insert one feedback record using Supabase's server-side REST API."""
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_API_KEY:
        raise FeedbackStorageError("Supabase feedback storage is not configured")

    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/chart_feedback"
    headers = {
        "apikey": settings.SUPABASE_API_KEY,
        "Prefer": "return=minimal",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=record, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        status_code = (
            exc.response.status_code
            if isinstance(exc, httpx.HTTPStatusError)
            else "network error"
        )
        raise FeedbackStorageError(f"Supabase returned {status_code}") from exc
