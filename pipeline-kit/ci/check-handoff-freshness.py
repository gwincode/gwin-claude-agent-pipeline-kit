#!/usr/bin/env python3
"""
HANDOFF.md freshness gate — repo-agnostic, config-driven (part of the portable agent-pipeline kit).

Fails a pull request when HANDOFF.md's "Last updated" date is older than the
newest commit the PR adds that touches anything outside HANDOFF.md and this
check's own config, or when HANDOFF.md exceeds its configured line ceiling.
Separately reports whether the working branch and the compare branch have
structurally diverged without HANDOFF.md tracking it.

Stdlib only, no third-party deps, no setup step: ubuntu-latest ships python3.
Deliberately the same file in every repo that uses it — per-repo variation
lives in .github/handoff-freshness.json, never in this script.

Exit codes: 0 = pass, 1 = fail (stale handoff), 2 = misconfiguration.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None

CONFIG_PATH = ".github/handoff-freshness.json"

DEFAULTS = {
    "handoffFile": "HANDOFF.md",
    # Branch this repo's PRs are gated against (staging where one exists, else main).
    "workingBranch": "main",
    # Branch to compare against for structural divergence; null disables that half.
    "compareBranch": None,
    # Paths whose changes do NOT by themselves demand a handoff rewrite. Keep this
    # list tight: the point of the gate is that docs and tooling are NOT exempt.
    "exemptPaths": [
        "HANDOFF.md",
        ".github/handoff-freshness.json",
        ".github/workflows/handoff-freshness.yml",
        "scripts/check-handoff-freshness.py",
    ],
    # "warn" (annotate, exit 0) or "fail" (exit 1). See the PR description for why
    # divergence defaults to warn while staleness fails.
    "divergenceMode": "warn",
    # Commit timestamps are UTC; humans date the handoff in local time. A session
    # working at 21:09 in America/Chicago commits at 02:09 UTC the NEXT DAY, and a
    # naive UTC comparison would call a handoff written minutes earlier "a day
    # stale". Real example: a staging commit made at
    # 2026-08-18T02:09:46Z, whose handoff correctly reads 2026-08-17. Commit times
    # are converted to this zone before the date comparison.
    "timezone": "UTC",  # set your team's zone in the JSON config
    # "maxLines" is deliberately NOT defaulted here. HANDOFF.md is state, not
    # history; a file that only grows means resolved entries are being stacked
    # instead of deleted. Set it in the per-repo config to enforce a ceiling;
    # absent, the size check is disabled and the gate warns that it is.
}

# Suggested ceiling, quoted in the warning when a repo has not configured one.
SUGGESTED_MAX_LINES = 250


def local_date(dt, tzname):
    """Commit instant -> calendar date in the repo's human timezone."""
    if ZoneInfo is not None:
        try:
            return dt.astimezone(ZoneInfo(tzname)).date()
        except Exception:
            pass
    # No tz database available: fall back to UTC but allow one day of slack, so a
    # missing tzdata degrades to a slightly looser gate rather than false failures.
    return (dt.astimezone(timezone.utc) - timedelta(days=1)).date()


def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode != 0:
        die(f"git command failed: {' '.join(args)}\n{p.stderr.strip()}", code=2)
    return p.stdout.strip()


def die(msg, code=2):
    print(f"::error::{msg}")
    sys.exit(code)


def load_config():
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                cfg.update(json.load(fh))
        except (OSError, ValueError) as exc:
            die(f"{CONFIG_PATH} is unreadable or not valid JSON: {exc}", code=2)
    return cfg


# --- handoff parsing ---------------------------------------------------------

# Tolerant of the surrounding markdown emphasis handoff files actually use:
#   **Last updated:** 2026-09-04 (prose continues...)
#   _Last updated: 2026-09-04_
#   Last updated 2026-09-04
LAST_UPDATED_RE = re.compile(
    r"^[\s>*_#-]*last\s+updated\b[^0-9]{0,40}?(\d{4})-(\d{2})-(\d{2})",
    re.IGNORECASE,
)


def parse_last_updated(text, path):
    for line in text.splitlines():
        m = LAST_UPDATED_RE.match(line)
        if m:
            y, mo, d = (int(g) for g in m.groups())
            try:
                return datetime(y, mo, d, tzinfo=timezone.utc).date(), line.strip()
            except ValueError:
                die(f"{path}: 'Last updated' has an impossible date: {line.strip()}", code=1)
    return None, None


# --- size ------------------------------------------------------------------

def check_size(cfg, text):
    """-> (ok, markdown lines). ok is False only for a configured, exceeded ceiling."""
    handoff = cfg["handoffFile"]
    count = len(text.splitlines())
    if "maxLines" not in cfg:
        msg = (f"`maxLines` is not set in {CONFIG_PATH}; the {handoff} size check is "
               f"disabled ({count} lines; suggested ceiling {SUGGESTED_MAX_LINES}).")
        print(f"::warning file={CONFIG_PATH}::{msg}")
        return True, [f"⚠️ **Warning** — {msg}"]
    limit = cfg["maxLines"]
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        die(f"{CONFIG_PATH}: maxLines must be a positive integer, got {limit!r}", code=2)
    if count > limit:
        prod = cfg.get("compareBranch") or cfg["workingBranch"]
        return False, [
            f"❌ **Fail** — `{handoff}` is **{count}** lines; the ceiling is **{limit}**.",
            "",
            f"`{handoff}` is state, not history. Delete entries whose work is merged to "
            f"`{prod}` and production-verified (or, for docs/process-only changes with "
            "nothing pending, merged to the working branch). Git history keeps every "
            "prior version.",
        ]
    return True, [f"✅ `{handoff}` is {count} lines (ceiling {limit})."]


# --- commit walking ----------------------------------------------------------

def changed_files(sha):
    out = run(["git", "show", "--name-only", "--format=", "--no-renames", sha])
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def is_exempt(path, exempt):
    for e in exempt:
        if path == e or path.startswith(e.rstrip("/") + "/"):
            return True
    return False


def newest_substantive_commit(base, head, exempt):
    """Newest commit in base..head touching at least one non-exempt path."""
    shas = run(["git", "rev-list", f"{base}..{head}"]).split()
    newest = None
    for sha in shas:
        # Merge commits report no files under --name-only with an empty format;
        # their content arrives via the commits they merge, which are in this list.
        files = changed_files(sha)
        if not files:
            continue
        if not any(not is_exempt(f, exempt) for f in files):
            continue
        iso = run(["git", "show", "-s", "--format=%cI", sha])
        when = datetime.fromisoformat(iso)
        subject = run(["git", "show", "-s", "--format=%s", sha])
        if newest is None or when > newest[1]:
            newest = (sha, when, subject, [f for f in files if not is_exempt(f, exempt)])
    return newest


def summary(md):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(md + "\n")
    print(md)


# --- divergence --------------------------------------------------------------

DIVERGENCE_NOTE_RE = re.compile(r"^[\s>*_#-]*divergence\s*:", re.IGNORECASE | re.MULTILINE)


def check_divergence(cfg, handoff_text):
    working, compare = cfg["workingBranch"], cfg.get("compareBranch")
    if not compare:
        return None
    refs = {}
    for br in (working, compare):
        p = subprocess.run(["git", "rev-parse", "--verify", f"origin/{br}"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            summary(f"- Divergence check skipped: `origin/{br}` not fetched in this checkout.")
            return None
        refs[br] = p.stdout.strip()

    # Commits on compare (main) that working (staging) does not have. This is the
    # dangerous direction: promoting working would regress those commits away.
    compare_ahead = run(["git", "rev-list", "--count", f"{refs[working]}..{refs[compare]}"])
    working_ahead = run(["git", "rev-list", "--count", f"{refs[compare]}..{refs[working]}"])
    compare_ahead, working_ahead = int(compare_ahead), int(working_ahead)

    tracked = bool(DIVERGENCE_NOTE_RE.search(handoff_text))
    return {
        "working": working, "compare": compare,
        "compare_ahead": compare_ahead, "working_ahead": working_ahead,
        "diverged": compare_ahead > 0, "tracked": tracked,
    }


# --- main --------------------------------------------------------------------

def _utf8_stdio():
    # Windows consoles default to a legacy code page (cp1252) that cannot encode the emoji below.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main():
    _utf8_stdio()
    cfg = load_config()
    handoff = cfg["handoffFile"]
    exempt = cfg["exemptPaths"]

    base = os.environ.get("HANDOFF_BASE_SHA", "").strip()
    head = os.environ.get("HANDOFF_HEAD_SHA", "HEAD").strip() or "HEAD"
    if not base:
        die("HANDOFF_BASE_SHA is not set; the workflow must pass the PR base SHA.", code=2)

    merge_base = run(["git", "merge-base", base, head])

    if not os.path.exists(handoff):
        summary(f"## ❌ Handoff freshness\n\n`{handoff}` does not exist at this branch's head.")
        die(f"{handoff} is missing. The agent pipeline keeps one; add it "
            f"(Last updated / What moved / Next up / Blockers).", code=1)

    with open(handoff, encoding="utf-8") as fh:
        text = fh.read()

    last_updated, raw_line = parse_last_updated(text, handoff)
    if last_updated is None:
        summary(f"## ❌ Handoff freshness\n\n`{handoff}` has no parseable "
                f"`Last updated:` line with an ISO date (YYYY-MM-DD).")
        die(f"{handoff}: could not find a 'Last updated' line containing a "
            f"YYYY-MM-DD date.", code=1)

    newest = newest_substantive_commit(merge_base, head, exempt)

    lines = ["## Handoff freshness", ""]
    div = check_divergence(cfg, text)
    # Size applies to every PR, handoff-only ones included: they are how it shrinks.
    size_ok, size_lines = check_size(cfg, text)
    fail = 0 if size_ok else 1

    if newest is None:
        lines += [
            "✅ **Pass** — this PR changes nothing outside the handoff/CI-config "
            "exempt list, so no handoff rewrite is demanded.",
            "", f"- `{handoff}` last updated: **{last_updated.isoformat()}**",
        ]
        emit(lines, div, size_lines, cfg)
        return fail

    sha, when, subject, files = newest
    tzname = cfg.get("timezone", "UTC")
    commit_date = local_date(when, tzname)
    shown = ", ".join(f"`{f}`" for f in files[:5]) + (" …" if len(files) > 5 else "")

    if last_updated < commit_date:
        lines += [
            f"❌ **Fail** — `{handoff}` is older than this branch's newest "
            "substantive commit.",
            "",
            f"| | |\n|---|---|\n"
            f"| `{handoff}` Last updated | **{last_updated.isoformat()}** |\n"
            f"| Newest substantive commit | **{commit_date.isoformat()}** (`{sha[:8]}`, {tzname}) |\n"
            f"| Commit subject | {subject} |\n"
            f"| Paths that demanded a rewrite | {shown} |",
            "",
            "Rewrite the handoff as the last step of the session — update "
            "**Last updated**, **What moved**, **Next up**, and **Blockers** — then "
            "push again. Docs-only and tooling-only changes are not exempt: if repo "
            "state moved, the handoff moves with it.",
        ]
        emit(lines, div, size_lines, cfg)
        return 1

    lines += [
        "✅ **Pass** — the handoff is at least as new as this branch's newest "
        "substantive commit.",
        "",
        f"- `{handoff}` Last updated: **{last_updated.isoformat()}**",
        f"- Newest substantive commit: **{commit_date.isoformat()}** (`{sha[:8]}` {subject})",
    ]
    emit(lines, div, size_lines, cfg)
    return fail


def emit(lines, div, size_lines, cfg):
    lines += ["", "### Size", ""] + size_lines
    if div is not None:
        lines += ["", "### Branch divergence", ""]
        w, c = div["working"], div["compare"]
        if not div["diverged"]:
            lines.append(
                f"✅ `{c}` has no commits missing from `{w}` "
                f"({w} is ahead by {div['working_ahead']} — normal unpromoted work)."
            )
        elif div["tracked"]:
            lines.append(
                f"✅ `{c}` is ahead of `{w}` by {div['compare_ahead']} commit(s), "
                f"and `{cfg['handoffFile']}` carries a `Divergence:` line tracking it."
            )
        else:
            msg = (f"`{c}` has {div['compare_ahead']} commit(s) that `{w}` does not, "
                   f"and `{cfg['handoffFile']}` has no `Divergence:` line tracking it. "
                   f"Promoting `{w}` would regress them.")
            if cfg.get("divergenceMode") == "fail":
                lines.append(f"❌ {msg}")
            else:
                lines.append(f"⚠️ **Warning** — {msg}")
                print(f"::warning file={cfg['handoffFile']}::{msg}")
    summary("\n".join(lines))
    if (div and div["diverged"] and not div["tracked"]
            and cfg.get("divergenceMode") == "fail"):
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
