# Contributing

How the team (and any AI agent working with us) changes this repository. Project rules and hard
constraints are in `AGENTS.md`; decisions are in `docs/decisions/README.md`.

## Branches
- Never commit to `main`. `main` is protected: PR + 1 approval, no direct pushes.
- **One meaningful unit = one branch = one PR.**
- Branch name: `<type>/stage<N>-<name>` (D23), lower-case, hyphen-separated.
  - Types: `feat` (new capability), `fix` (bug fix), `docs` (documentation only), `chore`
    (tooling, config, repo structure).
  - Examples: `feat/stage6-preprocessing-profile`, `docs/stage3-experimental-protocol`,
    `fix/stage7-eer-tie-handling`. Cross-stage housekeeping may omit the stage: `chore/ai-context`.

## Commits
- [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<optional scope>): <summary>`,
  e.g. `docs(protocol): define val-A / val-B usage`, `fix(audit): fail on empty revision`.
- Small, reviewable commits with clear messages. Never commit audio, datasets, checkpoints or secrets.

## Pull requests
- Push the branch and open a PR against `main` using the PR template. 1 approval is required.
- Run `pytest -q` before opening the PR and paste the real output.
- If the PR records a decision, add the D-ID row to `docs/decisions/README.md` (and an ADR for a
  major decision, D24).
- **Stacked PRs:** if your branch starts from another open branch, switch the PR base to `main` once
  the PR below it is merged, *before* merging. Never merge a PR whose base is not `main` unless that
  is intended.
- Delete the branch after merge, once its content is confirmed in `main`.

## AI assistance
- **Human in the loop:** every AI-produced artifact (code, documents, analysis) is reviewed by a team
  member before it is accepted. AI output is never merged, cited or reported as verified without
  that review.
- **AI agents never merge** and never push to `main`. They push a branch; a human opens and merges the PR.
- Disclose AI assistance in the PR (which tool, for what) and in `docs/project_log.md`.
- **Responsible use:** never paste secrets (API tokens, Kaggle/HF keys, passwords) or private data
  (personal recordings, anything not already in the repo) into an AI chat or prompt.
- AI agents follow `AGENTS.md`, including hard rule 1: DEEP-VOICE is never opened, played, plotted or
  scored outside the permitted accesses (D20).

## Issues
- Features: one issue per SRS requirement (FR / NFR / PC ID), tagged by track (`ml` / `backend` /
  `frontend`), grouped under one milestone per stage. Use the issue templates.
