"""
SCHEDULER — runs each agent automatically, on its own timer
================================================================

What this does:
  Instead of you manually running each agent's command by hand, this runs
  continuously in one terminal window and triggers each one when it's due:
    - Lead poller: every 5 minutes
    - Media optimizer: every 6 hours
    - Reporting: weekly (treated as every 7 days from last run, not tied
      to a specific calendar day — simpler and good enough for now)

  Remembers what it last ran across restarts (scheduler_state.json), so
  stopping and restarting this script doesn't cause duplicate runs.

Before running this for real:
  - Export every environment variable each agent needs (META_ACCESS_TOKEN,
    PAGE_ACCESS_TOKEN, META_AD_ACCOUNT_ID, etc.) in THIS SAME terminal
    session before starting the scheduler — it passes its own environment
    straight through to each agent it runs.
  - All agents stay in their existing DRY_RUN=True safety default; this
    scheduler doesn't change that, it just decides *when* to call them.

Run:
  python3 run_scheduler.py            (runs forever, checking every 60s)
  python3 run_scheduler.py --run-now  (forces every task to run once immediately, for testing)
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timezone

STATE_FILE = "scheduler_state.json"

TASKS = {
    "poll_leads": {"script": "agent_04b_lead_poller.py", "interval_minutes": 5},
    "optimize": {"script": "agent_02_media_optimizer.py", "interval_minutes": 360},
    "report": {"script": "agent_03_reporting.py", "interval_minutes": 10080},  # ~weekly
    "cross_channel_arbitrage": {"script": "agent_13_cross_channel_arbitrage.py", "interval_minutes": 720},  # ~2x daily
    "competitive_monitor": {"script": "run_competitive_monitor.py", "interval_minutes": 1440},  # daily
    "creative_intelligence": {"script": "agent_20_creative_intelligence.py", "interval_minutes": 10080},  # weekly
    "churn_check": {"script": "agent_17_churn_prediction.py", "interval_minutes": 10080},  # weekly
    "offer_diagnosis": {"script": "agent_18_offer_diagnosis.py", "interval_minutes": 10080},  # weekly
}


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_due(task_name, config, state, force=False):
    if force:
        return True
    last_run_str = state.get(task_name)
    if not last_run_str:
        return True  # never run before
    last_run = datetime.fromisoformat(last_run_str)
    elapsed_minutes = (datetime.now(timezone.utc) - last_run).total_seconds() / 60
    return elapsed_minutes >= config["interval_minutes"]


def run_task(task_name, config):
    script = config["script"]
    print(f"\n[scheduler] --- Running {task_name} ({script}) at {datetime.now(timezone.utc).isoformat()} ---")
    if not os.path.exists(script):
        print(f"[scheduler] WARNING: {script} not found in this folder — skipping.")
        return False
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=120,
            env=os.environ.copy(),  # pass through whatever tokens you've exported
        )
        print(result.stdout)
        if result.stderr:
            print(f"[scheduler] stderr from {script}:\n{result.stderr}")
        if result.returncode != 0:
            print(f"[scheduler] {script} exited with an error (code {result.returncode}) — "
                  f"NOT marking this as a successful run, will retry next cycle.")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"[scheduler] {script} took too long (>120s) and was killed.")
        return False
    except Exception as e:
        print(f"[scheduler] Failed to run {script}: {e}")
        return False


def main():
    force = "--run-now" in sys.argv
    state = load_state()

    print(f"[scheduler] Starting. Tasks: {list(TASKS.keys())}")
    if force:
        print("[scheduler] --run-now passed: forcing every task to run once, then exiting.")

    while True:
        for task_name, config in TASKS.items():
            if is_due(task_name, config, state, force=force):
                success = run_task(task_name, config)
                if success:
                    state[task_name] = datetime.now(timezone.utc).isoformat()
                    save_state(state)

        if force:
            print("\n[scheduler] --run-now complete. Exiting.")
            break

        time.sleep(60)  # check again in a minute


if __name__ == "__main__":
    main()
