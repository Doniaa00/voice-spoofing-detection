@AGENTS.md

## Claude-specific notes
- All shared rules live in `AGENTS.md` (imported above). Edit them there, never here (D22).
- Claude Code never merges a PR and never pushes to `main`; it pushes its branch and asks the team to
  open the PR.
- Commits authored with Claude Code end with the `Co-Authored-By` trailer for the model used, and the
  `docs/project_log.md` entry names Claude Code as the AI tool.
- Report checks with their real output (e.g. `pytest -q` from the project venv) before claiming success.
