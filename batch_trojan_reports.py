"""
batch_trojan_reports.py — Run Trojan Reports for all 10 Hyderabad dental clinics
================================================================================
Called automatically by run_batch_reports.sh

For each clinic in the CLINICS list below, this script runs trojan_report.py
and saves the output to reports_to_send/

DRY_RUN aware: if ORCHESTRATOR_DRY_RUN=true, prints commands instead of running.
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# ============================================================
# CLINIC LIST — 10 Hyderabad Dental Targets (Week 1 Batch)
# ============================================================
CLINICS = [
    {
        "name": "Dentist N Dontist",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "https://dentistndontist.com",
        "area": "Jubilee Hills",
        "slug": "DentistNDontist",
    },
    {
        "name": "Dollar Smiles Dental Hospital",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "https://dollarsmiles.com",
        "area": "Gachibowli",
        "slug": "DollarSmiles",
    },
    {
        "name": "My Smile Dental",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "https://mysmiledental.co.in",
        "area": "Nallagandla",
        "slug": "MySmileDental",
    },
    {
        "name": "Nihaans Dental Clinic",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "",
        "area": "Gachibowli",
        "slug": "NihaansDental",
    },
    {
        "name": "Toothway Dental Clinic",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "",
        "area": "Kondapur",
        "slug": "ToothwayDental",
    },
    {
        "name": "Roots Dental Care",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "",
        "area": "Miyapur",
        "slug": "RootsDentalCare",
    },
    {
        "name": "Capital Dental Clinic",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "",
        "area": "Madhapur",
        "slug": "CapitalDental",
    },
    {
        "name": "Smylexl Dental Studio",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "",
        "area": "Kukatpally",
        "slug": "SmylexlDental",
    },
    {
        "name": "GA Dental Clinic",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "",
        "area": "Banjara Hills",
        "slug": "GADentalClinic",
    },
    {
        "name": "Just Smile Dental Clinic",
        "niche": "dental clinic",
        "city": "Hyderabad",
        "website": "",
        "area": "Ameerpet",
        "slug": "JustSmileDental",
    },
]

# ============================================================
# CONFIG
# ============================================================
DRY_RUN = os.environ.get("ORCHESTRATOR_DRY_RUN", "true").lower() == "true"
OUTPUT_DIR = Path("reports_to_send")
OUTPUT_DIR.mkdir(exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d")


def run_report(clinic: dict) -> bool:
    """Run trojan_report.py for a single clinic. Returns True on success."""
    slug = clinic["slug"]
    output_txt = OUTPUT_DIR / f"trojan_report_{slug}.txt"
    output_html = OUTPUT_DIR / f"trojan_report_{slug}.html"

    cmd = [
        sys.executable, "trojan_report.py",
        "--business", clinic["name"],
        "--niche", clinic["niche"],
        "--city", clinic["city"],
        "--html",
    ]
    if clinic.get("website"):
        cmd += ["--website", clinic["website"]]

    print(f"\n[{slug}] Generating Trojan Report...")
    if DRY_RUN:
        print(f"  DRY_RUN=true — would run: {' '.join(cmd)}")
        print(f"  Output would go to: {output_html}")
        # Write a placeholder so the tracker can see a file was "generated"
        output_txt.write_text(
            f"[DRY RUN] Trojan Report placeholder for {clinic['name']} ({clinic['area']}, {clinic['city']})\n"
            f"Generated: {TIMESTAMP}\n"
            f"Command: {' '.join(cmd)}\n"
        )
        output_html.write_text(
            f"<html><body>"
            f"<h1>[DRY RUN] {clinic['name']}</h1>"
            f"<p>Area: {clinic['area']}, {clinic['city']}</p>"
            f"<p>This is a placeholder report generated in DRY_RUN mode.</p>"
            f"<p>Set ORCHESTRATOR_DRY_RUN=false and re-run to generate a real report.</p>"
            f"</body></html>"
        )
        return True
    else:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                output_txt.write_text(result.stdout)
                print(f"  SUCCESS — saved to {output_txt}")
                return True
            else:
                print(f"  ERROR — {result.stderr[:300]}")
                return False
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT — skipping {slug}")
            return False


def main():
    print("\n" + "=" * 60)
    print(" Apna Marketer — Batch Trojan Report Generator")
    print(" Week 1 | Hyderabad Dental Clinics")
    print(f" Mode: {'DRY RUN (safe)' if DRY_RUN else 'LIVE — real API calls'}")
    print("=" * 60)

    results = {"success": [], "failed": []}

    for clinic in CLINICS:
        ok = run_report(clinic)
        if ok:
            results["success"].append(clinic["name"])
        else:
            results["failed"].append(clinic["name"])

    print("\n" + "=" * 60)
    print(f" Done! {len(results['success'])}/10 reports generated.")
    print(f" Saved to: {OUTPUT_DIR.resolve()}")
    if DRY_RUN:
        print(" NOTE: DRY_RUN mode — all outputs are placeholders.")
        print(" To generate real reports: set ORCHESTRATOR_DRY_RUN=false")
    if results["failed"]:
        print(f" Failed: {', '.join(results['failed'])}")
    print("=" * 60)
    print("\nNext steps:")
    print(" 1. Open reports_to_send/ and review each .html file")
    print(" 2. Send good ones via WhatsApp / email (you do this manually)")
    print(" 3. Run: python3 outreach_tracker.py  (to log who you contacted)")
    print(" 4. Update OUTREACH_LOG.md with date sent + response")


if __name__ == "__main__":
    main()
