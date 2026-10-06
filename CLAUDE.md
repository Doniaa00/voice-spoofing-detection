# CLAUDE.md — Voice-Spoofing Detection for Fraud Prevention

Team: Donia Mabrouk, Iheb Zemzemi, Malak Ben Salem. Semester AI project (MUST University).

This file is the standing brief for every Claude Code session. Read it fully before any task.

## What this project is
A **decision-support** control that flags short speech recordings as authentic / synthetic / uncertain,
with a confidence score and a LOW/MEDIUM/HIGH risk level. It is not proof of fraud and not a biometric
authenticator. The research core: train on **FoR-2sec** (TTS speech), then evaluate the frozen system
**once** on **DEEP-VOICE** (RVC voice conversion) to measure cross-dataset generalization.

## Source-of-truth documents (in `docs/reference/`)
Priority order when they conflict: approved decisions in `docs/decisions.md` > SRS v3.0 > SDD v1.0 >
Execution Plan > Proposal. **Never resolve a conflict silently**: state it, name the documents, propose a
fix, and wait for approval.

- `docs/reference/SRS_Voice_Spoofing_Detection.pdf` — requirements (FR-xx, NFR-xx, PC-xx)
- `docs/reference/SDD_Voice_Spoofing_Detection_Lab5.pdf` — architecture, classes, interfaces
- `docs/reference/Execution_Plan.md` — phase-by-phase tasks (partly superseded, see decisions D2, D3, D6)
- `docs/reference/Voice_Spoofing_Detection_Project_Proposal.docx` — motivation and framing
- `docs/decisions.md` — **approved decision log; overrides the documents above**
- `docs/experimental_protocol.md` — to be written after the dataset audit (D1); does not exist yet

## HARD RULES — never break, never work around
1. **DEEP-VOICE is external and touched exactly once.** Never use it for training, tuning, threshold
   selection, calibration, early stopping, model selection, or exploration. No listening, no spectrograms,
   no feature statistics, no model scoring, except the single guarded external run after the ModelBundle
   freeze. Before that run, the only permitted accesses are (D20): download, zip hash, unzip, listing
   paths / extensions / sizes / byte hashes, and `src/audit/deepvoice_metadata_audit.py`. Nothing reads
   audio content. If a request would touch DEEP-VOICE in any other way, **stop and refuse**, explaining why.
2. **ModelBundle = CNN checkpoint + preprocessing profile + risk policy (thresholds, uncertain band,
   calibration).** All fitted on FoR only and frozen together *before* the external run (D2).
3. **Scope lock.** Baseline = MFCC (mean+std) + RBF-SVM, for evaluation only (D7). Deployed model =
   one CNN on log-Mel spectrograms. Do NOT add wav2vec2/WavLM/HuBERT/AASIST/RawNet, other features
   (LFCC, CQCC, raw waveform), ensembles, or explainability. These are future work.
4. **No training code before the dataset audit is signed off and Protocol v1.0 is frozen.**
5. **Metrics:** accuracy, precision, recall, F1, EER, ROC-AUC, confusion matrix (3-way, incl. uncertain),
   plus coverage/deferral. Positive class = spoof. No t-DCF. Never report accuracy alone.
6. **No silent changes** to datasets, splits, preprocessing, thresholds, metrics, or scope. Propose them,
   explain the impact, and wait for approval.
7. Never commit audio, datasets, or checkpoints. Only code, configs, docs, and small manifest CSVs.

## Working mode
- Work **one stage at a time**. Do only what the current stage needs, then stop and report.
- Before writing code: state the objective, which requirement or decision it serves, and which files you
  will touch.
- After writing code: run the tests and show the real output. Never claim something works without
  running it.
- End each stage with: what was done · evidence · checks run · open issues · gate → **WAITING FOR APPROVAL**.
- Label claims: [verified locally] / [documentation] / [hypothesis]. Never present a hypothesis as fact.
- If results look too good, suspect leakage or shortcuts before celebrating.
- At the end of each stage or session, update `docs/project_log.md`: append a new log entry, update
  Open items, rewrite Current status. Never edit old entries.
- **Human in the loop:** every AI-produced artifact (code, documents, analysis) is reviewed by a team
  member before it is accepted. AI output is never merged, cited or reported as verified without that
  review. Record AI assistance honestly in `docs/project_log.md`.

## Code rules
- Python 3.13 is the official version (D15): results come from Colab, whose runtime is 3.13.15.
  Local development on Python 3.14 is allowed for editing and quick tests. `requirements.txt` must
  install cleanly on both 3.13 and 3.14; CI tests on 3.13. Data roots and all paths come from
  config or CLI arguments. Never hardcode a Colab or
  Drive path.
- Every run is `dataset version + config + code version → results`. Configs live in `configs/*.yaml`.
  Log runs to W&B.
- Fail loudly on invalid input (e.g., raise on an ambiguous label). Never skip bad files silently;
  record them.
- `tests/` mirrors `src/`. Every new function gets a pytest test. Run `pytest -q` before reporting.
- `src/` is shared by research notebooks and the API (same preprocessing code everywhere: FR-04, NFR-09).
- Keep experiment code (`notebooks/`) separate from production inference code (`api/`, `src/`).
- Small, reviewable changes. Fix the root cause of errors; do not rewrite unrelated code.

## Git workflow
GitHub: `Doniaa00/voice-spoofing-detection`. `main` is protected (PR + 1 approval, no direct pushes).
- Never commit to `main`. Create one branch per task, named `stage-<N>-<short-name>`
  (e.g. `stage-1-audit-run`).
- Small commits with clear messages.
- Push the branch and tell the team to open a PR. Never merge it yourself.
- **Stacked branches:** while a stage's PR waits for sign-off/approval, the next stage branches
  from it (not from `main`), e.g. `stage-2-threat-model` from `stage-1-audit-run`. The waiting
  branch then receives **no more commits** except its sign-off (for Stage 1: §10 of
  `docs/dataset_audit.md`). All `docs/project_log.md` and `CLAUDE.md` updates go on the newest
  branch.

## Roadmap and current status
| # | Stage | Status |
|---|---|---|
| 0 | Repo scaffold + environment | done |
| 1 | Dataset audit (FoR full, DEEP-VOICE metadata-only) → `docs/dataset_audit.md` | done — awaiting sign-off/merge |
| 2 | Threat model → `docs/threat_model.md` | ← CURRENT |
| 3 | Experimental Protocol v1.0 (freeze) | |
| 4–5 | Leakage-aware split + dataset freeze (manifests + hashes) | |
| 6 | Preprocessing profile v1 + tests + compute benchmark | |
| 7 | Evaluation harness + MFCC/SVM baseline | |
| 8–9 | CNN training + model selection (FoR val-A) | |
| 10 | Risk policy + calibration fit (FoR val-B) | |
| 11 | FoR internal test (once) | |
| 12 | **ModelBundle freeze** | |
| 13 | **DEEP-VOICE external run (once, guarded)**, stores per-sample scores | |
| 14–16 | Robustness (FoR only) · calibration analysis · error analysis | |
| 17–19 | API (FastAPI) · dashboard (Streamlit) · tests/CI/Docker/docs | |

Update the status column when a stage passes its gate.

Open reminders:
- `docker-compose.yml` → Stage 17
- `configs/robustness.yaml` → Stage 14

## Compute and data
Colab/Kaggle with GPU. Datasets live in the shared Drive (`MyDrive/voice-spoofing-detection/raw/...`).
Copy them to `/content/data/` before heavy I/O. The repo `data/` folder holds only `manifests/` and a README.
