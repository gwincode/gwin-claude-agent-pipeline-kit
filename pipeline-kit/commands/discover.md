---
description: Research-only — po returns N ranked feature proposals (no mockups, no design doc, no build)
argument-hint: "[theme] [count]   e.g. /discover revenue 5 · /discover onboarding · /discover"
disable-model-invocation: true
---

You are the orchestrator for a **discovery run**: research only, ranked proposals, nothing built. `CLAUDE.md` → *Agent pipeline (orchestrator rules)* is canonical; this command carries the boilerplate.

Arguments: $ARGUMENTS

## 1. Parse

- **theme** — every word of the arguments that isn't a trailing integer (e.g. `revenue`, `onboarding`, `social sharing`). None given → "whatever moves the needle most" (engagement and revenue together).
- **count** — a trailing integer, 1–10. None given → **3**.

## 2. Run `po` in Discovery mode — exactly one `Agent` call

Call `po` once with: "Discovery mode (see `.claude/agents/po.md` → *Discovery mode*). Theme: <theme>. Count: <count>. Date: <today, {{TIMEZONE}}, YYYY-MM-DD>." Do not resume or re-run it in this command. If it returns `blocked`, show the owner what it tried and stop — no second call.

This run is **not** a feature: it has no `{{HANDOFF_FILE}}` ledger entry and no PR (it does get a `Discovery branches:` line, step 3). The one `po` call is counted against the feature that later picks a proposal (`/feature #n` resumes it — see `feature.md`).

## 3. Record the proposals

1. `git fetch origin`, then create branch `claude/discovery-<date>` from `origin/{{STAGING_BRANCH}}` (append `-2`, `-3` … if it exists).
2. Write `po`'s return verbatim to `claude/discovery-<date>.md`, using the same suffix as the branch (`claude/discovery-<date>-2.md` for a same-day re-run), under a header with: theme, count, date, and the `po` agent id (so `/feature #n` can resume it while it is live).
3. Commit and push it to its own remote branch with `git push origin claude/discovery-<date>`. Name the branch and use no flags. Every `git push` prompts the owner (`.claude/settings.json`), so expect an approval prompt here. A branch cut from `origin/{{STAGING_BRANCH}}` tracks `{{STAGING_BRANCH}}`, so never use a bare `git push`. **No PR.**
4. Per `CLAUDE.md` → *Session end*, record it in `{{HANDOFF_FILE}}` on a `Discovery branches:` line under *Next up*: `claude/discovery-<date>` (date, theme). **Not on the discovery branch.** That branch has no PR and never reaches `{{STAGING_BRANCH}}`. Make the edit in the orchestrator's own session checkout, and land it with the next `{{STAGING_BRANCH}}` PR, which is the feature PR that picks a proposal or the session-end `{{HANDOFF_FILE}}` rewrite. If no PR is open when the session ends, say so in the return to the owner so the line isn't lost. The line is open state. Prune it when the owner picks a proposal (`/feature #n`) or discards the run. Delete the remote branch only on the owner's explicit yes.

## 4. Return to the owner

Print the ranked proposals (number · name · one-line idea · size · biggest risk), the "what I'd skip and why" lines, the file path and branch, and: "Pick one with `/feature #<n>` or `/feature <proposal name>`."

Rules: read-only everywhere except that one file on that one branch, and the `Discovery branches:` line in `{{HANDOFF_FILE}}` (session checkout, never the discovery branch). Data sources stay read-only. Nothing is designed, mocked, or built.
