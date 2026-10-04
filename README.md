# Voice-Spoofing Detection for Fraud Prevention

A **decision-support** control that flags short speech recordings as authentic / synthetic /
uncertain, with a confidence score and a LOW/MEDIUM/HIGH risk level.

**This is not proof of fraud and not a biometric authenticator.** Every output is a signal for a
human fraud analyst to weigh alongside other evidence, never an automated accept/reject decision.

Research core: train on **FoR-2sec** (TTS speech), then evaluate the frozen system **once** on
**DEEP-VOICE** (RVC voice conversion) to measure cross-dataset generalization. See `CLAUDE.md` for
the full project brief and hard rules, and `docs/decisions.md` for the approved decision log.

Team: Donia Mabrouk, Iheb Zemzemi, Malak Ben Salem — semester AI project (MUST University).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Datasets are not stored in this repo. They live on the team's shared Google Drive; see
`data/README.md` for the layout and access rules.

## Running the tests

```bash
pytest -q
```

## Project status

See the roadmap table in `CLAUDE.md` for the current stage and what's done so far.
