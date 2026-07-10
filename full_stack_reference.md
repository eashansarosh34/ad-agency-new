# AI Ad Agency — Full Stack Reference (Ground Truth)

This is the one document to check when "what's actually real?" comes up. Every status
claim below reflects what was actually run and observed — not what the code is *supposed*
to do.

---

## Status legend
- ✅ **Live-verified** — ran against a real account/real data, output observed
- 🧪 **Mock-verified** — ran against fake data standing in for the real API, logic confirmed correct
- ⬜ **Built, unverified** — code exists, has never been run against anything real or mock

---

## Agent catalog

| # | Name | File(s) | Status | What it needs to go live |
|---|---|---|---|---|
| 01 | Creative & Copy | `creative_copy_agent.html` | ✅ Live-verified | Local proxy (`run_local_tools.py`) + real Anthropic key |
| 02 | Media Optimizer (Meta) | `agent_02_media_optimizer.py` | ✅ Live-verified | Meta access token, ad account ID |
| 03 | Reporting | `agent_03_reporting.py` | ✅ Live-verified | Meta token + `CLIENT_NAME` env var |
| 04 | WhatsApp Qualifier (webhook) | `agent_04_whatsapp.py` | 🧪 Mock-verified only | Real WhatsApp Business number + approved template — parked in favor of 04b |
| 04b | Lead Poller (webhook alternative) | `agent_04b_lead_poller.py` | ✅ Live-verified | Page access token w/ `leads_retrieval` + `pages_manage_ads`, Page ID |
| 05 | Trend Scout | `agent_05_trend_scout.py` | 🧪 Mock-verified only | Tavily API key + Anthropic key |
| 06 | Local Visibility | `agent_06_local_visibility.html` | ✅ Live-verified | Same proxy as Agent 01 |
| 07 | Google Ads Optimizer | `agent_07_google_ads_optimizer.py` | 🧪 Mock-verified only | Google Ads Developer Token (pending approval) + OAuth |
| 08 | SMS Reminder | `agent_08_sms_reminder.py` | 🧪 Mock-verified (window/dedup logic only) | DLT registration (pending) + MSG91 account |
| 09 | Email Nurture + Newsletter | `agent_09_email_nurture.py` | 🧪 Mock-verified (real payload tested against mock Brevo) | Brevo account + sender domain auth |
| 10 | Content & Social Studio | `agent_10_content_social_studio.html` | ✅ Live-verified | Same proxy as Agent 01 |
| 11 | Lead Intelligence / Voice-of-Customer | `agent_11_lead_intelligence.py` | 🧪 Mock-verified (fallback path only) | Real lead reply data to actually be useful — currently nothing to analyze since WhatsApp send isn't live yet |
| 12 | Compliance Gate | `agent_12_compliance_gate.py` | ✅ Live-verified (standalone) + wired into 01/06/10 | Nothing extra — works today, keyword fallback always active |
| 13 | Cross-Channel Arbitrage | `agent_13_cross_channel_arbitrage.py` | 🧪 Mock-verified only | Everything Agent 02 AND Agent 07 each need, simultaneously |
| 14 | Competitive Monitor | `agent_14_competitive_monitor.py` + `run_competitive_monitor.py` | 🧪 Mock-verified only | Tavily key + Anthropic key |

---

## Infrastructure

| File | Purpose | Status |
|---|---|---|
| `run_local_tools.py` | Local proxy — lets Agents 01/06/10 call Claude + the compliance gate from a browser | ✅ Live-verified |
| `run_scheduler.py` | Runs poll_leads (5min), optimize (6h), report (weekly), arbitrage (12h), competitive_monitor (daily) automatically | ✅ Live-verified (poll_leads + optimize + report cycle observed running unattended on real SunCap data) |
| `mock_meta_server.py`, `mock_google_ads_server.py`, `mock_msg91_server.py`, `mock_brevo_server.py`, `mock_tavily_server.py`, `mock_lead_poll_server.py` | Testing infrastructure only — never deploy these, they exist purely so agents could be verified without real credentials | N/A |

---

## Supporting documents
- `client_agreement_pricing.docx` — contract template (template only, have a lawyer review before real use)
- `client_onboarding_checklist.md` — account access steps for new clients
- `full_service_agency_roadmap.md` — the 8-channel/11-item roadmap and build sequence
- `local_seo_learning_guide.md` — the actual GMB/Local SEO skill content (not automatable)

---

## The honest summary

**Genuinely proven on a real account today:** the full funnel from ad → real lead capture
→ optimizer logic → report generation, running unattended via the scheduler, on SunCap's
real campaign. That's the actual achievement of this build.

**Built and logically sound, never touched real data:** Agents 04 (webhook path), 05, 07,
08, 09, 11, 13, 14. Every one of these has been tested against realistic fake data and the
logic is sound — but "the logic is correct" and "this works on a real account" are
different claims, and only the first one is true for this group right now.

**Structurally can't be finished by more code, ever:** SEO (needs a real audited site), CRO
(needs real traffic), full ORM monitoring (needs paid third-party tools), influencer
outreach (relationship work).

**The one thing every untested agent in the second group needs before being trusted:**
the same thing that made Agents 02/03/04b trustworthy — running them in `DRY_RUN=True`
against the real account for a few real cycles, reading what they *would* do, and only
then flipping the switch.
