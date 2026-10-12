# Changelog

All notable changes to this project. Newest at the top. Keep entries short and human: one line per
change. Based on [Keep a Changelog](https://keepachangelog.com). Detailed history with evidence is
in `project_log.md`.

Categories: **Added**, **Changed**, **Fixed**, **Removed**.

## [Unreleased]

### Added
- `AGENTS.md` as the single AI context for all tools (D22); `CLAUDE.md` imports it.
- Decision register moved to `docs/decisions/README.md`, with ADRs 0001–0005 (D24).
- `CONTRIBUTING.md`, PR and issue templates aligned with the CS 488 template.
- CI (GitHub Actions): `pytest` on Python 3.13 for PRs and pushes to `main`.
- Governance test: DEEP-VOICE paths only in D20-permitted files.
- `.gitattributes`, `.editorconfig`, `.env.example`, setup / docs-check / structure scripts,
  pre-push docs reminder.
- `docs/architecture.md`, `docs/setup.md`, `docs/README.md`, `docs/setup-report.md` (skeleton).
- MIT `LICENSE` for the code only (D25).
- Khalil Dridi in the team line (`AGENTS.md`, `README.md`), `LICENSE` and `.github/CODEOWNERS`.
- D26 work distribution (Execution Plan v2.1) in the decision register.
- Owner column (D26) in the `AGENTS.md` roadmap.
- `docs/reference/Execution_Plan_v2.1.pdf`.

### Changed
- `requirements.txt` pinned to exact versions (Python 3.13 + 3.14).
- Branch naming `<type>/stage<N>-<name>` (D23).
- Decision register header no longer limited to the readiness audit.
- `AGENTS.md`: branch-protection line (required check `checks`, branch up to date); Execution Plan pointer → v2.1.
- `Execution_Plan.md` marked superseded by v2.1 (kept for history).
- Issues tagged by part (A–E) and owner (D26) instead of track (`CONTRIBUTING.md`, feature template).
- `data/README.md`: Drive tree matches the real layout.
- D26 completed with the v2.1 §5 hand-overs; per-folder `CODEOWNERS` (owner + consumer reviewer); project log header updated.

### Fixed
- Stale `CLAUDE.md` mentions → `AGENTS.md` in `configs/audit.yaml` and the Stage 1 notebook intro.

## 2026-10-06 — Stages 0–2

### Added
- Repo scaffold (Stage 0), dataset audit tools and evidence (Stage 1), threat model v1.0 (Stage 2).
