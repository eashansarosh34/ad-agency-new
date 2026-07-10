"""
Wrapper for Agent 14 — lets the scheduler run it as a plain subprocess
without needing to pass a --niche argument through the scheduler itself.

Edit NICHE below once per client, then add this file (not agent_14
directly) to the scheduler's TASKS dict.
"""
import subprocess
import sys

NICHE = "dental clinic ads India"  # <-- change this per client

subprocess.run([sys.executable, "agent_14_competitive_monitor.py", "--niche", NICHE])
