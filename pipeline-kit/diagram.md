# Agent pipeline — how a feature ships

**Canonical rules:** `CLAUDE.md` → *Agent pipeline (orchestrator rules)* · **Agent definitions:** `.claude/agents/{po,code,qa,reviewer}.md`

This is the process diagram for how {{PROJECT_NAME}} features move from idea to production. Four subagents do the work; the main Claude Code session orchestrates; the owner touches it at exactly two gates. If this page and `CLAUDE.md` disagree, `CLAUDE.md` wins — fix this page. Install it as `docs/architecture/agent-pipeline.md`.

In the diagrams, `staging` means `{{STAGING_BRANCH}}`, `main` means `{{PROD_BRANCH}}`, and "deploy host" means {{DEPLOY_HOST}}. The Mermaid blocks deliberately contain no placeholders, so they render before and after substitution.

---

## 1. Overview — roles and the two owner gates

```mermaid
flowchart TB
    classDef owner fill:#f59e0b,stroke:#b45309,color:#000,font-weight:bold
    classDef orch fill:#dbeafe,stroke:#1d4ed8,color:#000
    classDef agent fill:#ede9fe,stroke:#6d28d9,color:#000
    classDef sys fill:#f3f4f6,stroke:#6b7280,color:#000
    classDef stop fill:#fee2e2,stroke:#b91c1c,color:#000

    K["👤 /feature<br/>idea · must · must-not · revenue · size"]:::owner
    PO["🤖 po  (opus)<br/>competitive research · engagement + revenue hypotheses<br/>design doc · HTML mockups · regression scenarios · code prompt"]:::agent
    CHK1["🎛️ orchestrator pre-check<br/>return trigger? revenue lever? dated citations?<br/>mockups not a form?"]:::orch
    G1{{"👤 GATE 1<br/>approve design + mockups<br/>+ regression scenarios"}}:::owner
    CODE["🤖 code  (sonnet)<br/>branch off staging · merge origin/main<br/>build to mockups · gates · housekeeping · rewrite handoff<br/>PR → staging"]:::agent
    QA["🤖 qa  (sonnet)<br/>suites · browser on PR preview<br/>every mockup state · evidence in qa/‹n›/<br/>PR comment"]:::agent
    REV["🤖 reviewer  (opus · read-only)<br/>cold diff · access control twice · scope vs mockups<br/>review via gh"]:::agent
    V1["🎛️ verify artifacts, not claims<br/>CI green · review visible · qa evidence exists<br/>handoff under ceiling · no owner click"]:::orch
    M1["⚙️ merge → staging<br/>staging deploy"]:::sys
    UATP["🎛️ staging READY → write UAT checklist<br/>(scenarios + mockup states, URL per screen)<br/>handoff ← Awaiting owner UAT"]:::orch
    STOP1["⏸ STOP — nothing moves toward main"]:::stop
    G2{{"👤 GATE 2<br/>UAT on staging<br/>(or /promote from a fresh session)"}}:::owner
    PROM["🎛️ promotion PR staging → main<br/>fresh reviewer · CI green<br/>qa again only if diff ≠ what was UAT'd"]:::orch
    M2["⚙️ merge → main<br/>production deploy"]:::sys
    DONE["🎛️ production READY · smoke check<br/>backlog item shipped · prune handoff entry"]:::orch
    BLK["⏸ blocked → owner decides<br/>(batched, not one at a time)<br/>also fires on: loop cap hit · same failure twice ·<br/>scope growth · ~40 tool calls w/o result"]:::stop
    CKP["⏸ agents checkpoint (every 10) → owner go to continue<br/>hard stop at ceiling (30) → state to handoff<br/>resume only on owner go: ceiling raised (30/30 → 30/60)"]:::stop

    K --> PO --> CHK1
    CHK1 -- "missing (max 1 bounce)" --> PO
    CHK1 -- "complete" --> G1
    G1 -- "changes (resume same po)" --> PO
    G1 -- "approve" --> CODE
    CODE --> QA
    CODE --> REV
    QA -- "VERDICT" --> V1
    REV -- "VERDICT" --> V1
    V1 -- "qa fail / BLOCK → fix (resume same code) · fix ≤ 2/PR · same failure twice = stop" --> CODE
    V1 -- "all gates green" --> M1 --> UATP --> STOP1 --> G2
    G2 -- "fail + notes → fix PR (resume same code) · uat ≤ 2/feature" --> CODE
    G2 -- "UAT approved" --> PROM --> M2 --> DONE
    PO -. "blocked" .-> BLK
    CODE -. "blocked" .-> BLK
    PROM -. "blocked" .-> BLK
    V1 -. "cap hit" .-> BLK
    G2 -. "2nd UAT fail" .-> BLK
    V1 -. "agents at 10 · 20 · ceiling" .-> CKP
    CKP -. "owner go (ceiling raised at hard stop)" .-> V1
```

**Reading it:** amber = owner, blue = orchestrator, purple = subagent, grey = system, red = a hard stop. The two amber hexagons are the only places the owner must act; everything else runs once the gates in §4 pass. Dotted lines are `blocked` returns, which always go to the owner.

---

## 2. Happy path — sequence

```mermaid
sequenceDiagram
    autonumber
    actor Owner
    participant Orch as Orchestrator
    participant po
    participant code
    participant qa
    participant rev as reviewer
    participant GH as GitHub / CI
    participant DH as Deploy host

    Owner->>Orch: /feature  (idea · must · must-not · revenue · size)
    Note over Orch: rename session → ‹project› vNEXT/‹feature›
    Orch->>po: design ‹feature›
    Note over po: competitive research (cited) · engagement + revenue hypotheses<br/>design doc · HTML mockups (phone + desktop, all states)<br/>code prompt · regression scenarios
    po-->>Orch: READY_FOR_CODE: awaiting owner approval
    Orch->>Owner: mockups + design summary + return trigger + revenue lever + comparables
    rect rgb(254, 243, 199)
        Note over Owner: GATE 1
        Owner-->>Orch: approve  (or change requests → resume po)
    end
    Orch->>code: implement claude/code-prompt-‹feature›.md
    Note over code: branch off staging · merge origin/main<br/>build to mockups · gates · housekeeping · rewrite handoff
    code->>GH: PR → staging
    code-->>Orch: STATUS: done · PR #35;n
    Note over Orch: rename session → ‹project› v‹ver›/PR#35;n/‹feature›
    par independent
        Orch->>qa: test PR #35;n
        qa->>DH: preview URL
        qa->>GH: PR comment: scenario table + evidence paths
        qa-->>Orch: VERDICT: pass
    and
        Orch->>rev: review PR #35;n (cold)
        rev->>GH: gh pr review --comment (body starts VERDICT: APPROVE)
        rev-->>Orch: VERDICT: APPROVE
    end
    Orch->>GH: verify checks green · review visible · qa/‹n›/ evidence exists
    Orch->>GH: merge PR #35;n → staging
    GH->>DH: deploy staging
    Orch->>DH: confirm staging READY
    Orch->>Owner: staging URL + UAT checklist (from scenarios + mockup states)
    Note over Orch: handoff ← "Awaiting owner UAT" · STOP
    rect rgb(254, 243, 199)
        Note over Owner: GATE 2
        Owner-->>Orch: UAT approved   (or fail + notes → resume code)
    end
    Orch->>GH: promotion PR staging → main
    Orch->>rev: review promotion PR (cold)
    rev-->>Orch: APPROVE
    Orch->>GH: merge → main
    GH->>DH: deploy production
    Orch->>DH: confirm production READY · smoke check
    Note over Orch: backlog item shipped · prune handoff entry
    Orch->>Owner: shipped v‹ver›
```

---

## 3. Feature lifecycle — states as recorded in the handoff file

```mermaid
stateDiagram-v2
    [*] --> Discovering: /discover
    Discovering --> [*]: proposals written, owner picks later
    Discovering --> Designing: owner picks /feature #n
    [*] --> Designing: /feature
    Designing --> AwaitingDesignApproval: po returns
    AwaitingDesignApproval --> Designing: owner requests changes (resume same po)
    AwaitingDesignApproval --> Building: owner approves (GATE 1)
    Building --> InReview: code opens PR
    InReview --> Building: qa fail or reviewer BLOCK (fix 1/2)
    InReview --> Blocked: 2nd fix fails · same failure twice · scope growth
    InReview --> OnStaging: all merge gates green → merged
    OnStaging --> AwaitingOwnerUAT: staging deploy READY
    AwaitingOwnerUAT --> Building: UAT fail + notes (uat 1/2)
    AwaitingOwnerUAT --> Blocked: 2nd UAT fail
    AwaitingOwnerUAT --> Promoting: UAT approved (GATE 2)
    Promoting --> Shipped: main merged · prod READY · smoke ok
    Shipped --> [*]: handoff entry pruned

    Building --> Blocked: any agent returns blocked
    Designing --> Designing: agents checkpoint or hard stop → wait · owner go
    Building --> Building: agents checkpoint (10 · 20) or hard stop (ceiling) → wait · owner go (hard stop — go = +30, 30/30 → 30/60 · Budget N = exactly N)
    Promoting --> Promoting: agents checkpoint or hard stop → wait · owner go (non-agent steps may proceed)
    InReview --> InReview: agents checkpoint or hard stop → wait · owner go (same rule)
    InReview --> Blocked
    Promoting --> Blocked
    Blocked --> Building: owner decides
    Blocked --> Designing: owner sends back to po
    Blocked --> [*]: owner drops the feature
```

Every entry carries its state in the heading and a loop ledger directly beneath — `## <feature> — Building` / `Loops: fix 1/2 · uat 0/2 · agents 6/30 · po-bounce 1/1` — updated by the orchestrator on each transition, so caps survive session boundaries. `/status` prints them all. A feature appears in `{{HANDOFF_FILE}}` from `Designing` through `Promoting`. Once `Shipped` and production-verified, its entry is **deleted** — the PR, the changelog, the design doc, and any `claude/pr-*-review-findings.md` are the permanent record.

---

## 4. Gates — what must be true to move

| Transition | Required | Who checks |
|---|---|---|
| `po` → owner | `RETURN_TRIGGER` present · `REVENUE_LEVER` present or reasoned `none` · dated competitor citations · mockups don't look like a form | Orchestrator bounces to `po` before owner sees it |
| owner → `code` (**GATE 1**) | Owner approves design doc, mockups, and regression scenarios (no separate scenario gate) | **Owner** |
| any fix loop | fix attempts < 2 · the failure is not the same one as last attempt · agent calls below the next checkpoint or ceiling | Orchestrator, from the ledger — exceeding a cap → `Blocked` or checkpoint |
| PR → `{{STAGING_BRANCH}}` | CI green · `reviewer` APPROVE visible on PR · `qa` pass with evidence in `qa/<n>/` · `{{HANDOFF_FILE}}` rewritten, ≤ {{HANDOFF_MAX_LINES}} lines · design + mockups + regression scenarios owner-approved on record | Orchestrator — against artifacts, not agent claims. **Autonomous — no owner click** |
| `{{STAGING_BRANCH}}` → owner | Staging deployment `READY` for the merge commit · UAT checklist (one line per scenario / mockup state, staging URL per screen) written under `Awaiting owner UAT` | Orchestrator, then **stops** |
| owner → `{{PROD_BRANCH}}` (**GATE 2**) | Owner says "UAT approved" (or `/promote`) | **Owner — no exceptions, not even docs-only** |
| promotion PR → `{{PROD_BRANCH}}` | Previous promotion production-verified · CI green · fresh `reviewer` APPROVE · no second `qa` unless the diff differs from what was UAT'd | Orchestrator |
| `{{PROD_BRANCH}}` → done | Production deployment `READY` · smoke check of {{SMOKE_URL}} passes · backlog item marked shipped (if tracked) · handoff entry pruned | Orchestrator |

---

## 5. Separation of duties

| Role | Can | Cannot |
|---|---|---|
| **po** | Research, write docs + mockups + code prompt, commit to `claude/po-*` branch | Write app code · apply migrations · open PRs |
| **code** | Branch, build, test, housekeeping, open PR against `{{STAGING_BRANCH}}` | Merge anything · push to `{{PROD_BRANCH}}`/`{{STAGING_BRANCH}}` · apply prod migrations · delete · commit secrets |
| **qa** | Run suites, drive a browser on the preview, post findings on PR, save evidence | Modify app code · touch production data · act on real users |
| **reviewer** | Read diff, review (`gh pr review`) | **Write files at all** (tool allowlist) · commit · push · merge |
| **orchestrator** | Sequence, verify, merge to `{{STAGING_BRANCH}}`, open/merge promotion PR after owner UAT | Write app code · merge a PR it authored code for · promote without owner UAT |
| **owner** | Approve design (GATE 1), approve UAT (GATE 2), decide `blocked` items, apply prod migrations, override model mix | — |

Author ≠ promoter holds at every merge: `code` writes, `reviewer` judges cold, orchestrator merges. The reviewer's tool allowlist (`Read, Grep, Glob, Bash`, optionally plus a GitHub connector's read tools) is what makes "independent" mechanical rather than aspirational.

---

## 6. Artifacts — where each thing lives

| Artifact | Path | Written by | Lifetime |
|---|---|---|---|
| Design doc | `claude/<feature>-design.md` | po | Permanent (indexed in `claude/design-doc-index.md`) |
| Mockups | `{{MOCKUP_DIR}}/<feature>/*.html` + `README.md` | po | Permanent — the UI spec `code` builds to and `qa` tests against |
| Code prompt | `claude/code-prompt-<feature>.md` | po | Permanent |
| Feature PR | GitHub, base `{{STAGING_BRANCH}}` | code | Permanent |
| QA evidence | `qa/<pr>/*.png` (gitignored) + PR comment | qa | PR comment permanent; files local |
| Review | GitHub review on PR; optional `claude/pr-<n>-review-findings.md` | reviewer (orchestrator commits the doc) | Permanent |
| Open state | `{{HANDOFF_FILE}}` | code (per PR), orchestrator (session end, UAT, promotion) | **Pruned on ship** — ≤ {{HANDOFF_MAX_LINES}} lines, optionally CI-enforced |
| Lessons | the relevant `CLAUDE.md` section | whoever finds one | Permanent |

---

## 7. Owner-only actions (never delegated)

Applying a production migration · deleting user data, branches, or files the session didn't create · any payment, purchase, or transfer · promotion to `{{PROD_BRANCH}}` · anything a subagent returns as `blocked`. The orchestrator prepares the action, states exactly what will happen, and waits for an explicit yes.

---

## 8. Circuit breakers — why the loop can't run away

| Breaker | Limit | On trip |
|---|---|---|
| Fix loop (qa fail / reviewer BLOCK → code → re-run) | **2 attempts per PR** | `Blocked` → owner, with both diffs and the finding |
| Same failure reproduced after a fix (a flaky-looking CI failure counts) | **0 retries** — stop immediately | `Blocked` — it's a misunderstanding, not a bug |
| Owner UAT fail | **2 cycles per feature** | `Blocked` — owner picks: re-design (po) or drop |
| `po` pre-check bounce | **1** | Second return goes to the owner as-is, gaps listed |
| CI re-trigger | **1 run per commit**, never re-run to "see if it passes" | Red is read, not retried |
| Per-agent effort | **~40 tool calls (~60 for `po` in Discovery mode) or ~3 attempts at one sub-problem** without a reportable result | Agent returns `blocked` with what it tried |
| Feature-level agent calls | **Checkpoint every 10** (10, 20); **hard stop at 30** (the ledger denominator) | Checkpoint: stop, report, wait for the owner's go. Hard stop: write state to the handoff and recommend a fresh session. A bare "go" adds +30 (`30/30` → `30/60`); `Budget: agents N` sets it to N only if N > current count. Counters never reset. A hard stop halts agent calls only |
| Scope growth | PR touches **> 2×** the files the prompt named, or adds a dependency / migration / env var the prompt didn't | `reviewer` BLOCKs on scope → `Blocked`, not a fix loop |

`Blocked` is terminal for the session. A breaker trips on an event — a failure while its counter is already at the cap — not on the value. These are conventions enforced by orchestrator rules; a `PreToolUse` hook (matcher `Agent`) that counts calls is the mechanical upgrade. Not built.

## 9. Commands

| Command | What it does |
|---|---|
| `/discover [theme] [count]` | Research-only → ranked proposals written to `claude/discovery-<date>.md` on branch `claude/discovery-<date>` (no PR). One `po` call |
| `/feature` + up to 6 lines (idea · must · must-not · revenue angle · size · budget), or `/feature #n` | Kicks off the pipeline; stops only at GATE 1 and GATE 2 |
| `/promote` | From a fresh session: finds the feature awaiting UAT and runs the promotion flow |
| `/status [--live]` | Read-only dashboard: one line per open feature with its ledger |
| "UAT approved" / "UAT fail: <notes>" | In the live orchestrator session |
