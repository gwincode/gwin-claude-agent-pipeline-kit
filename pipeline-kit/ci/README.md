# Optional CI gate: handoff freshness

Nothing in this folder runs until you copy it into place. It is inert here on purpose, because GitHub only
runs workflows under `.github/workflows/`.

## What it does

On every PR into `{{STAGING_BRANCH}}` or `{{PROD_BRANCH}}`, it fails the PR when:

- `{{HANDOFF_FILE}}`'s `Last updated` date is older than the newest commit the PR adds outside the exempt
  paths. Dates are compared as calendar dates in `timezone`, so a late-evening commit does not read as
  "tomorrow" in UTC.
- `{{HANDOFF_FILE}}` is longer than `maxLines`. The handoff is state, not history.
- `{{HANDOFF_FILE}}` is missing or has no parseable `Last updated` line.

It warns when `{{PROD_BRANCH}}` has commits `{{STAGING_BRANCH}}` lacks and the handoff has no
`Divergence:` line. Set `"divergenceMode": "fail"` to make that a failure.

Exit codes: 0 pass, 1 fail, 2 misconfiguration.

## Install

| Kit file | Copy to |
|---|---|
| `handoff-freshness.json` | `.github/handoff-freshness.json`. Substitute the placeholders, and change the literal `"maxLines": 250` to your `HANDOFF_MAX_LINES` value. It must be a bare integer (`300`), not a string: the script treats `"300"` as misconfiguration |
| `handoff-freshness.yml` | `.github/workflows/handoff-freshness.yml`. Substitute the two branch names |
| `check-handoff-freshness.py` | `scripts/check-handoff-freshness.py` |
| `test-handoff-freshness.sh` | `scripts/test-handoff-freshness.sh` |

If you put the scripts somewhere other than `scripts/`, update the workflow's `run:` line and the
`exemptPaths` list to match.

Check it locally with `bash scripts/test-handoff-freshness.sh`. It builds throwaway git repos in a temp
directory and needs only `git`, `bash` and Python 3.9+.

### On Windows

- Run the test script from Git Bash (it is a bash script), with `python3` on your `PATH`.
- Use a Python that has time-zone data. Windows Python ships none, so run `pip install tzdata` once (or
  `py -m pip install tzdata`). Without it the script falls back to a cautious UTC-minus-one-day date and
  one time-zone edge-case test fails. That one failure is about your machine, not the gate; the gate itself
  runs on `ubuntu-latest`, which has the data.
- The script switches its own output to UTF-8, so its ✅/❌ marks no longer crash a Windows console. You do
  not need `PYTHONUTF8=1`.

## The token you need

Creating or changing a file under `.github/workflows/` needs more than normal push rights:

- **A classic PAT** needs the `workflow` scope.
- **A fine-grained PAT** needs `Workflows: Read and write` as well as `Contents: Read and write`. Without
  it the push fails with *"refusing to allow a Personal Access Token to create or update workflow"*. That
  is the missing permission, not a branch-protection problem.
- **A GitHub App or MCP connector** usually cannot write there at all. The installer cannot add the
  permission; only the app's owner can request it.

If you can't get that permission, skip this gate. The pipeline works without it. The handoff rule is then
a convention the orchestrator follows, not a check CI enforces.
