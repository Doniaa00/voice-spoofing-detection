# Paste this into Claude Code (first session)

---

Read `CLAUDE.md` completely first, then `docs/decisions.md`. We are at **Stage 0: repo scaffold**.
This folder already contains the Stage 1 audit code (`src/audit/`, `tests/audit/`) and two docs.
**Do not modify those files**, except to move them if a path below requires it (it shouldn't).

Task: create the project structure from Execution Plan §0.5 (`docs/reference/Execution_Plan.md`),
adapted as follows:

```
voice-spoofing-detection/
├── CLAUDE.md                      # exists
├── README.md                      # short: purpose, decision-support disclaimer, setup, how to run tests
├── requirements.txt               # numpy, pandas, soundfile, librosa, pytest, pyyaml, huggingface_hub, kaggle
├── pytest.ini                     # pythonpath = .   testpaths = tests
├── .gitignore                     # data/* except data/manifests/ and data/README.md; *.wav *.flac *.mp3
│                                  #   *.pt *.ckpt *.npy; audit_out/; wandb/; .venv; __pycache__; .ipynb_checkpoints
├── configs/
│   ├── audit.yaml                 # data roots + output dirs for Stage 1 (placeholders, commented)
│   ├── baseline.yaml              # placeholder: "# filled in Stage 7"
│   └── cnn.yaml                   # placeholder: "# filled in Stage 8"
├── data/
│   ├── manifests/.gitkeep
│   └── README.md                  # data lives on shared Drive; DEEP-VOICE rule restated
├── docs/
│   ├── reference/                 # exists: the 4 project documents
│   ├── decisions.md               # exists
│   ├── dataset_audit.md           # exists
│   └── threat_model.md            # placeholder heading only
├── notebooks/
│   └── 01_stage1_dataset_audit.ipynb  # Colab runbook (see below)
├── src/
│   ├── audit/                     # exists
│   ├── preprocessing/__init__.py  # empty
│   ├── models/__init__.py         # empty
│   ├── evaluation/__init__.py     # empty
│   └── risk/__init__.py           # empty
├── api/.gitkeep
├── dashboard/.gitkeep
└── tests/
    └── audit/test_audit.py        # exists
```

The notebook `01_stage1_dataset_audit.ipynb` should contain, as separate cells, with a markdown cell
explaining each:
1. Mount Drive; clone or pull the repo; `pip install -r requirements.txt`; run `pytest -q`. Stop if tests fail.
2. FoR-2sec: get the dataset commit sha with `HfApi().dataset_info("UncovAI/FOR-2sec").sha`, then
   `snapshot_download(..., revision=sha)` into the Drive raw folder. Copy to `/content/data/for_2sec`.
   Print the sha. **Stop with an error if no audio files are found** (parquet-only snapshot).
3. DEEP-VOICE: `kaggle datasets download` (no unzip), print the zip's `sha256sum`, then unzip to
   `/content/data/deep_voice`. A markdown cell reminds the user: record the Kaggle version number; never
   open, play, or plot these files.
4. Dry run: `python -m src.audit.for2sec_audit ... --limit 500`.
5. Full FoR audit. 6. DEEP-VOICE metadata audit. 7. Cross-dataset byte-hash overlap check (expected 0).
8. Copy `audit_out/` to Drive `processed/metadata/stage1/`.

All paths are taken from `configs/audit.yaml`. Do not hardcode them in code cells.

Constraints:
- Do not write any preprocessing, model, training, or evaluation code. That belongs to later stages.
- Do not change anything in `src/audit/` or the tests.

Finish by running `pytest -q` and showing the real output. Print the final tree (`tree -a -I .git` or
equivalent). List anything in `CLAUDE.md` or the Execution Plan you found inconsistent with this layout.
Then stop and wait for approval.
