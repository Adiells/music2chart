"""Shared pytest fixtures for the music2chart test suite."""

import pytest


@pytest.fixture
def realistic_chart_content() -> str:
    """Return a realistic Clone Hero .chart string with variable BPM, chords, open notes, and Star Power."""
    return """[Song]
{
  Name = "Test Anthem"
  Artist = "Synthetics"
  Charter = "music2chart AI"
  Offset = 0
  Resolution = 192
  Player2 = bass
  Difficulty = 0
  PreviewStart = 0
  PreviewEnd = 0
  Genre = "rock"
  MediaType = "cd"
  MusicStream = "song.ogg"
}
[SyncTrack]
{
  0 = TS 4
  0 = B 120000 // 120 BPM
  768 = B 140000 // Tempo change to 140 BPM at measure 2
}
[Events]
{
  0 = E "section Intro"
  768 = E "section Verse 1"
}
[ExpertSingle]
{
  // Open note
  0 = N 7 0
  96 = N 0 0
  // Note with sustain
  192 = N 1 96
  // Two-note chord (Green + Yellow) and Star Power phrase
  384 = N 0 0
  384 = N 2 0
  384 = S 2 384
  // Notes in the 140 BPM section
  768 = N 3 0
  864 = N 4 48
}
"""
