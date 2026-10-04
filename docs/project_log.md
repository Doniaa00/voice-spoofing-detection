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

### Entry 7 — Stage 1: audit notebook ported, datasets pinned, D20 (2026-10-04)

**What we did:**
- **Notebook port** (commit `f8af88a`): rewrote `notebooks/01_stage1_dataset_audit.ipynb` from the working Colab copy. It has 9 code cells, each with a markdown explanation, and outputs stripped:
  - setup + tests
  - FoR download + `.tar` backup
  - DEEP-VOICE download
  - dry run
  - full FoR audit
  - codec check, now saved to `for2sec_codec_check.csv/.json`
  - DEEP-VOICE metadata audit
  - FoR ∩ DEEP-VOICE overlap, now saved to `cross_dataset_overlap.json`
  - archive

  Cells 6 and 8 also run from the Drive archive alone. The Colab copy was used as reference only and deleted, not committed.
- **Pins** in `configs/audit.yaml`:
  - `for2sec.revision = ff8c82c7…`; cell 2 stops if it is empty.
  - `deepvoice.zip_sha256 = 8cb25853…`; cell 3 stops before unzipping if the downloaded zip differs.
  - The DEEP-VOICE revision label no longer uses a relative date: `kaggle zip-sha256:<hash>, downloaded 2026-10-04`.
  - Outdated config comments fixed.
- **D20:** before the external run, the only permitted DEEP-VOICE accesses are download, zip hash, unzip, listing paths / extensions / sizes / byte hashes, and `deepvoice_metadata_audit.py`. Nothing reads audio content. `CLAUDE.md` hard rule 1 now says the same.

**Evidence [verified locally]:**
- The notebook validates with nbformat, and all 9 code cells compile.
- A local smoke test with synthetic inventories passed: the empty-revision and zip-mismatch guards raise, and cells 6 and 8 run from an archive-only layout.
- `pytest -q`: 12 passed.

Not yet run in Colab.

**Why it matters:** the audit can now be re-run from the repo alone, against exactly the same data, and every DEEP-VOICE touch before the external run is written down and limited.

### Entry 8 — Stage 1: Colab run of the ported notebook (2026-10-04)

**What we did:** ran the ported notebook in Colab, in the same session as the original audit: commit `c2136cb`, Python 3.13.15.
- **Cell 1 (setup):** clone/checkout, install, tests — 12 passed.
- **Cell 6 (codec check):** saved `for2sec_codec_check.csv` / `.json`.
- **Cell 8 (FoR ∩ DEEP-VOICE overlap):** saved `cross_dataset_overlap.json`.
- **Cell 9:** archived to Drive.
- Committed the three files to `docs/audit_evidence/`. `docs/dataset_audit.md` now cites them instead of "not yet archived".

**What we found [verified]:** the results are identical to the original run.
- Codec groups: REAL 8,800 / FAKE_mp3 7,592 / FAKE_other 1,329. 0 REAL clips have `mp3` in the stem.
- FAKE_other silence separability: 0.750.
- Overlap: 0 identical files (17,721 FoR vs 64 DEEP-VOICE file hashes).

**Caveat:** the Colab session still had its local outputs, so both cells read the local inventories (`source_inventory` = `/content/audit_out/...`). The archive-only read path of cells 6 and 8 has been exercised **on synthetic data only** (local smoke test, Entry 7), not on the real Drive archive.

**Why it matters:** every number in the audit document now points to a committed evidence file, produced by code in the repo at a recorded commit.

### Entry 9 — Stacked branch for Stage 2 (2026-10-04)

**Decision:** Stage 1 is waiting for team sign-off and PR approval. Work continues on a **stacked branch**, so the team review doesn't block progress.
- Created `stage-2-threat-model` **from `stage-1-audit-run`**, not from `main`.
- **Rule:** `stage-1-audit-run` receives no more commits except the §10 sign-off in `docs/dataset_audit.md`. All `docs/project_log.md` and `CLAUDE.md` updates now go on `stage-2-threat-model` (and later on the newest branch).
- `CLAUDE.md`:
  - The stacked-branch rule is added to the Git workflow section.
  - Roadmap: Stage 1 = "done — awaiting sign-off/merge", Stage 2 = CURRENT.
- The Git workflow section was only on the unmerged `stage-0-git-workflow` branch. It was brought in by merging `origin/stage-0-git-workflow` (`428e0b8`) into `stage-2-threat-model`, so both PRs carry the same commit and should not conflict.

**Merge order:** `stage-0-git-workflow` → `stage-1-audit-run` → `stage-2-threat-model`. Until the first two are merged, the Stage 2 PR also shows their changes.

**Why it matters:** the Stage 1 evidence stays frozen while it is reviewed, and the log stays on a single line of history.

### Entry 10 — Stage 2: threat model draft v0.1 (2026-10-04)

**What we did:**
- The team wrote `docs/threat_model.md` v0.1. It covers:
  - scenarios: call-center triage of high-risk requests (primary) and an executive voice message (secondary);
  - the attack path and detection point;
  - assets, attacker profiles and attack classes in and out of scope;
  - threats T1–T7 mapped to the planned evidence;
  - the error policy and threats to the system itself;
  - the oracle-abuse residual risk.
- Committed as-is (commit `8b7b679`).
- Checked the draft (Claude Code):
  - every FR / NFR / PC / WH / UN ID against the SRS v3.0 text;
  - every D* and H* against `docs/decisions.md`;
  - the cited audit facts against `docs/dataset_audit.md`;
  - Proposal §2.3;
  - the mermaid syntax.

**What we found [verified]:**
- **All cited IDs exist** and their meaning matches the SRS:
  - FR-03, FR-05–FR-07, FR-11, FR-12–FR-18, FR-20
  - NFR-01–NFR-05, NFR-07, NFR-09
  - PC-03–PC-05, WH-01–WH-04, UN-01, UN-02
  - D2, D8, D11, D12, D14, D16–D20, H5, H6
- SRS §1.2 and §7.4 support the cited content: scope, open limits, access-control mechanism. Proposal §2.3 is "Attacker capability assumptions".
- **Mermaid block parses** (flowchart; `mermaid.parse` 11.17.2, with a broken-diagram negative control).
- **Two mismatches, reported for team review, not fixed:**
  1. §3.2 says "all files `src-to-tgt`". Only the 56 FAKE files are; the 8 REAL files are `<speaker>-original.wav` (`docs/dataset_audit.md` §5).
  2. §10, "Tampering (data)", cites **D20** for the pinned FoR revision / DEEP-VOICE zip SHA-256 and the stop-on-mismatch. D20 defines the *permitted DEEP-VOICE accesses*; the pinning is in `configs/audit.yaml` (Entry 7) and has no decision ID.
- **Observations (not mismatches):**
  - The §10 spoofing control relies on FR-11, which is a *Could* requirement.
  - T6 cites D2 for calibration on val-B; the val-A / val-B split itself is D9.

**Why it matters:** the threat model sets the maximum claim for each threat. Its references have to be exact, because the final report will quote them.

### Entry 11 — Stage 2: threat model v0.2, D21 (2026-10-04)

**What we did:** applied the approved fixes from the v0.1 review (Entry 10). `docs/threat_model.md` → **v0.2**:
- **§3.2:** "8 source speakers [verified]; the 56 FAKE files are named `src-to-tgt`, the 8 REAL files `<speaker>-original`."
- **§10, Tampering (data):** now cites **D21** and `configs/audit.yaml` instead of D20.
- **§10, Spoofing:** status adds "FR-11 is Could priority; if not implemented, this threat is unmitigated."
- **§11:** new residual risk 7, analyst impersonation if FR-11 is not implemented.
- **§8 T6:** cites D2 and D9.
- **§12:** §8 row adds D9; §10 row cites D21 instead of D20.
- **D21** added to `docs/decisions.md`: datasets are pinned (FoR-2sec HF revision, DEEP-VOICE zip SHA-256) in `configs/audit.yaml`; the notebook refuses unpinned or mismatched data; changing a pin requires a new decision entry.

**Evidence [verified]:** citation check re-run on every changed line.
- All cited IDs exist: SRS v3.0, plus D2, D9 and D21 in `docs/decisions.md`.
- The D21 hashes equal the values in `configs/audit.yaml`.
- `deepvoice_summary` confirms 56 FAKE `src-to-tgt` and 8 REAL `<speaker>-original` files.
- The SRS lists FR-11 as Could (requirements table and MoSCoW table).
- D20 is no longer cited in the threat model.

**Why it matters:** every claim and citation in the threat model now traces to its source. The one gap, analyst authentication, is stated as a residual risk instead of being implied as covered.

### Entry 12 — Plan review and corrections (2026-10-04)

**Correction to Entry 10:** `docs/threat_model.md` v0.1 was drafted with Claude (AI assistant, chat) from the team's documents and decisions, then committed for team review. **The team has not reviewed it yet.** The audit code in `src/audit/` was likewise written with AI assistance and verified by tests.

**Execution Plan comparison:**
- **Phase 1:** SRS requirements covered. Threat model in progress. GitHub Issues board not created.
- **Phase 2:** dataset audit done. Preprocessing, manifests and compute benchmark not started.

**Document discrepancies found [doc, checked against the reference files]** — to fix later, not now:
- DEEP-VOICE zip is 3.96 GB [verified]; the Execution Plan says ~0.55 GB.
- The Proposal's architecture figure still shows "ASVspoof + WaveFake" as training data and "baseline + deep model" inside the deployed detector.
- Proposal §3.2 calls real-time / streaming detection a stretch goal; SRS WH-01 excludes it.
- The Execution Plan lists six named TTS engines for FoR; this is not determinable from the package (`docs/dataset_audit.md` §2).
- Execution Plan steps superseded by D2, D3, D6 and D10.

**Stage 6 flag:** the Execution Plan suggests `silero-vad` (a small pretrained model) for voice-activity detection / silence trimming. Choosing it must be an **explicit Stage 6 decision**, not a default. D17 (DEEP-VOICE speech-window filter) depends on the chosen detector.

**Stage 3 rule:** Experimental Protocol v1.0 may be **drafted now** on a stacked branch. It is **frozen only after the Stage 1 sign-off**.

---

## Open items

**GitHub / repo**
- [ ] PR `stage-0-git-workflow`: create it [to verify], get 1 teammate approval, merge.
- [ ] Iheb and Malak accept the collaborator invitations. Invitations expire after 7 days.
- [ ] Branch protection on `main` is active [to verify]: PR + 1 approval, no force-push, no bypass.
- [ ] `.gitattributes` PR (LF line endings for Windows + Colab).
- [ ] Transfer repo ownership to Iheb. Afterwards everyone runs `git remote set-url`, and we update repo URLs in the notebook and docs.
- [ ] `stage-1-audit-run` → PR + merge at the end of Stage 1.
- [ ] Merge PRs in order: `stage-0-git-workflow` → `stage-1-audit-run` → `stage-2-threat-model` (stacked; see Entry 9). `stage-1-audit-run` only gets the §10 sign-off commit from now on.

**Notebook (ported to the repo, `f8af88a`; pins and guards added in Entry 7)**
- [x] Cell 1: real `REPO_URL`; clone with `-b <branch>`; print Python version and commit hash; capture and print the `pytest` output.
- [x] Cell 2: download FoR to local disk (not Drive); print the folder/label structure; back up as one `.tar` + `REVISION.txt` in Drive.
- [x] Add the dry-run, full-run, and codec-check cells as used in the session.
- [x] Port Colab cells 1 / 2 / 3 and the run cells (FoR audit, codec check, DEEP-VOICE metadata audit, FoR ∩ DEEP-VOICE overlap check) to `notebooks/01_stage1_dataset_audit.ipynb` (9 cells, outputs stripped; `BRANCH` defaults to `main`; `deepvoice.audit_subdir` added to `configs/audit.yaml`).
- [x] Run the ported notebook once in Colab (cells 1, 6, 8, 9 at `c2136cb`; results identical, Entry 8). Archive-only read path exercised on synthetic data only.
- [ ] Optional: exercise the archive-only path of cells 6 and 8 on the real Drive archive in a fresh Colab session (no local outputs).

**Security**
- [ ] Regenerate the Kaggle API token.

**Documentation**
- [ ] `docs/dataset_audit.md` §9: confirm Iheb and Malak really re-confirmed D14 on 2026-10-04 [to verify]; correct the line if not.
- [x] Licenses recorded in `docs/dataset_audit.md` §1: FoR not stated by the HF repackager (original FoR terms apply); DEEP-VOICE MIT (Kaggle description), with attribution. Ethics / rights limitation added to §8.
- [ ] Check the original FoR source (Reimao & Tzerpos, 2019) for its stated terms of use.
- [x] HF dataset card checked 2026-10-04: empty; viewer shows only `audio` and `label`. No speaker / source / generator metadata; D14 stands.
- [x] Remaining TBDs in `docs/dataset_audit.md` filled: run by Donia Mabrouk, DEEP-VOICE audit commit `ae45e9f`, download dates 2026-10-04, Drive locations of full outputs (`processed/metadata/stage1/`) and of the DEEP-VOICE zip (`raw/deep-voice-deepfake-voice-recognition.zip`). D5 wording amended.
- [x] Codec-check and FoR ∩ DEEP-VOICE overlap outputs committed to `docs/audit_evidence/` (`for2sec_codec_check.csv/.json`, `cross_dataset_overlap.json`); "not yet archived" notes replaced in `docs/dataset_audit.md`.
- [x] Log D13, D14, D9, D16, H5, H6 in `docs/decisions.md` and fill in `docs/dataset_audit.md` (done, with D17–D19).
- [ ] Update Proposal and Execution Plan discrepancies after the audit (e.g., the DEEP-VOICE 628 / 4,425 counts).
  Also, from Entry 12:
  - DEEP-VOICE size 3.96 GB (Exec Plan: ~0.55 GB);
  - the Proposal architecture figure (ASVspoof + WaveFake; "baseline + deep model" in the detector);
  - Proposal §3.2 streaming as a stretch goal (vs SRS WH-01);
  - Exec Plan's six named TTS engines (not determinable);
  - Exec Plan steps superseded by D2, D3, D6, D10.

**Stage 1 gate**
- [ ] Team sign-off of `docs/dataset_audit.md` §10 (Donia, Iheb, Malak).

**Team meeting (next)**
- [ ] Collaborator invitations accepted (Iheb, Malak).
- [ ] Stage 1: `docs/dataset_audit.md` §10 sign-off.
- [ ] Stage 2: threat model review (§13 open questions, §14 sign-off).
- [ ] Assign the three tracks (0.9), set up W&B (0.6), confirm compute per person (0.7), set the weekly sync + channel (0.8).
- [ ] Agree the PR merge order: `stage-0-git-workflow` → `stage-1-audit-run` → `stage-2-threat-model`.

**Execution Plan phases (from the Entry 12 comparison)**
- [ ] Phase 0: compute per person (0.7); weekly sync + async channel (0.8); random-seed policy (0.10).
- [ ] Phase 1: GitHub Issues board, one issue per upcoming stage, tagged `ml` / `backend` / `frontend`.
- [ ] Phase 2: compute benchmark before Stage 8. Train the CNN on a small subset and record GPU type, VRAM, batch size and time per epoch.

**Stage 2 gate**
- [x] Resolve the two v0.1 mismatches from Entry 10 (§3.2 REAL filenames; §10 D20 → D21) → v0.2 (Entry 11).
- [ ] Team review of `docs/threat_model.md` v0.2 (§13 open questions, §14 sign-off).
- [ ] Decide the access-control mechanism (SRS §7.4) before the API stage (Stage 17), at the latest. The oracle-abuse residual risk (threat model §10.1) depends on it.

**Later stages (reminders)**
- [ ] `configs/robustness.yaml` → Stage 14. `docker-compose.yml` → Stage 17.
- [ ] Stage 17: verify the ModelBundle checkpoint hash at load (threat model §10, tampering recommendation).
- [ ] Stage 6: re-run the shortcut screen *after* preprocessing (silence, bandwidth).
- [ ] Stage 6: decide the silence / voice-activity detector explicitly (energy-based vs `silero-vad`) and record it as a decision; D17 depends on it.
- [ ] Phase 0 leftovers: confirm ML lead (0.9), W&B project (0.6), pin `requirements.txt` for 3.13 + 3.14 (0.10).

---

## Current status — updated 2026-10-04

**What was done:**
- Readiness audit and decisions D1–D21; hypotheses H5–H6 pre-registered.
- Repo scaffold on GitHub.
- **Stage 1 done — awaiting sign-off/merge.** Both audits run and written up in `docs/dataset_audit.md` and `docs/decisions.md`, with no TBDs and every cited number backed by a file in `docs/audit_evidence/`. Audit notebook ported, pinned, and confirmed in Colab.
- Stacked branch `stage-2-threat-model` created from `stage-1-audit-run` (Entry 9). **Stage 2 is CURRENT**: threat model **v0.2** (AI-assisted draft, citation fixes, D21), **not yet reviewed by the team** (Entries 10–12).
- Plan review against the Execution Plan (Entry 12): Phase 1 Issues board and Phase 2 preprocessing / manifests / compute benchmark not started; document discrepancies listed for a later fix.

**What we have:**
- FoR-2sec: a clean, balanced development set (17,721 clips, no duplicates, no corrupt files, uniform 16 kHz mono 2 s). No speaker metadata in filenames or the HF card. Re-split with near-duplicate groups at 0.95, stratified by REAL / FAKE_mp3 / FAKE_other, with val-A / val-B.
- One documented risk: MP3 history concentrated in FAKE, with bandwidth and silence differences between classes. H5 and H6 test whether the model exploits it.
- DEEP-VOICE: 64 long stereo files from 8 speakers (1,870 REAL / 13,090 FAKE windows), no overlap with FoR, untouched beyond the D20 accesses, pinned by D21. Rules for the one external run fixed in D17–D19. MIT license; public-figure rights noted as a limitation.
- A reproducible audit notebook that refuses to run on unpinned or changed data; full outputs archived in Drive.

**Branches:**
- `stage-0-git-workflow`: PR pending.
- `stage-1-audit-run`: frozen except the §10 sign-off.
- `stage-2-threat-model`: active; all log and `CLAUDE.md` updates go here.

**What we want:**
- A model that detects **synthetic voices**, not dataset accidents, and the evidence to prove which one it learned.
- Then one honest, one-time external test on DEEP-VOICE.

**What's next:**
1. Team meeting (see Open items): invitations, Stage 1 §10 sign-off, threat model review, tracks / W&B / compute / weekly sync, merge order.
2. PRs merged in order: stage-0 → stage-1 → stage-2.
3. Stage 2: threat model v0.2 → team review → sign-off (§14) → v1.0.
4. Stage 3: Experimental Protocol v1.0 (also fixes the D17 silence threshold). **It may be drafted now on a stacked branch, but it is frozen only after the Stage 1 sign-off.**
5. Before Stage 8: compute benchmark. In Stage 6: explicit silence-detector decision.
