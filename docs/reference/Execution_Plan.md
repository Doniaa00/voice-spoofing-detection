# Voice-Spoofing Detection for Fraud Prevention — Execution Reference

**How to use this document:** this is the working reference for the whole semester — not something to read start to finish. When you're ready to start a step, say the step name/number and we'll go deep on it: code, exact commands, file-by-file implementation, debugging, whatever it needs. Everything below is scoped so each step is genuinely startable without waiting on anything else, except where a dependency is explicitly flagged.

Team: Donia Mabrouk, Iheb, Malak

---

## Phase 0 — Pre-Kickoff (before Week 1 officially starts)

| # | Task | Owner | Tool | Done when |
|---|------|-------|------|-----------|
| 0.1 | Download FoR-2sec (train/val/in-domain test set) | ML lead | Kaggle API or Hugging Face `datasets` (in Colab) | Files in the shared Drive `raw/` folder |
| 0.2 | Download DEEP-VOICE (frozen external test set) — see note below | ML lead | Kaggle API or Hugging Face (in Colab) | Files in the shared Drive `raw/` folder |
| 0.3 | Create GitHub repo, add all 3 members | Backend lead | GitHub | Repo exists, all 3 have push access |
| 0.4 | Set branch protection on `main` | Backend lead | GitHub Settings → Branches | PRs required, no direct pushes |
| 0.5 | Agree on repo folder structure | Whole team | — | Structure below adopted |
| 0.6 | Set up shared experiment tracking | ML lead | Weights & Biases (free tier) | Project created, all invited |
| 0.7 | Confirm compute per person | Whole team | — | Each person knows their GPU access (personal / Colab / Kaggle / university lab) |
| 0.8 | Agree on weekly sync time + async channel | Whole team | Discord/Slack | Channel created, first sync scheduled |
| 0.9 | Assign the three tracks | Whole team | — | ML/Research, Backend/Security, Frontend/Systems each owned |
| 0.10 | Establish reproducibility baseline | Backend lead + ML lead | `configs/` YAML files, `requirements.txt` | Python/PyTorch/CUDA versions pinned, random seed policy set, `configs/baseline.yaml` and `configs/cnn.yaml` exist (even if mostly empty placeholders for now) |

**Note — dataset plan, updated from earlier versions of this document:** the project went through several dataset iterations before landing here (ASVspoof 2019 LA, WaveFake, In-the-Wild were each evaluated and set aside — see the proposal's Section 6 for the full reasoning). The current, final plan is a self-contained pair: **FoR-2sec** for training/validation/in-domain testing, and **DEEP-VOICE** used exclusively as a frozen external test set — never trained or tuned on. This is a smaller engineering lift than any earlier version (both datasets are under 1.2 GB, both available via Kaggle/Hugging Face, no institutional-server blocking, no separate real-audio pairing needed) while preserving a genuinely rigorous cross-dataset generalization test: FoR's attacks are TTS-based (multiple engines — Deep Voice 3, WaveNet, Google/Microsoft/Amazon/Baidu TTS), DEEP-VOICE's are RVC voice-conversion — a fundamentally different synthesis paradigm, which is what makes the generalization question meaningful rather than trivial.

**Storage reality check:** FoR-2sec (~1.13 GB) + DEEP-VOICE (~0.55 GB) together comfortably fit within a free Google account's 15 GB Drive quota, with no subsetting or storage juggling required.

### 0.10 in detail — why this matters
Before any modeling starts, freeze: Python version, PyTorch version, CUDA version (if using GPU), all package versions (`requirements.txt`, pinned not loose), the random seed policy (e.g. seed=42 everywhere, set at the top of every training script), and the dataset version/location. Each experiment should conceptually be `dataset + config + code version → results`, not "open Colab and train." Add a `configs/` folder now:
```
configs/
├── baseline.yaml
├── cnn.yaml
└── robustness.yaml   # added later, in Phase 9
```
Each YAML records the hyperparameters, preprocessing settings, and dataset split used for that run — and gets logged to W&B alongside the results, so a checkpoint is never orphaned from the configuration that produced it. This avoids the classic mess of `model_final.pt`, `model_final2.pt`, `model_best_REAL.pt` with no record of which is which.

### Repo folder structure (adopt this now, don't improvise later)

```
voice-spoofing-detection/
├── data/                  # gitignored — NO audio committed here; see Data & Compute Workflow below
│   ├── manifests/         # small CSVs (path/label/split/source) — these DO get committed
│   └── README.md          # points to the Drive folder, so anyone cloning the repo knows where data lives
├── notebooks/             # Colab notebooks — exploration + training entry points
├── src/
│   ├── preprocessing/     # resampling, VAD, feature extraction
│   ├── models/            # baseline + deep model definitions
│   ├── evaluation/        # EER, accuracy/F1, ROC-AUC, confusion matrix harness
│   └── risk/              # authentic/synthetic/uncertain layer
├── api/                   # FastAPI app
├── dashboard/             # Streamlit or React app
├── tests/                 # pytest — mirrors src/ structure
├── docs/                  # requirements, threat model, architecture, reports
├── configs/               # baseline.yaml, cnn.yaml, robustness.yaml — pinned run configs (see 0.10)
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### Data & Compute Workflow — Kaggle + Google Drive + Colab
This is the team's chosen setup (decided to avoid loading ~10+ GB of audio onto personal machines). It changes *where* things run, not the pipeline logic itself — `src/` code should be written to accept a data root path as a parameter/config value, never hardcoded, so it works identically whether that root is a local folder or a mounted Drive path.

- **Download once, to Drive, not to Colab's local disk permanently.** Kaggle datasets get pulled via the Kaggle API directly into a shared Google Drive folder (e.g. `MyDrive/voice-spoofing-detection/data/`), so all three members hit the same copy without re-downloading.
- **At the start of each Colab session, copy the working subset from Drive to Colab's local disk** (`/content/data/`) rather than reading audio files directly off a mounted Drive during training. Drive-mounted I/O is noticeably slow for thousands of small audio files and will bottleneck training — copying a zipped dataset to local disk first (then unzipping) is the standard workaround.
- **Shared Drive folder structure** (mirrors the repo's `data/` intent):
  ```
  MyDrive/voice-spoofing-detection/
  ├── raw/for_2sec/               # training, validation, in-domain test set
  ├── raw/deep_voice/             # frozen external test set — never trained/tuned on
  ├── processed/
  │   ├── manifests/        # dataset manifests (also mirrored into the repo's data/manifests/)
  │   ├── features/         # cached extracted features, so preprocessing isn't rerun every session
  │   └── metadata/         # dataset stats, compatibility audit outputs
  └── checkpoints/
      ├── baseline/
      ├── cnn/
      └── experiments/      # one subfolder per W&B run ID, so a checkpoint is never separated from its config/results
  ```
- **Only manifests and code live in Git** — never commit audio or model checkpoints to the repo. `data/manifests/*.csv` (small, path references) are the only data-adjacent files that get versioned.
- **Before trusting either dataset's packaging:** run the Section 2's dataset audit (provenance, speaker/source distribution, license) rather than assuming the Kaggle/Hugging Face repackaging matches the original release's documentation exactly — do it once, up front, time-boxed.

### Compute plan (decide this now)
- **Primary:** Google Colab (free tier to start; upgrade to Colab Pro ~$10/month, split 3 ways, once the deep-model weeks arrive — free tier's session length and GPU availability are the usual bottleneck there).
- **Fallback:** Kaggle Notebooks — free 30 GPU-hours/week per account, so 3 accounts ≈ 90 hrs/week combined if Colab access gets tight.
- **Personal GPU**, if any team member has one, is a bonus for local iteration/debugging but isn't required given the Colab-first plan.
- Decide the Pro-vs-free split before Week 3 (baseline doesn't need GPU, but the deep model in Weeks 5–7 does).

---

## Phase 1 — Week 1: Requirements & Threat Modeling
**Owner:** whole team | **Depends on:** nothing — startable immediately

### Tasks
1. Write the functional requirements (what the system must do) and non-functional requirements (latency, audio formats accepted, logging, security) as a formal doc.
2. Define the fraud-analyst persona and the user story ("As a fraud-prevention analyst, given a suspicious call recording, I need...").
3. Finalize the threat model (attacker → synthesis → vishing → target → loss → detection point) — reuse the diagram from the proposal, refine if needed.
4. **Define explicit attacker capability assumptions** (see below) — this is what makes the cybersecurity framing concrete rather than implied.
5. Turn requirements into GitHub Issues, one per requirement, tagged by track (ml/backend/frontend).

### Attacker capability assumptions (write this down explicitly)
A threat model diagram shows the attack path; it doesn't pin down what the attacker can and can't do. Document both sides:
- **Attacker can:** obtain a short voice sample of the target (public recording, social media, a prior call); generate synthetic speech from it using accessible TTS/voice-conversion tools; transmit that speech through a real phone/recording channel (introducing codec/compression artifacts your Week 12 robustness stretch goal targets).
- **Attacker cannot (out of scope for this project):** modify or tamper with the detection service itself; access the model's internals or training data; alter the analyst dashboard or its outputs.
- **Worth noting as a limitation, not implementing:** an attacker aware that detection exists could in principle adapt (adversarial evasion). The project does not implement or defend against adversarial attacks on the detector itself — this is stated as an explicit limitation in the final report, not silently ignored.

### Tools
- Markdown or Google Docs for the requirements doc
- GitHub Issues + labels for tracking
- Any diagramming tool (draw.io, Excalidraw, or we can regenerate the threat model diagram) for any refinements

### Deliverable / Definition of Done
- `docs/requirements.md` committed, reviewed by all three
- Threat model diagram finalized in `docs/`
- Attacker capability assumptions documented in `docs/threat_model.md`
- GitHub Issues board populated for Week 1–2 work

---

## Phase 2 — Week 2: Dataset & Preprocessing
**Owner:** ML lead (with backend lead reviewing the pipeline interface) | **Depends on:** FoR-2sec + DEEP-VOICE downloaded (0.1, 0.2)

### Tasks
1. Run the dataset audit (below) **before** exploring further or writing preprocessing code against assumptions.
2. Explore both datasets: class balance, sample rates, clip durations, and — critically for DEEP-VOICE — confirm the documented class imbalance (628 bonafide vs. 4,425 spoof) in whatever packaging you actually downloaded.
3. Build the preprocessing pipeline as a clean, testable function chain:
   - Resample all audio to a consistent rate (16kHz).
   - Voice-activity detection to trim silence.
   - Feature extraction: MFCCs for the baseline; log-mel spectrograms for the deep model.
   - Apply identically to both datasets — the experiment tests speech authenticity, not incidental preprocessing differences between datasets.
4. Decide the group-aware train/validation/test split strategy for FoR-2sec **based on what the audit finds** (see below) — don't split randomly by clip if speaker/source-recording metadata is available.
5. Write unit tests for every preprocessing function.

### Tools
- `torchaudio`, `librosa`, `soundfile` for audio I/O and features
- `silero-vad` (lightweight, pip-installable) for voice-activity detection
- `pytest` for unit tests
- `pandas` for dataset manifests (filepath, label, split, source)

### Deliverable / Definition of Done
- `src/preprocessing/` with resampling, VAD, and feature-extraction functions, each unit-tested
- A dataset manifest CSV for both FoR-2sec and DEEP-VOICE (path, label, split, source)
- Exploration notebook in `notebooks/` documenting class balance and dataset stats
- **Dataset audit completed and written up** (see below) — this gates all model training, not just Week 8

### Dataset audit & leakage-aware split protocol (do this first in Week 2, time-boxed to one focused session)
This is a required methodological check, not optional due diligence — the entire project's central research claim (that FoR → DEEP-VOICE is a meaningful generalization test) depends on it. This is a fixed checklist, not an open-ended investigation — if information genuinely isn't available in the packaging, document that as a limitation and move on, don't keep digging for days:

- **FoR-2sec provenance** — confirm which TTS generation methods are actually represented in this specific 2-second repackaging (the original FoR release spans 6 engines; the 2-second Hugging Face/Kaggle packaging's own dataset card doesn't fully document what survived). Don't assume full diversity without checking.
- **Speaker / source-recording distribution** — identify whether multiple clips derive from the same underlying recording or speaker. This is the actual leakage risk: if related clips land on both sides of a random split, accuracy numbers will be inflated by the model recognizing recording/source characteristics rather than synthetic-speech properties.
- **Duplicate / near-duplicate detection** — check for repeated or highly similar segments.
- **Group-aware split decision** — if speaker/source metadata exists, split FoR at the group level, not the clip level. If it doesn't, document that limitation explicitly in `docs/dataset_audit.md` rather than proceeding with an ungrounded random split and not mentioning it.
- **DEEP-VOICE class balance** — confirm the actual bonafide/spoof counts in your downloaded copy; report raw accuracy on it with that imbalance stated, never bare.
- **License/redistribution terms** for both datasets.

Write all of this into `docs/dataset_audit.md`. This file is the answer to "how do we know this experiment means what we say it means" — treat it as a required artifact, not paperwork.

**The single hard rule this protects:** DEEP-VOICE is touched exactly once — evaluated on the final frozen model, after all model selection and threshold tuning is complete using FoR alone. No retraining, no re-tuning, no threshold adjustment based on DEEP-VOICE results. Violating this silently turns the external test into a second validation set and invalidates the whole generalization claim — this is worth repeating to the whole team, not just the ML lead, since it's the easiest rule to accidentally break under deadline pressure.

### Compute benchmark (do this before committing to Week 3's timeline)
Before relying on any compute plan for real, run a small benchmark rather than assuming it'll work: train your chosen CNN architecture on a small representative subset (not the full dataset) and record GPU type, VRAM, batch size, audio duration used, training time per epoch, and GPU memory usage. This tells you whether the free Colab tier is workable or whether Colab Pro / Kaggle fallback is needed *before* Week 5 arrives and it's suddenly urgent.

---

## Phase 3 — Weeks 3–4: Baseline Model
**Owner:** ML lead | **Depends on:** Phase 2 complete

### Tasks
1. Implement the classical baseline: MFCC features → GMM or SVM classifier (GMM is the traditional anti-spoofing baseline; SVM is a reasonable simpler alternative).
2. **Build the evaluation harness now — this is reused for every model for the rest of the project.** It must compute: accuracy, precision/recall/F1, EER, ROC-AUC, and the confusion matrix. (t-DCF is intentionally not used — it's defined specifically around ASVspoof's protocol, which this project no longer uses; see the proposal's Section 8 note.)
3. Log the first results to Weights & Biases, with the run's config (from `configs/baseline.yaml`) attached to the run.
4. Write up a short baseline results section for the final report now, while it's fresh.

### Tools
- `scikit-learn` (GMM via `sklearn.mixture`, SVM via `sklearn.svm`)
- Custom EER implementation (straightforward from the ROC curve — the false-accept/false-reject crossover point; no need for the heavier ASVspoof-specific t-DCF machinery)
- Weights & Biases for logging

### Deliverable / Definition of Done
- `src/models/baseline.py` + `src/evaluation/metrics.py`
- Baseline EER/accuracy/F1 numbers logged in W&B and written into `docs/results_baseline.md`
- Evaluation harness is a reusable module, not baseline-specific code

---

## Phase 4 — Weeks 5–7: Deep Model
**Owner:** ML lead (Backend/Frontend leads can start their own phases in parallel — see note below) | **Depends on:** Phase 3's evaluation harness

### Tasks
1. Implement a CNN over log-mel spectrograms as the **single primary deep model** — commit to this one architecture and evaluate it rigorously rather than splitting effort across several.
2. Train, tune (learning rate, architecture depth, augmentation), and compare against the baseline **on FoR-2sec only** (train/val/in-domain test) using the same evaluation harness. DEEP-VOICE is not touched yet.
3. Apply data augmentation relevant to the fraud scenario: additive noise, codec simulation (telephone-quality compression) — this doubles as prep for the Week 12 robustness stretch goal.
4. **Do not start the wav2vec2/WavLM fine-tune in parallel.** It's explicitly parked (see Week 12) — only touch it once the CNN is solid, evaluated end-to-end, and there's real time to spare. One well-evaluated model beats three partially-evaluated ones.
5. Once model selection and hyperparameters are finalized on FoR alone, **freeze the model.** No further tuning after this point — Phase 5 depends on that freeze being real.

### Tools
- **PyTorch** + `torchaudio` (model + training loop)
- `audiomentations` for augmentation
- Weights & Biases for training curves and run comparison
- (Parked, not used in this phase: `transformers` for wav2vec2/WavLM — see Week 12 parking lot)

### Note on parallelism
This is the natural point for Backend and Frontend leads to start their own tracks early rather than waiting idle:
- Backend lead can start scaffolding the FastAPI app structure and writing integration tests against a stub/mock model.
- Frontend lead can start the dashboard UI against mocked API responses.
Both integrate with the real model once it's ready — this avoids a bottleneck where two people wait on the ML track for 5 weeks.

### Deliverable / Definition of Done
- `src/models/deep_model.py`, trained checkpoint saved, model explicitly frozen (documented in W&B which run/checkpoint is final)
- Deep model beats baseline on the held-out FoR-2sec test split (if it doesn't, that's a documented finding, not a failure — report it honestly)
- Results logged and compared side-by-side with baseline in W&B

---

## Phase 5 — Week 8: Cross-Dataset Generalization
**Owner:** ML lead | **Depends on:** Phase 4 (frozen, finalized deep model)

### Tasks
1. Evaluate the frozen FoR-trained model on DEEP-VOICE — this is the core generalization experiment, and the model must not be modified in any way based on these results.
2. Compute the same metrics as Phase 3/4 (accuracy, precision/recall/F1, EER, ROC-AUC, confusion matrix), reporting DEEP-VOICE's class imbalance explicitly alongside the numbers.
3. Analyze *why* performance shifts — the hypothesis going in is that RVC voice conversion is a different synthesis paradigm than FoR's TTS-based attacks, so some degradation is expected and itself informative. Don't just report a number; explain it.
4. State the scope of the generalization claim precisely: this tests generalization to RVC voice conversion specifically, not to all possible modern voice-cloning methods — say so explicitly rather than overclaiming.
5. Write this up as its own report section — this is your strongest research contribution, give it real space.

### Tools
- Same evaluation harness from Phase 3
- `matplotlib`/`seaborn` for comparison plots (FoR in-domain vs. DEEP-VOICE external EER/accuracy)

### Deliverable / Definition of Done
- `docs/generalization_analysis.md` with numbers, plots, and a written interpretation, including the DEEP-VOICE class-imbalance caveat and the RVC-specific scope statement
- This section is explicitly referenced in the final report's abstract/intro as the project's key finding

---

## Phase 6 — Week 9: Risk & Confidence Layer
**Owner:** ML lead + Backend lead jointly | **Depends on:** Phase 4/5 (a trained model to wrap)

### Tasks
1. Define the thresholding logic: at what confidence range does a prediction become "uncertain" rather than a forced authentic/synthetic call?
2. Decide whether confidence comes directly from softmax output (simple, but often overconfident) or from a calibrated score (better, ties into the Week 12 stretch goal if pursued).
3. Build this as a standalone function: raw model output → `{prediction, confidence, risk_level}`.

### Tools
- Plain Python/NumPy for the thresholding logic
- `scikit-learn.calibration` if doing calibration now instead of as a stretch goal

### Deliverable / Definition of Done
- `src/risk/risk_layer.py`, unit tested with mock model outputs across the full confidence range
- Documented threshold values and the reasoning behind them

---

## Phase 7 — Week 10: API & Containerization
**Owner:** Backend lead | **Depends on:** Phase 6 (risk layer) — but scaffolding can start in Phase 4

### Tasks
1. Build the FastAPI app: `POST /analyze-audio` accepting an audio file, running preprocessing → model → risk layer, returning structured JSON.
2. Add basic request logging (timestamp, filename hash, prediction, confidence, latency).
3. Write the Dockerfile for the API; write `docker-compose.yml` to eventually run API + dashboard together.
4. Write integration tests hitting the actual endpoint.

### Tools
- **FastAPI** + Uvicorn
- `pydantic` for request/response schemas
- Docker + `docker-compose`
- `httpx` + `pytest` for integration tests

### Deliverable / Definition of Done
- `docker-compose up` brings up a working API
- `POST /analyze-audio` with a sample file returns a correct, well-formed JSON response
- Integration tests passing in CI

---

## Phase 8 — Week 11: Dashboard
**Owner:** Frontend lead | **Depends on:** Phase 7 (a live API to consume) — UI work can start earlier against mocks

### Tasks
1. Build the analyst dashboard: upload/submit audio, view prediction + risk level + confidence, view a history of past submissions.
2. Keep the UI decision-support framed — never present a verdict as certain fact (reflect the "authentic/synthetic/uncertain" language directly in the UI).
3. Basic styling — doesn't need to be beautiful, needs to be clear and credible for a demo.

### Tools
- **Streamlit** (fastest path to a working, demo-ready UI) — or React + Vite if the team wants the frontend portfolio reps
- If Streamlit: `requests` to call the FastAPI backend
- If React: `fetch`/`axios`, plus whatever component library the team prefers

### Deliverable / Definition of Done
- A non-technical person can submit audio and understand the result without explanation
- Dashboard containerized and added to `docker-compose.yml`

---

## Phase 9 — Week 12: Stretch Goals
**Owner:** ML lead, split by relevance | **Depends on:** Core MVP (Phases 1–8) stable

### Required — both of these, not a pick-two menu
1. **Robustness / degradation curve** — measure EER as a function of injected noise/compression/reverberation level, plot the curve; applied to FoR test data (and optionally DEEP-VOICE, carefully — see note). Directly ties the ML result back to the fraud scenario (real vishing calls aren't studio-quality audio).
2. **Confidence calibration** — apply temperature scaling or Platt scaling, verify with a reliability diagram / Expected Calibration Error. This is what makes the "uncertain" category from Phase 6 scientifically meaningful instead of an arbitrary threshold.

**Note on robustness + DEEP-VOICE:** if degradation testing is applied to DEEP-VOICE as well as FoR, this still counts as evaluation, not tuning — the model itself is not modified. Keep it that way; don't let robustness testing become a backdoor for indirectly tuning against DEEP-VOICE.

### Parking lot — only if both required goals are done with real time to spare, and never at their expense
- Speaker- or attack-specific held-out evaluation within FoR, if the Phase 2 audit's metadata supports it
- A second independent external dataset (ASVspoof, WaveFake, or In-the-Wild — each evaluated and set aside earlier in planning; still viable as a further generalization check)
- wav2vec2/WavLM fine-tune (highest ceiling, but only once the CNN MVP is fully evaluated)
- Explainability (spectrogram saliency) — deliberately lowest priority; audio explainability is less mature than image explainability and easy to over-promise

### Tools
- `scikit-learn.calibration`, `netcal` (calibration library) for calibration
- `audiomentations` for controlled degradation
- Same evaluation harness throughout

### Deliverable / Definition of Done
- Both required stretch goals documented with results and plots — regardless of outcome. A model that degrades sharply under distribution shift or channel noise is not a failed result; documented and explained, it's one of the project's most valuable findings.

---

## Phase 10 — Week 13: Testing & Monitoring Pass
**Owner:** Whole team | **Depends on:** everything else functionally complete

### Tasks
1. Full regression pass: run the entire test suite, fix anything broken.
2. Review logging/monitoring output — does it actually capture what you'd want to debug a production issue?
3. Bug triage session across all three tracks.
4. Optional: deploy the demo publicly to Hugging Face Spaces for easy sharing in portfolios.

### Tools
- `pytest` (full suite), GitHub Actions CI
- Hugging Face Spaces (Gradio or Streamlit) if deploying publicly

### Deliverable / Definition of Done
- No known critical bugs
- CI green on `main`
- (Optional) public demo link live

---

## Phase 11 — Week 14: Documentation & Delivery
**Owner:** Whole team | **Depends on:** everything

### Tasks
1. Finalize the full technical report (requirements, threat model, architecture, methodology, results, generalization analysis, limitations, conclusion).
2. Update architecture docs to match what was actually built (not just the plan).
3. Curate a demo audio set: a mix of clearly in-distribution and out-of-distribution samples, so the live demo actually shows the generalization story, not just easy wins.
4. Rehearse the presentation end-to-end at least twice as a team.

### Tools
- Word/Markdown for the final report (we can generate this as a formal document, same as the proposal)
- Slides tool of choice for the presentation

### Deliverable / Definition of Done
- Report submitted
- Demo rehearsed, timing checked against the presentation slot
- Repo README updated so it stands alone as a portfolio piece

---

## Standing Rules (apply every week, not just once)

- Don't start coding the deep model until four things are scientifically solid: the FoR-2sec provenance/leakage audit, the DEEP-VOICE external-test protocol (frozen model, evaluated once), the group-aware split strategy, and the exact EER/accuracy/F1 definitions. These are worth getting right before Week 5, not fixing retroactively.
- One strong, rigorously evaluated deep model beats three mediocre ones — resist the urge to run parallel architectures; the CNN is the only required model, everything else is parking lot.
- The dataset audit (Phase 2) gates all training — and DEEP-VOICE is evaluated exactly once, on the frozen final model, never for tuning. This is the single easiest rule to accidentally break under deadline pressure.
- Every training run gets logged to W&B with config + results — no exceptions, even for "quick tests."
- No direct pushes to `main` — PR + one reviewer, always.
- If a stretch goal is at risk of eating MVP time, drop it — the MVP core is non-negotiable, stretch goals are not.
- Report EER/accuracy/F1 with the confusion matrix for every model comparison, never accuracy alone.
- Any team member touching the pipeline should be able to explain the full flow end-to-end, not just their own track.
