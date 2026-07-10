"""
AGENT 12 — Compliance & Decision Gate
=========================================

What this does:
  Checks any AI-generated content (ad copy, claims) against rules BEFORE
  it goes live — banned claims for regulated categories, required
  disclaimers, brand-safety language — and logs every check with its
  reasoning. This is the exact capability the ad-tech industry's own
  verification vendors say they won't ship broadly until later this year
  (autonomous execution with inline guardrails) — built here at small
  scale, today, deliberately ahead of that curve.

  Defense in depth: a hard keyword check runs regardless of API access
  (catches the worst literal violations even with zero internet), and a
  nuanced Claude-based check catches paraphrased/disguised versions of
  the same violations when a live key is available.

Categories included (extend RULES below for your client's actual niche):
  - financial_services: relevant to SunCap specifically — SEBI-sensitive
    language around guaranteed returns, risk-free claims
  - healthcare: relevant if you take on clinic/medical clients later
  - general: baseline brand-safety check for anything else

Usage:
  python3 agent_12_compliance_gate.py --check "your ad copy here" --category financial_services
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LOG_FILE = os.environ.get("COMPLIANCE_LOG_PATH", "compliance_log.json")

RULES = {
    "financial_services": {
        "banned_phrases": ["guaranteed return", "guaranteed returns", "risk-free", "risk free",
                            "no risk", "100% safe", "double your money", "assured profit",
                            "guaranteed profit", "zero risk"],
        "required_context": "Any mention of returns or investment performance should be "
                             "accompanied by a risk disclaimer (e.g. 'investments are subject "
                             "to market risk') — flag if missing, don't auto-add it.",
        "notes": "SEBI-sensitive category — relevant to SunCap. When in doubt, flag for human "
                 "review rather than guess at compliance; this is not legal advice.",
    },
    "healthcare": {
        "banned_phrases": ["guaranteed cure", "100% effective", "no side effects", "miracle",
                            "guaranteed results", "fda approved" ],
        "required_context": "Medical/health claims should not promise specific outcomes.",
        "notes": "Relevant if onboarding clinic-type clients again later.",
    },
    "general": {
        "banned_phrases": ["guaranteed", "100% effective", "miracle", "no risk"],
        "required_context": "Baseline brand-safety check — vague superlatives without backing.",
        "notes": "Default category for anything not in a regulated vertical.",
    },
}


def keyword_check(text, category):
    rules = RULES.get(category, RULES["general"])
    lowered = text.lower()
    hits = [phrase for phrase in rules["banned_phrases"] if phrase in lowered]
    return hits


def claude_check(text, category):
    rules = RULES.get(category, RULES["general"])
    prompt = f"""You are a compliance reviewer for advertising content in the "{category}" category.
Rules context: {rules['required_context']}
Notes: {rules['notes']}

Review this ad copy for compliance risk, including PARAPHRASED or implied versions of banned
claims (not just exact phrase matches) — e.g. "your money is completely protected" implies
risk-free even without using that exact phrase:

"{text}"

Respond with ONLY raw JSON, no markdown:
{{"verdict": "PASS" or "FLAGGED", "issues": ["..."], "reasoning": "..."}}"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 400,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    response.raise_for_status()
    raw = "".join(b.get("text", "") for b in response.json().get("content", []) if b.get("type") == "text")
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def check_compliance(text, category="general"):
    keyword_hits = keyword_check(text, category)

    claude_result = None
    claude_error = None
    if ANTHROPIC_API_KEY:
        try:
            claude_result = claude_check(text, category)
        except Exception as e:
            claude_error = str(e)

    if claude_result:
        verdict = claude_result["verdict"]
        issues = claude_result["issues"] + [f"keyword match: '{h}'" for h in keyword_hits]
        reasoning = claude_result["reasoning"]
        if keyword_hits and verdict == "PASS":
            verdict = "FLAGGED"  # hard keyword hit always overrides a soft PASS
    else:
        verdict = "FLAGGED" if keyword_hits else "PASS (keyword check only — no live review available)"
        issues = [f"keyword match: '{h}'" for h in keyword_hits]
        reasoning = f"Live compliance review unavailable ({claude_error or 'no API key set'}); "\
                    f"only the hard keyword list was checked. Treat PASS here as provisional."

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "text_preview": text[:120],
        "verdict": verdict,
        "issues": issues,
        "reasoning": reasoning,
    }
    log_check(result)

    if verdict == "FLAGGED":
        try:
            from agent_22_human_escalation import escalate
            escalate("compliance", os.environ.get("CLIENT_NAME", "Client"),
                     f"Compliance check FLAGGED ad copy in '{category}' category: {issues}",
                     details=result, notify_client=False)
        except ImportError:
            pass  # Agent 22 not present — compliance check still works standalone

    return result


def log_check(result):
    existing = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(result)
    with open(LOG_FILE, "w") as f:
        json.dump(existing, f, indent=2)


if __name__ == "__main__":
    if "--check" not in sys.argv:
        print('Usage: python3 agent_12_compliance_gate.py --check "your text" --category financial_services')
        sys.exit(0)

    text = sys.argv[sys.argv.index("--check") + 1]
    category = "general"
    if "--category" in sys.argv:
        category = sys.argv[sys.argv.index("--category") + 1]

    result = check_compliance(text, category)
    print(f"\n[agent-12] Verdict: {result['verdict']}")
    if result["issues"]:
        print(f"[agent-12] Issues: {result['issues']}")
    print(f"[agent-12] Reasoning: {result['reasoning']}")
