# Lab 6 — Setup Report (skeleton)

> Skeleton only. Every section is a TODO for the team to write; nothing here is a result yet.

## 1. Team and project
- TODO: team members and roles (tracks: ml / backend / frontend).
- TODO: one-paragraph project summary (link `README.md`).

## 2. Repository setup
- TODO: repository URL, branch protection settings (to verify: PR + 1 approval, no force-push).
- TODO: how the CS 488 template was adopted (link `docs/project_log.md` Entries 15–17).

## 3. Development environment
- TODO: Python version policy (D15), local venv vs Colab, `scripts/setup.sh` (link `docs/setup.md`).
- TODO: screenshot or output of `pytest -q` on a clean clone.

## 4. Continuous integration
- TODO: what `.github/workflows/ci.yml` runs; link to a green run.

## 5. AI tooling
- TODO: which AI tools each member uses and how they read `AGENTS.md` (D22).
- TODO: human-in-the-loop rule and how AI use is disclosed (PR template, project log).

### Malak Ben Salem

- **Tool:** Codex
- **Date:** 2026-10-15
- **Result:** Passed
- **Pass basis:** The answer identified D20, the one-time external evaluation of DEEP-VOICE,
  and `src/preprocessing/`.

**Exact test question:**

```text
What are this project’s hard rules about DEEP-VOICE, and what exact repository directory contains preprocessing code? Include the applicable decision IDs and exact directory path.
```

**Exact answer:**

```markdown
[doc] DEEP-VOICE rules:

- **D2:** Use DEEP-VOICE only after the complete ModelBundle—CNN, preprocessing profile, thresholds, uncertain band, and calibration—is frozen using FoR data.
- **D3:** Do not run robustness testing on DEEP-VOICE; use the FoR test split only.
- **D6 / D20:** Before the single external evaluation, access is limited to download, ZIP hashing, unzip, and listing paths, extensions, sizes, and byte hashes, plus `src/audit/deepvoice_metadata_audit.py`. No listening, spectrograms, feature statistics, or other audio-content reads.
- **D21:** Use only the pinned DEEP-VOICE archive SHA-256 in `configs/audit.yaml`; changing it requires a new decision.
- **D17 / D19:** During the one external run, apply the frozen speech-window filter and report the required per-speaker results.
- Never use DEEP-VOICE for training, tuning, model selection, early stopping, threshold selection, calibration, or exploratory analysis. It is touched for model scoring exactly once.

The preprocessing code directory is:

`C:\Users\malak\Downloads\voice-spoofing-detection\src\preprocessing\`
```

## 6. Workflow
- TODO: branch naming (D23), Conventional Commits, PR template, issue templates, stacked PRs.

## 7. Data and safety
- TODO: dataset pins (D21), DEEP-VOICE single-use guard (D20, governance test), secrets handling
  (`.env.example`, `.gitignore`).

## 8. Problems met and fixes
- TODO

## 9. Next steps
- TODO
