"""Chorus / Chorus Encore API client for downloading community chart reference packages."""

import os
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any

import httpx

CHART_EXTENSIONS = (".chart", ".mid", ".midi")
AUDIO_EXTENSIONS = (".ogg", ".mp3", ".wav", ".flac", ".opus")


class ChorusScraper:
    """Client for Chorus / Chorus Encore API with retries, rate-limiting, and safe package extraction."""

    def __init__(
        self,
        base_url: str = "https://api.enchor.us/search",
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._external_client = client

    def _get_client(self) -> httpx.Client:
        if self._external_client is not None:
            return self._external_client
        return httpx.Client(timeout=self.timeout)

    def search_charts(
        self,
        query: str,
        instrument: str = "guitar",
        diff: str = "expert",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search for community charts matching query parameters."""
        params: dict[str, str | int] = {
            "query": query,
            "instrument": instrument,
            "diff": diff,
            "limit": limit,
        }

        client = self._get_client()
        should_close = self._external_client is None

        try:
            for attempt in range(self.max_retries):
                try:
                    response = client.get(self.base_url, params=params)
                    if response.status_code == 429:
                        # Rate limit reached, inspect Retry-After or apply exponential backoff
                        retry_after = response.headers.get("Retry-After")
                        sleep_time = (
                            float(retry_after)
                            if retry_after
                            else self.backoff_factor * (2**attempt)
                        )
                        time.sleep(sleep_time)
                        continue

                    response.raise_for_status()
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        # Some endpoints wrap list under "data" or "results"
                        return data.get("data") or data.get("results") or [data]
                    return []
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    if attempt == self.max_retries - 1:
                        raise RuntimeError(
                            f"Failed to search charts after {self.max_retries} attempts: {exc}"
                        ) from exc
                    time.sleep(self.backoff_factor * (2**attempt))

            raise RuntimeError(
                f"Rate limit exceeded after {self.max_retries} retries on {self.base_url}"
            )
        finally:
            if should_close:
                client.close()

    def download_chart_package(
        self,
        chart_id: str,
        destination_dir: Path,
        download_url: str | None = None,
    ) -> Path:
        """Download chart package archive (ZIP or SNG) into destination_dir."""
        destination_dir.mkdir(parents=True, exist_ok=True)
        url = download_url or f"{self.base_url.rstrip('/')}/download/{chart_id}"

        client = self._get_client()
        should_close = self._external_client is None

        # Determine target file extension
        ext = ".sng" if url.endswith(".sng") else ".zip"
        target_path = destination_dir / f"{chart_id}{ext}"

        try:
            for attempt in range(self.max_retries):
                try:
                    with client.stream("GET", url) as response:
                        if response.status_code == 429:
                            retry_after = response.headers.get("Retry-After")
                            sleep_time = (
                                float(retry_after)
                                if retry_after
                                else self.backoff_factor * (2**attempt)
                            )
                            time.sleep(sleep_time)
                            continue

                        response.raise_for_status()
                        with open(target_path, "wb") as f:
                            for chunk in response.iter_bytes():
                                f.write(chunk)
                        return target_path
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    if attempt == self.max_retries - 1:
                        raise RuntimeError(
                            f"Failed to download chart {chart_id} after {self.max_retries} attempts: {exc}"
                        ) from exc
                    time.sleep(self.backoff_factor * (2**attempt))

            raise RuntimeError(
                f"Failed to download package for {chart_id} due to persistent errors."
            )
        finally:
            if should_close:
                client.close()

    def extract_chart_package(self, archive_path: Path, extract_dir: Path) -> Path:
        """Safely extract chart package archive and verify mandatory assets (.chart/.mid + audio)."""
        extract_dir.mkdir(parents=True, exist_ok=True)
        resolved_extract_dir = extract_dir.resolve()

        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                for member in zf.infolist():
                    target_path = (extract_dir / member.filename).resolve()
                    if not target_path.is_relative_to(resolved_extract_dir):
                        raise ValueError(f"Malicious zip entry path detected: {member.filename}")
                zf.extractall(extract_dir)
        elif archive_path.suffix.lower() == ".sng":
            # Direct copy of single-file container
            target_path = extract_dir / archive_path.name
            shutil.copy2(archive_path, target_path)
            return extract_dir
        else:
            raise ValueError(f"Unsupported archive format: {archive_path.suffix}")

        # Validate extracted files
        chart_file = None
        audio_file = None

        for root, _, files in os.walk(extract_dir):
            for file_name in files:
                lower = file_name.lower()
                if lower.endswith(CHART_EXTENSIONS):
                    chart_file = Path(root) / file_name
                elif lower.endswith(AUDIO_EXTENSIONS):
                    audio_file = Path(root) / file_name

        if not chart_file:
            raise ValueError("Extracted package is missing a chart file (.chart or .mid)")
        if not audio_file:
            raise ValueError("Extracted package is missing an audio track (.ogg, .mp3, or .wav)")

        return extract_dir
