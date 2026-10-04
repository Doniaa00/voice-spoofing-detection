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

**Documentation**
- [ ] `docs/dataset_audit.md` §9: confirm Iheb and Malak really re-confirmed D14 on 2026-10-04 [to verify]; correct the line if not.
- [ ] §1: FoR license from the Hugging Face dataset page; DEEP-VOICE version and license from Kaggle.
- [ ] Log D13, D14, D9, D16, H5, H6 in `docs/decisions.md` and fill in `docs/dataset_audit.md`.
- [ ] Update Proposal and Execution Plan discrepancies after the audit (e.g., the DEEP-VOICE 628 / 4,425 counts).

**Later stages (reminders)**
- [ ] `configs/robustness.yaml` → Stage 14. `docker-compose.yml` → Stage 17.
- [ ] Stage 6: re-run the shortcut screen *after* preprocessing (silence, bandwidth).
- [ ] Phase 0 leftovers: confirm ML lead (0.9), W&B project (0.6), pin `requirements.txt` for 3.13 + 3.14 (0.10).

---

## Current status — updated 2026-10-04

**What was done:**
- Readiness audit and decisions D1–D16.
- Repo scaffold on GitHub.
- Stage 1 rules pre-registered.
- Full FoR-2sec audit plus codec check, with D13, D14, and D9 settled by the rules.

**What we have:**
- A clean, balanced development dataset: no duplicates, no corrupt files, uniform format.
- One documented risk: MP3 history concentrated in FAKE, with bandwidth and silence differences between classes.
- Tests H5 and H6, designed to detect whether the model exploits that risk.

**What we want:**
- A model that detects **synthetic voices**, not dataset accidents, and the evidence to prove which one it learned.
- Then one honest, one-time external test on DEEP-VOICE.

**What's next:**
1. **Step 9:** DEEP-VOICE download and metadata-only audit (no listening, no plots).
2. Fill in `docs/dataset_audit.md` and log the decisions (one Claude Code commit on `stage-1-audit-run`).
3. Team sign-off on the audit → PR + merge → Stage 1 closed.
4. Stage 2 (threat model) and Stage 3 (Experimental Protocol v1.0).
