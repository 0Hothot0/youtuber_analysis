# CLAUDE.md

Guidance for Claude Code in this repository. See README.md for the project overview.

## Layout
- `src/youtuber_analysis/` – package (config, db, collect, analyze, market, dataset)
- `scripts/00_…05_*.py` – pipeline steps, run in numeric order; thin CLIs over the package
- `config/*.yaml` – YouTubers, horizons, threshold, features. Change settings here, not in code.
- `data/raw`, `data/interim` – SQLite databases (gitignored). `data/processed` – exported Excel (tracked).
- `results/soft_margin_svm/` – SVM workbooks (tracked, produced outside this codebase)

## Conventions
- Install with `pip install -e ".[dev]"`; run tests with `pytest`.
- Paths come from `youtuber_analysis.config` – never hard-code database or output paths.
- One parameterised script per step (`--youtuber`, `--period`); do not add per-YouTuber copies.
- Labelling rule lives only in `market/labeling.py`.
- Secrets go in `.env` (see `.env.example`); never commit it.
