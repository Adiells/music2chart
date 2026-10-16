## Summary of Changes

Briefly explain the goal and approach of this PR. Reference any related issues (e.g., `Fixes #12` or `Closes #42`).

---

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🎨 Code style / formatting / refactoring
- [ ] 🧪 Testing & CI improvements
- [ ] ⚡ Performance optimization

---

## Affected Subsystems

- [ ] Audio Processing (Demucs, TempoTracker, Basic Pitch, HarmonicFilter)
- [ ] Game Design Engine (Quantizer, Pitch-to-Fret, ChordBuilder, HopoEngine, SustainProcessor)
- [ ] Serialization (.chart writer, song.ini, .sng v1 Little-Endian binary packager)
- [ ] FastAPI Backend & Asynchronous Workers
- [ ] Frontend Web Workstation (Vite / React / Highway Scene)
- [ ] Infrastructure, Docker & GitHub Community

---

## Contributor Checklist

- [ ] My code adheres to the project's coding standards and style guidelines.
- [ ] I have executed `ruff check .` and `ruff format` with zero warnings or errors.
- [ ] I have written unit tests for any new or modified logic.
- [ ] All unit tests pass locally via `pytest -v` (and `pytest --cov=src` maintains >90% coverage).
- [ ] If frontend code was modified, `npm run build` inside `frontend/` succeeds without errors.
- [ ] Documentation and type annotations have been updated accordingly.
- [ ] My commits follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.
