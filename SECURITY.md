# Security Policy

The **music2chart** team takes the security and integrity of our codebase, public services, and user systems seriously. We appreciate the responsible disclosure of any security vulnerabilities found in this software.

---

## Supported Versions

We provide security updates and patches for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| `0.1.x` | :white_check_mark: |
| `< 0.1` | :x:                |

---

## Reporting a Vulnerability

**Please do not report security vulnerabilities via public GitHub issues or discussions.**

Instead, please report security issues responsibly through one of the following channels:

1. **GitHub Private Vulnerability Reporting**:
   - Navigate to the [Security Advisories tab](https://github.com/Adiells/music2chart/security/advisories) of the repository.
   - Click **"Report a vulnerability"** to open a confidential draft advisory with the maintainers.

2. **Direct Security Contact**:
   - Email **`adiel@adiels.me`** with the subject `[SECURITY] music2chart Vulnerability Report`.
   - If sensitive material is included, please encrypt communications or request a PGP key.

### What to Include in Your Report

To help us investigate and remediate the issue promptly, please include:
- A descriptive summary of the vulnerability type (e.g., path traversal, SSRF, DoS, command injection).
- Step-by-step instructions or proof-of-concept (PoC) code/audio file demonstrating the issue.
- The affected component (e.g., `src/utils/security.py`, `src/serialization/sng_packer.py`, API endpoints).
- An assessment of the potential impact on users or host environments.

---

## Response Timeline & Disclosure Process

- **Acknowledgment**: You will receive an initial response acknowledging your report within **48 hours**.
- **Assessment & Triage**: Our team will validate and score the issue within **5 business days**.
- **Fix & Advisory**: We aim to release a patch within **14 days** of confirmation, depending on complexity.
- **Credit**: We will publicly credit you in release notes and CVE advisories (unless you prefer anonymity).

---

## Known Security Architecture & Defenses

`music2chart` incorporates proactive defense-in-depth measures against common multimedia attack vectors:
- **Zip-Slip & Path Traversal Mitigation**: File paths within `.chart` archives and `.sng` containers are sanitized and validated to prevent filesystem escape (`src/utils/security.py`).
- **Input Sanitization**: Song titles, artist metadata, and charter strings are strictly escaped before inclusion in `notes.chart` or `song.ini` text files to prevent injection attacks.
- **Audio Bomb / Memory Allocation Clamping**: Uploaded audio files are bounded in duration, file size, and decompression memory footprint before passing to Demucs or Basic Pitch.
- **FFmpeg Execution Hardening**: Subprocess calls avoid shell interpretation (`shell=False`) and invoke sanitized argument arrays directly.
