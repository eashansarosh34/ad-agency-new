# Clinic Targets — Week 1 Batch (10 Dental Clinics, Hyderabad)

> These are your 10 targets for Days 3–5. Run the trojan report for each one locally.
> GitHub is NOT involved. Open Terminal in your agent files folder and run these commands.
> The PDF guide (dental_report_guide.pdf) has full step-by-step instructions.

**Before running ANY command, set your keys once in Terminal:**
```bash
export ANTHROPIC_API_KEY=your-anthropic-key
export TAVILY_API_KEY=your-tavily-key
```
_(Windows: use `set` instead of `export`)_

---

## Clinic 1 — Dentist N Dontist, Jubilee Hills

- **Location:** Road No. 36, Jubilee Hills, Hyderabad
- **Website:** https://dentistndontist.com
- **Why selected:** Single-doctor independent clinic, 253 reviews on Practo, no visible paid ads, active Instagram
- **Size:** Small (1 doctor)

```bash
python3 trojan_report.py --business "Dentist N Dontist" --niche "dental clinic" \
  --city "Hyderabad" --website "https://dentistndontist.com" --html
```

**Output files:**
- `trojan_report_DentistNDontist.txt`
- `trojan_report_DentistNDontist.html`

---

## Clinic 2 — Dollar Smiles Dental Hospital, Gachibowli

- **Location:** Gachibowli, Hyderabad
- **Website:** https://dollarsmiles.com
- **Why selected:** 2-branch independent hospital, actively markets 3D scanning, no chain backing
- **Size:** Small-medium (2 branches)

```bash
python3 trojan_report.py --business "Dollar Smiles Dental Hospital" --niche "dental clinic" \
  --city "Hyderabad" --website "https://dollarsmiles.com" --html
```

**Output files:**
- `trojan_report_DollarSmiles.txt`
- `trojan_report_DollarSmiles.html`

---

## Clinic 3 — My Smile Dental, Nallagandla

- **Location:** Nallagandla, Serilingampally, Hyderabad
- **Website:** https://mysmiledental.co.in
- **Why selected:** Single-location independent, growing residential area, website exists but thin on content/ads
- **Size:** Small

```bash
python3 trojan_report.py --business "My Smile Dental" --niche "dental clinic" \
  --city "Hyderabad" --website "https://mysmiledental.co.in" --html
```

**Output files:**
- `trojan_report_MySmileDental.txt`
- `trojan_report_MySmileDental.html`

---

## Clinic 4 — Nihaans Dental Clinic, Gachibowli

- **Location:** Gachibowli / Bandlaguda, Hyderabad
- **Instagram:** @nihaansdentalclinic
- **WhatsApp:** +91 99891 99412
- **Why selected:** Instagram-only presence, no website, WhatsApp booking — perfect Trojan target
- **Size:** Small

```bash
python3 trojan_report.py --business "Nihaans Dental Clinic" --niche "dental clinic" \
  --city "Hyderabad" --html
```
_(No --website because they are Instagram-only)_

**Output files:**
- `trojan_report_NihaansDental.txt`
- `trojan_report_NihaansDental.html`

---

## Clinic 5 — Toothway Dental Clinic, Gachibowli

- **Location:** Gachibowli, Hyderabad
- **WhatsApp:** 7416722020
- **Instagram:** Active (posts before/after cases)
- **Why selected:** Instagram-active, WhatsApp contact, no visible paid ads, active in 2026
- **Size:** Small

```bash
python3 trojan_report.py --business "Toothway Dental Clinic" --niche "dental clinic" \
  --city "Hyderabad" --html
```

**Output files:**
- `trojan_report_ToothwayDental.txt`
- `trojan_report_ToothwayDental.html`

---

## Clinic 6 — Roots Dental Care, Jubilee Hills

- **Location:** Jubilee Hills, Hyderabad
- **Website:** https://www.rootsdentalcare.co.in
- **Phone:** 9640252525
- **Why selected:** Modern independent clinic, growing reputation, limited digital marketing visible
- **Size:** Small-medium

```bash
python3 trojan_report.py --business "Roots Dental Care" --niche "dental clinic" \
  --city "Hyderabad" --website "https://www.rootsdentalcare.co.in" --html
```

**Output files:**
- `trojan_report_RootsDental.txt`
- `trojan_report_RootsDental.html`

---

## Clinic 7 — Capital Dental Care, Kondapur

- **Location:** Kondapur, Hyderabad (near Chirec School, above SBI Bank)
- **Website:** None found — send via WhatsApp/call
- **Why selected:** Kondapur is high-density residential + IT crowd, clinic has no web presence
- **Size:** Small

```bash
python3 trojan_report.py --business "Capital Dental Care" --niche "dental clinic" \
  --city "Hyderabad" --html
```

**Output files:**
- `trojan_report_CapitalDental.txt`
- `trojan_report_CapitalDental.html`

---

## Clinic 8 — Smylexl Dental Clinic, Hyderabad

- **Location:** Hyderabad (Justdial listed)
- **Why selected:** Listed as "affordable prices", independent, not a chain
- **Size:** Small

```bash
python3 trojan_report.py --business "Smylexl Dental Clinic" --niche "dental clinic" \
  --city "Hyderabad" --html
```

**Output files:**
- `trojan_report_SmylexlDental.txt`
- `trojan_report_SmylexlDental.html`

---

## Clinic 9 — GA Dental Clinic, Malakpet

- **Location:** Old Malakpet, Hyderabad
- **Rating:** 4.7 / 427 reviews (Justdial)
- **Why selected:** High volume of reviews = active patient base, older part of city with less digital competition
- **Size:** Small-medium

```bash
python3 trojan_report.py --business "GA Dental Clinic" --niche "dental clinic" \
  --city "Hyderabad" --html
```

**Output files:**
- `trojan_report_GADental.txt`
- `trojan_report_GADental.html`

---

## Clinic 10 — Just Smile Dental Care, Miyapur

- **Location:** Madhav Nagar Colony, Miyapur, Hyderabad
- **Why selected:** 2-doctor independent, Practo listed, residential area with growing population
- **Size:** Small

```bash
python3 trojan_report.py --business "Just Smile Dental Care" --niche "dental clinic" \
  --city "Hyderabad" --html
```

**Output files:**
- `trojan_report_JustSmile.txt`
- `trojan_report_JustSmile.html`

---

## Why These 10 Were Selected

| # | Clinic | Area | Has Website | Has Instagram | Chain? | Why Good Target |
|---|---|---|---|---|---|---|
| 1 | Dentist N Dontist | Jubilee Hills | YES | YES | NO | Active, 253 reviews, no paid ads |
| 2 | Dollar Smiles | Gachibowli | YES | YES | NO | 2 branches, IT crowd area |
| 3 | My Smile Dental | Nallagandla | YES | YES | NO | Growing suburb, thin digital presence |
| 4 | Nihaans Dental | Gachibowli | NO | YES | NO | WhatsApp-only = easy to reach directly |
| 5 | Toothway Dental | Gachibowli | NO | YES | NO | Before/after content, WhatsApp contact |
| 6 | Roots Dental Care | Jubilee Hills | YES | YES | NO | Good reputation, limited ads |
| 7 | Capital Dental Care | Kondapur | NO | NO | NO | IT hub, zero digital presence |
| 8 | Smylexl Dental | Hyderabad | NO | NO | NO | Affordable positioning, no ads |
| 9 | GA Dental Clinic | Malakpet | NO | NO | NO | High review volume, underdigitized |
| 10 | Just Smile Dental | Miyapur | NO | NO | NO | 2-doctor independent, residential |

**All 10 are:**
- Independent (no Apollo / Partha chain)
- Small to medium (1-2 doctors or 1-2 branches max)
- No visible paid Meta/Google ad campaigns
- Reachable via WhatsApp or email

---

## Send Order (Priority)

Do clinics with websites FIRST (reports will be richer with Tavily web intel):
1. Dentist N Dontist
2. Dollar Smiles
3. My Smile Dental
4. Roots Dental Care
5. Nihaans Dental Clinic
6. Toothway Dental Clinic
7. Capital Dental Care
8. GA Dental Clinic
9. Just Smile Dental Care
10. Smylexl Dental Clinic

---

## After Running All 10

Update `OUTREACH_LOG.md` with:
- Which reports you sent
- Via WhatsApp / email / Instagram DM
- Date sent
- Response (if any)

The goal: **10 reports run, at least 8 sent, by end of Day 5.**
