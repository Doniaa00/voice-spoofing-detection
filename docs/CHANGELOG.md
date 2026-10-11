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

### Changed
- `requirements.txt` pinned to exact versions (Python 3.13 + 3.14).
- Branch naming `<type>/stage<N>-<name>` (D23).

## 2026-10-06 — Stages 0–2

### Added
- Repo scaffold (Stage 0), dataset audit tools and evidence (Stage 1), threat model v1.0 (Stage 2).
