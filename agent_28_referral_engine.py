"""
AGENT 28 — Referral & Affiliate Engine
==========================================

The "be unique to enter the market" idea, done legitimately. Two growth
mechanics most small agencies never build:

  1. CLIENT REFERRALS — every happy client gets a unique referral code.
     When they refer another business that signs up, both get a reward
     (a discount month, a free add-on). For local businesses, word-of-
     mouth is the strongest channel — this systematizes and rewards it.

  2. AFFILIATE PARTNERS — people who aren't clients but send you business
     (web designers, business consultants, CA/accountants who serve SMBs)
     get a commission for every client they refer who signs. This turns
     other people's networks into your sales team.

This tracks codes, attributes signups to referrers, computes rewards/
commissions owed, and flags who to thank/pay. All local JSON — no
external service, no monthly fee.

This is a genuine differentiator: performance-aligned growth. You only
reward referrals that actually convert to paying clients.
"""

import os
import json
import argparse
from datetime import datetime, timezone

REFERRAL_DB = "referral_db.json"

# Reward structure — tune to your economics
REWARDS = {
    "client_referral": {"referrer": "1 month 20% off", "new_client": "1 month 20% off"},
    "affiliate": {"commission_pct": 15, "note": "15% of first month's fee, one-time, per converted client"},
}


def load_db():
    if not os.path.exists(REFERRAL_DB):
        return {"referrers": {}, "signups": []}
    with open(REFERRAL_DB) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"referrers": {}, "signups": []}


def save_db(db):
    with open(REFERRAL_DB, "w") as f:
        json.dump(db, f, indent=2)


def _gen_code(name):
    base = "".join(c for c in name.upper() if c.isalnum())[:6]
    return f"{base}{str(abs(hash(name)))[:3]}"


def register_referrer(name, kind, contact=""):
    """kind: 'client_referral' or 'affiliate'"""
    db = load_db()
    code = _gen_code(name)
    db["referrers"][code] = {
        "name": name, "kind": kind, "contact": contact,
        "code": code, "registered_at": datetime.now(timezone.utc).isoformat(),
        "conversions": 0, "rewards_owed": [],
    }
    save_db(db)
    print(f"[agent-28] Registered {name} as {kind}. Their code: {code}")
    print(f"           Share this code with them to pass to businesses they refer.")
    return code


def record_signup(new_client_name, referral_code, first_month_fee=0):
    """Call when a new client signs up citing a referral code."""
    db = load_db()
    referrer = db["referrers"].get(referral_code)
    if not referrer:
        print(f"[agent-28] Code '{referral_code}' not found — signup recorded with no attribution.")
        db["signups"].append({"client": new_client_name, "code": None,
                              "at": datetime.now(timezone.utc).isoformat()})
        save_db(db)
        return

    referrer["conversions"] += 1
    reward = REWARDS[referrer["kind"]]

    if referrer["kind"] == "affiliate":
        commission = round(first_month_fee * reward["commission_pct"] / 100)
        owed = f"₹{commission} commission ({reward['commission_pct']}% of ₹{first_month_fee})"
    else:
        owed = reward["referrer"]

    referrer["rewards_owed"].append({"for_client": new_client_name, "reward": owed,
                                     "at": datetime.now(timezone.utc).isoformat(), "paid": False})
    db["signups"].append({"client": new_client_name, "code": referral_code,
                          "referrer": referrer["name"], "at": datetime.now(timezone.utc).isoformat()})
    save_db(db)

    print(f"[agent-28] ✅ {new_client_name} signed up via {referrer['name']} ({referral_code})")
    print(f"           Owed to {referrer['name']}: {owed}")
    if referrer["kind"] == "client_referral":
        print(f"           New client {new_client_name} also gets: {reward['new_client']}")


def show_whats_owed():
    db = load_db()
    print(f"\n{'='*55}")
    print("REWARDS & COMMISSIONS OWED")
    print(f"{'='*55}")
    any_owed = False
    for code, r in db["referrers"].items():
        unpaid = [rw for rw in r["rewards_owed"] if not rw["paid"]]
        if unpaid:
            any_owed = True
            print(f"\n  {r['name']} ({r['kind']}, code {code}) — {r['conversions']} conversion(s)")
            for rw in unpaid:
                print(f"    • {rw['reward']}  (for {rw['for_client']})")
    if not any_owed:
        print("\n  Nothing outstanding.")
    print(f"{'='*55}\n")


def leaderboard():
    db = load_db()
    ranked = sorted(db["referrers"].values(), key=lambda r: r["conversions"], reverse=True)
    print("\n=== TOP REFERRERS ===")
    for r in ranked[:10]:
        if r["conversions"] > 0:
            print(f"  {r['name']:<25} {r['conversions']} client(s) referred")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", nargs=2, metavar=("NAME", "KIND"), help="KIND: client_referral or affiliate")
    parser.add_argument("--signup", nargs=2, metavar=("CLIENT", "CODE"))
    parser.add_argument("--fee", type=int, default=14999, help="first month fee for affiliate commission calc")
    parser.add_argument("--owed", action="store_true")
    parser.add_argument("--leaderboard", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        # Full demo of the whole flow
        c1 = register_referrer("Priya (Rold Gold)", "client_referral", "9999999999")
        c2 = register_referrer("Ramesh (CA who serves SMBs)", "affiliate", "8888888888")
        print()
        record_signup("epixsave lamps", c1)
        record_signup("A local gym", c2, first_month_fee=14999)
        record_signup("A dental clinic", c2, first_month_fee=24999)
        show_whats_owed()
        leaderboard()
    elif args.register:
        register_referrer(args.register[0], args.register[1])
    elif args.signup:
        record_signup(args.signup[0], args.signup[1], args.fee)
    elif args.owed:
        show_whats_owed()
    elif args.leaderboard:
        leaderboard()
    else:
        print("Use --demo to see the full flow, or --register / --signup / --owed / --leaderboard")
