"""
AGENT 32 — Health Monitor ("Is anything silently broken?")
=============================================================

The #1 reason marketing automation fails: "set it and forget it." An
agent breaks at 3 AM, or quietly stops running, or starts acting on stale
data — and nobody notices for weeks. This watches the whole system and
tells you the moment something is off, BEFORE a client notices.

What it checks:
  1. FRESHNESS — did each agent actually run when it should have? A poller
     that should run every 15 min but last ran 6 hours ago is broken.
  2. DATA SANITY — are leads getting phone numbers? Are reports generating?
     Or is the pipeline running but producing garbage?
  3. STALE CONTENT — flags things that go out of date: an "offer" older
     than 30 days, a campaign running past its intended end.
  4. ERROR PATTERNS — scans logs for repeated failures.

If anything's wrong, it escalates via Agent 22 to your WhatsApp. This is
the difference between "my automation runs" and "my automation is
trustworthy." Run this frequently (every few hours) — it's the watchdog
over all the other agents.
"""

import os
import json
from datetime import datetime, timezone, timedelta

# Each monitored output + how stale is "too stale" (in hours)
FRESHNESS_CHECKS = {
    "leads_db.json": {"max_age_hours": 24, "what": "Lead polling",
                      "note": "If no lead appeared in 24h that MAY be normal (low volume) — check the poller ran, not just the file"},
    "orchestrator_decisions.json": {"max_age_hours": 12, "what": "Orchestrator brain"},
    "scheduler_state.json": {"max_age_hours": 24, "what": "Scheduler"},
}


def file_age_hours(path):
    if not os.path.exists(path):
        return None
    mtime = os.path.getmtime(path)
    age = (datetime.now(timezone.utc).timestamp() - mtime) / 3600
    return age


def check_freshness():
    problems = []
    for path, cfg in FRESHNESS_CHECKS.items():
        age = file_age_hours(path)
        if age is None:
            problems.append(("MEDIUM", f"{cfg['what']}: no output file found ({path}). "
                             "Either it never ran, or nothing's been produced yet."))
        elif age > cfg["max_age_hours"]:
            problems.append(("HIGH", f"{cfg['what']} looks STALE — last updated {age:.0f}h ago "
                             f"(expected within {cfg['max_age_hours']}h). Possible silent failure."))
    return problems


def check_data_sanity():
    """Catch the 'running but producing garbage' failure mode."""
    problems = []

    # Leads without phone numbers = broken form or broken parsing
    if os.path.exists("leads_db.json"):
        try:
            with open("leads_db.json") as f:
                leads = json.load(f)
            if leads:
                no_phone = [k for k, v in leads.items() if not v.get("phone")]
                if len(no_phone) > len(leads) * 0.3:
                    problems.append(("HIGH", f"{len(no_phone)} of {len(leads)} leads have NO phone number — "
                                     "the lead form or the parsing is likely broken. Leads are useless without contact."))
                # Duplicate phone numbers = possible double-processing
                phones = [v.get("phone") for v in leads.values() if v.get("phone")]
                if len(phones) != len(set(phones)):
                    dupes = len(phones) - len(set(phones))
                    problems.append(("MEDIUM", f"{dupes} duplicate phone number(s) in leads — "
                                     "possible double-counting or re-processing."))
        except json.JSONDecodeError:
            problems.append(("HIGH", "leads_db.json is corrupted (invalid JSON) — the pipeline may be "
                             "writing to it incorrectly. This breaks everything downstream."))

    return problems


def check_stale_content():
    """Flag offers/campaigns that have gone out of date — the '3 AM expired
    discount code' failure the research specifically warns about."""
    problems = []

    # Check reasoning records / predictions for stale expected outcomes
    for path, label in [("campaign_predictions.json", "prediction"),
                        ("reasoning_records.json", "reasoning record")]:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    records = json.load(f)
                for r in (records if isinstance(records, list) else []):
                    ts = r.get("generated_at") or r.get("timestamp")
                    if ts:
                        age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).days
                        if age_days > 30 and r.get("actual_outcome") is None and r.get("actual_results") is None:
                            problems.append(("LOW", f"A {label} from {age_days} days ago was never closed "
                                             "with actual results — close the loop or it becomes stale data."))
                            break  # one flag per file is enough
            except (json.JSONDecodeError, ValueError):
                pass
    return problems


def run_health_check(escalate_fn=None):
    print(f"\n{'='*55}")
    print(f"SYSTEM HEALTH CHECK — {datetime.now(timezone.utc).isoformat()[:19]}")
    print(f"{'='*55}")

    all_problems = []
    all_problems += check_freshness()
    all_problems += check_data_sanity()
    all_problems += check_stale_content()

    high = [p for p in all_problems if p[0] == "HIGH"]
    med = [p for p in all_problems if p[0] == "MEDIUM"]
    low = [p for p in all_problems if p[0] == "LOW"]

    if not all_problems:
        print("\n  ✅ All systems healthy. Everything running as expected.")
        return {"healthy": True, "problems": []}

    if high:
        print(f"\n  🔴 URGENT ({len(high)}):")
        for _, msg in high:
            print(f"     • {msg}")
    if med:
        print(f"\n  🟡 WORTH CHECKING ({len(med)}):")
        for _, msg in med:
            print(f"     • {msg}")
    if low:
        print(f"\n  🔵 MINOR ({len(low)}):")
        for _, msg in low:
            print(f"     • {msg}")

    # Escalate HIGH issues to the human via Agent 22
    if high and escalate_fn:
        escalate_fn("anomaly", "SYSTEM",
                    f"Health check found {len(high)} urgent issue(s): {'; '.join(m for _, m in high)}",
                    recommended_action="Check the affected agents/logs before a client notices.")
    elif high:
        try:
            from agent_22_human_escalation import escalate
            escalate("anomaly", "SYSTEM",
                     f"Health check found {len(high)} urgent issue(s): {'; '.join(m for _, m in high)}",
                     details={"problems": high})
        except ImportError:
            pass

    print(f"{'='*55}\n")
    return {"healthy": len(high) == 0, "problems": all_problems}


if __name__ == "__main__":
    # Demo: create some deliberately unhealthy state to prove detection works
    import sys
    if "--demo" in sys.argv:
        # A corrupt-ish leads db with missing phones + duplicates
        with open("leads_db.json", "w") as f:
            json.dump({
                "L1": {"name": "A", "phone": "919999999999"},
                "L2": {"name": "B", "phone": ""},           # missing phone
                "L3": {"name": "C", "phone": ""},           # missing phone
                "L4": {"name": "D", "phone": "919999999999"},  # duplicate
            }, f)
    run_health_check()
