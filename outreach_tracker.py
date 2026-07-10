"""
OUTREACH TRACKER — never lose a prospect to a forgotten follow-up
====================================================================

The part that actually scales a solo operator isn't sending the first
message — it's following up. Most one-person agencies lose deals simply
because they forget who they messaged and never circle back. This fixes
that, without any risky auto-sending.

What it does:
  - Auto-builds your outreach list from the reports you generated
  - Tracks the status of each prospect (not sent / sent / replied / closed / passed)
  - Tells you who's DUE for a follow-up (sent 3+ days ago, no reply)
  - Keeps a clean history so you always know where each clinic stands

What it does NOT do: send anything. It's your memory and your pipeline,
not an auto-sender. You still send every message personally.

USAGE:
  python3 outreach_tracker.py                        # show the dashboard
  python3 outreach_tracker.py --sent "Smile Care"    # mark as sent today
  python3 outreach_tracker.py --replied "Smile Care" # mark as replied
  python3 outreach_tracker.py --closed "Smile Care"  # mark as won!
  python3 outreach_tracker.py --passed "Smile Care"  # mark as not interested
  python3 outreach_tracker.py --note "Smile Care" "called, asked to WhatsApp Tuesday"
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

TRACKER_FILE = "outreach_tracker.json"
REPORTS_DIR = "reports_to_send"
FOLLOWUP_AFTER_DAYS = 3


def load():
    if not os.path.exists(TRACKER_FILE):
        return {}
    with open(TRACKER_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save(data):
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2)


def sync_from_reports(data):
    """Add any newly-generated reports as 'not sent' prospects."""
    if not os.path.isdir(REPORTS_DIR):
        return data, 0
    added = 0
    for fname in os.listdir(REPORTS_DIR):
        m = re.match(r"trojan_report_(.+)\.html$", fname)
        if not m:
            continue
        name = m.group(1).replace("_", " ")
        if name not in data:
            data[name] = {"status": "not_sent", "history": [],
                          "created": datetime.now(timezone.utc).isoformat(),
                          "last_action": None}
            added += 1
    return data, added


def _match(data, partial):
    """Find a prospect by partial name (case-insensitive)."""
    partial_l = partial.lower()
    matches = [k for k in data if partial_l in k.lower()]
    if not matches:
        print(f"No prospect matching '{partial}'. Known: {', '.join(data.keys()) or '(none)'}")
        return None
    if len(matches) > 1:
        print(f"Ambiguous '{partial}' — matches: {', '.join(matches)}. Be more specific.")
        return None
    return matches[0]


def set_status(data, partial, status, note=None):
    key = _match(data, partial)
    if not key:
        return data
    now = datetime.now(timezone.utc).isoformat()
    data[key]["status"] = status
    data[key]["last_action"] = now
    entry = f"{status}"
    if note:
        entry += f" — {note}"
    data[key]["history"].append({"at": now, "event": entry})
    print(f"✓ {key}: marked as {status}" + (f" ({note})" if note else ""))
    return data


def add_note(data, partial, note):
    key = _match(data, partial)
    if not key:
        return data
    now = datetime.now(timezone.utc).isoformat()
    data[key]["history"].append({"at": now, "event": f"note — {note}"})
    data[key]["last_action"] = now
    print(f"✓ {key}: note added")
    return data


def dashboard(data):
    if not data:
        print("\nNo prospects yet. Generate reports first (batch_trojan_reports.py),")
        print("then run this again — it'll pick them up automatically.\n")
        return

    buckets = {"not_sent": [], "sent": [], "replied": [], "closed": [], "passed": []}
    due_followup = []
    now = datetime.now(timezone.utc)

    for name, info in data.items():
        buckets.get(info["status"], buckets["not_sent"]).append(name)
        if info["status"] == "sent" and info.get("last_action"):
            days = (now - datetime.fromisoformat(info["last_action"])).days
            if days >= FOLLOWUP_AFTER_DAYS:
                due_followup.append((name, days))

    print("\n" + "=" * 50)
    print(" OUTREACH DASHBOARD")
    print("=" * 50)
    print(f"  Not sent yet:   {len(buckets['not_sent'])}")
    print(f"  Sent, waiting:  {len(buckets['sent'])}")
    print(f"  Replied:        {len(buckets['replied'])}  <- focus here")
    print(f"  Closed (won):   {len(buckets['closed'])}")
    print(f"  Passed:         {len(buckets['passed'])}")

    if buckets["replied"]:
        print(f"\n  🔥 REPLIED — talk to these now:")
        for n in buckets["replied"]:
            print(f"     • {n}")

    if due_followup:
        print(f"\n  ⏰ DUE FOR FOLLOW-UP (sent {FOLLOWUP_AFTER_DAYS}+ days ago, no reply):")
        for n, days in sorted(due_followup, key=lambda x: -x[1]):
            print(f"     • {n} (sent {days} days ago)")

    if buckets["not_sent"]:
        print(f"\n  📤 READY TO SEND (reports generated, not sent yet):")
        for n in buckets["not_sent"]:
            print(f"     • {n}")

    # Simple funnel math
    total = len(data)
    contacted = total - len(buckets["not_sent"])
    if contacted:
        print(f"\n  Funnel: {contacted} contacted → {len(buckets['replied'])+len(buckets['closed'])} engaged "
              f"→ {len(buckets['closed'])} closed")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sent", metavar="NAME")
    parser.add_argument("--replied", metavar="NAME")
    parser.add_argument("--closed", metavar="NAME")
    parser.add_argument("--passed", metavar="NAME")
    parser.add_argument("--note", nargs=2, metavar=("NAME", "TEXT"))
    args = parser.parse_args()

    data = load()
    data, added = sync_from_reports(data)
    if added:
        print(f"[tracker] Found {added} new report(s), added to your pipeline.")

    if args.sent:
        data = set_status(data, args.sent, "sent")
    elif args.replied:
        data = set_status(data, args.replied, "replied")
    elif args.closed:
        data = set_status(data, args.closed, "closed")
    elif args.passed:
        data = set_status(data, args.passed, "passed")
    elif args.note:
        data = add_note(data, args.note[0], args.note[1])
    else:
        dashboard(data)

    save(data)
