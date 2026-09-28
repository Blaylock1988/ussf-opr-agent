"""Install, update or remove the opr-writer skill for Claude Code and/or Google Antigravity.

The skill folder itself is always a real directory (a copy). Antigravity, and other harnesses, will not
load a skill whose root folder is a symlink or junction. Only a *parent* skills folder may be linked:
the working layout is ~/.agents/skills/opr-writer (real folder) with ~/.gemini/config/skills linked to
~/.agents/skills, so one copy serves both. A copy doesn't follow repo edits, so run `update` after a
`git pull`.

Targets:
  agents      ~/.agents/skills/opr-writer                 (shared skills folder)
  agy         ~/.gemini/config/skills/opr-writer          (Antigravity 2.0 / IDE, global; offers the parent link)
  agy-cli     ~/.gemini/antigravity-cli/skills/opr-writer (Antigravity CLI, global)
  agy-legacy  ~/.gemini/antigravity/skills/opr-writer     (older Antigravity IDE builds)
  claude      ~/.claude/skills/opr-writer                 (Claude Code personal skill; or use the plugin marketplace)
  workspace   <dir>/.agents/skills/opr-writer             (Antigravity workspace skill; pass --workspace DIR)

Usage:
  python install.py install agy             # Antigravity IDE (offers ~/.gemini/config/skills -> ~/.agents/skills)
  python install.py install claude agy      # both
  python install.py update                  # re-copy the repo skill into every existing install
  python install.py status                  # which installs are current, stale or missing
  python install.py uninstall agy
  python install.py install workspace --workspace "C:/path/to/My 2026 OPR"
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parent / "skills" / "opr-writer"
HOME = Path.home()
AGENTS = HOME / ".agents" / "skills"
TARGETS = {
    "agents": AGENTS,
    "agy": HOME / ".gemini" / "config" / "skills",
    "agy-cli": HOME / ".gemini" / "antigravity-cli" / "skills",
    "agy-legacy": HOME / ".gemini" / "antigravity" / "skills",
    "claude": HOME / ".claude" / "skills",
}
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
MANIFEST = ".installed_from.json"  # source + fingerprint, read by scripts/data_check.py


def is_link(p):
    """True for a symlink or a Windows junction."""
    if p.is_symlink():
        return True
    is_junction = getattr(p, "is_junction", None)  # Python 3.12+
    if is_junction:
        return is_junction()
    try:
        return bool(os.readlink(p))
    except (OSError, ValueError):
        return False


def link_dir(src, dst):
    if os.name == "nt":
        import _winapi

        _winapi.CreateJunction(str(src), str(dst))  # no admin rights needed
    else:
        os.symlink(src, dst, target_is_directory=True)


def remove(dst):
    """Remove an install. A link is only unlinked, never followed, so the repo is never touched."""
    if not os.path.lexists(dst):
        return False
    if is_link(dst):
        os.unlink(dst) if dst.is_symlink() else os.rmdir(dst)
        return True
    if dst.resolve() == SKILL.resolve():
        sys.exit(f"refusing to delete {dst}: it is the repository's skill folder")
    shutil.rmtree(dst)
    return True


def skill_hash(root):
    """Same fingerprint as scripts/common.py skill_hash, so data_check.py can spot a stale copy."""
    h = hashlib.sha1()
    for p in sorted(Path(root).rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and p.name != MANIFEST and "__pycache__" not in rel and p.suffix != ".pyc" and ".pytest_cache" not in rel:
            h.update(rel.encode("utf-8") + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:12]


def copy(dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL, dst, ignore=IGNORE)
    (dst / MANIFEST).write_text(json.dumps({"source": str(SKILL), "hash": skill_hash(SKILL),
                                            "installed": date.today().isoformat()}, indent=1), encoding="utf-8")


def status(targets, workspace):
    repo = skill_hash(SKILL)
    print(f"repository {repo}: {SKILL}")
    for t in targets:
        dst = base_of(t, workspace) / "opr-writer"
        if not os.path.lexists(dst):
            state = "missing"
        elif is_link(dst):
            state = "LINKED skill root (harnesses won't load it; run update)"
        else:
            state = "current" if skill_hash(dst) == repo else "STALE (run: python install.py update)"
        print(f"{t:10} {state}: {dst}")


def ask(question, assume_yes):
    if assume_yes:
        return True
    try:
        return input(f"{question} [Y/n] ").strip().lower() in ("", "y", "yes")
    except EOFError:
        return False


def agy_parent(assume_yes):
    """Offer ~/.gemini/config/skills -> ~/.agents/skills. Skip when it is already linked or already a real folder."""
    base = TARGETS["agy"]
    if is_link(base):
        print(f"agy        parent already linked: {base} -> {os.path.realpath(base)}")
        return
    if base.exists():
        print(f"agy        {base} is a real folder; installing into it (link it to {AGENTS} yourself to share one copy)")
        return
    if ask(f"Link {base} -> {AGENTS} so Antigravity and ~/.agents share one copy?", assume_yes):
        AGENTS.mkdir(parents=True, exist_ok=True)
        base.parent.mkdir(parents=True, exist_ok=True)
        link_dir(AGENTS, base)
        print(f"agy        linked parent: {base} -> {AGENTS}")


def base_of(target, workspace):
    if target == "workspace":
        if not workspace:
            sys.exit("--workspace DIR is required for the workspace target")
        return Path(workspace) / ".agents" / "skills"
    return TARGETS[target]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["install", "update", "uninstall", "status"])
    ap.add_argument("targets", nargs="*", choices=list(TARGETS) + ["workspace"],
                    help="install/uninstall: required; update: defaults to every existing install; status: every target")
    ap.add_argument("--workspace", help="workspace folder for the 'workspace' target")
    ap.add_argument("--force", action="store_true", help="install: replace an existing install")
    ap.add_argument("--yes", "-y", action="store_true", help="accept the parent-link offer without asking")
    args = ap.parse_args()
    if not (SKILL / "SKILL.md").is_file():
        sys.exit(f"skill not found at {SKILL}")
    targets = args.targets
    if args.action == "status":
        return status(targets or list(TARGETS) + (["workspace"] if args.workspace else []), args.workspace)
    if not targets:
        if args.action != "update":
            sys.exit(f"name at least one target for {args.action}")
        targets = [t for t, b in TARGETS.items() if os.path.lexists(b / "opr-writer")]
        if args.workspace:
            targets.append("workspace")
        if not targets:
            sys.exit("no existing installs found; use: python install.py install <target>")

    done = set()  # linked parents make two targets the same folder; handle each real folder once
    for t in targets:
        if t == "agy" and args.action == "install":
            agy_parent(args.yes)
        dst = base_of(t, args.workspace) / "opr-writer"
        real = os.path.realpath(dst.parent) if dst.parent.exists() else str(dst.parent)
        if real in done:
            print(f"{t:10} same folder as an earlier target ({real}); skipped")
            continue
        done.add(real)
        if args.action == "uninstall":
            print(f"{t:10} {'removed' if remove(dst) else 'not installed'}: {dst}")
            continue
        if os.path.lexists(dst):
            old_link = is_link(dst)
            if args.action == "install" and not (args.force or old_link):
                print(f"{t:10} already installed: {dst} (use 'update' to refresh it)")
                continue
            remove(dst)
            if old_link:
                print(f"{t:10} replaced an old link at the skill root (harnesses won't load a linked skill folder)")
        elif args.action == "update":
            print(f"{t:10} not installed: {dst}")
            continue
        copy(dst)
        print(f"{t:10} {'updated' if args.action == 'update' else 'installed'} (copy): {dst}")
    if args.action != "uninstall":
        print("\nNext: python -m pip install -r skills/opr-writer/scripts/requirements.txt  (once per Python install)")
        print("After each `git pull`, run: python install.py update")
        if any(t.startswith("agy") or t in ("workspace", "agents") for t in targets):
            print("Antigravity: reload the window, then type /opr-writer (or just ask it to write an OPR).")


if __name__ == "__main__":
    main()
