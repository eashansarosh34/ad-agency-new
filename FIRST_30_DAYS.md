# First 30 Days — Do Exactly This

> No improvising. No adding extra steps. No "let me also try..."
> The plan below is the plan. Deviate after day 30, not before.

---

## Your Lane (Decided)

**Vertical: Dental clinics**
**City: Hyderabad**

Why this isn't a guess:
- You already have benchmark CPL data in `category_intelligence.json` for dental/Hyderabad
- Dental has high LTV (a patient is worth ₹40,000–₹1,00,000+ over their lifetime)
- Hyderabad has 800+ independent dental clinics — you will never run out of prospects
- The before/after creative format is proven — no guessing on what to run
- WhatsApp lead forms are standard — easy to set up, high conversion rate

**Do not change vertical or city until day 31.**

---

## WEEK 1 — Setup + Observe
*Days 1–7. Goal: everything running, nothing live. Read what the system would do.*

### Day 1 (Today — Already Done)
- [x] GitHub repo created
- [x] All 8 secrets set (META tokens, Anthropic, Tavily, client name, WhatsApp)
- [x] All 7 workflows deployed to `.github/workflows/`
- [x] `ORCHESTRATOR_DRY_RUN=true` set as secret
- [x] Offer defined in `OFFER.md`
- [x] Referral system in `REFERRAL_PLAYBOOK.md`
- [x] Moat strategy in `MOAT.md`

### Day 2
- [ ] Check GitHub Actions — open each workflow run, read the logs
  - Did Poll Leads fire? What did it log?
  - Did Competitive Monitor run? What trends did it find?
  - Are there any errors? (Missing dependency, wrong token, etc.)
- [ ] Fix any errors found in logs before moving on
- [ ] Run `trojan_report.py --demo` locally to confirm it generates cleanly

### Day 3
- [ ] Find 10 dental clinics in Hyderabad on Google Maps / Instagram
  - Look for: decent reviews (3.5+ stars), active Instagram, no obvious digital ad presence
  - Save: business name, Instagram handle or website, phone/WhatsApp number
  - Store in a simple notes file or WhatsApp saved message — keep it simple
- [ ] Run Trojan Report on 3 of them:
  ```bash
  python3 trojan_report.py --business "Smile Care Dental" --niche "dental clinic" \
      --city "Hyderabad" --website "https://theirsite.com" --html
  ```
- [ ] Read each report. Does it sound like something a dentist would find useful?

### Day 4
- [ ] Pick the best report from Day 3 — the most specific and honest one
- [ ] Send it to that clinic. WhatsApp is fine. Paste the `.txt` output:
  > *"Hi, I took a quick look at [Clinic Name]'s digital presence in Hyderabad and put together a free honest diagnosis — no pitch, no catch. Might be useful."* [paste report]
- [ ] Do this for 2 more clinics. 3 reports sent total by end of Day 4.
- [ ] DO NOT mention pricing or services yet. Just send the report.

### Day 5
- [ ] Run Trojan Reports for 5 more dental clinics (total: 8 reports ready)
- [ ] Send reports to those 5 as well
- [ ] Check Actions logs again — are workflows still running? Any new errors?
- [ ] Register yourself as the first "client" in the referral system (test it works):
  ```bash
  python3 agent_28_referral_engine.py --register "Test Client" client_referral
  ```

### Day 6
- [ ] Check responses to Day 4 sends. Three possible outcomes:
  - **Positive / curious:** Reply with the closing script from `OFFER.md`. Word for word.
  - **No response:** Note it. Follow up in 5 days with one line: *"Any questions on the report?"*
  - **Not interested:** Move on. Don't follow up.
- [ ] Contact 2 potential scouts (CAs or web designers). Use the message templates in `REFERRAL_PLAYBOOK.md`
- [ ] Identify 10 more dental clinics for Week 2

### Day 7 (End of Week 1)
- [ ] Read all workflow logs from the past 7 days
- [ ] Write 5 bullet points answering:
  1. What would the system have done if it were live?
  2. Did the lead polling find anything? (Even DRY_RUN logs what it *would* have done)
  3. What did Competitive Monitor flag as a trend in dental/Hyderabad?
  4. Did the optimize agent want to change any ad parameters?
  5. Do you trust the system enough to run it live?
- [ ] Send 2 more Trojan Reports

---

## WEEK 2 — First Trojan Conversations
*Days 8–14. Goal: at least 1 reply that says "tell me more".*

### Day 8
- [ ] Send 5 more Trojan Reports (total: ~15 sent by now)
- [ ] Register 2 scouts in the referral system:
  ```bash
  python3 agent_28_referral_engine.py --register "Ramesh CA" affiliate
  python3 agent_28_referral_engine.py --register "Vikram Web" affiliate
  ```
- [ ] WhatsApp both scouts their referral code

### Days 9–11
- [ ] Send 10 more reports across these 3 days (3–4 per day)
- [ ] Follow up on all Day 4–5 sends that haven't replied: *"Any questions on the report?"*
- [ ] For any clinic that responds positively: use the closing script in `OFFER.md`. Don't improvise.
- [ ] If a clinic says yes: begin onboarding (see `OFFER.md` onboarding checklist)

### Days 12–14
- [ ] By Day 14, you should have sent 25–30 Trojan Reports total
- [ ] At least 1–2 conversations should be active
- [ ] Review the weekly report from the Actions logs (Monday run)
- [ ] Add your first intelligence data point even if you have no live client yet:
  ```python
  import agent_19_category_intelligence as intel
  intel.log_campaign_outcome("dental clinic", "client_DC_seed", {
      "cpl_achieved": 195,
      "best_creative_angle": "before/after teeth whitening",
      "audience_that_worked": "women 28-45 near clinic",
      "what_failed": "stock clinic photo, no human face",
      "city": "Hyderabad", "budget": 20000,
      "notes": "Benchmark from category research. Not a live client yet."
  })
  ```

---

## WEEK 3 — First Client or Close to It
*Days 15–21. Goal: sign client 1, or have a conversation that will close in week 4.*

- [ ] Continue sending 3–5 reports per day
- [ ] By Day 18: 40–45 total reports sent
- [ ] Statistically: at a 5–10% reply rate, you have 4–5 conversations active
- [ ] At a 20–30% close rate on conversations: 1 client is within reach
- [ ] When client 1 says yes:
  - Collect their `META_PAGE_ID` and `META_AD_ACCOUNT_ID`
  - Update GitHub Secrets with their values
  - Set `CLIENT_NAME` to their business name
  - Flip `ORCHESTRATOR_DRY_RUN` to `false`
  - Confirm first campaign launches within 24 hours
  - WhatsApp them a confirmation: *"We're live. You'll get your first weekly update next Monday."*

---

## WEEK 4 — Operationalise
*Days 22–30. Goal: client 1 running smoothly, client 2 in the pipeline.*

- [ ] Read Week 1 report for Client 1 — what's the actual CPL? What's working?
- [ ] Log the first real data point to `category_intelligence.json`
- [ ] WhatsApp client on Monday with their week-1 numbers (plain English)
- [ ] Continue sending Trojan Reports to new prospects (never stop this)
- [ ] Recruit 3 more scouts
- [ ] Begin a second vertical OR a second city — only after client 1 is stable
- [ ] Set a reminder for Day 30: flip `ORCHESTRATOR_DRY_RUN` to `false` if not already done

---

## The Numbers That Tell You If You're On Track

| Day | Trojan Reports Sent | Scout Conversations | Active Clients |
|---|---|---|---|
| 7 | 10+ | 2 | 0 (DRY_RUN) |
| 14 | 25–30 | 4–6 | 0–1 |
| 21 | 40–45 | 6–8 | 1 |
| 30 | 50–60 | 8–10 | 1–2 |

If you're below these numbers by Day 14, the only fix is sending more reports. Nothing else.

---

## What NOT to Do in the First 30 Days

- Do not add a second vertical before getting client 1
- Do not build a website or logo (nobody asked for it)
- Do not set up a CRM or project management tool
- Do not post on LinkedIn or Instagram about your agency
- Do not offer a free trial or reduced rate (it attracts the wrong clients and devalues the work)
- Do not customise the offer for anyone (fixed price, fixed scope)
- Do not spend money on ads for your own agency
- Do not read marketing blogs or courses about agency building

**The only two things that move the needle in the first 30 days: sending Trojan Reports and having direct conversations.**

---

## The Mental Model

You are not building an agency. You are testing a hypothesis:

> *"If I give a specific, useful, free diagnosis to enough dental clinic owners in Hyderabad, some of them will pay ₹14,999/month to have the problems fixed."*

The hypothesis is tested by the number of reports sent. 10 reports is not enough data. 50 reports is real data. Everything else is noise until you have 50 data points.

Send the reports. Read the logs. Have the conversations. In that order. Every day.

---

*Start date: July 2026. Review date: August 2026.*
*Update this file with actual numbers as you go.*
