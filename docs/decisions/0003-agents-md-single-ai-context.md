# 0003 — AGENTS.md is the single AI context

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-06 |
| Register | D22 |
| Deciders | Donia Mabrouk, Iheb Zemzemi, Malak Ben Salem |

## Context
The project rules lived in `CLAUDE.md`, which only Claude Code reads. The team may use several AI
tools (Claude Code, Codex, Antigravity, Gemini CLI). Separate per-tool rule files would drift apart,
and a rule (e.g. hard rule 1 on DEEP-VOICE) must be identical for every tool.

## Decision
- `AGENTS.md` at the repo root holds **all** project rules and pointers, written tool-neutrally.
- Tool files only point to it:
  - `CLAUDE.md` contains `@AGENTS.md` (Claude Code import) plus a short Claude-specific section;
  - `.gemini/settings.json` sets `{"context": {"fileName": ["AGENTS.md"]}}` for Gemini CLI;
  - Codex and Antigravity read `AGENTS.md` natively;
  - `AI_CONTEXT.md` explains this for humans.
- Rules are edited only in `AGENTS.md`. `AGENTS.md` stays concise (well under 32 KiB): rules and
  pointers, not copies of documents.

## Consequences
- One place to change a rule; every tool sees the same hard rules.
- Tool-specific files must not restate shared rules.
- Old log entries and decisions that say "`CLAUDE.md`" refer to the rules now in `AGENTS.md`.

## Links
`AGENTS.md` · `CLAUDE.md` · `AI_CONTEXT.md` · `.gemini/settings.json` · `CONTRIBUTING.md`
