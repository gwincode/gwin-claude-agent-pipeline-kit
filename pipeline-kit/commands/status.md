---
description: Read-only pipeline dashboard — one line per open feature from {{HANDOFF_FILE}}, with its loop ledger
argument-hint: "[--live]"
disable-model-invocation: true
allowed-tools: Read, Bash(gh pr view *)
---

Read-only. Read `{{HANDOFF_FILE}}` once and print a dashboard. Make no other tool calls — except, **only if** `--live` appears here: `$ARGUMENTS` — one `gh pr view <n> --json state,isDraft,mergeable,headRefName` per PR number found. Never edit any file, never start an agent. Finish in this one turn.

## What counts as a feature entry

A heading of the form `## <feature> — <State>` where `<State>` is one of:
Designing · AwaitingDesignApproval · Building · InReview · OnStaging · AwaitingOwnerUAT · Promoting · Blocked.
Its ledger is the `Loops:` line directly beneath, e.g. `Loops: fix 0/2 · uat 0/2 · agents 1/30 · po-bounce 0/1`. Denominators may differ from the defaults (the owner moves the agents ceiling per run with `Budget:` — e.g. `agents 6/40`); always parse both numbers, never assume 30.

Fixed sections (`What moved`, `Next up`, `Blockers and open decisions` and the like) are not feature entries — ignore them.

## Output

One line per feature entry, in file order:

```
<feature> · <State> · <Loops: line verbatim> · PR #<n> <branch> | no PR · waiting on: owner|CI|agent
```

- **waiting on** — `owner` for AwaitingDesignApproval, AwaitingOwnerUAT, Blocked; `CI` when the entry says CI is pending/red; `agent` otherwise (Designing, Building, InReview, OnStaging, Promoting).
- A heading with a State but no `Loops:` line directly beneath → print the line with `MALFORMED: no Loops: line` instead of the ledger.
- A heading whose State isn't in the list above → `MALFORMED: unknown state "<x>"`.

Then one summary line:

```
<N> open · <M> waiting on owner · no headroom: <feature (counter x/y), …> | none · checkpoint due: <feature (agents x/y), …> | none · hard stop: <feature (agents x/y), …> | none
```

A counter has **no headroom** when its left number ≥ its right number. That is informational, not a trip: a breaker trips only on a failure while at the cap (`CLAUDE.md` → *Circuit breakers*), so `fix 2/2` on a PR whose second attempt passed is healthy. For `agents`: **checkpoint due** when the count is ≥ 10 and a multiple of 10 (10, 20, …) and still below the ceiling. The owner's go is needed before the next agent call. **hard stop** when the count is ≥ the ceiling (the denominator, 30 by default). State should be in `{{HANDOFF_FILE}}`. The feature resumes only after the owner's explicit go raises the ceiling. A bare "go" adds +30 (`30/30` becomes `30/60`); `Budget: agents N` sets it to N, but only if N is greater than the current count; otherwise it is report-only. The orchestrator rewrites the denominator before the next `Agent` call. A hard stop halts agent calls only. Counters never reset. Append `(checkpoint due)` or `(HARD STOP)` to that feature's line as well. If there are no feature entries, print `0 open · 0 waiting on owner · no headroom: none · checkpoint due: none · hard stop: none` and, on a second line, `No feature entries in {{HANDOFF_FILE}} (pipeline idle or entries not yet in ledger format).`
