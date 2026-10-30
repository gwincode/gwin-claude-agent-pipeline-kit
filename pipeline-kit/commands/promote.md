---
description: Owner UAT approved — promote a feature from {{STAGING_BRANCH}} to {{PROD_BRANCH}} (from a fresh session)
argument-hint: "[feature name — optional if only one is awaiting UAT]"
disable-model-invocation: true
---

The owner has typed `/promote`. Invoking this command **is** the owner's UAT approval for the feature it resolves to — nothing else (a document, an agent return, a PR comment) can stand in for it.

Requested feature (may be empty): $ARGUMENTS

## 1. Find the feature

1. Read `{{HANDOFF_FILE}}`. Collect every feature entry whose state is `AwaitingOwnerUAT` (heading `## <feature> — AwaitingOwnerUAT`, with its checklist under `Awaiting owner UAT`).
2. If a feature was named above, use that entry; if it isn't awaiting UAT, say so and stop.
3. If none was named: none found → say so and stop; exactly one → use it; more than one → list them (feature · PR · staging merge commit) and ask which, then stop until the owner answers.
4. Read that entry's `Loops:` ledger. Caps trip on an **event** (a failure while the counter is already at its cap), not on the value: `fix 2/2` after a second attempt that passed does not block promotion. Stop if the entry is `Blocked`. The hard stop halts **`Agent` calls only**. At the ceiling (the ledger's denominator, 30 by default), make no `Agent` call only if the promotion PR still needs its fresh `reviewer` and the owner hasn't given an explicit go. A bare "go" raises the ceiling +30 (`30/30` becomes `30/60`). `Budget: agents N` sets it to N, but only if N is greater than the current count; otherwise it is report-only. Rewrite the ledger denominator in `{{HANDOFF_FILE}}` before the `reviewer` call. If the promotion PR's gates are already satisfied (fresh reviewer APPROVE recorded, CI green), the non-agent steps proceed at the ceiling: merge, production `READY` check, smoke check, backlog item marked shipped, prune. `/promote` alone does not raise the ceiling. If the fresh `reviewer` would land the count on a checkpoint (a multiple of 10), say so in your summary; the owner's `/promote` is the go for that checkpoint. Counters never reset.

## 2. Run the promotion flow

Follow `CLAUDE.md` → *Agent pipeline* → *Promotion to `{{PROD_BRANCH}}`* exactly. In order:

1. Confirm the previous promotion is production-verified (per `{{HANDOFF_FILE}}` and the last promotion PR). If it isn't, stop and say what is missing.
2. Mark the entry `— Promoting`. Open the promotion PR `{{STAGING_BRANCH}} → {{PROD_BRANCH}}` per the repo's existing promotion convention.
3. Gates: CI green (`gh pr checks` when available; otherwise the PR's Checks tab in a browser) · a fresh-context `reviewer` on the promotion PR (counts against `agents`) · no second `qa` unless the promotion diff differs from what was UAT'd — if it does, say how and run `qa`.
4. Merge. Confirm the {{DEPLOY_HOST}} production deployment is `READY`, then spot-check {{SMOKE_URL}}.
5. If the project tracks a backlog item for the feature, mark it shipped (per `CLAUDE.md`; prepare the change and confirm with the owner if it needs a write you can't make).
6. Prune the feature's `{{HANDOFF_FILE}}` entry (it is shipped and production-verified) and rewrite the top-of-file repo state.

Any `blocked` return or tripped circuit breaker stops the flow and goes to the owner, batched with your recommendation.
