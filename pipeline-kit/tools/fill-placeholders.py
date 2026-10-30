#!/usr/bin/env python3
"""
Fill the kit's {{PLACEHOLDER}} tokens from a values file.

    python fill-placeholders.py values.json .claude CLAUDE.md HANDOFF.md            # preview only
    python fill-placeholders.py values.json .claude CLAUDE.md HANDOFF.md --write    # change the files

Run it FROM your project's root folder and point it at the copies you installed there, as simple relative
paths (`.claude`, `CLAUDE.md`, `HANDOFF.md`, and `.github` or `docs/architecture/agent-pipeline.md` if you
installed those). Absolute paths, drive letters, `..`, `~`, and on Windows `:` or a name ending in a dot or
space are refused. Never point it at `pipeline-kit/` itself or at `.`: it refuses any target inside a
folder named `pipeline-kit` (any letter case), and `.` when it contains this script (true in the standard
layout, with the kit inside your project). If your own project folder is literally named `pipeline-kit`,
rename it or copy the files elsewhere first; that is a known limitation.

values.json maps each KEY to its text, e.g. {"PROJECT_NAME": "Acme Notes", "PROD_BRANCH": "main"}.
A value of null deletes every line containing that token instead (use it for HOUSEKEEPING_NOTE when you
have no per-PR chores). Line deletion is never done in .json files (it could break the JSON); those are
reported and the token is left for you to fix by hand.

Safety rules:
- Without --write nothing is changed: you get a preview. --dry-run says the same thing explicitly.
- Everything is checked before anything is written: every target is allowed and exists, every file can be
  read, every file that would change can be written where it is (not read-only, and opening it for writing
  is allowed, which catches a Windows permissions-list write deny), and with --write each folder of a file
  that would change accepts a new file. If any check fails, nothing changes.
- Each file is written to a temporary `.fill-*.tmp` file in the same folder and then swapped in, so a crash
  or a full disk never leaves a half-written file. The temporary file is always removed.
- Links: every folder on the way from the current folder to a target is checked on disk, and a target that
  is or goes through a symbolic link, a Windows junction or any other Windows reparse point is refused
  (every Python version). Inside a target, links and reparse points are skipped and listed ("skipped
  symlink: <path>"), and every file must really live inside the current folder. Folders above the current
  folder are never inspected; that is fine because only paths inside it are accepted.
- Checks and writes are not one atomic step: a program that can already write your folders could swap a
  folder for a link between the check and the write. The file itself is safe (the rename replaces a
  swapped-in link rather than following it).
- A folder that can't be listed is skipped and listed ("skipped (couldn't list this folder): <path>").
- Only permission bits (the read-only flag on Windows) are copied to the new file. Not kept: Windows
  permissions-list (ACL) entries set on the file itself (the new file takes the folder's inherited
  permissions), Windows Hidden/System attributes, and POSIX owner, group, ACLs and extended attributes.
- Hard-linked files (the same file under two names) are never written: they are listed ("skipped
  hard-linked file: <path>") and any {{...}} in them is reported as left over, because changing one name
  would change, or silently detach, the other.
- Binary and non-UTF-8 files are skipped and listed.
- A {{...}} immediately preceded by "$" is GitHub Actions syntax (`${{ github.event... }}`), not a
  placeholder. It is never substituted and never reported as left over.
- If a write fails part way, you get one plain message saying which files were already updated and which
  were not. Nothing is rolled back; running the same command again is safe and fills only what is left.

Python 3.8+, standard library only. Works the same on Windows, macOS and Linux. Line endings (LF/CRLF)
and a UTF-8 byte-order mark are kept as they were.
Exit codes: 0 = nothing left to fill, 1 = placeholders left over, 2 = bad input, refused target, or a file
that couldn't be changed. --debug (for maintainers) shows the full Python error instead of the plain message.
"""

import argparse
import errno
import json
import os
import re
import secrets
import shutil
import stat
import sys

KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
# Any {{...}} not preceded by "$". The substitution below uses the same "(?<!\$)" guard.
LEFTOVER_RE = re.compile(r"(?<!\$)\{\{[^{}\n]*\}\}")
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
KIT_DIR_NAME = "pipeline-kit"
TMP_PREFIX, TMP_SUFFIX = ".fill-", ".tmp"
SELF = os.path.realpath(os.path.abspath(__file__))
DEBUG = False


class Stop(Exception):
    """An expected problem, already worded for the reader."""


def utf8_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def why(e):
    """Plain words for an OSError."""
    if isinstance(e, PermissionError) or getattr(e, "errno", None) in (errno.EACCES, errno.EPERM, errno.EROFS):
        return "it is read-only, open in another program, or you don't have permission to change it"
    if getattr(e, "errno", None) == errno.ENOSPC:
        return "the disk is full"
    if isinstance(e, FileNotFoundError):
        return "it disappeared while the tool was running"
    return "the system refused (" + (getattr(e, "strerror", None) or type(e).__name__) + ")"


REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def is_link(path):
    """A symlink, or on Windows any reparse point (junctions included, on every Python version)."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & REPARSE_POINT)


def is_hard_linked(path):
    return os.lstat(path).st_nlink > 1


def under(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:  # different drives on Windows
        return False


def load_values(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        fail(f"can't read {path}: {e}")
    if not isinstance(data, dict):
        fail(f"{path} must be a JSON object of KEY: value pairs")
    for k, v in data.items():
        if not KEY_RE.match(k):
            fail(f"{path}: key {k!r} must be UPPER_SNAKE (write PROJECT_NAME, not {{{{PROJECT_NAME}}}})")
        if v is not None and (isinstance(v, bool) or not isinstance(v, (str, int))):
            fail(f"{path}: value for {k} must be text, a number, or null")
        if isinstance(v, str):
            try:
                v.encode("utf-8")
            except UnicodeEncodeError:
                fail(f"{path}: value for {k} contains a broken character (a lone \\ud800-style escape); "
                     "retype that value")
    return {k: (None if v is None else str(v)) for k, v in data.items()}


def refuse(problems):
    for p in problems:
        print(f"error: {p}", file=sys.stderr)
    print("Nothing was changed.", file=sys.stderr)
    sys.exit(2)


SIMPLE_HINT = "Run this from your project folder and give it simple paths inside it, like .claude or CLAUDE.md."


def components(t):
    """-> list of path components for a simple relative path, or a plain-words reason it is refused.

    Only cwd-relative paths are accepted, so no other spelling of the project (an 8.3 short name, a
    symlinked ancestor, "..") can route around the per-component link check below.
    """
    windows = os.name == "nt"
    if not t.strip():
        return "it is empty"
    if "\0" in t:
        return "it contains a NUL character"
    if t.startswith(("/", "\\")) or os.path.isabs(t) or re.match(r"^[A-Za-z]:", t):
        return "it is an absolute path (or has a drive letter)"
    if t.startswith("~"):
        return "it starts with ~"
    if windows and ":" in t:
        return "it contains ':' (a drive letter or an alternate data stream)"
    parts = re.split(r"[\\/]" if windows else r"/", t)
    if ".." in parts:
        return "it contains '..'"
    if windows and any(p not in ("", ".") and p[-1] in ". " for p in parts):
        return "a name in it ends with a dot or a space"
    return [p for p in parts if p not in ("", ".")]


def check_targets(targets):
    """Validate every target before anything is read or written. -> [(target, real root)]"""
    problems, ok = [], []
    cwd = os.getcwd()
    cwd_real = os.path.realpath(cwd)
    for t in targets:
        comps = components(t)
        if isinstance(comps, str):
            problems.append(f"I won't use {t!r} because {comps}. {SIMPLE_HINT}")
            continue
        # A real filesystem check of every component below the current folder; no text comparison.
        acc, bad = cwd, None
        for c in comps:
            acc = os.path.join(acc, c)
            try:
                os.lstat(acc)
            except OSError:
                bad = f"{t} does not exist"
                break
            if is_link(acc):
                bad = (f"{t} goes through a symbolic link or junction ({os.path.relpath(acc, cwd)}); "
                       "give the real folder instead")
                break
        if bad:
            problems.append(bad)
            continue
        real = os.path.realpath(acc)
        if not under(real, cwd_real):  # belt and braces: unreachable unless a link was swapped in
            problems.append(f"{t} leads outside the folder you ran this from. {SIMPLE_HINT}")
            continue
        parts = [p.lower() for p in real.replace("\\", "/").split("/")]
        if KIT_DIR_NAME in parts:
            problems.append(f"{t}: that folder looks like the kit itself. Run this on your project's own files "
                            "(for example .claude, CLAUDE.md, HANDOFF.md), not on the kit. (If your project "
                            f"folder is really named '{KIT_DIR_NAME}', rename it first.)")
            continue
        if under(SELF, real):
            problems.append(f"{t} contains this tool itself; point at .claude, CLAUDE.md, HANDOFF.md, .github, "
                            "not the whole project")
            continue
        ok.append((os.path.join(*comps) if comps else os.curdir, real))
    if problems:
        refuse(problems)
    return ok


def iter_files(checked, skipped):
    for t, root in checked:
        if os.path.isfile(t):
            yield t
            continue
        def unlisted(e, t=t):
            skipped.append(("(couldn't list this folder)", e.filename or t))

        for dirpath, dirs, files in os.walk(t, followlinks=False, onerror=unlisted):
            keep = []
            for d in sorted(dirs):
                full = os.path.join(dirpath, d)
                if d in SKIP_DIRS:
                    continue
                if is_link(full):
                    skipped.append(("symlink", full))
                else:
                    keep.append(d)
            dirs[:] = keep
            for name in sorted(files):
                full = os.path.join(dirpath, name)
                if is_link(full) or not under(os.path.realpath(full), root):
                    skipped.append(("symlink", full))
                    continue
                if name.startswith(TMP_PREFIX) and name.endswith(TMP_SUFFIX):
                    continue
                yield full


def read_text(path):
    """-> text, or None for a binary / non-UTF-8 file. An unreadable file raises OSError."""
    with open(path, "rb") as f:
        raw = f.read()
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def fill(text, values, is_json):
    """-> (new text, {key: count}, [keys whose null-deletion was refused])"""
    used, refused = {}, set()
    patterns = {k: re.compile(r"(?<!\$)" + re.escape("{{" + k + "}}")) for k in values}
    out = []
    for line in text.splitlines(keepends=True):
        drop = False
        for k, v in values.items():
            hits = len(patterns[k].findall(line))
            if not hits:
                continue
            if v is None:
                if is_json:
                    refused.add(k)
                    continue
                used[k] = used.get(k, 0) + hits
                drop = True
            else:
                used[k] = used.get(k, 0) + hits
                line = patterns[k].sub(lambda _m, v=v: v, line)
        if not drop:
            out.append(line)
    return "".join(out), used, sorted(refused)


def remove_quietly(path):
    try:
        os.remove(path)
    except PermissionError:  # our own temp file may have inherited a read-only flag
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            os.remove(path)
        except OSError:
            pass
    except OSError:
        pass


def make_temp(folder):
    """-> (fd, path) of a new, empty temp file in folder.

    Not tempfile.mkstemp: on Windows it treats "access denied" as a name clash and retries ~238,000
    times, which looks like a hang in a folder the user can't write to.
    """
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    for _ in range(10):
        path = os.path.join(folder, TMP_PREFIX + secrets.token_hex(6) + TMP_SUFFIX)
        try:
            return os.open(path, flags, 0o600), path
        except FileExistsError:
            continue
    raise FileExistsError(errno.EEXIST, "no free temporary file name", folder)


def probe_folder(folder):
    """Can a new file be created (and removed) here? Raises OSError if not."""
    fd, tmp = make_temp(folder)
    os.close(fd)
    remove_quietly(tmp)


def replace_file(path, data):
    """Write data to a temp file beside path, then swap it in. The original is untouched on any failure."""
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = make_temp(folder)
    try:
        try:
            f = os.fdopen(fd, "wb")
        except BaseException:
            os.close(fd)
            raise
        with f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            remove_quietly(tmp)


def writable_in_place(path):
    """Could this file be written where it is? The swap-in only needs delete rights, so without this a
    Windows write-deny (or a POSIX read-only file) would be silently replaced. Opening for append without
    writing changes nothing, not even the modified time."""
    if not os.access(path, os.W_OK):
        return False
    try:
        with open(path, "ab"):
            pass
    except OSError:
        return False
    return True


def preflight(plan, write):
    """Check every planned file can be replaced. Nothing is changed by a failed check."""
    problems = []
    folders = []
    for path, _, _ in plan:
        if not writable_in_place(path):
            problems.append(f"I can't change {path} because it is read-only or its permissions don't allow "
                            "changes. Change that yourself if you want it filled.")
        folder = os.path.dirname(os.path.abspath(path))
        if folder not in folders:
            folders.append(folder)
    if write:
        for folder in folders:
            try:
                probe_folder(folder)
            except OSError as e:
                if DEBUG:
                    raise
                problems.append(f"I can't create a file in {folder} because {why(e)}.")
    if problems:
        refuse(problems)


def write_all(plan):
    done = []
    for i, (path, new, _) in enumerate(plan):
        try:
            if is_link(path) or is_hard_linked(path):  # changed since it was checked
                raise Stop(f"{path} became a link while the tool was running")
            replace_file(path, new.encode("utf-8"))
        except (OSError, Stop) as e:
            if DEBUG:
                raise
            reason = str(e) if isinstance(e, Stop) else why(e)
            rest = [p for p, _, _ in plan[i:]]
            print(f"I couldn't change {path} because {reason}. Nothing in that file was changed.", file=sys.stderr)
            print("Files already updated before this: " + (", ".join(done) or "none"), file=sys.stderr)
            print("Files not yet updated: " + ", ".join(rest), file=sys.stderr)
            print("You can run this again safely: it only fills in what is left. "
                  "(Files already updated are not rolled back.)", file=sys.stderr)
            sys.exit(2)
        done.append(path)


def main():
    global DEBUG
    utf8_stdio()
    p = argparse.ArgumentParser(description="Fill {{PLACEHOLDER}} tokens from a values.json file.")
    p.add_argument("values", help="JSON file mapping KEY to value")
    p.add_argument("targets", nargs="+", help="simple relative paths inside the folder you run this from, e.g. .claude CLAUDE.md "
                        "(never pipeline-kit/ or .)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="actually change the files")
    mode.add_argument("--dry-run", action="store_true", help="preview only (the default)")
    p.add_argument("--debug", action="store_true", help="show full Python errors (for maintainers)")
    args = p.parse_args()
    DEBUG = args.debug

    values = load_values(args.values)
    checked = check_targets(args.targets)

    skipped, plan, totals, leftovers, json_refusals, unreadable = [], [], {}, [], [], []
    for path in iter_files(checked, skipped):
        try:
            hard = is_hard_linked(path)
            text = read_text(path)
        except OSError as e:
            if DEBUG:
                raise
            unreadable.append(f"I can't read {path} because {why(e)}.")
            continue
        if text is None:
            skipped.append(("binary or non-UTF-8 file", path))
            continue
        if hard:  # read, never written; its tokens still count as left over
            skipped.append(("hard-linked file", path))
            for i, line in enumerate(text.splitlines(), 1):
                for m in LEFTOVER_RE.finditer(line):
                    leftovers.append(f"{path}:{i}: {m.group(0)}  (skipped hard-linked file; fill by hand)")
            continue
        new, used, refused = fill(text, values, path.lower().endswith(".json"))
        for k in refused:
            json_refusals.append(f"{path}: {{{{{k}}}}} is null, but lines are never deleted in .json files")
        for k, n in used.items():
            totals[k] = totals.get(k, 0) + n
        if new != text:
            plan.append((path, new, sum(used.values())))
        for i, line in enumerate(new.splitlines(), 1):
            for m in LEFTOVER_RE.finditer(line):
                leftovers.append(f"{path}:{i}: {m.group(0)}")
    if unreadable:
        refuse(unreadable)

    for kind, s in skipped:
        print(f"skipped {kind}: {s}")
    preflight(plan, args.write)
    if args.write:
        write_all(plan)

    verb = "Changed" if args.write else "Would change"
    print(f"{verb} {len(plan)} file(s):")
    for path, _, n in plan:
        print(f"  {path}  ({n} placeholder(s))")
    for r in json_refusals:
        print(f"Not deleted: {r}")
    scope = " in the files checked" if skipped else ""
    unused = sorted(k for k in values if k not in totals)
    if unused and plan:
        print(f"Values never used{scope} (check the spelling): " + ", ".join(unused))
    if not args.write and plan:
        print("Nothing was written. Run again with --write to apply.")
    if skipped:
        print(f"Not checked: {len(skipped)} skipped file(s) or folder(s) listed above, so the left-over list "
              "below may under-count. Fill any placeholders in them by hand.")

    if leftovers:
        label = "Still left after filling" if args.write else "Would still be left after filling"
        print(f"{label}{scope} ({len(leftovers)}):")
        for item in leftovers:
            print("  " + item)
        return 1
    print(f"No placeholders left{scope}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
