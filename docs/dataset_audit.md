# Dataset Audit — Stage 1

| Field | Value |
|---|---|
| Status | §0 rules approved 2026-10-04, audit not yet run |
| Audit code commit | `<git sha>` |
| Run by / date | `<name>` / `<date>` |
| Machine outputs | `audit_out/for2sec/*`, `audit_out/deepvoice/*` (archived in Drive `processed/metadata/stage1/`) |

Evidence labels used in this document: **[B] verified locally** · **[C] publisher documentation / literature** · **[E] hypothesis, unverified**.

---

## 0. Pre-registered decision rules (written BEFORE running the audit)

These rules were fixed before any audit output was seen, so the results cannot shape the rules that interpret them. Changing a rule after seeing results requires change control (master prompt §45) and a note in §9.

| Decision | Rule |
|---|---|
| **D13: official split vs re-split** | Use the packaged split **only if** (a) train/val/test folders exist, (b) there are zero cross-split exact duplicates (bytes or PCM), and (c) there are zero cross-split near-duplicate pairs at sim ≥ 0.95. Otherwise re-split. |
| **D14: grouping unit** | Speaker or source-recording metadata, if it exists in filenames or the card. Otherwise near-duplicate components (transitive) merged with PCM-hash groups, with the threshold chosen by this procedure. A threshold is **eligible** only if both checks pass: (1) **chaining check**: the largest near-duplicate group holds ≤ 5% of decodable clips (corrupt files excluded); (2) **sanity check**: the minimum fingerprint similarity among exact-PCM-duplicate pairs is ≥ the threshold. If there are no such pairs, the sanity check passes. If pairs exist but none can be checked (no fingerprints), it fails. If only some can be checked, it is decided on the checkable pairs and the unchecked count is reported. **Selection order:** 0.95 → 0.98 → `pcm_hash_only` (the first eligible threshold is used). If neither is eligible, group by exact PCM-hash duplicates only and record the residual near-duplicate risk as a limitation. Group statistics and both checks are reported at 0.90, 0.95 and 0.98. |
| **Re-split ratios** (if re-split) | Group-aware, label-stratified 70 / 15 / 15 (train / val / test). Val is further split 50/50 into val-A (early stopping, model selection) and val-B (threshold, calibration), per D9, if val-B has ≥ 500 clips per class; otherwise single val with the reuse documented. |
| **D5: evaluation unit** | Training unit = FoR clip. If DEEP-VOICE files are longer than 2 s, evaluate on non-overlapping 2 s windows from file start and drop the remainder under 2 s. Windows are the primary unit; file-level mean score is secondary; bootstrap CIs are clustered by source speaker. The pad/crop rule for clips under 2 s is set from the FoR duration distribution (§2). |
| **Shortcut rule** | Any numeric feature with separability AUC ≥ 0.90, or any categorical value with purity ≥ 0.99 at ≥ 1% support, must be either neutralized by the preprocessing profile and **re-screened after preprocessing (Stage 6)**, or carried forward as a named limitation. A flag in the 0.75–0.90 range is reported and discussed. |
| **Corrupt files** | Excluded, listed by path and hash in §9. The exclusion list is part of the dataset freeze. |
| **Exact duplicates** | Within-label duplicates: keep one copy (lowest path lexicographically). Cross-label duplicates: exclude **all** copies (label noise) and report the count. |

Approved by Donia, Iheb and Malak (team chat, 2026-10-04) before any audit output was produced.

---

## 1. Provenance and license

| Item | FoR-2sec | DEEP-VOICE |
|---|---|---|
| Source | Hugging Face `UncovAI/FOR-2sec` | Kaggle `birdy654/deep-voice-deepfake-voice-recognition` |
| Exact revision | `<HF commit sha>` [B] | `<Kaggle version #>` [B] |
| Download date | | |
| Archive / snapshot hash | | |
| License (from card) | | |
| Original work | Reimao & Tzerpos, Fake-or-Real (FoR) dataset, 2019 [C] | Bird & Lotfi, *Real-time Detection of AI-Generated Speech for DeepFake Voice Conversion*, 2023 [C] |
| Packaging notes | HF viewer lists format "soundfolder" and one parquet-converted `train` split, 1.13 GB [C]. If true, the original train/val/test split is **not** preserved; verify. | Publisher: raw audio in `AUDIO/REAL`, `AUDIO/FAKE`; filenames encode source → target speaker; `DATASET-balanced.csv` holds 1-s-window features balanced by random sampling; RVC applied to extracted vocals, then re-layered onto the original background [C]. |

## 2. FoR-2sec: verified facts

| Fact | Value | Evidence | Label |
|---|---|---|---|
| Total files / REAL / FAKE | | `for2sec_summary.json` → counts | [B] |
| Packaged split folders | | counts.by_split_dir_label | [B] |
| Extensions, formats, subtypes | | summary.md §2 | [B] |
| Sample rates by label | | summary.md §2 | [B] |
| Channels by label | | summary.md §2 | [B] |
| Duration distribution by label | | summary.md §3 | [B] |
| Clips outside 2.0 s ± 50 ms | | summary.md §3 | [B] |
| Header / decode failures | | counts | [B] |
| Speaker metadata available? | | filename tokens §6 + card | [B] |
| Source-recording metadata available? | | filename tokens §6 + card | [B] |
| Generator (TTS engine) metadata available? | | filename tokens §6 + card | [B] |
| Generators actually present | | | [B] or "not determinable" |

## 3. Shortcut / artifact analysis

For every flagged feature, fill in:

- **Observation** (what the table shows):
- **Interpretation:**
- **Hypothesis** [E]:
- **Decision** (neutralize in profile + re-screen in Stage 6 / document as limitation):

Note: resampling to 16 kHz neutralizes a sample-rate flag, but **not** band-limited content below 8 kHz (`bw99_hz`) or loudness and silence differences. Stage 6 re-screen is mandatory for every flag.

## 4. Leakage analysis

| Check | Result | Consequence |
|---|---|---|
| Exact duplicates (bytes): groups / cross-label / cross-split | | |
| Exact duplicates (decoded PCM): groups / cross-label / cross-split | | |
| Near-dup pairs @0.90 / 0.95 / 0.98 (cross-label, cross-split) | | |
| Near-dup components @0.95: n groups, largest | | |
| Max-sim quantiles by label | | |
| Known limitation | Aligned fingerprints miss time-shifted overlapping excerpts of the same recording | Residual leakage risk stated in the report |

## 5. DEEP-VOICE: metadata-only facts

> Paste the attestation line from `deepvoice_summary.md` here.

| Fact | Value | Label |
|---|---|---|
| Files by label | | [B] |
| Total seconds / hours by label | | [B] |
| 2 s windows by label (if D5 adopted) | | [B] |
| Sample rates / channels by label | | [B] |
| Source speakers / target speakers | | [B] |
| Exact duplicate files; FoR ∩ DEEP-VOICE byte overlap | | [B] |
| CSV schema and label counts (never used for evaluation) | | [B] |

## 6. Discrepancies with project documents

| Document claim | Where | Audit finding | Action |
|---|---|---|---|
| DEEP-VOICE 628 bonafide / 4,425 spoof | Proposal §6.1, Exec Plan Phase 2 | | Update or remove |
| "Eight public figures" | Proposal §6 | | |
| FoR-2sec spans six TTS engines | Proposal §6, Exec Plan Phase 0 | | |
| ~17,700 clips, ~1.13 GB | Master prompt §15 | | |

## 7. Decisions (applying the §0 rules)

| Decision | Outcome | Evidence |
|---|---|---|
| D13 | | |
| D14 | | |
| D5 | | |

## 8. Limitations carried forward

## 9. Exclusions and change log

### Change log

- 2026-10-04: D14 refined before any audit output — PCM sanity check made part of threshold eligibility; unverifiable pairs fail; partially checkable pairs decided on checkable ones. Re-confirmed by Donia, Iheb and Malak (team chat, 2026-10-04).

## 10. Sign-off

| Member | Reviewed | Date |
|---|---|---|
| Donia | | |
| Iheb | | |
| Malak | | |
