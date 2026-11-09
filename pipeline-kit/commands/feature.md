---
description: Kick off one feature of {{PROJECT_NAME}} through the agent pipeline (po → owner → code → qa + reviewer → {{STAGING_BRANCH}} → owner UAT → {{PROD_BRANCH}})
argument-hint: "#<n> | <proposal name> | Idea: … / Must have: … / Must not: … / Revenue angle: … / Size: … / Budget: …"
disable-model-invocation: true
---

You are the orchestrator for one {{PROJECT_NAME}} feature. Run it per `CLAUDE.md` → *Agent pipeline (orchestrator rules)* — that section is canonical; this command only carries the kickoff boilerplate. Diagram: `docs/architecture/agent-pipeline.md` (if you installed it).

## Owner's kickoff

$ARGUMENTS

## 0. Resume check — always first

Before parsing anything, read `{{HANDOFF_FILE}}` and look for a feature heading `## <feature> — <State>` whose `<feature>` matches the kickoff's first line. The match ignores case and strips any `Budget: agents N`, whether it sits on its own line or trails the name (`/feature foo Budget: agents 60` → `foo`). A `#<n>` never matches a heading. If one exists, it **wins over everything below**, including a discovery-proposal name match. In that case:
- Skip the proposal lookup and the empty-`Idea` check (step 1), and the new-entry seeding (step 2.2).
- Take the entry's state and `Loops:` ledger as authoritative and go straight to **2.1 Resume**.

Only when no heading matches does step 1 run.

## 1. Parse the kickoff (new features only)

Read these fields from the kickoff above. A missing or blank field means "po decides" (for `Must not`: "none"; for `Budget`: the default caps).

```
Idea:          who it's for, what they do, why they'd come back
Must have:     1–3 non-negotiables | "po decides"
Must not:      excluded scope | "none"
Revenue angle: hunch | "po decides"
Size:          "small — one PR" | "normal" | "big — split if needed"
Budget:        optional agents ceiling, e.g. "agents 40" | default 30 (checkpoints stay every 10)
```

**Picking a discovery proposal.** If the kickoff starts with `#<n>`, or its first line names a proposal (`/feature #2`, `/feature Streak reveals`), load that proposal from the **latest** discovery file only. That is the `claude/discovery-<suffix>.md` with the newest suffix: newest date first, then the highest same-day `-2`, `-3` …. Fetch `origin` and read it from its `claude/discovery-<suffix>` branch if it isn't on yours. A `#<n>` never refers to an older discovery file. Wherever you name the proposal (the summary, the entry's notes), write the full suffix, e.g. `discovery-2026-10-05-2 #2`.
- The proposal becomes the `Idea`. Its return trigger, revenue lever, and size pre-fill those fields unless the kickoff overrides them.
- In step 3, **resume the discovery `po` agent** (its id is in the file header) if it is still live, so the research isn't paid for twice. If it can't be resumed, start a fresh `po` seeded with the proposal text and the discovery file path.
- A `#<n>` with no matching proposal → list the file's proposals and stop.

A first line that matches neither a `{{HANDOFF_FILE}}` heading nor a proposal is a new idea: it is the `Idea` text.

If `Idea` is still empty, ask the owner for it in one line and stop. That is the only field you may ask for.

## 2. The ledger

**2.1 Resume** (from step 0). Rename the session per the entry's state, then check the ledger's `agents` count against its denominator (the ceiling):
- **Below a checkpoint:** continue from the entry's state in step 3. The next `Agent` call increments the count.
- **At a checkpoint** (a multiple of 10, below the ceiling): the owner typing `/feature <name>` is the go for that checkpoint. Continue.
- **At the ceiling (hard stop):** apply the one rule below. If this kickoff has `Budget: agents N` with **N greater than the current count**, or the owner says "go" in chat, rewrite the denominator in `{{HANDOFF_FILE}}` first, then continue. Otherwise, including `Budget: agents N` with N ≤ the current count, report state (entry, ledger, next step, open PR) and make **no** `Agent` call.

**2.2 New entry** (from step 1). Record the entry in your own working notes until a PR carries it:
`## <feature> — Designing` then `Loops: fix 0/2 · uat 0/2 · agents 1/30 · po-bounce 0/1`. The `po` run you are about to start counts as 1.
- A `Budget: agents N` override replaces the denominator, which is the hard stop: `Budget: agents 40` gives `agents 1/40`. It moves only the ceiling, never the checkpoint cadence. Agents never raise their own caps.
- A `/feature #n` run counts the discovery `po` call too, so it starts at `agents 1/…`, and the resume makes it 2.

**2.3 Checkpoints and hard stop.**
- When the count reaches 10, 20, … (every multiple of 10 below the ceiling), stop. Report what's done, what remains, and why continuing is worth it, then wait for the owner's go.
- When the count reaches the ceiling (30 by default), hard-stop. Write full state to the feature's `{{HANDOFF_FILE}}` entry (state, ledger, next step, open PR, agent ids worth resuming) and recommend the owner continue in a fresh session. The feature is paused, not dropped. The hard stop exists because context and token use are likely high by then.
- **Resuming past a hard stop (the one rule):** the ceiling rises only on the owner's explicit go.
  - A bare "go" in chat raises it by **+30** (one more block: `30/30` → `30/60`).
  - `Budget: agents N` on a resumed `/feature <name>` sets it to exactly N. N must be **greater than the current count**. If N ≤ count, nothing is raised and the session only reports.
  - Before the first `Agent` call, rewrite the ledger's denominator in `{{HANDOFF_FILE}}`.
  - Without that go, the session only reports state.
  - Counters themselves never reset.

**2.4** Increment `agents` on **every** later `Agent` call for this feature, runs and resumes alike. Always read the ceiling from the ledger's denominator; never assume 30. Apply 2.3 at each increment. `fix` is per PR, so a UAT fix PR starts at `fix 0/2`. `uat` and `agents` never reset.

## 3. Run the pipeline

- **po** — pass the parsed fields verbatim (for a picked proposal: resume the discovery `po`, per step 1). On a resumed entry (2.1), start at the entry's state, not here. When `po` names the feature, rename the session `{{PROJECT_NAME}} vNEXT/<feature>`. Pre-check the return per `CLAUDE.md` (return trigger, reasoned revenue lever, dated citations, mockups under `{{MOCKUP_DIR}}/<feature>/` that aren't a form); bounce at most **once**, then send the second return to the owner as-is with the gaps listed.
- **GATE 1 — owner.** Show the mockups and the design summary: return trigger, revenue lever, both metric hypotheses, comparables, **the regression scenarios**, and any `DECISIONS_NEEDING_OWNER` with `po`'s recommendation. Stop and wait. Change requests resume the same `po`.
- **code** — on approval, hand it the code prompt path. When it returns a PR, rename the session `{{PROJECT_NAME}} v<version>/PR#<n>/<feature>`.
- **qa + reviewer** — run both, independently. Fix loop per the circuit breakers: 2 attempts per PR, same failure twice = stop, scope growth = `blocked` to the owner.
- **Merge to `{{STAGING_BRANCH}}`** when every merge gate in `CLAUDE.md` holds, verified against artifacts (CI, the review on the PR, `qa/<n>/`), not agent claims.
- **UAT hand-off** — confirm the {{DEPLOY_HOST}} staging deployment is `READY`, write the UAT checklist (one line per regression scenario / mockup state, staging URL per screen) into the feature's `{{HANDOFF_FILE}}` entry under `Awaiting owner UAT`, give the owner the staging URL + checklist, and **stop**. If `{{DEPLOY_HOST}}` is `none`, there is no deployment: skip the `READY` check, write the checklist without staging URLs (say "no deploy host: run locally per `CLAUDE.md`" in its place), and tell the owner so.
- **GATE 2 — owner.** "UAT approved" → run the promotion flow in `CLAUDE.md`. "UAT fail: <notes>" → resume the same `code` with the notes (UAT cap: 2 cycles).

## 4. Rules for this run

- Stop only at GATE 1 and GATE 2, or on a `blocked` return / tripped breaker. Everything else runs without asking.
- Batch: collect `blocked` returns and owner decisions and present them together, each with your recommendation — never one question at a time.
- `blocked` is terminal for the session: no alternative route, no re-prompt, no fresh agent for a second opinion.
- Update the entry's state tag and `Loops:` line on every transition.
- Never promote to `{{PROD_BRANCH}}` without the owner's UAT approval in this conversation (or via `/promote`).
