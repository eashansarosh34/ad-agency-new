#!/bin/bash
# ============================================================
# BATCH TROJAN REPORT RUNNER — 10 Hyderabad Dental Clinics
# Run this from your local agent files folder
# ============================================================
#
# BEFORE RUNNING:
# 1. Open Terminal in your agent files folder
# 2. Set your API keys (one-time per session):
#    export ANTHROPIC_API_KEY=your-anthropic-key
#    export TAVILY_API_KEY=your-tavily-key
# 3. Run this script:
#    bash run_batch_reports.sh
#
# Takes ~2-3 minutes per report. All 10 = ~25 minutes.
# Reports saved in the same folder as this script.
# ============================================================

echo "================================================"
echo " TROJAN REPORT BATCH — 10 Hyderabad Dental Clinics"
echo " Start time: $(date)"
echo "================================================"
echo ""

# Clinic 1 — Dentist N Dontist, Jubilee Hills
echo "[1/10] Running: Dentist N Dontist, Jubilee Hills..."
python3 trojan_report.py \
  --business "Dentist N Dontist" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --website "https://dentistndontist.com" \
  --html
echo "  DONE. Check trojan_report_DentistNDontist.txt / .html"
echo ""

# Clinic 2 — Dollar Smiles Dental Hospital, Gachibowli
echo "[2/10] Running: Dollar Smiles Dental Hospital, Gachibowli..."
python3 trojan_report.py \
  --business "Dollar Smiles Dental Hospital" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --website "https://dollarsmiles.com" \
  --html
echo "  DONE. Check trojan_report_DollarSmiles.txt / .html"
echo ""

# Clinic 3 — My Smile Dental, Nallagandla
echo "[3/10] Running: My Smile Dental, Nallagandla..."
python3 trojan_report.py \
  --business "My Smile Dental" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --website "https://mysmiledental.co.in" \
  --html
echo "  DONE. Check trojan_report_MySmileDental.txt / .html"
echo ""

# Clinic 4 — Nihaans Dental Clinic, Gachibowli (Instagram only)
echo "[4/10] Running: Nihaans Dental Clinic, Gachibowli..."
python3 trojan_report.py \
  --business "Nihaans Dental Clinic" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --html
echo "  DONE. Check trojan_report_NihaansDental.txt / .html"
echo ""

# Clinic 5 — Toothway Dental Clinic, Gachibowli (Instagram only)
echo "[5/10] Running: Toothway Dental Clinic, Gachibowli..."
python3 trojan_report.py \
  --business "Toothway Dental Clinic" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --html
echo "  DONE. Check trojan_report_ToothwayDental.txt / .html"
echo ""

# Clinic 6 — Roots Dental Care, Jubilee Hills
echo "[6/10] Running: Roots Dental Care, Jubilee Hills..."
python3 trojan_report.py \
  --business "Roots Dental Care" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --website "https://www.rootsdentalcare.co.in" \
  --html
echo "  DONE. Check trojan_report_RootsDental.txt / .html"
echo ""

# Clinic 7 — Capital Dental Care, Kondapur (no website)
echo "[7/10] Running: Capital Dental Care, Kondapur..."
python3 trojan_report.py \
  --business "Capital Dental Care" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --html
echo "  DONE. Check trojan_report_CapitalDental.txt / .html"
echo ""

# Clinic 8 — Smylexl Dental Clinic, Hyderabad (no website)
echo "[8/10] Running: Smylexl Dental Clinic..."
python3 trojan_report.py \
  --business "Smylexl Dental Clinic" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --html
echo "  DONE. Check trojan_report_SmylexlDental.txt / .html"
echo ""

# Clinic 9 — GA Dental Clinic, Malakpet (no website)
echo "[9/10] Running: GA Dental Clinic, Malakpet..."
python3 trojan_report.py \
  --business "GA Dental Clinic" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --html
echo "  DONE. Check trojan_report_GADental.txt / .html"
echo ""

# Clinic 10 — Just Smile Dental Care, Miyapur (no website)
echo "[10/10] Running: Just Smile Dental Care, Miyapur..."
python3 trojan_report.py \
  --business "Just Smile Dental Care" \
  --niche "dental clinic" \
  --city "Hyderabad" \
  --html
echo "  DONE. Check trojan_report_JustSmile.txt / .html"
echo ""

echo "================================================"
echo " ALL 10 REPORTS COMPLETE"
echo " End time: $(date)"
echo "================================================"
echo ""
echo "NEXT STEPS:"
echo "1. Open each .html file in your browser (double-click it)"
echo "2. Read the report — does it sound useful to a dentist?"
echo "3. Open OUTREACH_LOG.md and log which ones you send"
echo "4. WhatsApp message template is in CLINIC_TARGETS.md"
echo ""
echo "Send message:"
echo '  "Hi, I work in digital marketing in Hyderabad and took a quick'
echo '  look at how [Clinic Name] is showing up online. Put together a'
echo '  few honest observations — free, no catch. Sharing in case it is'
echo '  useful to you either way." [paste .txt report or attach .html PDF]'
echo ""
