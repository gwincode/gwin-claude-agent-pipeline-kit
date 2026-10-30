# HANDOFF — {{PROJECT_NAME}}

**Last updated:** YYYY-MM-DD — <one line: what this session did>
**Repo state:** `{{STAGING_BRANCH}}` `<sha>` · `{{PROD_BRANCH}}` `<sha>`.
**Divergence:** none (`{{PROD_BRANCH}}` has no commits `{{STAGING_BRANCH}}` lacks).

This file is **state, not history**: what is unpromoted, blocked, or next. Delete an entry once its work is
merged to `{{PROD_BRANCH}}` and production-verified. Don't archive; git history is the record. Keep it under
{{HANDOFF_MAX_LINES}} lines. Keep the `Last updated` and `Divergence:` lines: the freshness gate parses both
(dates are read in {{TIMEZONE}}).

**Pipeline feature entries:** every feature in flight gets a heading `## <feature> — <State>` (Designing ·
AwaitingDesignApproval · Building · InReview · OnStaging · AwaitingOwnerUAT · Promoting · Blocked) and,
directly beneath it, one ledger line. The orchestrator owns both; anyone else rewriting this file preserves
them verbatim. `/status` renders them. The entry format is shown in the kit's `handoff-example.md`.

## Next up

- **Discovery branches:** none open.

## Blockers and open decisions

- None.
