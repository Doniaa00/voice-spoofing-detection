---
name: pr-prep
description: Prepare a branch of the voice-spoofing-detection repo for a pull request — run the tests, add the CHANGELOG line and project_log entry, check the DEEP-VOICE rule (D20), check for secrets, save the diff outside the repo and write the short PR report. Use this whenever someone says they are done with a change, wants to push, open or update a PR, "wrap up", "get this ready for review", or asks for the PR description or report, even if they don't mention this skill. The agent prepares; a human pushes, reviews and merges.
---

# pr-prep — get a branch ready for review

This repository is a team research project with strict rules (`AGENTS.md`). A pull request is the
only way into `main`, and a teammate reviews every one. Your job is to hand that reviewer a branch
whose claims are backed by real command output, so the review checks substance instead of
chasing missing steps. Read `AGENTS.md` first if it is not already in your context: it overrides
anything here.

Work through the steps in order. If a step fails, stop, report the failure with its real output,
and wait. Do not work around it, because a red step is exactly what the reviewer needs to know.

## 1. Check the branch

```bash
git branch --show-current
git status
git fetch origin
git log --oneline origin/main..HEAD
```

- The branch must not be `main`, and its name must follow `<type>/stage<N>-<name>` with type
  `feat`, `fix`, `docs` or `chore` (D23).
- Uncommitted work is fine at this point, but note it in the report.
- If `origin/main` has moved ahead, say so; the human decides whether to update the branch.

## 2. Run the tests first

```bash
python -m pytest -q
```

Every test must pass before anything else happens; the team rule is "never push on red". Copy the
final summary line (for example `33 passed in 15.80s`) into the report exactly as printed. Never
estimate it, and never report a test run you did not execute in this session.

## 3. DEEP-VOICE check (D20)

DEEP-VOICE is the external test set and is touched exactly once, in Stage 13 (AGENTS.md hard
rule 1). A change that reads, plays, plots or loads it any other way can invalidate the project's
central result, so this check matters more than any other.

```bash
python -m pytest -q tests/governance/test_deepvoice_access.py
git diff --name-only origin/main...HEAD
```

- The governance test must pass. It also scans untracked files, which is why step 6 saves the
  diff outside the repository.
- Read the list of changed files. If any change loads audio, datasets or features from outside the
  repository, or touches DEEP-VOICE beyond the accesses D20 permits, stop and report it instead of
  continuing.
- To extend the governance allowlist you need a decision, never a quiet edit.

## 4. Secrets and data check

```bash
git grep -n -E "gh[p]_|github_[p]at_|ctx7s[k]|sk-[A-Za-z0-9]{20}" || echo "no token found"
git diff --name-only origin/main...HEAD
```

- No token may appear. A reference such as `${CONTEXT7_API_KEY}` is fine; a literal value is not.
- No audio, dataset, checkpoint, `.env` or `.claude/settings.local.json` may be in the change
  (hard rule 7). If one is, stop and report it.

## 5. Documentation updates

Each merged PR adds one line to `docs/CHANGELOG.md` and one entry to `docs/project_log.md`.

- **CHANGELOG:** one short line under `## [Unreleased]`, in the right category (**Added**,
  **Changed**, **Fixed**, **Removed**). Match the style of the lines already there.
- **project_log:** append a new entry after the last one. Copy the heading format of the latest
  entry exactly (for example `### Entry 27 — Short title (YYYY-MM-DD)`) and use the next number.
  The log is append-only: never edit or reword an old entry. As AGENTS.md asks, also update the
  Open items and rewrite the Current status section. Name the AI tool used and what it did,
  honestly.
- **Decisions:** if the change introduces a decision, it needs a row in
  `docs/decisions/README.md` with the next free D-ID, and a major one also needs an ADR from
  `docs/decisions/TEMPLATE.md` (D24). Two open PRs may want the same number; flag that for the
  human instead of guessing.

## 6. Save the diff outside the repository

```bash
git diff origin/main...HEAD > ../pr-$(git branch --show-current | tr '/' '-').diff
```

The `../` matters: a diff file inside the repo would be scanned by the governance test and could
end up committed.

## 7. Write the report

Keep it to about 20 lines. Show real output, not summaries of output. Use this structure:

```
## PR report: <branch>
What changed: <2–4 lines, one per meaningful change>
Requirement / decision served: <FR-xx, NFR-xx, D-ID>
Checks (real output):
- pytest: <exact summary line>
- governance test: <exact summary line>
- token grep: <"no token found" or the hits>
Docs: CHANGELOG line added: yes/no · project_log Entry <N>: yes/no
Diff saved: ../<file name>
AI assistance: <tool, and what it did>
Open questions for the reviewer: <or "none">
→ WAITING FOR HUMAN REVIEW
```

Label claims as AGENTS.md does: [verified] for what you checked with a command, [doc] for what
comes from a document, [hypothesis] for anything else.

## What you never do

- Never merge, approve a PR, push to `main`, force-push, or change branch protection. "AI agents
  never merge" is a team rule; a human does those steps after a teammate reviews.
- Never edit old project_log entries, frozen documents (Protocol v1.0 and later freezes) or
  another person's section to make a check pass.
- Never call a step done without its real output.
