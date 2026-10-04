# Data

No audio, datasets, or checkpoints are committed to this repo (see `CLAUDE.md` hard rule 7).
This folder holds only:

- `manifests/` — small CSVs (path, label, split, source) that pin down exactly which files
  belong to which split. These are the only data-adjacent files that get versioned.
- This README.

## Where the actual data lives

Raw audio lives on the team's shared Google Drive:

```
MyDrive/voice-spoofing-detection/
├── raw/for_2sec/               # training, validation, in-domain test set
├── raw/deep_voice/             # frozen external test set — never trained/tuned on
├── processed/
│   ├── manifests/               # mirrored into this repo's data/manifests/
│   ├── features/                # cached extracted features
│   └── metadata/                # dataset stats, audit outputs
└── checkpoints/
```

At the start of each Colab session, copy the working subset from Drive to `/content/data/`
before doing any heavy I/O — see `CLAUDE.md` → Compute and data.

## DEEP-VOICE — hard rule

DEEP-VOICE is an external, frozen test set. It is touched **exactly once**: the single guarded
evaluation run of the final, frozen ModelBundle. It is never used for training, tuning, threshold
selection, calibration, early stopping, model selection, or exploration — no listening, no
spectrograms, no feature statistics, no model scoring outside that one run. The only other
permitted access is `src/audit/deepvoice_metadata_audit.py` (metadata-only, decision D6). See
`CLAUDE.md` hard rule 1.
