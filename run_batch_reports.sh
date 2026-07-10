#!/bin/bash
# ============================================================
# run_batch_reports.sh — one-step Trojan Report launcher
# ============================================================
# Double-click this (or run: bash run_batch_reports.sh) to
# generate all your prospect reports in one go.
#
# FIRST TIME SETUP: open this file in any text editor and paste
# your two keys between the quotes below, then save. You only
# do this once.
# ============================================================

# ---- PASTE YOUR KEYS HERE (between the quotes) ----
export ANTHROPIC_API_KEY=""
export TAVILY_API_KEY=""
# ---------------------------------------------------

# Optional: your Meta creds, only needed if a report should pull live account data.
# Leave blank otherwise — reports work fine without them.
export META_ACCESS_TOKEN="${META_ACCESS_TOKEN:-}"
export META_AD_ACCOUNT_ID="${META_AD_ACCOUNT_ID:-}"

echo "============================================"
echo " Apna Marketer — Batch Report Generator"
echo "============================================"
echo ""

# Sanity check: are keys set?
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "NOTE: No Anthropic key set. Reports will still generate using the"
  echo "      built-in benchmarks, but without the AI-written sections."
  echo "      To add keys, open this file in a text editor and paste them at the top."
  echo ""
fi

# Make sure the batch script is here
if [ ! -f "batch_trojan_reports.py" ]; then
  echo "ERROR: batch_trojan_reports.py not found in this folder."
  echo "Make sure you're running this from your agent files folder."
  exit 1
fi

# Run it
python3 batch_trojan_reports.py

echo ""
echo "============================================"
echo " Done. Next:"
echo " 1. Open the 'reports_to_send' folder"
echo " 2. Read each .html report in your browser"
echo " 3. Send the good ones yourself via WhatsApp/email"
echo " 4. Run: python3 outreach_tracker.py  (to log who you contacted)"
echo "============================================"
