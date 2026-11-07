# Setup

You can let Claude Code do this for you (paste `INSTALL-PROMPT.md`), or follow these steps by hand. Either
way, nothing here runs a feature: installing only copies files.

## 1. Choose your values

Every `{{UPPER_SNAKE}}` token in the kit is a placeholder. Replace each one everywhere it appears.

| Placeholder | Meaning | Example / default | Used in |
|---|---|---|---|
| `{{PROJECT_NAME}}` | Human name of the project, also the session-name prefix | `Acme Notes` | agents, commands, CLAUDE block, handoff template, diagram |
| `{{REPO}}` | GitHub `owner/name` | `acme/notes` | agents, CLAUDE block |
| `{{STAGING_BRANCH}}` | Branch PRs merge into; UAT runs on its deployment | `staging` | agents, commands, CLAUDE block, ci, handoff template, diagram |
| `{{PROD_BRANCH}}` | Production branch; only the owner-gated promotion PR merges here | `main` | agents, commands, settings.json denies, CLAUDE block, ci, diagram |
| `{{DEPLOY_HOST}}` | Where preview, staging and production deploy | `Vercel`, `Netlify`, `Fly.io`, `none` | qa, feature, promote, CLAUDE block, diagram |
| `{{SMOKE_URL}}` | URL to spot-check after a production deploy | `https://notes.example.com` | promote, CLAUDE block, diagram |
| `{{TEST_COMMAND}}` | The command agents run for your tests (text in the agent instructions only; never an allow rule) | the detected test script, e.g. `npm test`; `pytest`; or `none` | code, qa |
| `{{MOCKUP_DIR}}` | Where `po` writes HTML mockups | `docs/mockups` | po, code, qa, reviewer, feature, CLAUDE block, diagram |
| `{{HANDOFF_FILE}}` | Open-state file holding the ledger | `HANDOFF.md` | everywhere |
| `{{HANDOFF_MAX_LINES}}` | Size ceiling for the handoff file | `250` | CLAUDE block, handoff template, diagram. **Also edit by hand:** `ci/handoff-freshness.json` has `"maxLines": 250` as a literal (JSON can't hold a placeholder there); change that number to the same value, unquoted |
| `{{TIMEZONE}}` | IANA zone the team dates the handoff in | `America/New_York`, `UTC` | code, discover, handoff template, ci |
| `{{HOUSEKEEPING_NOTE}}` | One or two sentences naming your per-PR chores, or a pointer to the `CLAUDE.md` section that lists them | `Bump the version in package.json and add a CHANGELOG.md entry; see CLAUDE.md → Per-PR housekeeping.` or `None beyond the defaults.` | po, code, CLAUDE block |

If `{{HOUSEKEEPING_NOTE}}` would be "none", don't substitute it: delete each line that contains it (one in
each of `agents/po.md`, `agents/code.md`, and the CLAUDE block). The fill tool in step 2 does this for you
when you give that key the value `null`.

`po` uses your product positioning as its strategic lens. If neither `CLAUDE.md` nor the README states it
("who it's for and why it's different", in a sentence or two), add it to `CLAUDE.md`; otherwise `po` asks you
once per feature.

### Project commands (build, lint, type-check, test)

**The starter `settings.json` allows no npm, pnpm or yarn command at all.** Out of the box, every build,
test, install or script run asks first. That is deliberate: yarn turns any unknown verb into a script or a
dependency binary (`yarn ci`, `yarn ls`, `yarn vercel` all run whatever has that name), npm and yarn also run
`pre<name>`/`post<name>` hooks, and the three tools differ on both. No wildcard rule is safe across them.

If you want the everyday commands to run quietly, add exact rules for *your* project. The install prompt
does this for you (`INSTALL-PROMPT.md` step 4); by hand it is:

1. **Detect the tool.** `package-lock.json` → npm; `pnpm-lock.yaml` → pnpm; `yarn.lock` → yarn (berry if
   there is a `.yarnrc.yml` or `"packageManager": "yarn@2+"`, otherwise v1). Anything else (bun, uv,
   pipenv, poetry, pdm, hatch, cargo, make, or no `package.json`) is **not supported**: add nothing, and
   every command asks. **A conflict is not supported either:** two or more lockfiles, or a
   `packageManager` field naming a different tool than the lockfile (`pnpm@9` with `package-lock.json`).
   You can't be sure which tool really runs, so add nothing.
2. **Pick at most one script per job** from `package.json` → `scripts`: build (`build`), lint (`lint`),
   type-check (`typecheck`, or `type-check`, `tsc`, `check`), test (`test`, or `test:unit`).
3. **Read each one, and drop it if anything it runs deploys, publishes, or writes somewhere remote.** Read
   the script, its `pre<name>` and `post<name>` hooks, and one level of anything it calls (another script via
   `npm run`/`yarn`/`pnpm`, a local `node scripts/x.js`, a shell file). Drop it if any of these appear:
   `vercel`, `netlify`, `firebase deploy`, `gh-pages`, `surge`, `wrangler`, `semantic-release`,
   `changeset publish`, any `publish`, `docker push`, `aws`/`gcloud`/`az`, `rsync`/`scp`, `curl … | sh`,
   `git push`, `rm -rf`, or a write outside the project.
   - **Drop anything you can't fully read.** Task runners and fan-out hide many scripts behind one name:
     `turbo`, `nx`, `lerna`, `npm-run-all`, `run-p`, `run-s`, `concurrently`, `--workspaces`/`-w`/`-ws`,
     `pnpm -r`/`--recursive`/`--filter`, `yarn workspaces foreach`, `make`, `just`, `task`, `docker
     compose`. Drop the script too if it calls something that calls something further you'd have to
     chase (another script, a `node` file or a shell file more than one step deep).
   - **Drop anything that points at production secrets:** `.env.production`, `dotenv -e`/`env-cmd` with
     a production file, `DATABASE_URL`, env variables ending in `_SECRET`/`_TOKEN`/`_KEY`, or a URL that
     looks like a live site. A test suite that touches a production database is a real risk
     (`KNOWN-GAPS.md` §1).
4. **Add exact lines only** (Bash and PowerShell), nothing with `*`:

   | Tool | Script job | Allow line |
   |---|---|---|
   | npm | build/lint/type-check | `"Bash(npm run <name>)"`, `"PowerShell(npm run <name>)"` |
   | npm | test | `"Bash(npm test)"`, `"PowerShell(npm test)"` (only if the script is named `test`; otherwise `npm run <name>`) |
   | pnpm | any | `"Bash(pnpm run <name>)"`, `"PowerShell(pnpm run <name>)"`; `pnpm test` for a script named `test` |
   | yarn | any | `"Bash(yarn run <name>)"`, `"PowerShell(yarn run <name>)"`. Never the bare `yarn <name>` |

   Never allow `install`, `ci`, `exec`, `dlx`, `publish`, or any wildcard. `install` and `ci` run your own
   project's `preinstall`/`install`/`postinstall`/`prepare` scripts and every dependency's install scripts,
   and bare `install` can rewrite the lockfile, so they always ask.

**Worked example** (yarn v1: `yarn.lock`, no `.yarnrc.yml`):

```json
"scripts": {
  "build": "next build",
  "postbuild": "vercel deploy --prebuilt --prod",
  "lint": "eslint .",
  "type-check": "tsc --noEmit",
  "test": "vitest run",
  "ci": "yarn test && vercel deploy --prod",
  "dev": "next dev"
}
```

Scan: `build` is dropped, because its `postbuild` hook runs `vercel deploy`. `lint`, `type-check` and `test`
are clean. `ci` and `dev` aren't one of the four jobs, so they are never considered and keep asking. Lines
added:

```json
"Bash(yarn run lint)", "Bash(yarn run type-check)", "Bash(yarn run test)",
"PowerShell(yarn run lint)", "PowerShell(yarn run type-check)", "PowerShell(yarn run test)"
```

The scan is best-effort (`KNOWN-GAPS.md` §1): a deploy hidden behind an unfamiliar command can slip past.
That is why you always see the exact list before anything is allowed. Know what you are allowing, too: an
allowed project command also runs your test files, config files (vitest, eslint, next, tsconfig plugins)
and build scripts, which an agent can edit. **An allowed project command is effectively permission to run
any code**, the same as approving `node`, and can reach `git push` or `gh` around the denies. Allow only
what you'd approve every time anyway.

`{{TEST_COMMAND}}` is only text in the agent instructions (the detected test command, e.g. `yarn run test`).
It never becomes an allow rule.

The concrete `npm publish`/`unpublish`/`exec`/`token`/`access`/`owner`, `pnpm publish`/`dlx`,
`yarn publish`/`dlx`/`npm publish`, `npx`, `pnpx`, `bunx`, `uvx`, `uv publish`, `uv tool run`, `pip install`,
`poetry publish`, `twine upload`, `cargo publish`/`install` and `gem push` rules are explicit `ask`. They
never match an exact `run <name>` line, so they don't interfere with yours.

Interpreters and fetchers (`node`, `python`/`python3`, `curl`, `wget`, `docker`, `make`) are explicit `ask`:
each one can run anything, so allowing one would void every other rule.

### Only one branch?

`{{STAGING_BRANCH}}` and `{{PROD_BRANCH}}` must be different branches. Setting both to `main` breaks the
model: every PR would merge straight to production with no UAT surface, and the settings would deny pushes
the pipeline needs. Pick one:

1. **Recommended: create a staging branch.** You do this yourself; the install never pushes a branch.
   `git switch -c staging origin/main && git push origin staging`, point a deployment at it (most hosts call this a branch or preview deployment), and make it the default PR
   base. Promotion is then a `staging → main` PR.
2. **Use the PR preview as the UAT surface.** Keep `{{STAGING_BRANCH}}` as a long-lived integration branch
   that nobody deploys, and tell the orchestrator in `CLAUDE.md` that UAT happens on the promotion PR's
   preview deployment instead. You lose "UAT on what's actually integrated", so prefer option 1.

## 2. Copy the files

From your repo root, with the kit at `pipeline-kit/`:

| Kit file | Destination |
|---|---|
| `agents/*.md` | `.claude/agents/` |
| `commands/*.md` | `.claude/commands/` |
| `settings.json` | `.claude/settings.json` (**merge** into an existing one; see below) |
| `CLAUDE-pipeline-block.md` | append to `CLAUDE.md` |
| `handoff-template.md` | `{{HANDOFF_FILE}}` (only if you don't have one) |
| `diagram.md` | `docs/architecture/agent-pipeline.md` (optional) |
| `ci/*` | see `ci/README.md` (optional) |

Then substitute the placeholders with the kit's fill tool (Python 3.8+, nothing to install):

1. Copy `pipeline-kit/tools/values.example.json` to `values.json` **outside your repo** (or don't commit
   it) and put your values from step 1 in it. Use `null` for `HOUSEKEEPING_NOTE` if you have no per-PR
   chores. Never put a password, token or key in it; none of the placeholders needs one.
2. Preview: `python pipeline-kit/tools/fill-placeholders.py ../values.json .claude CLAUDE.md {{HANDOFF_FILE}}`
   (write your handoff file's real name, usually `HANDOFF.md`; add `docs/architecture/agent-pipeline.md`
   and `.github` if you installed those; on Windows use `py` instead of `python` if `python` isn't found).
   Nothing changes yet; it lists the files it would change. If any path is mistyped, it changes nothing.
3. Apply: run the same command with `--write` at the end. It then lists any `{{...}}` still left. GitHub's
   own `${{ github.event... }}` expressions in the workflow file are not placeholders and are ignored.

Run it from your project's root folder (`cd` there first) and give it **simple relative paths inside that
folder**, exactly like the command above. It refuses absolute paths, drive letters, `..`, paths starting
with `~`, and on Windows any `:` or a name ending in a dot or a space, with the message "Run this from your
project folder and give it simple paths inside it, like .claude or CLAUDE.md."

Only fill your copies, never the files inside `pipeline-kit/` itself and never `.` (the whole project):
the tool refuses both (it refuses `.` because `.` contains the tool, which holds in the standard layout with
the kit inside your project). It refuses any path with a folder named `pipeline-kit` in it, so if your own
project folder is literally named `pipeline-kit`, rename it (or copy the files to a path outside it) first.

What the tool does to keep your files safe:
- It checks everything first: every path is allowed and exists, every file can be read, every file that
  would change can be written where it is (not read-only, and opening it for writing is allowed, which also
  catches a Windows permissions-list write deny), and with `--write` each folder of a file that would change
  accepts a new file. If anything fails, it changes nothing.
- It writes each file to a temporary `.fill-*.tmp` file in the same folder, then swaps it in, so a crash or
  a full disk can't leave a half-written `CLAUDE.md`. The temporary file is always cleaned up.
- If a write still fails part way, it tells you in plain words which files were already updated and which
  were not. It does not undo the ones already done; run the same command again and it fills only what is
  left.
- It checks every folder on the way from your project folder to each target on disk, and refuses a target
  that is, or goes through, a symbolic link, a Windows junction or another Windows reparse point. Inside a
  target it skips and lists links, reparse points and hard-linked files (the same file under two names).
  Checked on Windows (Python 3.9, 3.11, 3.13) and Linux (Python 3.12); macOS follows the same POSIX rules
  but was not run.
- It never clears a read-only setting or a permissions entry. Change those yourself if you want that file
  filled.
- The new file keeps only the old one's permission bits (on Windows, the read-only flag). It does not keep
  permissions-list (ACL) entries set on the file itself (it takes the folder's inherited permissions),
  Windows Hidden/System attributes, or POSIX owner, group, ACLs and extended attributes.

In a new handoff file, also replace `YYYY-MM-DD` with today's date in `{{TIMEZONE}}` and each `<sha>` with
the branch's real short SHA (`git rev-parse --short origin/<branch>`). The CI gate fails a handoff whose
`Last updated` line has no real date.

**Never overwrite existing files.** If `.claude/agents/code.md` or a `/feature` command already exists,
diff the two and merge by hand, or rename the kit's copy. For `settings.json`, add the kit's `allow`, `ask`
and `deny` entries to your existing arrays; keep your own entries. A rule in `deny` beats `ask`, and `ask`
beats `allow`. Some existing rules conflict with the kit, so check for them:

- **A blanket allow** (Bash or PowerShell form) of `npm run *`, `npm:*`, `yarn:*`, `pnpm:*`, `node:*`,
  `npx:*`, `python:*`/`python3:*`, `git:*`, `gh:*`, or `*`. Each one lets Claude run *anything* in that
  tool without asking, for example `npm run deploy` or `npm publish`, which cancels the kit's checks.
  Replace it with the exact project-command lines above (or, for git and gh, the kit's named rules).
  It's your call: if you keep one, know that it overrides the kit's safety design.
- **A `deny` on `git push*`** also blocks the pipeline's routine `git push origin claude/<branch>` and
  `/discover`'s push. Change it to `ask`; the kit already denies the dangerous push forms.

**An existing `## Agent pipeline` heading in `CLAUDE.md`** (any section with that name): don't append a
second one. Compare the two, merge the kit's rules into yours by hand, and keep one heading.

**An existing handoff file** needs three things the gate and `/status` read: a `**Last updated:** YYYY-MM-DD`
line, a `**Divergence:**` line, and feature entries in the `## <feature> — <State>` + `Loops:` format
(`handoff-example.md`). Add what's missing; keep everything else.

Also add `qa/` to `.gitignore` (screenshots land there) and create `claude/` with an empty
`claude/design-doc-index.md`. Commit `.claude/`, `CLAUDE.md` and `{{HANDOFF_FILE}}` so teammates and CI see
them.

The kit's `settings.json` is pure JSON with no comment keys: Claude Code validates its settings file, so
guidance lives here instead. What it does:

- Named git and `gh` subcommands run quietly. No npm/pnpm/yarn command does until you add your own exact
  lines (*Project commands* above). For `gh` that means
  `pr view/diff/checks/list/status/comment/review`, `pr create … --head <branch>`, `run view/list/watch`,
  `repo view`, `issue view/list`, and bare `auth status`. Within those, `pr comment --edit-last` /
  `--delete-last` and `pr review --approve` / `-a` ask: editing or deleting a comment rewrites the review
  record, and an approval can satisfy a required-review rule whenever the agent's GitHub identity is not
  the PR's author.
- Every `git push` prompts, and so does every other `gh` command.
- `gh pr merge`, `gh api`, repo admin, `release`, `secret`, `variable`, `workflow`, `alias`, `extension`,
  auth changes and `auth status --show-token` are explicit `ask`. So is `--output` on any git command,
  which can write a file anywhere, including `.git/hooks/`.
- Force, `+`, `--mirror`, `--all` and production-branch pushes are denied when written the way the patterns
  expect. Written another way, they only prompt: bundled short flags (`-uf`), abbreviated long options
  (`--forc`, `--mirr`, `--al`), and shell-split names (`m''ain`).

It is advisory: see `KNOWN-GAPS.md` §1.

## 3. Adding MCP connector rules

If your Claude Code has MCP connectors (GitHub, a deploy host, a database), their tools are named
`mcp__<server-id>__<tool>`. The server id depends on your account and client: a desktop session may show a
UUID-like id, and a CLI session may show a readable name. The kit can't know yours, so it ships none.

To find your ids, run `/mcp` in Claude Code, or ask Claude to list the tools it has from a server. Then add
rules to `.claude/settings.json`:

- **`allow`** read-only tools you want quiet: `"mcp__<id>__get_*"`, `"mcp__<id>__list_*"`, `"mcp__<id>__search_*"`.
- **`ask`** anything that writes to the repo or merges: `merge_pull_request`, `push_files`,
  `create_or_update_file`, `delete_file`, `create_branch`.
- **`deny`** anything irreversible or production-facing you never want an agent to run: database
  `apply_migration`, `delete_branch`, `reset_branch`, `pause_project`, deploy-host `delete_project`,
  `request_rollback`, `buy_*`, edge or serverless `deploy_*` tools.

A bare server id (`"mcp__<id>"`) matches every tool on that server, so use it only in `allow` for servers
that are entirely read-only. Rules only match the exact id you wrote; if another session spells the server
differently, those rules silently don't apply there.

To let the `reviewer` use a GitHub connector, see the comment at the top of `agents/reviewer.md`. Add read
tools only.

## 4. Verify the install

Start a **fresh** Claude Code session in the repo (settings load at session start), then check:

- [ ] `/agents` lists `po`, `code`, `qa`, `reviewer`, with models `claude-opus-5-5`, `claude-sonnet-5-5`,
  `claude-sonnet-5-5`, `claude-sonnet-5-5` (on Bedrock, Vertex or Foundry, your provider's IDs).
- [ ] Typing `/` shows `/feature`, `/promote`, `/status`, `/discover`.
- [ ] `/status` prints `0 open · 0 waiting on owner · no headroom: none · checkpoint due: none · hard stop: none`
      and `No feature entries in {{HANDOFF_FILE}} …` (on a fresh template).
- [ ] `git status`, `gh pr list` and `gh repo view` run without a prompt; `git push --dry-run origin HEAD`
      and `gh secret list` ask for approval; a push naming your production branch (plain spelling) is denied.
- [ ] No placeholder is left. Bash: `grep -rn "{{" .claude CLAUDE.md {{HANDOFF_FILE}} .github | grep -v '\${{'`
      prints nothing. PowerShell: `Get-ChildItem .claude, .github -Recurse -File | Select-String '\{\{' | Where-Object { $_.Line -notmatch '\$\{\{' }; Select-String '\{\{' CLAUDE.md, {{HANDOFF_FILE}}`
      prints nothing. (Skip `.github` if you didn't install the CI gate. The `${{ github.event … }}` lines in
      the workflow file are GitHub's own syntax and are expected.) `python pipeline-kit/tools/fill-placeholders.py ../values.json .claude CLAUDE.md {{HANDOFF_FILE}}`
      ending in `No placeholders left.` is the same check.
- [ ] Real date and SHAs filled in. Bash: `grep -nE "YYYY-MM-DD|<sha>" {{HANDOFF_FILE}}` prints nothing.
      PowerShell: `Select-String -Pattern 'YYYY-MM-DD','<sha>' -Path {{HANDOFF_FILE}}` prints nothing.
- [ ] `.claude/settings.json` has no blanket allow (`git:*`, `gh:*`, `npm:*`, `npm run *`, `yarn:*`,
      `pnpm:*`, `node:*`, `npx:*`, `python*:*`, `*`) and no `git push*` deny (unless you chose to keep
      one, knowing the trade-off above). Bash: `grep -nE ':\*\)|run \*\)|"\*"' .claude/settings.json`.
      PowerShell: `Select-String -Pattern ':\*\)','run \*\)','"\*"' -Path .claude/settings.json`. Every hit
      should be in the `ask` or `deny` list, not `allow`.
- [ ] If you installed the CI gate, `maxLines` in `.github/handoff-freshness.json` equals your
      `{{HANDOFF_MAX_LINES}}`, as a bare number.
- [ ] `python -c "import json; json.load(open('.claude/settings.json'))"` succeeds. (Under the kit's own
      settings this prompts, because `python` is `ask`; approve it, or run it in your own terminal.)
- [ ] If you installed the CI gate: `bash scripts/test-handoff-freshness.sh` ends with `0 failed`. (This
      prompts too: `bash <script>` matches no allow rule.)
- [ ] Each project command you allowed (e.g. `npm run lint`) runs without a prompt; any other script
      (`npm run dev`, `yarn ci`) asks. With no project-command lines added, all of them ask.
- [ ] **Dry run that touches nothing:** ask the session "Walk me through what `/feature` would do for the idea
      'dark mode toggle', step by step, without calling any agent or editing any file." It should name
      GATE 1, the `code` → `qa` + `reviewer` step, the merge gates, GATE 2, and the ledger seed
      `Loops: fix 0/2 · uat 0/2 · agents 1/30 · po-bounce 0/1`.

Your first real run: `/discover` (one research agent, no code), or `/feature Idea: …`.
