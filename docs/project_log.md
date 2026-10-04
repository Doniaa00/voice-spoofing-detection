# Project Log — Voice-Spoofing Detection for Fraud Prevention

Team: Donia Mabrouk · Iheb Zemzemi (backend lead) · Malak Ben Salem
Repo: `Doniaa00/voice-spoofing-detection` (ownership to be transferred to Iheb)

---

## How to use this file

- **Purpose:** the chronological story of the project — what we did, what we found, what we decided, and why. Anyone joining (teammate, instructor, new Claude Code session) reads the **Current status** block at the bottom first.
- **This file points; it does not duplicate.** Official decisions live in `docs/decisions.md`. Official audit facts live in `docs/dataset_audit.md`. The log references them by ID (D13, H5, …).
- **Log entries are append-only.** Never edit an old entry; if something was wrong, add a new entry that corrects it.
- **At every update:** (1) add a new log entry, (2) tick or add items in **Open items**, (3) rewrite **Current status**.
- **Evidence labels:** **[verified]** = checked on real data/output · **[doc]** = from documentation · **[hypothesis]** = not yet tested · **[to verify]** = we are not sure it happened.

---

## Log entries

### Entry 1 — Project Readiness Audit (before 2026-10-04)

**What we did:** compared the Proposal, SRS v3.0, SDD v1.0 and Execution Plan against each other and against the research goal, before writing any code.

**What we found:**
- Readiness score 60/100: governance and architecture strong; experimental protocol missing.
- 5 pre-training blockers:
  - B1: no Experimental Protocol document.
  - B2: the schedule ran the DEEP-VOICE test before thresholds and calibration existed.
  - B3: the Execution Plan touched DEEP-VOICE twice.
  - B4: metrics undefined for a 3-way output.
  - B5: evaluation unit / clip length undefined.

**Decisions:** D1–D14 approved (D5 provisional, D13 deferred to the audit) → `docs/decisions.md`. Research question narrowed to FoR (TTS) → DEEP-VOICE (RVC) generalization (D8).

**Why it matters:** fixing the order and the rules before coding protects the project's central claim — an honest, one-time external test.

### Entry 2 — Stage 0: repo scaffold (2026-10-04)

**What we did:**
- Built the repo with Claude Code from a bootstrap package (`CLAUDE.md`, `docs/decisions.md`, audit code, reference documents).
- `CLAUDE.md` holds the standing rules for every Claude Code session.
- Fixed two Windows bugs in the audit code: UTF-8 file writing, and `/` paths in manifests.
- **D15:** official Python = 3.13 (Colab 3.13.15); local development on 3.14 allowed; CI will test on 3.13.
- Created the GitHub repo `Doniaa00/voice-spoofing-detection`, pushed the first commit (31 files, checked with `git status` before committing), and invited Iheb and Malak.
- Claude Code added a "Git workflow" section to `CLAUDE.md`: one branch per task, PRs only, Claude Code never merges.

**Evidence:** 5 tests passed on Windows after the fixes [verified].

**Decisions:** Iheb will become repo owner via ownership transfer (Option A), timing open.

### Entry 3 — Stage 1 preparation: rules before results (2026-10-04)

**What we did:**
- Approved the pre-registered decision rules in `docs/dataset_audit.md` §0 **before** any audit output existed.
- Refined D14 before running anything:
  - Chaining guard: the largest group must hold ≤ 5% of decodable clips.
  - PCM sanity check now part of threshold eligibility.
  - Selection order: 0.95 → 0.98 → PCM hash only.
  - Edge cases: unverifiable pairs fail; partially checkable pairs are decided on the checkable ones.
- Extended the audit code so it applies the rule automatically.

**Commits on `stage-1-audit-run`:** `05dd22e` (group stats per threshold) → `31f6503` (sanity check wired into selection) → `ae45e9f` (§0 text + §9 change log).

**Evidence:** 12 tests passed locally (3.14) and in Colab on Python 3.13.15 at commit `ae45e9f` [verified].

**Why it matters:** rules written before seeing data cannot be bent to fit the data.

### Entry 4 — Stage 1: FoR-2sec audit run (2026-10-04)

**What we did:**
- Downloaded FoR-2sec at the exact revision `ff8c82c79e7bbefef811941bac9775c9328e9055`.
- Backed it up as one archive: Drive `raw/for_2sec_ff8c82c7.tar` (1.22 GB), with the sha in `raw/for_2sec_REVISION.txt`.
- Ran the full audit on 17,721 clips (3.3 min), then a codec follow-up check.

**What we found [verified]:**
- 17,721 WAV: 8,921 FAKE / 8,800 REAL (50.3 / 49.7%).
- 0 corrupt files.
- All clips: 16 kHz mono PCM-16, exactly 2.0 s.
- 0 exact duplicates.
- Near-duplicates at 0.95: 98 pairs, largest group 6 clips, 0 across labels.
- No train/val/test folders. No speaker or source metadata: `fileN` numbers are independent per folder.
- The package contains no README or license file.
- **MP3 history:** 7,592 FAKE clips (85% of FAKE) were MP3 files before conversion; 0 REAL clips were.
- **Codec check:** both fake subgroups differ from REAL in similar ways.
  - Bandwidth (99% energy) median: FAKE_mp3 3,221 Hz, FAKE_other 3,461 Hz, REAL 5,074 Hz.
  - Separability on bandwidth: 0.666 for FAKE_mp3 vs 0.600 for FAKE_other.
  - Loudness separability ≈ 0.70 for both.
  - Silence: FAKE_other median 6% vs REAL 1% (separability 0.750, moderate).
- Interpretation: MP3 history is not the main separator in coarse statistics. The CNN could still exploit finer traces [hypothesis].

**Decisions (applying the §0 rules):**
- **D13 → re-split** (no packaged split).
- **D14 → near-duplicate groups at 0.95** (no speaker metadata; both checks pass).
- **D9 → val-A / val-B applies** (val-B ≈ 665 per class ≥ 500).
- **D16 (accepted by the team):**
  - no data changes;
  - re-split stratified by subgroup (REAL / FAKE_mp3 / FAKE_other);
  - pre-registered subgroup test (H5);
  - silence re-checked after trimming in Stage 6;
  - codec-history imbalance recorded as a limitation.
- **H5:** if the CNN relies on MP3 traces, its recall on FAKE_other will be clearly lower than on FAKE_mp3 (FoR test, Stages 11/16).
- **H6:** if the CNN relies on bandwidth, band-limiting REAL clips to ~3.4 kHz will raise false "FAKE" calls (Stage 14 robustness test).

**Not yet written into `docs/decisions.md` / `docs/dataset_audit.md`** — planned as one commit at the end of Stage 1.

### Entry 5 — Stage 1: DEEP-VOICE metadata audit and audit documentation (2026-10-04)

**What we did:**
- Downloaded DEEP-VOICE from Kaggle (`birdy654/deep-voice-deepfake-voice-recognition`, "updated 3 years ago", no version number).
- Archived the download: zip 3.96 GB, sha256 `8cb25853…f732bdcf` (full hash in `docs/dataset_audit.md` §1). Drive location TBD.
- Ran the metadata-only audit (`src/audit/deepvoice_metadata_audit.py`) on `KAGGLE/` only. It read headers, byte hashes, filenames and the CSV schema; it decoded no audio (attestation in `docs/dataset_audit.md` §5). `DEMONSTRATION/` (2 MP3) was excluded and never opened; `DATASET-balanced.csv` is never used.
- Checked FoR ∩ DEEP-VOICE for identical files.
- Wrote up Stage 1: `docs/dataset_audit.md` §1–§9, `docs/decisions.md` (D5, D9, D13, D14 settled; D16–D19 and H5–H6 added). Evidence summaries committed in `docs/audit_evidence/`.

**What we found [verified]:**
- 64 WAV files: 8 REAL / 56 FAKE. All stereo. Sample rates 40 / 44.1 / 48 kHz.
- 8 speakers (biden, linus, margot, musk, obama, ryan, taylor, trump). FAKE = every source → target pair (8 × 7).
- Durations 79–600 s. As 2-s windows: 1,870 REAL / 13,090 FAKE (87.5% FAKE).
- 0 exact duplicates inside DEEP-VOICE; 0 identical files shared with FoR.
- The "628 / 4,425" counts in the Proposal and Execution Plan match nothing in the package (files, windows or CSV).

**Decisions:**
- **D5 confirmed:** 2-s windows on DEEP-VOICE.
- **D17:** speech-window filter on DEEP-VOICE using the frozen silence detector. Threshold fixed in Protocol v1.0. Filtered (primary) and unfiltered (sensitivity) views come from the same single run. Drop counts reported per class and per speaker.
- **D18:** mono averaging + 16 kHz resampling, identical everywhere. Stage 6 tests pipeline invariance on FoR clips converted to 40 / 44.1 / 48 kHz stereo.
- **D19:** external results include a per-speaker table (8 rows) and a speaker average.

**Why it matters:** DEEP-VOICE differs from FoR in format (stereo, higher sample rates, long files) and has only 8 speakers. D17–D19 fix how the one external run handles that, before anything is scored.

### Entry 6 — Stage 1: open TBDs resolved (2026-10-04)

**What we did:** filled every TBD left in `docs/dataset_audit.md` (commit `c4a1b56`) and aligned D5 wording in `docs/decisions.md`.
- **Provenance:**
  - Audit run by Donia Mabrouk.
  - DEEP-VOICE audit code commit `ae45e9f` (printed by notebook cell 1, same Colab session as the FoR run).
  - Both datasets downloaded 2026-10-04.
- **Drive locations:**
  - Full audit outputs: `MyDrive/voice-spoofing-detection/processed/metadata/stage1/{for2sec,deepvoice}`.
  - DEEP-VOICE zip: `MyDrive/voice-spoofing-detection/raw/deep-voice-deepfake-voice-recognition.zip`, hash in `raw/deep_voice_ZIP_SHA256.txt`. This resolves "Drive location TBD" in Entry 5.
- **HF card checked [verified]:** the card is empty; the dataset viewer shows only `audio` and `label`. No per-file speaker, source or generator metadata. **D14 confirmed** on filenames + card (groups at 0.95).
- **Licenses recorded [doc]:**
  - FoR: not stated by the HF repackager; the original FoR terms apply (Reimao & Tzerpos, 2019).
  - DEEP-VOICE: MIT (Kaggle description), attribution Bird & Lotfi 2023, arXiv:2308.12734.
  - Both are used for academic research only; audio is never redistributed.
- **Ethics / rights:** DEEP-VOICE recordings are of real public figures, and the dataset license does not necessarily cover rights in the original speeches. Added as limitation 6 in `docs/dataset_audit.md` §8.
- **D5 wording:** raw FoR clips need no pad/crop (all 2.0 s); whether silence trimming introduces length variation is decided in Stage 6.

**Why it matters:** the audit document now has no open placeholders, so the team can sign it off as written.

---

## Open items

**GitHub / repo**
- [ ] PR `stage-0-git-workflow`: create it [to verify], get 1 teammate approval, merge.
- [ ] Iheb and Malak accept the collaborator invitations. Invitations expire after 7 days.
- [ ] Branch protection on `main` is active [to verify]: PR + 1 approval, no force-push, no bypass.
- [ ] `.gitattributes` PR (LF line endings for Windows + Colab).
- [ ] Transfer repo ownership to Iheb. Afterwards everyone runs `git remote set-url`, and we update repo URLs in the notebook and docs.
- [ ] `stage-1-audit-run` → PR + merge at the end of Stage 1.

**Notebook fixes made only in the Colab copy — must be ported to the repo notebook**
- [ ] Cell 1: real `REPO_URL`; clone with `-b <branch>`; print Python version and commit hash; capture and print the `pytest` output.
- [ ] Cell 2: download FoR to local disk (not Drive); print the folder/label structure; back up as one `.tar` + `REVISION.txt` in Drive.
- [ ] Add the dry-run, full-run, and codec-check cells as used in the session.
- [ ] Port Colab cells 1 / 2 / 3 and the run cells (FoR audit, codec check, DEEP-VOICE metadata audit, FoR ∩ DEEP-VOICE overlap check) to `notebooks/01_stage1_dataset_audit.ipynb`.

**Security**
- [ ] Regenerate the Kaggle API token.

**Documentation**
- [ ] `docs/dataset_audit.md` §9: confirm Iheb and Malak really re-confirmed D14 on 2026-10-04 [to verify]; correct the line if not.
- [x] Licenses recorded in `docs/dataset_audit.md` §1: FoR not stated by the HF repackager (original FoR terms apply); DEEP-VOICE MIT (Kaggle description), with attribution. Ethics / rights limitation added to §8.
- [ ] Check the original FoR source (Reimao & Tzerpos, 2019) for its stated terms of use.
- [x] HF dataset card checked 2026-10-04: empty; viewer shows only `audio` and `label`. No speaker / source / generator metadata; D14 stands.
- [x] Remaining TBDs in `docs/dataset_audit.md` filled: run by Donia Mabrouk, DEEP-VOICE audit commit `ae45e9f`, download dates 2026-10-04, Drive locations of full outputs (`processed/metadata/stage1/`) and of the DEEP-VOICE zip (`raw/deep-voice-deepfake-voice-recognition.zip`). D5 wording amended.
- [ ] Archive the codec-check and FoR ∩ DEEP-VOICE overlap outputs in `docs/audit_evidence/` (values are cited in the audit but the outputs are not committed). Done as part of the notebook port.
- [x] Log D13, D14, D9, D16, H5, H6 in `docs/decisions.md` and fill in `docs/dataset_audit.md` (done, with D17–D19).
- [ ] Update Proposal and Execution Plan discrepancies after the audit (e.g., the DEEP-VOICE 628 / 4,425 counts).

**Stage 1 gate**
- [ ] Team sign-off of `docs/dataset_audit.md` §10 (Donia, Iheb, Malak).

**Later stages (reminders)**
- [ ] `configs/robustness.yaml` → Stage 14. `docker-compose.yml` → Stage 17.
- [ ] Stage 6: re-run the shortcut screen *after* preprocessing (silence, bandwidth).
- [ ] Phase 0 leftovers: confirm ML lead (0.9), W&B project (0.6), pin `requirements.txt` for 3.13 + 3.14 (0.10).

---

## Current status — updated 2026-10-04

**What was done:**
- Readiness audit and decisions D1–D19; hypotheses H5–H6 pre-registered.
- Repo scaffold on GitHub.
- Stage 1 rules pre-registered, then both audits run: full FoR-2sec audit + codec check; DEEP-VOICE metadata-only audit + FoR ∩ DEEP-VOICE overlap check.
- Stage 1 fully written up in `docs/dataset_audit.md` (no TBDs left) and `docs/decisions.md`. Provenance, licenses and the HF card check recorded. Audit is **awaiting team sign-off (§10)**.

**What we have:**
- FoR-2sec: a clean, balanced development set (17,721 clips, no duplicates, no corrupt files, uniform 16 kHz mono 2 s). No speaker metadata in filenames or the HF card. Re-split with near-duplicate groups at 0.95, stratified by REAL / FAKE_mp3 / FAKE_other, with val-A / val-B.
- One documented risk: MP3 history concentrated in FAKE, with bandwidth and silence differences between classes. H5 and H6 test whether the model exploits it.
- DEEP-VOICE: 64 long stereo files from 8 speakers (1,870 REAL / 13,090 FAKE windows), no overlap with FoR, untouched beyond metadata. Rules for the one external run fixed in D17–D19. MIT license; public-figure rights noted as a limitation.
- Full audit outputs archived in Drive (`processed/metadata/stage1/`); summaries in `docs/audit_evidence/`.

**What we want:**
- A model that detects **synthetic voices**, not dataset accidents, and the evidence to prove which one it learned.
- Then one honest, one-time external test on DEEP-VOICE.

**What's next:**
1. Team review and sign-off of `docs/dataset_audit.md` §10.
2. PR `stage-1-audit-run` → 1 approval → merge → Stage 1 closed.
3. Port the Colab cells to the repo notebook and archive the codec-check and overlap outputs in `docs/audit_evidence/`.
4. Stage 2 (threat model) and Stage 3 (Experimental Protocol v1.0, which also fixes the D17 silence threshold).
