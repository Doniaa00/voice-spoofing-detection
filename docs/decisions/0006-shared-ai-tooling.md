# 0006. Shared AI tooling v1: one skill and one documentation MCP server

- **Status:** Proposed
- **Date:** 2026-10-16
- **Register:** D27 in `README.md` (renumber to the next free D-ID at merge if Stage 5 takes D27)
- **Deciders:** Iheb Zemzemi (author), Donia Mabrouk (reviewer), Malak Ben Salem, Khalil Dridi

## Context

- The CS 488 handout "AI Coding: Skills and MCPs" recommends shared skills and MCP servers, with
  three rules: install only maintained servers and skills, a server runs with your permissions, and
  keep a small set enabled because every tool description costs context. [doc]
- Every member uses a different AI tool (Claude Code, Codex, Antigravity/Gemini). `AGENTS.md` is
  the single source of rules for all of them (D22). Skills and MCP config files are tool-specific
  (handout, "Where they go in each tool"). [doc]
- Hard rules that any tooling must respect: DEEP-VOICE is touched exactly once (AGENTS.md hard rule
  1, D20); no data or secrets in the repo (hard rule 7); AI agents never merge (AGENTS.md, Working
  mode). [doc]
- `tests/governance/test_deepvoice_access.py` scans the repository only. An MCP server that can
  read Google Drive, `/content/data` or Colab would reach the datasets without passing that test.
  [doc]
- The repository is a personal repository (`kahlanzzi/voice-spoofing-detection`) with three
  collaborators. `main` requires a PR, 1 approval and the `checks` CI job. An agent holding a
  collaborator's write-capable token could approve a PR as that collaborator, which would satisfy
  the approval rule without a human review. [doc]
- GitHub documents that fine-grained personal access tokens cannot be used to contribute to
  repositories where the user is a repository collaborator, and that each fine-grained token
  accesses resources of a single owner. [doc: GitHub Docs, "Managing your personal access
  tokens"] Not tested by a collaborator: the exclusion relies on GitHub's documentation and the team's
  agreement of 2026-10-16. [doc]
- The official GitHub MCP server offers a read-only mode (`--read-only` / `GITHUB_READ_ONLY=1`,
  or the `/readonly` remote URL) that removes write tools. [doc: github/github-mcp-server] This is
  a filter in the server, not a limit on the token. Issue #2156 reports write actions succeeding
  in v0.31.0 HTTP mode despite read-only. [doc] A write-capable token also stays usable outside the
  MCP server, for example from the agent's shell.

## Decision

Scope agreed by Donia Mabrouk and Malak Ben Salem on 2026-10-16, before the PR; final approval is
the PR review.

v1 of the shared AI tooling contains **one skill (`pr-prep`) and one MCP server (Context7)**. No
MCP server with GitHub write capability, file-system, Git, web-fetch or data access is
configured, and no MCP server is used for Stage 13.

1. **Skill `pr-prep`** in `.claude/skills/pr-prep/SKILL.md`, written with Anthropic's
   `skill-creator` (used as a tool, not committed). Procedure: `python -m pytest -q` passes first;
   `docs/CHANGELOG.md` line; `docs/project_log.md` entry (append-only); D20 check (no DEEP-VOICE
   access, governance test green); any diff saved outside the repo; report of at most ~20 lines
   with real output; the agent never merges or approves. Tools without native skill support
   (Codex, Gemini) follow the same file as plain instructions, pointed to from `AGENTS.md`.
2. **Context7** (Upstash, MIT licence; public library documentation) as a remote server in
   `.mcp.json`. The API key is referenced as `${CONTEXT7_API_KEY}` and set by each member in their
   own environment; no key is committed. Queries contain only library names and API questions,
   never project code, data descriptions or file paths.
3. **GitHub MCP is excluded from v1.** Read-only can be guaranteed at the token level only for the
   repository owner. For collaborators it would rely on a server-side filter while a
   write-capable token stays available. That does not meet "read-only, verified". Revisit only if
   the repository moves to a GitHub organization (members can then create fine-grained read-only
   tokens); that move needs its own decision.
4. **Excluded on purpose:** Filesystem MCP (Claude Code already has project-scoped file tools; a
   second server adds access without adding ability); Git MCP (the shell already provides Git, and
   the server exposes write operations); Fetch MCP (can download any URL, including Drive share
   links, which bypasses the governance test); Supabase, Postgres, Figma, Sentry, mcp-builder (no
   use in this project); Superpowers and other community skill collections (overlap with
   AGENTS.md Working mode; would need a full review first).
5. **Enabled per stage:**

   | Stages | Skills | MCP servers |
   |---|---|---|
   | 4–12, 14–16 | `pr-prep` | Context7 (optional, per member) |
   | 13 (DEEP-VOICE external run) | none needed | **none**; run from the Colab notebook, where `.mcp.json` is not loaded; Claude Code users disable project servers locally |
   | 17–19 | `pr-prep` (+ Stage 17 PR) | Context7; Playwright, `webapp-testing`, `frontend-design` only through a separate Stage 17 PR and decision |

6. **Adoption rule for later additions:** any new skill or MCP server is added by PR with a
   decision row, after its SKILL.md or source has been read, and its maintenance status and
   licence checked.

## Consequences

- Easier: every agent follows one PR procedure; current library docs reduce outdated API use.
- No new path to the datasets: no configured server can read Drive, Colab or `/content/data`.
- Forbidden: committing tokens (`.mcp.json` holds only `${VAR}` references); any MCP during
  Stage 13; adding servers or skills outside a decision.
- Harder: agents cannot read PRs, issues or Actions through MCP. Members check those in the GitHub
  web interface.
- Each member sets `CONTEXT7_API_KEY` locally and approves the project server in their own tool.
  Codex and Gemini users configure Context7 in their tool's own file with the same rule.
- To verify after merge: `claude mcp list` shows Context7 connected for a Claude Code user;
  `git grep` finds no token in the repository.

## Links

- D20, D22, D26; ADR 0003 (AGENTS.md as single AI context); ADR 0005 (DEEP-VOICE single use).
- CS 488 handout "AI Coding: Skills and MCPs".
- GitHub Docs, personal access tokens: fine-grained token limitations.
- github/github-mcp-server: read-only mode; issue #2156.
- upstash/context7 (MIT).
- PR: (to fill in).
