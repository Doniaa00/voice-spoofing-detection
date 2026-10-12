# Data

No audio, datasets, or checkpoints are committed to this repo (see `AGENTS.md` hard rule 7).
This folder holds only:

- `manifests/` — small CSVs (path, label, split, source) that pin down exactly which files
  belong to which split. These are the only data-adjacent files that get versioned.
- This README.

## Where the actual data lives

Raw audio lives on the team's shared Google Drive:

```
MyDrive/voice-spoofing-detection/
├── raw/
│   ├── for_2sec_ff8c82c7.tar                       # FoR-2sec archive (pinned HF revision, D21)
│   ├── for_2sec_REVISION.txt                       # full HF revision of the archive
│   ├── deep-voice-deepfake-voice-recognition.zip   # frozen external test set — never trained/tuned on
│   └── deep_voice_ZIP_SHA256.txt                   # zip SHA-256 (D21)
├── processed/
│   ├── metadata/stage1/                            # Stage 1 audit outputs
│   │   ├── for2sec/
│   │   ├── deepvoice/                              # metadata only (D20)
│   │   └── cross_dataset_overlap.json
│   ├── manifests/                                  # planned (Stage 4+)
│   └── features/                                   # planned (Stage 4+)
└── checkpoints/                                    # planned (Stage 4+)
```

At the start of each Colab session, copy the working subset from Drive to `/content/data/`
before doing any heavy I/O — see `AGENTS.md` → Compute and data.

## DEEP-VOICE — hard rule

DEEP-VOICE is an external, frozen test set. It is touched **exactly once**: the single guarded
evaluation run of the final, frozen ModelBundle. It is never used for training, tuning, threshold
selection, calibration, early stopping, model selection, or exploration — no listening, no
spectrograms, no feature statistics, no model scoring outside that one run. The only other
permitted accesses are listed in decision D20 (download, zip hash, unzip, listings, and the metadata-only `src/audit/deepvoice_metadata_audit.py`). See
`AGENTS.md` hard rule 1.
