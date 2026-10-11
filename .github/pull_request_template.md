<!-- This text appears automatically when you open a Pull Request. Fill it in. -->

## What does this PR do?

_One or two sentences. One meaningful unit per PR._

## Stage and requirements

- Stage: <!-- e.g. Stage 3 -->
- SRS IDs / decisions: <!-- e.g. FR-13, PC-03, D12 -->
- Related issue: Closes #___ <!-- or "none" -->

## How did you test it?

_Real output of checks (`pytest -q`, validation scripts). No claims without output._

## Checklist

- [ ] I understand every line in this PR (including AI-generated parts)
- [ ] Branch name follows `<type>/stage<N>-<name>` (D23); commits follow Conventional Commits
- [ ] `pytest -q` passes (output pasted above) and CI is green
- [ ] Added/updated tests for new behavior
- [ ] DEEP-VOICE untouched (D20)
- [ ] No audio, datasets, checkpoints or secrets committed (checked for `.env`, keys, tokens)
- [ ] Updated `docs/CHANGELOG.md` if behavior changed
- [ ] Decision logged in `docs/decisions/` (D-ID row; ADR if major) if one was made
- [ ] `docs/project_log.md` updated (entry, Open items, Current status) if a stage or session ended
- [ ] PR base is `main` (stacked PRs: base switched to `main` before merging)

## AI assistance used

_Which tools helped and with what (e.g. "Claude Code drafted X, reviewed by Y"), or "none".
Every AI-produced artifact is reviewed by a team member before it is accepted._
