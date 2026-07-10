# Referral Army Playbook
## Your Scale Engine as a Solo Operator

> You can't knock on 500 doors. So recruit ~20 people who already stand inside them.

---

## The Two Tiers

### Tier 1 — Happy Clients (Word-of-Mouth, Systematised)

Every client who signs up gets a unique referral code. When they refer another business:
- **They get**: 1 month at 50% off (₹7,499 instead of ₹14,999)
- **New client gets**: 1 month at 50% off too
- You pay nothing extra — the discount comes off your fee, not out of pocket

Register them:
```bash
python3 agent_28_referral_engine.py --register "Priya Dental" client_referral
```
Output: their unique code (e.g. `PRIYAD847`). WhatsApp it to them.

---

### Tier 2 — Scouts / Affiliates (Your External Sales Team)

People who **aren't clients** but talk to dozens of SMB owners every month. You give them a code. Every business that signs up using their code earns them a commission — forever, per client they bring.

**Commission: 15% of first month's fee = ₹2,249 per converted client**

No retainer. No commitment. Pure performance.

Register a scout:
```bash
python3 agent_28_referral_engine.py --register "Ramesh CA" affiliate
```

Record a signup via their code:
```bash
python3 agent_28_referral_engine.py --signup "New Clinic" RAMES123 --fee 14999
# Output: ₹2,249 commission owed to Ramesh CA
```

Check who you owe:
```bash
python3 agent_28_referral_engine.py --owed
```

Leaderboard:
```bash
python3 agent_28_referral_engine.py --leaderboard
```

---

## Target Scout Profiles (The 20 People to Recruit)

These are people who speak to SMB owners **every single day** as part of their existing job. They don't need to be convinced to sell for you — they just need a reason to mention you.

| Scout Type | Why They're Perfect | Where to Find Them |
|---|---|---|
| **Chartered Accountants / Tax CAs** | They do GST, ITR for 50–200 small businesses. Their clients ask them "how do I grow?" all the time | CA listings on IndiaMART, local CA associations, LinkedIn |
| **Web Designers / Developers** | They build sites but don't run ads. Clients ask "can you help us get more customers?" — and they have no answer | Freelancer.in, local WhatsApp groups, Behance |
| **POS / Billing Software Sellers** | They physically walk into restaurants, clinics, and salons. They're already trusted. | Zoho, Petpooja, TallyPrime reseller networks |
| **Wedding Planners** | They work with caterers, decorators, mehendi artists, photographers — all SMBs who need leads | Instagram, WeddingWire, Shaadi.com vendor lists |
| **Commercial Real-Estate Agents** | They see new businesses opening before anyone else | MagicBricks, 99acres commercial listings, local property dealers |
| **Print & Signage Shops** | Every new shop gets a banner and a flex board before they open | Local industrial areas, Google Maps |
| **Business Loan DSAs** | They talk to businesses that need capital — which means they also need more customers | Bank DSA networks, LoanTap, Lendingkart partners |

**Target: 3–5 scouts from each category = ~20 total**

---

## Scout Outreach Messages

### Message to a CA (WhatsApp)

```
Hi [Name], I run a marketing service for small businesses — clinics, salons, 
restaurants — in [city]. We charge ₹14,999/month flat and handle everything: 
ads, lead tracking, weekly reports.

I know you work with a lot of business owners. If any of them mention wanting 
more customers and you pass on our name, we pay ₹2,249 for every one that 
signs up — one time, no strings.

Nothing to sell or explain on your end. Just: "there's a guy I know who runs 
ad campaigns for local businesses, want me to connect you?" That's it.

Interested? I'll send you a code you can pass along.
```

### Message to a Web Designer (WhatsApp / DM)

```
Hi [Name], saw your work — really clean stuff.

Quick question: when clients ask you how to get more traffic or customers 
after you build their site, what do you tell them?

I run a performance marketing service (Meta Ads + lead tracking, ₹14,999/month). 
If you'd want to refer your clients to us instead of leaving that question 
unanswered, we pay you ₹2,249 per client that signs up. You stay the "full 
solution" guy — we handle the ads side.

Want to set it up?
```

### Message to a POS Seller (In-person or WhatsApp)

```
Hey [Name], I work in the same space as you — we manage digital ads for the 
kind of shops you install billing software in: restaurants, salons, clinics.

Straight to it: if a shop owner you're dealing with wants more footfall or 
enquiries and you mention us, you make ₹2,249 if they sign. No paperwork, 
no targets. Just a referral code you pass along.

Worth 2 minutes to set up?
```

---

## What to Send Them After They Say Yes

1. Run `--register` to generate their code
2. Send them this WhatsApp message:

```
Done! Your referral code is: [CODE]

Anytime someone signs up using this code, I'll let you know and 
transfer your commission within the same week. You can refer as many 
businesses as you like — no limit.

If you ever want to see your tally, just ask me anytime.
```

---

## Monthly Scout Maintenance (10 minutes/month)

1. Run `--leaderboard` — see who's active, who's gone quiet
2. Run `--owed` — pay anyone with unpaid commissions (same week, bank transfer)
3. Message anyone who referred someone in the last 30 days:
   > *"Your ₹2,249 is on its way — thanks again. Got anyone else who could use this?"*
4. Drop a WhatsApp to scouts who haven't referred in 60+ days:
   > *"Hey [Name] — just checking in. Any of your clients asking about getting more customers lately? Happy to send you a Trojan Report for any specific one, free."*

---

## The Economics

At ₹14,999/month:
- Affiliate commission per signup: **₹2,249** (15%)
- Your net from that client (month 1): **₹12,750**
- Month 2 onwards (no commission): **₹14,999**
- Break-even on paying the commission: **immediately** — one client month covers it

20 active scouts, each referring 1 client per quarter = **~7 new clients/month**
at essentially zero extra effort from you.

---

*Track everything with `agent_28_referral_engine.py`. All data in `referral_db.json` — no third-party service, no monthly fee.*
