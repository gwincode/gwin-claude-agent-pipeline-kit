# Known gaps

Read this before you rely on the pipeline. None of these is hidden; all of them are deliberate trade-offs or
work nobody has done yet.

1. **Permissions are advisory, not a control.** `settings.json` rules match only the command text Claude
   writes. Every tool is allowlisted by named safe subcommand; nothing is allowed as `<tool> *`. These
   holes remain:
   - **Interpreters and browsers.** `node`, `python3`, `npx`, `curl`, `docker` and `make` are `ask`, but
     once you approve one, its script can reach `git push`, `gh` or the GitHub UI without matching any
     rule. A browser extension (if you allow one) can use the GitHub web UI directly.
   - **Project commands (npm, pnpm, yarn).** The starter `settings.json` ships no rule for them, so every
     build, test, install and script run asks. No wildcard is safe: yarn turns any unknown verb into a
     script or a dependency binary (`yarn ci`, `yarn ls`, `yarn vercel`), npm and yarn run `pre`/`post`
     hooks, and the three tools differ on both. The installer may add a few exact lines after a risk scan
     (SETUP.md → *Project commands*). That scan is **best-effort**: it reads each script, its hooks and
     one level of what it calls, so a deploy hidden behind an unfamiliar command or deeper in a file can
     slip past. You always see the exact allowed list before it is written. **An allowed project command
     is effectively permission to run any code, the same as approving `node`.** `npm test`, `npm run
     lint` or `npm run build` also run your test files, config files (vitest, jest, eslint, next, babel,
     tsconfig plugins and the like) and build scripts, and an agent can edit all of those (Edit is
     allowed), as well as `package.json` itself. So an allowed project command can reach `git push` or
     `gh` around every deny. Allow only commands you would be comfortable approving every time anyway.
     The scan also can't see what a test *does* when it runs: a test suite that reads credentials from
     an env file and talks to a **production** database or API looks clean in `package.json`. The
     installer excludes scripts that name production env files or secrets, but a suite that does it
     inside its own code still slips past; keep tests pointed at test infrastructure. Monorepo task
     runners (turbo, nx, lerna, `npm-run-all`, workspace fan-out) hide many scripts behind one, so the
     installer never allows a script that uses one. `install` and `ci` are
     never allowed: they run your project's own `preinstall`/`postinstall`/`prepare` scripts and every
     dependency's install scripts, and bare `install` can rewrite the lockfile. bun, uv, poetry, pipenv,
     pdm, hatch, cargo and make projects get no lines at all. Concrete publish/token/`exec`/`dlx` forms
     are `ask`, but only under the spellings listed.
   - **`git fetch`.** `git fetch *` is allowed, and a refspec like `+src:refs/heads/<local>` can
     force-update a *local* branch. Nothing leaves your machine, and the old tip is recoverable from
     `git reflog`, but uncommitted-to-remote work on that branch can look lost.
   - **`gh`.** Merge, `gh api`, repo admin, releases, secrets, variables, workflows, aliases, extensions,
     auth changes and `--show-token` are `ask`. But once a prompt for `gh alias set`, `gh extension
     install` or `gh api` is approved, admin actions can run under names no pattern sees. `gh pr review`
     and `gh pr comment` are allowed, but `--approve`/`-a`, `--edit-last` and `--delete-last` ask: an
     approval can satisfy a required-review rule when the agent's identity isn't the PR author.
     `gh pr create` without `--head` can offer to push the current branch, which would skip the
     `git push` prompt, so the kit allows only the `--head <branch>` form, and `code` pushes with
     `git push origin <branch>` first.
   - **File writes.** `Edit`/`Write` are allowed and can write `.git/hooks/*`, `.git/config` or
     `.claude/settings.json` itself. A hook written that way runs on the next quiet `git commit`. Git's
     `--output=<file>` (log/diff/show/stash list) is `ask` for the same reason.
   - **Spelling.** Force, mirror, `--all` and production-branch pushes are denied only as the patterns
     spell them. Bundled short flags (`-uf`), abbreviated long options (`--forc`, `--mirr`, `--al`) and
     shell-split names (`m''ain`) fall through to the `git push` prompt.

   The real control on releasing to production is the orchestrator rules in `CLAUDE.md` plus the owner's
   two gates. Add server-side branch protection on your production branch if you want a hard stop.
1a. **The production-branch deny over-matches.** `git push * {{PROD_BRANCH}}*` also denies pushing a branch
   whose name starts with the production branch's name (`maintenance-fix` when it is `main`). This false
   positive is accepted. With `main` as production, a push of `main-fix` or `maintenance` is denied
   outright, not just prompted. Pick branch names that don't start with your production branch's name;
   the pipeline's routine `claude/<name>` branches never match.
2. **Settings apply only to new sessions.** A Claude Code session that started before you installed or
   changed `.claude/settings.json` keeps the old rules. Start a fresh session after installing.
3. **Connector rules are not portable.** MCP tool names carry an account-specific server id
   (`mcp__<server-id>__<tool>`). The kit ships no connector rules; you add your own (SETUP.md →
   *Adding MCP connector rules*). A different client or account may spell the same connector differently, so
   a rule written for one session may silently not match in another.
4. **Models and cost.** `po` defaults to Opus 5.5 (`claude-opus-5-5`); `code`, `qa` and `reviewer` default
   to Sonnet 5.5 (`claude-sonnet-5-5`). A normal feature is 5–6 agent runs; the default ceiling is 30 per
   feature. Opus runs are the expensive ones, including any one-run model upgrade the orchestrator makes.
   The full IDs pin the version, so a new model release does not change them; update the `model:` lines
   yourself when you want a newer model. On Bedrock, Vertex or Foundry the IDs can differ; use your
   provider's IDs. Change the `model:` lines if your plan or budget calls for it.
5. **Caps are conventions.** The fix-loop, UAT, bounce and agent-count caps are rules the orchestrator follows
   and records in the handoff ledger. No hook enforces them. A `PreToolUse` hook on `Agent` that counts calls
   is the mechanical upgrade; it is not built.
6. **Ledger state before the first PR is fragile.** The ledger lives in the handoff file, and is durable only
   once a PR carries it. A session that ends before a PR exists pastes the entry into chat; a fresh session
   that can't find it starts counting again at 1.
7. **`.claude/` must be committed to be shared.** Agents, commands and settings in `.claude/` reach teammates
   (and their Claude Code) only if the folder is committed. A `.claude/settings.local.json` is personal and
   should stay uncommitted.
8. **The CI gate needs a workflow-capable token.** Adding `.github/workflows/handoff-freshness.yml` needs a
   token with GitHub's Workflows permission. Most connector apps can't get it. The gate is optional.
9. **Browser QA depends on what your environment can reach.** `qa` drives a browser against a preview or
   staging deployment. Sandboxed or proxied sessions sometimes can't open those hosts; `qa` then reports
   what it couldn't check instead of passing it.
10. **Windows.** Claude Code on Windows exposes both a Bash (Git Bash) tool and a PowerShell tool, so the
    settings mirror every rule for both. In Git Bash, `git show <ref>:<path>` can have its path mangled by
    MSYS path conversion; prefix the command with `MSYS_NO_PATHCONV=1`. To run the CI gate's script or test
    suite locally on Windows, `pip install tzdata` first (Windows Python ships no time-zone database; without
    it the script falls back to a conservative UTC-minus-one-day date, and one time-zone edge-case test fails
    for that reason alone). The script sets its own output to UTF-8, so `PYTHONUTF8=1` is no longer needed.
    The gate itself runs on `ubuntu-latest`, where none of this applies (`ci/README.md` → *On Windows*).
11. **The fill tool's limits.** `tools/fill-placeholders.py` refuses any target with a folder named
    `pipeline-kit` in its path, so a project whose own folder is literally named `pipeline-kit` must be
    renamed (or its files copied elsewhere) first; this is accepted to keep the kit from filling itself. It
    accepts only simple relative paths inside the folder it is run from (no absolute paths, drive letters,
    `..` or `~`), so run it from the project root. Every folder on the way to a target is checked on disk for
    links; a symlink, junction or other Windows reparse point is refused. Windows marks some cloud-sync
    placeholder files (OneDrive "online-only") as reparse points too, so those are skipped; make them
    available offline or work outside the synced folder. If a write fails part way, files already updated
    are not rolled back; the tool says which, and re-running it finishes the rest. Hard-linked files are
    skipped, not filled. The new file keeps only the old one's permission bits (on Windows, the read-only
    flag): permissions-list (ACL) entries set on the file itself are lost (the new file takes the folder's
    inherited permissions), and Windows Hidden/System attributes and POSIX owner, group, ACLs and extended
    attributes are not preserved. A file you can't open for writing (read-only, or a write deny in its
    permissions list) is refused before anything changes. Checks and writes are separate steps, so a program
    that can already write your folders could swap a folder for a link in between (negligible in practice;
    the file itself is safe because the rename replaces a swapped-in link). Link handling was verified on
    Windows and Linux; macOS was not run.
