# Pull requests

Thanks for opening a PR. A few ground rules:

## Before opening
- [ ] Tests pass locally: `PYTHONPATH=. pytest tests/ -v`
- [ ] No new lint warnings from `ruff` or `pyright` (if configured)
- [ ] No secrets, keys, or tokens in the diff (gitleaks runs in CI on push)

## Scope
- One focused change per PR
- Keep the public CLI surface stable unless the change is explicitly a breaking one (call it out in the PR title)
- Match the existing module layout — `canopy/<thing>.py`, with tests in `tests/`

## Docs
If your change affects CLI behavior, update `README.md` and `docs/00-spec/PLAN.md`. If your change is a new architectural choice, add an ADR under `docs/02-decisions/`.

## Commit messages
Short subject line (50 chars or less), blank line, body explaining *why*. Reference any issues with `(#N)` at the end of the subject or in the body.

## License
By submitting a PR you agree your contribution is MIT-licensed, matching the project license.