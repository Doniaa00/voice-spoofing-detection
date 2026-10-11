# 0001 — Record architecture decisions

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-06 |
| Register | D24 |
| Deciders | Donia Mabrouk, Iheb Zemzemi, Malak Ben Salem |

## Context
The project already keeps a decision register (D1–D21) that overrides the Proposal and the Execution
Plan. Some decisions are short and self-explanatory; others (dataset pinning, single use of DEEP-VOICE,
the AI-context setup) need their context and consequences written down so a reviewer or a new session
can understand them without the chat history.

## Decision
- Every approved decision gets a D-ID row in `docs/decisions/README.md` (the register).
- **Major** decisions also get an Architecture Decision Record (ADR) in `docs/decisions/`, numbered
  `NNNN-short-title.md`, created from `TEMPLATE.md`. The register row links to it.
- An ADR is never rewritten after acceptance; a change is a new ADR that supersedes it.

## Consequences
- The register stays the single list of what was decided; ADRs carry the reasoning for the big ones.
- Small decisions stay one-line rows and do not need an ADR.

## Links
`README.md` (register) · `TEMPLATE.md` · `AGENTS.md` (Working mode, Decisions)
