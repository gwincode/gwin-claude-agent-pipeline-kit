# Claude Code agent pipeline kit

A set of Markdown and JSON files that teaches [Claude Code](https://claude.com/claude-code) to take a
feature from idea to production with four specialised helpers (`po`, `code`, `qa`, `reviewer`), while **you**
sign off at exactly two points: the design, and the result on your staging site. Nothing is installed or
run on your machine; you copy a folder into your project and let Claude Code set it up with you.

You do not need to know anything about build tools or package managers. The installer finds what your
project uses, asks you one batch of plain questions, and shows you every change before it is written.

## Quick start

1. **Get the folder.** Download this repo as a ZIP (green **Code** button → **Download ZIP**) or clone it,
   then copy the `pipeline-kit/` folder into the **root of your project**.
2. **Paste the install prompt.** Open Claude Code in your project, open `pipeline-kit/INSTALL-PROMPT.md`,
   and paste everything between the two lines in that file.
3. **Answer one set of questions, then check each change.** Claude shows what it plans to write and asks
   before changing any file that already exists. When it finishes, **close and reopen Claude Code** so the
   new settings take effect.

After that, type `/feature` in Claude Code and describe what you want built.

## What you get

- Four agents and four commands (`/feature`, `/promote`, `/status`, `/discover`).
- A starter permissions file that lets Claude run safe commands quietly and asks before anything that
  pushes, publishes, deletes or changes settings.
- Fixed limits so agents can't loop forever: 2 fix attempts per change, a checkpoint every 10 agent calls,
  and a hard stop at 30.
- An optional GitHub check that fails a pull request when the handoff file is stale.

The full tour is in [`pipeline-kit/README.md`](pipeline-kit/README.md); manual steps and the list of
settings are in [`pipeline-kit/SETUP.md`](pipeline-kit/SETUP.md).

## Please read before you rely on it

- **The permissions file is a seatbelt, not a sandbox.** It matches the text of commands, and anything that
  can run code can get around it. The real controls are the pipeline rules in your `CLAUDE.md` and your own
  approval at the two gates. For a hard stop, turn on branch protection for your production branch.
- **Settings apply to new sessions only.** Restart Claude Code after installing.
- **Status: version 1.0.5.** The install flow has been checked with scripted walk-throughs and several
  independent reviews, but it has had little use on real projects. Expect rough edges and
  [open an issue](../../issues) if you hit one.
- Known limits are listed in [`pipeline-kit/KNOWN-GAPS.md`](pipeline-kit/KNOWN-GAPS.md).

## License

[MIT](LICENSE). Use it, change it, share it; keep the copyright notice. It comes with no warranty.
