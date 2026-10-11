# 0005. DEEP-VOICE is used once, as a frozen external test

- **Status:** Accepted
- **Date:** Sept 2026 (D2, D3, D6) and 2026-10-04 (D20)
- **Register:** D2, D3, D6, D20
- **Deciders:** Donia Mabrouk, Iheb Zemzemi, Malak Ben Salem

## Context

The research question is generalization from TTS (FoR-2sec) to RVC voice conversion (DEEP-VOICE)
(D8). That claim holds only if DEEP-VOICE never influences the model, its preprocessing or its risk
policy. The Execution Plan originally ran the external test before thresholds and calibration existed,
explored both datasets, and optionally ran robustness tests on DEEP-VOICE (SRS PC-05 requires a single
evaluation).

## Decision

- **D2:** the risk policy (thresholds, uncertain band) and calibration are fitted on FoR validation and
  frozen in the ModelBundle **before** the DEEP-VOICE run.
- **D3:** no robustness evaluation on DEEP-VOICE; robustness runs on the FoR test split only.
- **D6:** the DEEP-VOICE audit is metadata-only: no listening, spectrograms or feature statistics.
- **D20:** before the external run, the only permitted accesses are download, zip hash, unzip, listing
  paths / extensions / sizes / byte hashes, and `src/audit/deepvoice_metadata_audit.py`. Nothing reads
  audio content.
- DEEP-VOICE is evaluated **exactly once** (Stage 13), on the frozen ModelBundle; its results never
  trigger retraining, retuning or threshold changes.

## Consequences

- `AGENTS.md` hard rule 1 enforces this for every AI agent; agents must refuse any other access.
- Any finding about DEEP-VOICE before Stage 13 is limited to its metadata audit.
- The external result is reported once, next to the FoR result, with its RVC-only scope and class
  imbalance stated (SRS FR-15, FR-16).

## Links

D2, D3, D6, D8, D20 in `README.md` · `AGENTS.md` hard rule 1 · `docs/dataset_audit.md` §5 ·
`src/audit/deepvoice_metadata_audit.py`
