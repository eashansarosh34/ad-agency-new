"""
AGENT 29 — Strategy Reasoning Layer ("Show Your Working")
============================================================

The Tempo lesson, applied: every action any agent takes should be
inspectable by the client — not just "we paused an ad" but the full
reasoning: what we observed, the insight, the hypothesis, and what
we expect to happen. This turns your decision logs into a client-facing
"here's exactly why we did everything" feature.

This is the deepest version of your "Nothing to Hide" positioning:
not just showing the NUMBERS (Agent 15 dashboard), but showing the
THINKING. No agency at your tier does this. Tempo does it for e-commerce
creative; you'd do it across every decision, for every client.

It reads the decision logs every agent already writes (orchestrator_decisions.json,
agent_02_actions.json, compliance_log.json, etc.) and renders them as a
clean, plain-language "strategy story" a client can read and trust.
"""

import os
import json
import argparse
from datetime import datetime, timezone

# All the decision logs the various agents write
LOG_SOURCES = {
    "orchestrator_decisions.json": "Strategic decisions",
    "agent_02_actions.json": "Ad optimizations",
    "compliance_log.json": "Compliance checks",
    "agent_13_actions.json": "Budget shifts across platforms",
    "human_escalations.json": "Flagged for human review",
    "orchestrator_predictions.json": "Predictions made",
}


def load_log(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            return []


def build_strategy_story(client_name=None, days=7):
    """Assemble every logged decision into one readable narrative."""
    cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
    all_events = []

    for path, label in LOG_SOURCES.items():
        for entry in load_log(path):
            ts_str = entry.get("timestamp") or entry.get("checked_at") or entry.get("escalated_at") or entry.get("generated_at")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str).timestamp()
            except ValueError:
                continue
            if ts < cutoff:
                continue
            if client_name and entry.get("client") and entry["client"] != client_name:
                continue
            all_events.append({"when": ts_str, "category": label, "raw": entry})

    all_events.sort(key=lambda e: e["when"])
    return all_events


def render_for_client(events, client_name="your"):
    """Plain-language, no-jargon rendering a client can actually read."""
    print(f"\n{'='*60}")
    print(f"WHY WE DID WHAT WE DID — {client_name}'s campaign")
    print(f"The thinking behind every decision, in plain language")
    print(f"{'='*60}")

    if not events:
        print("\n  No decisions logged in this period. Campaign running steadily.")
        return

    for e in events:
        raw = e["raw"]
        when = e["when"][:10]
        reasoning = (raw.get("reasoning") or raw.get("summary") or raw.get("reason")
                     or raw.get("owner_summary") or "")
        action = raw.get("action") or raw.get("category") or e["category"]

        print(f"\n  📅 {when} — {e['category']}")
        if action and action != e["category"]:
            print(f"     What we did: {_humanize_action(action)}")
        if reasoning:
            print(f"     Why: {reasoning}")


def _humanize_action(action):
    """Turn internal action names into client-readable phrases."""
    mapping = {
        "pause_ad": "Paused an underperforming ad",
        "adjust_budget": "Shifted budget between ads",
        "adjust_adset_budget": "Adjusted an ad set's daily budget",
        "boost": "Increased budget on a winning ad",
        "escalate": "Flagged something for a human to decide",
        "escalated_budget_increase": "Held back an aggressive change for human review",
        "pause": "Paused an ad",
    }
    return mapping.get(action, action.replace("_", " ").capitalize())


def generate_reasoning_record(observed, insight, hypothesis, expected_outcome, client=None):
    """
    The forward-looking version: BEFORE/AS an agent acts, it records the
    full reasoning in Tempo's structure. Call this from any agent that
    wants its decisions to be client-inspectable.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client": client,
        "observed": observed,       # what the data showed
        "insight": insight,         # what it means
        "hypothesis": hypothesis,   # what we think will help
        "expected_outcome": expected_outcome,  # what we expect to happen
        "actual_outcome": None,     # filled in later, closing the loop
    }
    existing = load_log("reasoning_records.json")
    existing.append(record)
    with open("reasoning_records.json", "w") as f:
        json.dump(existing, f, indent=2)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", default=None)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        # Show the forward-looking reasoning structure
        print("=== Example: a fully-reasoned decision (Tempo-style) ===")
        r = generate_reasoning_record(
            observed="The 'Before/After' ad has a 4.8% click rate and ₹200 cost per lead, "
                     "while the 'Product Photo' ad has 0.8% clicks and no leads over 7 days.",
            insight="Customers respond far more to transformation stories than to plain product shots. "
                    "The audience wants to see the result, not the item.",
            hypothesis="Shifting budget from the product-photo ad to the before/after ad, and creating "
                       "two more transformation-style variants, should lower overall cost per lead.",
            expected_outcome="Cost per lead should drop from the current ₹221 average toward ₹200 or below "
                             "within one week.",
            client="Demo Client")
        print(json.dumps(r, indent=2))

        print("\n\n=== Example: the client-facing 'strategy story' view ===")
        # Seed a couple of decision-log entries to render
        with open("orchestrator_decisions.json", "w") as f:
            json.dump([
                {"timestamp": datetime.now(timezone.utc).isoformat(), "client": "Demo Client",
                 "action": "pause_ad", "reasoning": "Product-photo ad spent ₹2,900 with zero leads while "
                 "other ads converted well. Clear waste, so we stopped it."},
                {"timestamp": datetime.now(timezone.utc).isoformat(), "client": "Demo Client",
                 "action": "boost", "reasoning": "The before/after ad is your best performer at ₹200 per "
                 "lead, so we moved more of the daily budget toward it."},
            ], f)
        events = build_strategy_story(client_name="Demo Client")
        render_for_client(events, "Demo Client")
    else:
        events = build_strategy_story(client_name=args.client, days=args.days)
        render_for_client(events, args.client or "your")
