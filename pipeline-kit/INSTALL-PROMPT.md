# Install prompt

Put the `pipeline-kit/` folder at the root of your repo, open Claude Code there, and paste everything
between the lines below.

---

Install the agent pipeline kit in this repository. The kit is in `pipeline-kit/`.

1. **Read the kit first.** Read `pipeline-kit/README.md`, `SETUP.md` and `KNOWN-GAPS.md` in full, then
   skim every other file in `pipeline-kit/`. `SETUP.md` is your procedure and its placeholder table is the
   list of values you need.

2. **Look before asking.** Detect what you can: the GitHub remote (`git remote -v`), the default and other
   branches (`git branch -r`), the package manager and test command (lockfiles, `package.json` scripts,
   `pyproject.toml`, `Makefile`), the deploy host (`vercel.json`, `netlify.toml`, `fly.toml`, workflow
   files), an existing `HANDOFF.md`, `CLAUDE.md`, `.claude/agents/`, `.claude/commands/`,
   `.claude/settings.json`, and an existing changelog or version file.

3. **Interview me once.** In a single message, list every placeholder from the `SETUP.md` table with your
   proposed value (detected, or the table's default), and ask me to confirm or correct them all at once.
   Also ask: whether to install the optional CI gate, and whether to install `diagram.md`. If the repo has
   no staging branch, say so and recommend option 1 in `SETUP.md` → *Only one branch?*; never set the
   staging and production branches to the same value. For `TEST_COMMAND`, propose the test command you
   found in step 4 (or `none`); it is only text for the agents, never a permission. Do step 4's detection
   and scan before you write this message, and put its summary (4d) in it, so I answer everything once. Wait for my answer. Don't ask again unless an answer
   is contradictory.

4. **Project commands (do this yourself; don't make me understand it).** Decide which of my project's
   everyday commands Claude may run without asking. Never use the words "package runner" or "lifecycle
   script" with me.
   a. **Detect the tool from lockfiles.** `package-lock.json` → npm. `pnpm-lock.yaml` → pnpm. `yarn.lock`
      → yarn (berry if `.yarnrc.yml` exists or `package.json` has `"packageManager": "yarn@2…"` or later,
      otherwise v1). Anything else (bun, uv, pipenv, poetry, pdm, hatch, cargo, make, or no
      `package.json`) is not supported. **Conflicts count as unsupported too:** more than one lockfile
      (including `bun.lockb`/`bun.lock` next to another), or a `packageManager` field that names a
      different tool than the lockfile (e.g. `pnpm@9` with `package-lock.json`). When unsupported, allow
      nothing and skip b–e. Tell me in this one sentence and no other: "I can't safely pre-approve
      commands for this project, so Claude will ask before running any of them." For a conflict, add one
      plain clause saying why, e.g. "(it has both an npm and a yarn lockfile, so I can't tell which one
      really runs)".
   b. **Pick candidates for four jobs** from `package.json` → `scripts`: build, lint, type-check, test.
      Use the exact names first (`build`, `lint`, `typecheck`, `test`); otherwise map a common alias
      (`type-check`, `tsc` or `check` for type-check; `test:unit` for test) and show me the mapping.
      At most one script per job.
   c. **Risk-scan every candidate yourself.** Read the script body, its `pre<name>` and `post<name>`
      scripts, and one level of whatever it calls: another script (`npm run x`, `yarn x`, `pnpm x`), a
      local `node scripts/x.js`, or a shell file. Exclude the candidate if anything there deploys,
      publishes, releases, uses credentials or cloud CLIs, or writes somewhere remote: `vercel`, `netlify`,
      `firebase deploy`, `gh-pages`, `surge`, `wrangler`, `semantic-release`, `changeset publish`, any
      `publish`, `docker push`, `aws`, `gcloud`, `az`, `rsync`, `scp`, `curl … | sh`, `git push`,
      `rm -rf`, or a write outside the project. For each exclusion, tell me in plain words, e.g. "`build`
      also runs `postbuild`, which deploys, so I won't auto-allow it."
      **Also exclude anything you can't fully read.** Treat a candidate as unscannable if it (or a hook or
      script it calls) uses a task runner or runs many scripts at once: `turbo`, `nx`, `lerna`,
      `npm-run-all`, `run-p`, `run-s`, `concurrently`, `--workspaces`/`--workspace`/`-w`/`-ws`,
      `pnpm -r`/`--recursive`/`--filter`, `yarn workspaces foreach`, `make`, `just`, `task`
      (Taskfile), `docker compose`/`docker-compose`; or if it calls another script, a `node` file or a
      shell file that calls something further you can't open in one step. Plain reason, e.g. "`build`
      hands off to a tool that runs the build in every sub-project, and I can't check all of those, so I
      won't auto-allow it."
      **And exclude anything that points at production secrets.** If the script, a hook, or the file it
      runs mentions `.env.production`, `dotenv -e`/`dotenv-cli`/`env-cmd` with a production file,
      `DATABASE_URL`, an env variable ending in `_SECRET`, `_TOKEN` or `_KEY`, or a URL that looks like a
      live site rather than `localhost`/a test host, exclude it. Plain reason, e.g. "`test` loads your
      production settings file, so it might touch real data; I won't auto-allow it."
   d. **Show one plain summary:** "I'll let Claude run these without asking: `<exact commands>`.
      Everything else will ask first. I checked these for anything that deploys or publishes, but I can't
      catch everything." Offer three answers: **Looks good** (the default; "ok", "yes" or "I don't know"
      all mean this), **Let me choose** (a yes/no for each command), or **Skip** (ask me every time). If a
      candidate was excluded, Looks good still applies to the rest. If nothing safe was found, say the same
      single sentence as in 4a ("I can't safely pre-approve commands for this project, so Claude will ask
      before running any of them.") and skip the question.
   e. **Write only what I confirmed, as exact commands.** npm: `npm run <name>`, or `npm test` for a
      script named `test`. pnpm: `pnpm run <name>`, or `pnpm test`. yarn: only `yarn run <name>`, never
      the bare `yarn <name>`. Add each as both `"Bash(<command>)"` and `"PowerShell(<command>)"` to the
      `allow` list of my `.claude/settings.json`, through the same show-diff-then-merge flow as step 5.
      No wildcards, no `run *`. Never allow `install`, `ci`, `exec`, `dlx`, `publish` or any other command:
      install and ci run my project's own install scripts and every dependency's.

5. **Never overwrite.** For every destination that already exists, show me a diff of the kit's version
   (after substitution) against mine and propose a merge: keep my content, add what the kit adds. For
   `.claude/settings.json`, merge the `allow`/`ask`/`deny` arrays, keep all my entries, and never move one
   of my `deny` rules to `ask` or `allow` on your own.
   **Check my existing `allow` list for blanket rules** (in either `Bash(...)` or `PowerShell(...)` form):
   `npm run *`, `npm:*`, `yarn:*`, `pnpm:*`, `node:*`, `npx:*`, `python:*`, `python3:*` (any
   `python…:*`), `git:*`, `gh:*`, or a bare `*`/`Bash`/`PowerShell` that allows everything. If you find
   one, tell me plainly, without jargon, e.g.: "Your settings already let Claude run *any* `npm` command
   without asking, including things like `npm run deploy` or `npm publish`. That would cancel out the
   safety checks this kit adds." Propose replacing it with the exact lines from step 4 (or, for `git:*`/
   `gh:*`, with the kit's named rules), show me the diff, and ask. Never change it without a yes; if I say
   no, keep it and note it in the report.
   Also warn me if I have a `deny` on `git push*` (it blocks the pipeline's routine branch push: propose
   changing it to `ask`, and change it only on a yes). For `CLAUDE.md`, append the pipeline block under its own heading; if a section called "Agent
   pipeline" exists, show the diff and ask. If a handoff file exists, propose adding only what the gate and
   `/status` need (`Last updated` line, `Divergence:` line, the entry format in `handoff-example.md`). Apply
   nothing to an existing file until I say yes.

6. **Copy and substitute.** Copy `agents/*.md` to `.claude/agents/`, `commands/*.md` to `.claude/commands/`,
   `settings.json` to `.claude/settings.json`, append `CLAUDE-pipeline-block.md` to `CLAUDE.md`, and create
   the handoff file from `handoff-template.md` only if none exists. Substitute every placeholder; if
   `HOUSEKEEPING_NOTE` is "none", delete each line containing it instead. `pipeline-kit/tools/fill-placeholders.py`
   does both: write my values to a `values.json` outside the repo's tracked files, `cd` into my project's
   root folder, then run it there with exact relative targets for the copies you made: `.claude`,
   `CLAUDE.md`, the handoff file, plus `.github` and `docs/architecture/agent-pipeline.md` if installed
   (for example `python pipeline-kit/tools/fill-placeholders.py ../values.json .claude CLAUDE.md HANDOFF.md
   .github`). Never on `pipeline-kit/` itself or `.`, and never an absolute path or `..` (the tool refuses
   all of them). Preview first, then `--write`. In a new handoff file, replace
   `YYYY-MM-DD` with today's date in my timezone and each `<sha>` with the real short SHA. Add `qa/` to
   `.gitignore` and create `claude/design-doc-index.md` if missing. Keep `‹x›` in Mermaid blocks as is.

7. **Optional CI gate.** If I said yes, follow `pipeline-kit/ci/README.md`. Explain first that adding a file
   under `.github/workflows/` needs a token with GitHub's Workflows permission. Write `maxLines` in
   `.github/handoff-freshness.json` as my `HANDOFF_MAX_LINES`, a bare number. Write the files locally
   only; the install never pushes. When I push them, the workflow file needs that permission. Skip the gate if I can't
   get that permission.

8. **Verify.** Run every check in `SETUP.md` → *Verify the install* that you can run in this session:
   placeholder grep, JSON parse, the CI test script if installed. List the checks that need a fresh session
   (`/agents`, `/status`, the permission prompts) and tell me to run those after restarting Claude Code,
   because settings load at session start.

9. **Report** in this shape: files created · files merged (with what changed) · files skipped · placeholder
   values used · project commands allowed (exact list) and excluded (with the reason) · check results (pass/fail, verbatim output for failures) · what I must do next. If the repo
   had no staging branch, "next" starts with: create and push it yourself
   (`git switch -c <staging> origin/<production> && git push origin <staging>`) and point a deployment at it.

Rules for this install:
- Do **not** run `/feature`, `/discover`, `/promote` or any subagent. Installing is copying files.
- Never write a secret, token, password or API key into any file, and never ask me to paste one.
- Don't commit or push unless I ask. If I do, use a new branch and open a PR; don't push to the
  production branch.
- Don't delete anything. If you think a file should go, tell me.
- Leave `pipeline-kit/` in place; I'll decide whether to keep it.

---
