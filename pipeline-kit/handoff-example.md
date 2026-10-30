# Handoff entry format (reference only, don't copy into your handoff file)

This is what one in-flight feature looks like inside `{{HANDOFF_FILE}}`. It lives in its own file so that a
fresh install has zero feature entries: `/status` reads every `## <feature> — <State>` heading in the
handoff file, including ones inside an HTML comment.

```markdown
## Example feature — InReview
Loops: fix 0/2 · uat 0/2 · agents 4/30 · po-bounce 0/1
- PR #<n> (`claude/<branch>`) → `{{STAGING_BRANCH}}`. Design `claude/example-design.md`; mockups `{{MOCKUP_DIR}}/example/`.
- Next: qa + reviewer verdicts, then merge to `{{STAGING_BRANCH}}`.

### Awaiting owner UAT
- [ ] S1 — <scenario> — <staging URL>
- [ ] S2 — <mockup state> — <staging URL>
```

Rules:
- The heading is `## <feature> — <State>`. State is one of Designing · AwaitingDesignApproval · Building ·
  InReview · OnStaging · AwaitingOwnerUAT · Promoting · Blocked.
- The `Loops:` line sits directly under the heading. The orchestrator owns it, and anyone else rewriting the
  file copies it verbatim.
- `Awaiting owner UAT` is added after the staging merge. The whole entry is deleted once the feature is on
  `{{PROD_BRANCH}}` and production-verified.
