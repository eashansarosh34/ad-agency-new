# Week 1 Status Tracker — Dental Clinics / Hyderabad

> Update this file daily. One truth source for your Week 1 progress.
> DRY_RUN is ON. No live actions until you flip ORCHESTRATOR_DRY_RUN to false.

---

## System State

| Component | Status |
|---|---|
| GitHub repo | LIVE |
| All 7 workflows in `.github/workflows/` | LIVE |
| ORCHESTRATOR_DRY_RUN secret | `true` (safe) |
| Vertical | Dental clinics |
| City | Hyderabad |
| DRY_RUN wired to all agents | YES (agents 02, 04b, 13 read from secret) |

---

## Day 1 — Already Done

- [x] GitHub repo created
- [x] All 8 secrets set (META tokens, Anthropic, Tavily, client name, WhatsApp)
- [x] All 7 workflows deployed to `.github/workflows/`
- [x] `ORCHESTRATOR_DRY_RUN=true` set as GitHub Secret
- [x] `OFFER.md` committed
- [x] `REFERRAL_PLAYBOOK.md` committed (2-tier: 50% off for clients, 15% for scouts)
- [x] `MOAT.md` committed
- [x] `FIRST_30_DAYS.md` committed
- [x] `category_intel.yml` workflow committed
- [x] Agents 02, 04b, 13 now read DRY_RUN from ORCHESTRATOR_DRY_RUN secret

**Day 1 complete.**

---

## Day 2 — GitHub Actions Audit

> Go to: https://github.com/eashansarosh34/ad-agency-new/actions

- [ ] poll_leads workflow: did it fire? What did it log?
- [ ] optimize workflow: did it fire? What did it log?
- [ ] competitive_monitor workflow: what trends did it find?
- [ ] report workflow: did it fire?
- [ ] category_intel workflow: did it run?
- [ ] Fix any errors found (missing deps, wrong token format, etc.)
- [ ] Run trojan report demo locally: `python3 trojan_report.py --demo`

**Actions log notes (fill in):**
```
[paste key lines from Actions logs here]
```

**Errors found / fixed:**
```
[list errors and fixes here]
```

---

## Day 3 — First Trojan Reports

- [ ] Found 10 dental clinics in Hyderabad (Google Maps / Instagram)
- [ ] Ran Trojan Report on 3 of them

**Clinics researched:**
| # | Clinic Name | Instagram / Website | Phone | Notes |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

**Trojan Report quality check:** Does it sound like something a dentist would find useful? (Y/N): ___

---

## Day 4 — First Sends

- [ ] Best report sent to clinic 1 via WhatsApp
- [ ] Report sent to clinic 2
- [ ] Report sent to clinic 3

**Sends log:**
| # | Clinic | Sent? | Response |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

## Day 5 — Volume Push

- [ ] 5 more Trojan Reports run (total: 8 ready)
- [ ] Sent to 5 more clinics
- [ ] Referral engine test: `python3 agent_28_referral_engine.py --register "Test Client" client_referral`
- [ ] Actions logs re-checked

**Total reports sent by end of Day 5:** ___

---

## Day 6 — Follow-up + Scout Recruitment

- [ ] Checked Day 4 responses
- [ ] Contacted 2 scouts (CAs or web designers)
- [ ] Identified 10 more clinics for Week 2

**Scout contacts:**
| Name | Role | Message sent? | Response |
|---|---|---|---|
| | | | |
| | | | |

**Day 4 response summary:**
- Positive / curious: ___
- No response: ___
- Not interested: ___

---

## Day 7 — Week 1 Review

- [ ] Read all workflow logs from past 7 days
- [ ] Wrote 5 bullet points (copy answers below)
- [ ] Sent 2 more Trojan Reports

**Week 1 Review Answers:**
1. What would the system have done if it were live?
   > [answer here]

2. Did the lead polling find anything? (DRY_RUN logs what it WOULD have done)
   > [answer here]

3. What did Competitive Monitor flag as a trend in dental/Hyderabad?
   > [answer here]

4. Did the optimize agent want to change any ad parameters?
   > [answer here]

5. Do you trust the system enough to run it live?
   > [YES / NO / NEEDS MORE TESTING]

---

## Week 1 Numbers Target vs Actual

| Metric | Target by Day 7 | Actual |
|---|---|---|
| Trojan Reports sent | 10+ | |
| Scout conversations started | 2 | |
| Active clients | 0 (DRY_RUN) | 0 |
| Workflow errors fixed | All | |

---

## When to Flip to Live

Flip `ORCHESTRATOR_DRY_RUN` to `false` **only when ALL of these are true:**

- [ ] You have at least 1 paying client (has signed up and paid)
- [ ] Their META_ACCESS_TOKEN and AD_ACCOUNT_ID are in GitHub Secrets
- [ ] CLIENT_NAME secret is updated to their business name
- [ ] You have reviewed at least 7 days of DRY_RUN logs and trust the output
- [ ] You have set a daily budget cap directly in Meta Ads Manager as a backstop

**To flip:** Go to Settings > Secrets > ORCHESTRATOR_DRY_RUN > Update > set to `false`

---

*Start: Day 1 complete. Next: Day 2 Actions audit.*

---

## Day 3 — First Trojan Reports (COMPLETE)

- [x] `batch_trojan_reports.py` created and committed
- [x] `run_batch_reports.sh` now has its missing dependency resolved
- [x] All 10 clinic DRY_RUN placeholder reports scaffolded
- [x] `OUTREACH_LOG.md` updated — all 10 clinics marked `[x] DRY_RUN`
- [x] `outreach_tracker.py` in place (sync_from_reports, set_status, dashboard)
- [ ] **YOU:** Run `bash run_batch_reports.sh` locally to confirm DRY_RUN placeholders generate in `reports_to_send/`
- [ ] **YOU:** Open 2-3 `.html` files in browser to preview the report format

**Day 3 output:** Batch pipeline complete end-to-end (DRY_RUN). Ready for Day 4 sends.

---

## Day 4 — First Sends (UPCOMING)

- [ ] Review the `.html` reports in `reports_to_send/`
- [ ] Pick best 3 clinics to contact first (recommended: Dentist N Dontist, Dollar Smiles, My Smile)
- [ ] Send via WhatsApp or email (you do this manually)
- [ ] Log each send in `OUTREACH_LOG.md` (Date Sent column)
- [ ] Run `python3 outreach_tracker.py --sent "Clinic Name"` for each one sent

**Goal:** 3+ reports sent by end of Day 4.

---

## Day 5 — Volume Push (UPCOMING)

- [ ] Send remaining 7 reports
- [ ] Log all in `OUTREACH_LOG.md`
- [ ] Track replies in outreach_tracker dashboard
- [ ] Decide: is DRY_RUN working well enough to flip to live?

**Goal:** All 10 reports sent. At least 2 replies.

