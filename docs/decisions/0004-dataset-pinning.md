# 0004. Dataset pinning

- **Status:** Accepted
- **Date:** 2026-10-04
- **Register:** D21
- **Deciders:** Donia Mabrouk, Iheb Zemzemi, Malak Ben Salem

## Context

The audit and every later result are valid only for an exact dataset version. FoR-2sec on Hugging
Face can change revision; DEEP-VOICE on Kaggle has no version number ("updated 3 years ago").
A silent change of either dataset would invalidate the audit and the single external test.

## Decision

- FoR-2sec is pinned to HF revision `ff8c82c79e7bbefef811941bac9775c9328e9055`.
- DEEP-VOICE is pinned to the Kaggle zip SHA-256
  `8cb258530daa2bb678121f3b276313a4d56fc638280bfd276a610dd8f732bdcf`.
- Both pins live in `configs/audit.yaml`. The audit notebook refuses an empty revision and stops before
  unzipping if the zip hash differs.
- Changing a pin requires a new decision entry (and a new ADR superseding this one).

## Consequences

- Re-runs use exactly the audited data or fail loudly.
- Backups in Drive `raw/` (`for_2sec_ff8c82c7.tar`, the DEEP-VOICE zip and their hash files) are the
  fallback if a source disappears.

## Links

D21 in `README.md` · `configs/audit.yaml` · `notebooks/01_stage1_dataset_audit.ipynb` (cells 2, 3) ·
`docs/dataset_audit.md` §1 · `docs/threat_model.md` §10 (Tampering, data)
