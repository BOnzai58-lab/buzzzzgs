#!/usr/bin/env python3
"""Shared team chat for multi-agent work. Standard library only.

Messages are one file each in team/chat/, so agents never clobber each other.

  python team/chat.py post --from recon --to lead --type question "Need the Asset schema"
  python team/chat.py read --me recon            # unread messages addressed to me (or to 'all')
  python team/chat.py read --me recon --all      # everything addressed to me, read or not
  python team/chat.py log                        # whole channel, oldest first
  python team/chat.py roles                      # list valid roles
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAT = ROOT / "chat"
STATE = ROOT / ".state"
ROLES = ["lead", "scope", "recon", "scanner", "triage", "frontend", "qa", "human", "all"]
TYPES = ["msg", "question", "blocker", "decision", "done", "review"]
NAME = re.compile(r"^(\d{4})-([a-z]+)-to-([a-z]+)-([a-z]+)\.md$")


def messages():
    CHAT.mkdir(exist_ok=True)
    out = []
    for p in sorted(CHAT.glob("*.md")):
        m = NAME.match(p.name)
        if m:
            out.append((int(m.group(1)), m.group(2), m.group(3), m.group(4), p))
    return out


def post(args):
    if args.sender not in ROLES or args.to not in ROLES:
        sys.exit(f"Unknown role. Valid: {', '.join(ROLES)}")
    if args.type not in TYPES:
        sys.exit(f"Unknown type. Valid: {', '.join(TYPES)}")
    CHAT.mkdir(exist_ok=True)
    body = " ".join(args.text).strip()
    if not body:
        sys.exit("Empty message.")
    n = (messages()[-1][0] + 1) if messages() else 1
    while True:  # O_EXCL makes number allocation safe if two agents post at once
        path = CHAT / f"{n:04d}-{args.sender}-to-{args.to}-{args.type}.md"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            n += 1
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"# #{n:04d} {args.sender} -> {args.to} [{args.type}]\n_{stamp}_\n\n{body}\n")
    print(f"posted #{n:04d}")


def seen_path(me):
    STATE.mkdir(exist_ok=True)
    return STATE / f"{me}.json"


def read(args):
    if args.me not in ROLES:
        sys.exit(f"Unknown role. Valid: {', '.join(ROLES)}")
    sp = seen_path(args.me)
    seen = json.loads(sp.read_text()) if sp.exists() else 0
    shown = 0
    top = seen
    for n, sender, to, typ, p in messages():
        if to not in (args.me, "all") and not (args.me == "lead" and typ in ("blocker", "decision")):
            continue
        if not args.all and n <= seen:
            continue
        print(p.read_text(encoding="utf-8").rstrip(), "\n---")
        shown += 1
        top = max(top, n)
    if not args.all:
        sp.write_text(json.dumps(top))
    if shown == 0:
        print("No new messages.")


def log(_):
    for n, sender, to, typ, p in messages():
        first = p.read_text(encoding="utf-8").splitlines()
        text = next((l for l in first[3:] if l.strip()), "")
        print(f"#{n:04d} {sender} -> {to} [{typ}] {text[:110]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post")
    p.add_argument("--from", dest="sender", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--type", default="msg")
    p.add_argument("text", nargs="+")
    p.set_defaults(fn=post)
    r = sub.add_parser("read")
    r.add_argument("--me", required=True)
    r.add_argument("--all", action="store_true")
    r.set_defaults(fn=read)
    sub.add_parser("log").set_defaults(fn=log)
    sub.add_parser("roles").set_defaults(fn=lambda _: print("\n".join(ROLES)))
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
