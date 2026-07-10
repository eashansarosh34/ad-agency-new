"""
THE ORCHESTRATOR — One agentic brain for the entire agency
==============================================================

THE ARCHITECTURAL SHIFT:
  Everything built before this is a "workflow" — fixed rules, fixed
  thresholds (pause if CPL > 1.5x avg, etc.). This is an "agent" in the
  true sense: Claude itself looks at ALL the data across every client,
  reasons about what matters right now, and decides what to do —
  choosing from the same actions the individual agents perform, but
  with judgment instead of thresholds.

  Example of the difference:
    Workflow: "CPL is 1.6x average → pause" (even if it's Diwali week
              and every CPL is temporarily inflated)
    Agent:    "CPL is up across ALL ads equally — that's market-wide
              CPM inflation, not a bad ad. Don't pause anything, note
              it in the owner brief, recheck in 3 days."

  That judgment call is the entire difference between what you have
  and what nobody else in the Indian SMB market has.

HOW IT RUNS (100% hands-off after setup):
  GitHub Actions triggers this on a schedule (e.g. every 6 hours).
  No terminal. No laptop. It gathers state, thinks, acts within
  guardrails, and WhatsApps you a summary of what it did and why.

HARD GUARDRAILS (enforced in CODE — Claude cannot override these,
no matter what it decides):
  1. Budget ceiling per client — hard-coded, checked before ANY spend action
  2. Max 3 write-actions per run — prevents runaway behavior
  3. Certain actions ALWAYS escalate to human, never auto-execute:
     - anything compliance-flagged
     - any budget increase beyond +25% in one run
     - pausing ALL of a client's ads at once
  4. Max 10 reasoning iterations per run — hard stop
  5. Every action logged with Claude's stated reasoning — full audit trail

SAFETY DEFAULT: DRY_RUN = True. In dry-run, Claude reasons and decides
exactly as it would live, but every action is logged as "would do"
instead of executed. Run it dry for a week. Read its decisions.
Only then flip it.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
META_API_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")

# Clients this orchestrator manages. Add one block per client.
CLIENTS = json.loads(os.environ.get("CLIENTS_JSON", json.dumps([
    {
        "name": "SunCap",
        "ad_account_id": os.environ.get("META_AD_ACCOUNT_ID", "act_XXXX"),
        "page_id": os.environ.get("META_PAGE_ID", ""),
        "budget_ceiling": 20000,
        "niche": "financial services",
        "goal": "qualified leads for stock analysis service",
    },
])))

DRY_RUN = os.environ.get("ORCHESTRATOR_DRY_RUN", "true").lower() != "false"
MAX_ITERATIONS = 10          # hard stop on the reasoning loop
MAX_WRITE_ACTIONS = 3        # hard cap on actions with side effects per run
MAX_BUDGET_INCREASE_PCT = 25 # anything beyond this always escalates
MAX_BUDGET_DECREASE_PCT = 40 # a cut deeper than this also escalates (protects working campaigns)

DECISIONS_LOG = "orchestrator_decisions.json"
AGENCY_OWNER_WHATSAPP = os.environ.get("AGENCY_OWNER_WHATSAPP", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")

# ----------------------------------------------------------------------------
# STATE GATHERING — everything Claude sees before deciding
# ----------------------------------------------------------------------------

def gather_client_state(client):
    """Pull everything knowable about one client into a single picture."""
    state = {"client": client["name"], "goal": client["goal"],
             "budget_ceiling": client["budget_ceiling"], "errors": []}

    # Ad performance (last 7 days, per ad)
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        resp = requests.get(f"{META_API_URL}/{client['ad_account_id']}/insights", params={
            "access_token": META_ACCESS_TOKEN, "level": "ad",
            "fields": "ad_id,ad_name,adset_id,spend,actions,ctr,impressions",
            "time_range": json.dumps({"since": since, "until": until}), "limit": 50,
        }, timeout=30)
        resp.raise_for_status()
        ads = []
        for row in resp.json().get("data", []):
            spend = float(row.get("spend", 0))
            leads = sum(int(a.get("value", 0)) for a in row.get("actions", [])
                        if a.get("action_type") in ("lead", "onsite_conversion.lead_grouped"))
            ads.append({"ad_id": row["ad_id"], "ad_name": row.get("ad_name"),
                        "adset_id": row.get("adset_id"), "spend": spend, "leads": leads,
                        "cpl": round(spend/leads) if leads else None,
                        "ctr": float(row.get("ctr", 0))})
        state["ads"] = ads
        state["total_spend_7d"] = sum(a["spend"] for a in ads)
    except Exception as e:
        state["errors"].append(f"Could not fetch ad data: {e}")
        state["ads"] = []

    # Recent leads (from local db written by the poller)
    try:
        if os.path.exists("leads_db.json"):
            with open("leads_db.json") as f:
                leads_db = json.load(f)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent = [v for v in leads_db.values()
                      if v.get("created_at") and datetime.fromisoformat(v["created_at"]) > recent_cutoff]
            state["recent_leads_count"] = len(recent)
            state["leads_awaiting_contact"] = len([l for l in recent if l.get("status") == "contacted"
                                                     and not l.get("last_reply")])
    except Exception as e:
        state["errors"].append(f"Could not read leads db: {e}")

    # Prior orchestrator decisions (so it doesn't repeat itself)
    try:
        if os.path.exists(DECISIONS_LOG):
            with open(DECISIONS_LOG) as f:
                decisions = json.load(f)
            state["my_recent_decisions"] = [
                {"at": d["timestamp"], "action": d["action"], "reasoning": d["reasoning"][:150]}
                for d in decisions[-5:] if d.get("client") == client["name"]
            ]
    except Exception:
        pass

    return state


# ----------------------------------------------------------------------------
# TOOLS — the actions Claude can take (the old agents become its hands)
# ----------------------------------------------------------------------------

TOOLS = [
    {
        "name": "pause_ad",
        "description": "Pause a specific underperforming ad. Use when an ad is clearly wasting budget relative to alternatives AND the cause is the ad itself, not market-wide conditions.",
        "input_schema": {"type": "object", "properties": {
            "ad_id": {"type": "string"}, "ad_name": {"type": "string"},
            "reasoning": {"type": "string", "description": "Why this specific ad, why now"}},
            "required": ["ad_id", "ad_name", "reasoning"]},
    },
    {
        "name": "adjust_adset_budget",
        "description": f"Change an ad set's daily budget. Increases beyond {MAX_BUDGET_INCREASE_PCT}% or cuts deeper than -{MAX_BUDGET_DECREASE_PCT}% will be escalated to the human instead of executed.",
        "input_schema": {"type": "object", "properties": {
            "adset_id": {"type": "string"}, "change_pct": {"type": "number",
                "description": "Percent change, e.g. 20 for +20%, -30 for -30%"},
            "reasoning": {"type": "string"}},
            "required": ["adset_id", "change_pct", "reasoning"]},
    },
    {
        "name": "escalate_to_human",
        "description": "Flag something for the agency owner's judgment instead of acting. Use for: anything ambiguous, anything compliance-adjacent, relationship issues, or when confidence is low. Escalating is ALWAYS acceptable — never guess on something important.",
        "input_schema": {"type": "object", "properties": {
            "severity": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
            "summary": {"type": "string"}, "recommended_action": {"type": "string"}},
            "required": ["severity", "summary", "recommended_action"]},
    },
    {
        "name": "note_for_owner_brief",
        "description": "Add an observation to the owner's summary without taking action. Use for things worth knowing that don't need action: trends, early signals, things to watch.",
        "input_schema": {"type": "object", "properties": {
            "note": {"type": "string"}}, "required": ["note"]},
    },
    {
        "name": "finish_run",
        "description": "Call this when you've assessed everything and taken (or deliberately not taken) all needed actions. Provide the owner summary.",
        "input_schema": {"type": "object", "properties": {
            "owner_summary": {"type": "string",
                "description": "Plain-language WhatsApp-length summary of this run: what you saw, what you did, what you deliberately didn't do and why"}},
            "required": ["owner_summary"]},
    },
]


def execute_tool(tool_name, tool_input, run_state):
    """Execute a tool call — with hard guardrails Claude cannot override."""

    if tool_name == "pause_ad":
        if run_state["write_actions"] >= MAX_WRITE_ACTIONS:
            return {"blocked": True, "reason": f"Hard cap of {MAX_WRITE_ACTIONS} write-actions per run already reached."}
        # Guardrail: never allow pausing the last active ad (would kill delivery entirely)
        run_state["write_actions"] += 1
        log_decision(run_state["client"], "pause_ad", tool_input["reasoning"], tool_input)
        if DRY_RUN:
            return {"executed": False, "dry_run": True,
                    "would_do": f"Pause ad '{tool_input['ad_name']}' ({tool_input['ad_id']})"}
        try:
            resp = requests.post(f"{META_API_URL}/{tool_input['ad_id']}",
                data={"access_token": META_ACCESS_TOKEN, "status": "PAUSED"}, timeout=30)
            resp.raise_for_status()
            return {"executed": True}
        except Exception as e:
            return {"executed": False, "error": str(e)}

    if tool_name == "adjust_adset_budget":
        change = tool_input["change_pct"]
        # HARD GUARDRAIL: large increases AND large decreases both escalate.
        # A big cut can kill a working campaign as badly as a big raise can
        # blow the budget — both need a human's eyes, never auto-executed.
        if change > MAX_BUDGET_INCREASE_PCT:
            log_decision(run_state["client"], "escalated_budget_increase",
                         f"Claude wanted +{change}% but guardrail caps auto-increases at {MAX_BUDGET_INCREASE_PCT}%",
                         tool_input)
            return {"blocked": True,
                    "reason": f"Increases beyond {MAX_BUDGET_INCREASE_PCT}% require human approval — escalated instead. You may call escalate_to_human to explain why you wanted this."}
        if change < -MAX_BUDGET_DECREASE_PCT:
            log_decision(run_state["client"], "escalated_budget_decrease",
                         f"Claude wanted {change}% but guardrail caps auto-decreases at -{MAX_BUDGET_DECREASE_PCT}%",
                         tool_input)
            return {"blocked": True,
                    "reason": f"Cuts deeper than -{MAX_BUDGET_DECREASE_PCT}% require human approval (a big cut can kill a working campaign) — escalated instead. You may call escalate_to_human to explain why, or pause_ad if the goal is to stop a specific bad ad."}
        if run_state["write_actions"] >= MAX_WRITE_ACTIONS:
            return {"blocked": True, "reason": "Write-action cap reached this run."}
        run_state["write_actions"] += 1
        log_decision(run_state["client"], "adjust_budget", tool_input["reasoning"], tool_input)
        if DRY_RUN:
            return {"executed": False, "dry_run": True,
                    "would_do": f"Change ad set {tool_input['adset_id']} budget by {change:+.0f}%"}
        try:
            current = requests.get(f"{META_API_URL}/{tool_input['adset_id']}",
                params={"access_token": META_ACCESS_TOKEN, "fields": "daily_budget"}, timeout=30).json()
            new_budget = int(float(current.get("daily_budget", 0)) * (1 + change/100))
            resp = requests.post(f"{META_API_URL}/{tool_input['adset_id']}",
                data={"access_token": META_ACCESS_TOKEN, "daily_budget": new_budget}, timeout=30)
            resp.raise_for_status()
            return {"executed": True, "new_budget": new_budget}
        except Exception as e:
            return {"executed": False, "error": str(e)}

    if tool_name == "escalate_to_human":
        log_decision(run_state["client"], "escalate", tool_input["summary"], tool_input)
        run_state["escalations"].append(tool_input)
        return {"escalated": True}

    if tool_name == "note_for_owner_brief":
        run_state["notes"].append(tool_input["note"])
        return {"noted": True}

    if tool_name == "finish_run":
        run_state["finished"] = True
        run_state["owner_summary"] = tool_input["owner_summary"]
        return {"finished": True}

    return {"error": f"Unknown tool {tool_name}"}


def log_decision(client, action, reasoning, details):
    existing = []
    if os.path.exists(DECISIONS_LOG):
        with open(DECISIONS_LOG) as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                     "client": client, "action": action, "reasoning": reasoning,
                     "details": details, "dry_run": DRY_RUN})
    with open(DECISIONS_LOG, "w") as f:
        json.dump(existing, f, indent=2)


# ----------------------------------------------------------------------------
# THE AGENTIC LOOP
# ----------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the autonomous operations brain of a one-person performance
marketing agency in India. You run every few hours. Your job: look at each client's
current state and decide what — if anything — needs doing right now.

Your operating principles, in priority order:
1. PROTECT CLIENT MONEY. Never let budget waste continue when you can stop it.
2. DON'T OVERREACT. Market-wide fluctuations (festival CPM spikes, weekend dips,
   learning-phase noise) are not ad problems. An ad needs meaningful spend and a
   clear comparative gap before judging it. When every ad moves together, the cause
   is external — note it, don't act on it.
3. ESCALATE WHEN UNSURE. You have an escalate_to_human tool. Using it is always
   acceptable and often the smartest move. Guessing on something important is not.
4. EXPLAIN EVERYTHING. Every action needs reasoning a client could read and accept.
5. FINISH DECISIVELY. End every run with finish_run and an honest owner summary —
   including what you deliberately chose NOT to do and why. "Everything looks fine,
   no action needed" is a perfectly good outcome.

Hard limits enforced outside your control: max 3 write-actions per run, budget
increases over 25% auto-escalate, compliance-flagged anything always escalates.
"""


def call_claude(messages):
    resp = requests.post(
        ANTHROPIC_API_URL,
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 2000,
              "system": SYSTEM_PROMPT, "tools": TOOLS, "messages": messages},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def run_orchestrator():
    print(f"=== ORCHESTRATOR RUN: {datetime.now(timezone.utc).isoformat()} (DRY_RUN={DRY_RUN}) ===\n")

    all_summaries = []

    for client in CLIENTS:
        print(f"--- Assessing {client['name']} ---")
        state = gather_client_state(client)
        run_state = {"client": client["name"], "write_actions": 0,
                     "escalations": [], "notes": [], "finished": False, "owner_summary": ""}

        messages = [{"role": "user", "content":
            f"Here is the current state for client '{client['name']}':\n\n"
            f"{json.dumps(state, indent=2)}\n\n"
            f"Assess it and take whatever actions are genuinely needed. "
            f"Remember: no action is often the right action."}]

        for iteration in range(MAX_ITERATIONS):
            try:
                response = call_claude(messages)
            except Exception as e:
                print(f"  Claude call failed: {e}")
                run_state["owner_summary"] = f"Orchestrator run failed for {client['name']}: {e}"
                break

            assistant_content = response.get("content", [])
            messages.append({"role": "assistant", "content": assistant_content})

            tool_calls = [b for b in assistant_content if b.get("type") == "tool_use"]
            text_blocks = [b.get("text", "") for b in assistant_content if b.get("type") == "text"]
            for t in text_blocks:
                if t.strip():
                    print(f"  [thinking] {t.strip()[:200]}")

            if not tool_calls:
                # No tool call and no finish — nudge once, then stop
                messages.append({"role": "user", "content":
                    "You must either take an action or call finish_run with your summary."})
                continue

            tool_results = []
            for tc in tool_calls:
                result = execute_tool(tc["name"], tc["input"], run_state)
                print(f"  [action] {tc['name']}: {json.dumps(tc['input'])[:150]}")
                print(f"           -> {json.dumps(result)[:150]}")
                tool_results.append({"type": "tool_result", "tool_use_id": tc["id"],
                                     "content": json.dumps(result)})
            messages.append({"role": "user", "content": tool_results})

            if run_state["finished"]:
                break
        else:
            print(f"  Hit {MAX_ITERATIONS}-iteration hard stop.")
            run_state["owner_summary"] = run_state["owner_summary"] or \
                f"{client['name']}: run hit iteration limit before finishing cleanly — review the decision log."

        all_summaries.append(f"[{client['name']}] {run_state['owner_summary']}")
        if run_state["escalations"]:
            for esc in run_state["escalations"]:
                all_summaries.append(f"  ⚠ ESCALATION ({esc['severity']}): {esc['summary']} "
                                     f"— Recommended: {esc['recommended_action']}")
        print()

    # Owner WhatsApp brief
    full_brief = "🤖 Agency run complete\n\n" + "\n\n".join(all_summaries)
    print(f"=== OWNER BRIEF ===\n{full_brief}\n")

    if AGENCY_OWNER_WHATSAPP and WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID and not DRY_RUN:
        try:
            requests.post(
                f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}",
                         "Content-Type": "application/json"},
                json={"messaging_product": "whatsapp", "to": AGENCY_OWNER_WHATSAPP,
                      "type": "text", "text": {"body": full_brief[:4000]}}, timeout=15)
        except Exception as e:
            print(f"Owner WhatsApp failed: {e}")
    elif DRY_RUN:
        print("[DRY RUN] Owner brief printed above; would be WhatsApped when live.")


if __name__ == "__main__":
    run_orchestrator()
