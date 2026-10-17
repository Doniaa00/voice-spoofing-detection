# Lab 6 — Setup Report (in progress)

> In progress. Recorded local results and AI-tool answers are included below; remaining TODOs and team review are still open.

## 1. Team and project
- TODO: team members and roles (tracks: ml / backend / frontend).
- TODO: one-paragraph project summary (link `README.md`).

## 2. Repository setup
- TODO: repository URL, branch protection settings (to verify: PR + 1 approval, no force-push).
- TODO: how the CS 488 template was adopted (link `docs/project_log.md` Entries 15–17).

## 3. Development environment
- TODO: Python version policy (D15), local venv vs Colab, `scripts/setup.sh` (link `docs/setup.md`).
### Khalil Dridi — local setup verification

- Operating system: Windows.
- Python version: 3.13.16, verified with `py -3.13 --version`.
- Git version: 2.56.0.windows.2.
- Created the project environment with `py -3.13 -m venv .venv`.
- Installed dependencies with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
- Ran the tests with `.\.venv\Scripts\python.exe -m pytest -q`.
- Observed result: `266 passed in 299.59s (0:04:59)`.
- This verifies Khalil's local setup; it does not establish completion of the other team members' setup checks.

## 4. Continuous integration
- TODO: what `.github/workflows/ci.yml` runs; link to a green run.

## 5. AI tooling
- TODO: which AI tools each member uses and how they read `AGENTS.md` (D22).
- TODO: human-in-the-loop rule and how AI use is disclosed (PR template, project log).

### Khalil Dridi

- **Tool:** Codex desktop.
- **Date:** 2026-10-17.
- **Method:** Existing conversation with supplied project documents; Codex explicitly read the local `AGENTS.md` and decision register. This was not a fresh-session automatic-context-loading test.
- **Question:** What are this project's hard rules about DEEP-VOICE, and where would preprocessing code go?
- **Answer summary:** DEEP-VOICE is reserved for the single guarded external scoring run after the complete ModelBundle is frozen using FoR only (D2). It must not guide training, tuning, model selection, thresholds or calibration; before that run only D20-permitted accesses are allowed. Robustness uses FoR only (D3), later external analyses use stored scores, and preprocessing code belongs in `src/preprocessing/`.
- **Review status:** Answer recorded for teammate review. Fresh-session automatic-context loading was not tested.

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
- **Git command unavailable:** PowerShell initially did not recognize `git`. Installed Git for Windows and verified it with `git --version`, which returned `git version 2.56.0.windows.2`.
- **Python command unavailable:** The `python` command displayed the Windows “Python not found” message. After installation, `py -3.13 --version` returned `Python 3.13.16`, although the `python` command still did not work. Used the Python launcher to create `.venv`, then called `.\.venv\Scripts\python.exe` directly to install dependencies and run tests.
- **Verification:** The local test run completed with `266 passed in 299.59s (0:04:59)`.

## 9. Next steps
- TODO
