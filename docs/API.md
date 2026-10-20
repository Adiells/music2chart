# music2chart — REST API Specification

Comprehensive guide to all HTTP endpoints, schemas, headers, rate limits, and integration examples.

---

## 🌐 Base URL
- **Local Development**: `http://localhost:8000`
- **Official Live Service**: `https://music2chart.adiels.me`

All chart endpoints are prefixed with `/api/v1/chart`.

---

## 🔒 Security & Rate Limits

- **Rate Limit**: Default `20 requests/hour` per client IP on `/generate`.
- **IP Deduplication**: Only `1` active task (in `PENDING` or `PROCESSING` state) per IP address at any given time.
- **Maximum Upload Size**: `50 MB`.
- **Maximum Audio Duration**: `900 seconds` (15 minutes).
- **Accepted Formats**: `.mp3`, `.wav`, `.ogg`, `.flac`. Magic byte verification enforced.

---

## 📑 Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/chart/generate` | Submit an audio file to queue chart generation. |
| `GET` | `/api/v1/chart/stream/{task_id}` | Real-time SSE event stream for task lifecycle. |
| `GET` | `/api/v1/chart/status/{task_id}` | Poll current progress, status, and output files. |
| `GET` | `/api/v1/chart/preview/{task_id}/audio` | Stream processed `song.ogg` for audio playback. |
| `GET` | `/api/v1/chart/download/{task_id}` | Download `.sng`, `notes.chart`, or `.zip` bundle. |
| `GET` | `/health` / `/api/v1/health` | Health check probe. |

---

## 🚀 Endpoint Reference

### 1. `POST /api/v1/chart/generate`
Queues a background job to convert uploaded audio into playable charts.

#### Request Headers
- `Content-Type: multipart/form-data`

#### Form Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `file` | `binary` | **Yes** | — | Raw audio file (MP3, WAV, FLAC, OGG). |
| `song_name` | `string` | No | *File stem* | Title of the track. |
| `artist` | `string` | No | *File stem* | Artist / Band name. |
| `preset` | `string` | No | `"the_best"` | Preset profile: `the_best`, `standard`, `strict_rhythm`, `dynamic_solo`. |
| `output_format` | `string` | No | `"both"` | Packaging format: `sng`, `chart`, or `both`. |
| `bpm_scale` | `float` | No | `0.65` | Tempo multiplier / scroll speed scaler (e.g. `0.65` or `1.0`). |
| `min_amplitude` | `float` | No | `0.41` | Noise gate threshold (0.0 to 1.0). Higher values reject background noise. |
| `max_frets` | `int` | No | `2` | Maximum concurrent fret notes (1 to 3). |
| `hopo_threshold` | `int` | No | `48` | Maximum tick distance between notes to trigger HOPOs (0 to 192). |
| `chord_fusion_window_s` | `float` | No | `0.040` | Acoustic chord fusion window in seconds (0.005 to 0.100). |
| `min_sustain_ticks` | `int` | No | `96` | Minimum note length in ticks to draw sustain tails. |
| `release_margin` | `int` | No | `24` | Safety margin in ticks before subsequent notes (0 to 96). |
| `disable_open_notes` | `bool` | No | `true` | Suppress open notes on lead guitar. |
| `collapse_fast_runs` | `bool` | No | `true` | Collapse chords in fast 16th-note runs into single notes. |
| `consistent_patterns` | `bool` | No | `true` | Enforce consistent fret patterns on recurring musical motifs. |
| `auto_calibrate_bpm` | `bool` | No | `true` | Auto-halve tempos exceeding 160 BPM for comfortable highway speeds. |
| `merge_sustained_notes` | `bool` | No | `true` | Merge consecutive notes of identical pitch into long sustains. |

#### Response (`202 Accepted`)
```json
{
  "task_id": "8f484ddf-9988-47a8-a53b-e3c3b03f0b24",
  "status": "PENDING",
  "message": "Chart generation task queued successfully.",
  "song_name": "Free Bird",
  "artist": "Lynyrd Skynyrd"
}
```

#### Error Responses
- `400 Bad Request`: Invalid file format or missing filename.
- `413 Request Entity Too Large`: File exceeds 50MB.
- `422 Unprocessable Entity`: Audio corrupted or exceeds 15 minutes duration.
- `429 Too Many Requests`: IP rate limit hit or concurrent task already running.

---

### 2. `GET /api/v1/chart/stream/{task_id}`
Establishes a persistent Server-Sent Events (SSE) stream. Pushes state changes immediately as the pipeline progresses.

#### Response Headers
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

#### Event Stream Example
```
data: {"task_id": "8f484ddf...", "status": "PROCESSING", "progress": 0.05, "stage": "Initializing pipeline", "error": null, "result_files": null}

data: {"task_id": "8f484ddf...", "status": "PROCESSING", "progress": 0.20, "stage": "Meta Demucs v4 guitar stem isolation", "error": null, "result_files": null}

data: {"task_id": "8f484ddf...", "status": "PROCESSING", "progress": 0.45, "stage": "Spotify Basic Pitch polyphonic transcription", "error": null, "result_files": null}

data: {"task_id": "8f484ddf...", "status": "COMPLETED", "progress": 1.0, "stage": "Completed successfully", "error": null, "result_files": {"sng": "/app/tmp/output/.../track.sng", "chart": "/app/tmp/output/.../notes.chart"}}
```

---

### 3. `GET /api/v1/chart/status/{task_id}`
Polls current task progress and stage without maintaining an open socket.

#### Response (`200 OK`)
```json
{
  "task_id": "8f484ddf-9988-47a8-a53b-e3c3b03f0b24",
  "status": "COMPLETED",
  "progress": 1.0,
  "stage": "Completed successfully",
  "error": null,
  "result_files": {
    "sng": "tmp/output/8f484ddf/track.sng",
    "chart": "tmp/output/8f484ddf/notes.chart",
    "package_dir": "tmp/output/8f484ddf/package"
  }
}
```

---

### 4. `GET /api/v1/chart/preview/{task_id}/audio`
Streams the processed `song.ogg` audio file directly to the client browser or player.

#### Response Headers
- `Content-Type: audio/ogg`
- `Content-Disposition: inline; filename="song.ogg"`
- Supports `206 Partial Content` (HTTP Range requests).

---

### 5. `GET /api/v1/chart/download/{task_id}`
Downloads the generated deliverables.

#### Query Parameters
| Parameter | Type | Options | Default | Description |
| :--- | :--- | :--- | :---: | :--- |
| `format` | `string` | `sng`, `chart`, `zip` | `sng` | Deliverable format to download. |

- `format=sng`: Returns the binary `SongBinary v1` package (`Content-Type: application/octet-stream`).
- `format=chart`: Returns the raw `notes.chart` file (`Content-Type: text/plain; charset=utf-8`).
- `format=zip`: Returns a compressed archive containing `notes.chart`, `song.ini`, and `song.ogg` (`Content-Type: application/zip`).

---

## 💻 Integration Code Examples

### Python (`httpx`)
```python
import httpx
import time

BASE_URL = "http://localhost:8000"

# 1. Submit audio file
with open("solo.mp3", "rb") as f:
    res = httpx.post(
        f"{BASE_URL}/api/v1/chart/generate",
        files={"file": ("solo.mp3", f, "audio/mpeg")},
        data={"song_name": "Solo", "artist": "Guitarist", "preset": "the_best"}
    )
task_id = res.json()["task_id"]

# 2. Poll until completed
while True:
    status_res = httpx.get(f"{BASE_URL}/api/v1/chart/status/{task_id}").json()
    print(f"Status: {status_res['status']} ({int(status_res['progress'] * 100)}%) - {status_res['stage']}")
    if status_res["status"] in ("COMPLETED", "FAILED"):
        break
    time.sleep(2)

# 3. Download .sng package
if status_res["status"] == "COMPLETED":
    dl = httpx.get(f"{BASE_URL}/api/v1/chart/download/{task_id}?format=sng")
    with open("song.sng", "wb") as f:
        f.write(dl.content)
    print("Downloaded song.sng successfully!")
```

### JavaScript / TypeScript (`fetch` & SSE)
```typescript
const BASE_URL = "http://localhost:8000";

async function generateChart(audioFile: File) {
  const formData = new FormData();
  formData.append("file", audioFile);
  formData.append("preset", "the_best");

  const res = await fetch(`${BASE_URL}/api/v1/chart/generate`, {
    method: "POST",
    body: formData,
  });
  const { task_id } = await res.json();

  // Listen to SSE updates
  const eventSource = new EventSource(`${BASE_URL}/api/v1/chart/stream/${task_id}`);
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`[${Math.round(data.progress * 100)}%] ${data.stage}`);
    if (data.status === "COMPLETED" || data.status === "FAILED") {
      eventSource.close();
    }
  };
}
```
