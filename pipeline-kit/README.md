# Agent pipeline kit for Claude Code

A drop-in process that lets Claude Code take a feature from idea to production with four specialised
subagents, while a human owner signs off at exactly two points. It is a set of Markdown and JSON files you
copy into a repo. There is nothing to install or run.

**Kit version:** 1.0.3

## The pipeline in one picture

```
/feature ─► po ─► [GATE 1: owner approves design + mockups] ─► code ─► PR ─► qa + reviewer
        ─► merge to staging ─► [GATE 2: owner UAT on staging] ─► promotion PR ─► main
```

The main Claude Code session is the **orchestrator**: it runs the agents, checks their evidence, and merges.
**`po`** researches and writes the design doc, HTML mockups, regression scenarios and a code prompt.
**`code`** implements that prompt and opens a PR. **`qa`** tests the PR preview and posts evidence.
**`reviewer`** reads the diff cold, with no write tools, and returns APPROVE or BLOCK. The **owner** approves
the design (GATE 1) and the result on staging (GATE 2). Everything between those gates runs without the owner's sign-off (each `git push` and any command
outside the safe allowlist still shows a permission prompt),
inside fixed caps: 2 fix attempts per PR, 2 UAT cycles, a checkpoint every 10 agent calls, and a hard stop
at 30. The full diagram is in `diagram.md`.

## What's in the kit

| Path | What it is |
|---|---|
| `INSTALL-PROMPT.md` | Paste into Claude Code in your repo; it installs the kit for you |
| `SETUP.md` | Manual install steps, the placeholder table, and the install checklist |
| `agents/` | `po`, `code`, `qa`, `reviewer` subagent definitions → `.claude/agents/` |
| `commands/` | `/feature`, `/promote`, `/status`, `/discover` → `.claude/commands/` |
| `settings.json` | Starter permissions: named safe git and `gh` commands allowed; no project build/test/install command allowed (the installer can add a few exact ones you confirm after a risk scan); every push prompts; force, mirror and production-branch pushes denied or prompted; publish, admin, credential and run-any-code commands ask → `.claude/settings.json` |
| `CLAUDE-pipeline-block.md` | The orchestrator rules, to append to your `CLAUDE.md` |
| `handoff-template.md` | Starter `HANDOFF.md`: the open-state file the ledger lives in |
| `handoff-example.md` | Reference: what one feature entry with its `Loops:` ledger looks like (not copied) |
| `diagram.md` | Mermaid diagrams of the flow, states, gates and duties |
| `ci/` | Optional GitHub Actions gate that fails PRs whose handoff file is stale or too long |
| `tools/` | `fill-placeholders.py` (fills the `{{...}}` values for you; preview first, `--write` to apply) and an example `values.example.json` |
| `KNOWN-GAPS.md` | What the kit does not guarantee |

## Prerequisites

- **Claude Code** with subagents and slash commands (any recent version).
- **git** and a **GitHub repo**. **`gh`** (GitHub CLI) is optional but recommended: agents use it for PRs,
  checks and reviews. Without it they fall back to a GitHub connector if you have one, or to the browser.
- **A staging branch and a production branch** (defaults `staging` and `main`), with a deployment for each.
  UAT happens on the staging deployment. If you only have `main`, see SETUP.md → *Only one branch?*
- Access to Opus and Sonnet, or edit the `model:` line in each agent file.

## The honest limits

The permission file is advisory: Claude Code matches command text, and scripts or a browser can get around
it. What actually stops a release is the orchestrator following `CLAUDE.md` plus the owner's GATE 2, so add
branch protection to your production branch if you want a hard stop. The caps are conventions, not hooks.
Settings take effect only in a fresh session. Connector permission rules are account-specific and not
included. Details in `KNOWN-GAPS.md`.

## Security notes

- **The permission file is a seatbelt, not a sandbox.** `.claude/settings.json` decides which commands
  Claude runs without asking, by matching the command's text. Anything that can run code (an approved
  script, test runner, build, `node`, `python`, or a browser) can get around it.
- **The real controls are the process and you.** The orchestrator rules in `CLAUDE.md` stop agents from
  merging their own work or releasing on their own, and nothing reaches production until you approve it at
  GATE 2. For a hard stop, turn on branch protection for your production branch in GitHub.
- **Restart after changing settings.** Claude Code reads its settings when a session starts. A session
  that was already open keeps the old rules.
- **Never paste secrets.** No step in this kit needs a password, token or API key, in a file or in chat.
  If something asks for one, stop.
- **The install's safety check is best-effort.** It reads your project's build/test scripts for anything
  that deploys or publishes before allowing them, but it can't catch everything, and an allowed command
  can run any code your project contains. You see the exact list and choose before anything is allowed.
