# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-10-06
- **Register:** D24
- **Deciders:** Donia Mabrouk, Iheb Zemzemi, Malak Ben Salem

## Context

As a team we make decisions throughout the project: which datasets and splits, which model, how to
guard the external test set, what trade-off to accept. Three weeks later nobody remembers *why*, and
we re-argue it or accidentally undo it. The project already keeps a decision register (D1–D21) that
overrides the Proposal and the Execution Plan. Some decisions are short and self-explanatory; others
(dataset pinning, single use of DEEP-VOICE, the AI-context setup) need their context and
consequences written down so a reviewer or a new session can understand them without the chat
history.

## Decision

- Every approved decision gets a D-ID row in `docs/decisions/README.md` (the register).
- **Major** decisions also get a short **Architecture Decision Record (ADR)** in this folder, one
  file per decision, numbered in order (`NNNN-short-title.md`) and created from `TEMPLATE.md`. The
  register row links to it.
- Each ADR has **Context** (what forced the decision), **Decision** (what we chose), **Status**
  (Proposed / Accepted / Superseded) and **Consequences** (what gets easier and what gets harder).
- An ADR is short, about half a page. It records *why we chose* something; *how* it works goes in
  `docs/architecture.md` or the stage documents.
- An ADR is never rewritten after acceptance; a change is a new ADR that supersedes it.

## Consequences

- The register stays the single list of what was decided; ADRs carry the reasoning for the big ones.
- New teammates and AI sessions can read the ADRs and understand the project's reasoning.
- We stop re-litigating settled decisions.
- Small decisions stay one-line rows and do not need an ADR.

## Links

`README.md` (register) · `TEMPLATE.md` · `AGENTS.md` (Working mode, Decisions)

---

> **How to add one:** copy `TEMPLATE.md` to the next number, fill it in, add the D-ID row to the
> register, and commit both in the same PR as the change it describes.
