"""
Seed demo Parquet with synthetic PPP records matching our sample CSV.
Creates varied match quality for a realistic demo:
- ~60% High confidence → "Worth a credit"
- ~25% Probable → "Verify first"
- ~10% with franchise flags
- ~5% no match (won't seed those) → "Skip"
"""
import csv
import random
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from groundtruth.normalize import normalize_name

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = PROJECT_ROOT / "data" / "samples" / "saasquatch_export_sample.csv"
DEMO_DIR = PROJECT_ROOT / "data" / "demo"

REVENUE_PARSE = {
    "$2.5M": 2500000, "$1.8M": 1800000, "$4.2M": 4200000, "$3.1M": 3100000,
    "$900K": 900000, "$1.2M": 1200000, "$2.8M": 2800000, "$1.5M": 1500000,
    "$3.5M": 3500000, "$2.0M": 2000000, "$750K": 750000, "$4.5M": 4500000,
    "$3.8M": 3800000, "$8.2M": 8200000, "$500K": 500000, "$1.1M": 1100000,
    "$12M": 12000000, "$6.5M": 6500000, "$15M": 15000000, "$2.2M": 2200000,
    "$5.0M": 5000000, "$2.9M": 2900000, "$1.7M": 1700000, "$1.9M": 1900000,
    "$1.4M": 1400000, "$800K": 800000, "$600K": 600000, "$3.4M": 3400000,
    "$2.1M": 2100000, "$1.6M": 1600000, "$1.3M": 1300000, "$5.8M": 5800000,
    "$7.5M": 7500000, "$3.0M": 3000000, "$9.5M": 9500000, "$700K": 700000,
    "$4.0M": 4000000, "$1.0M": 1000000, "$2.4M": 2400000, "$6.0M": 6000000,
    "$2.6M": 2600000, "$2.3M": 2300000, "$8.0M": 8000000, "$350K": 350000,
    "$5.5M": 5500000, "$2.7M": 2700000, "$400K": 400000, "$3.2M": 3200000,
    "$7.0M": 7000000, "$8.5M": 8500000, "$450K": 450000,
    "$9.0M": 9000000, "$950K": 950000, "$9.5M": 9500000,
}

NAICS_MAP = {
    "Heating and Air Conditioning": 238220, "HVAC": 238220,
    "Plumbing": 238220, "Dental Practice": 621210,
    "Roofing Contractor": 238160, "Landscaping Services": 561730,
    "Automotive Repair": 811111, "Electrical Contractor": 238210,
    "Machine Shop": 332710, "Moving Company": 484210,
    "Accounting Services": 541211, "Pest Control": 561710,
    "Waste Collection": 562111, "Trucking": 484110,
    "Janitorial Services": 561720, "Physical Therapy": 621340,
    "Agriculture": 111000, "Metal Fabrication": 332710,
    "Hotel Management": 721110, "IT Services": 541512,
    "Concrete Contractor": 238110, "Boat Repair": 811490,
    "Veterinary Services": 541940, "Welding Services": 332710,
    "Tree Trimming": 561730, "General Contractor": 236220,
    "Commercial Printing": 323111, "Insurance": 524210,
    "Heating & Air": 238220, "Medical Practice": 621111,
    "Boat Dealer": 441222, "Chiropractic": 621310,
    "Farm Equipment": 423820, "Fencing Contractor": 238990,
    "Pool Services": 561790, "Building Materials": 444190,
    "Painting Contractor": 238320, "Catering Services": 722320,
    "Sheet Metal Work": 238170, "Retail - Sporting Goods": 451110,
    "Fire Protection": 238990, "Food Manufacturing": 311000,
    "Interior Design": 541410, "Tire Dealer": 441320,
    "Staffing Services": 561320, "Auto Body Repair": 811121,
    "Charter Fishing": 487210, "Security Guard Services": 561612,
    "Office Supply Store": 453210, "Art Dealer": 453920,
    "Farm Supply Store": 444240, "Nursery & Garden Center": 444220,
    "Urgent Care Clinic": 621493, "Property Management": 531311,
    "Wholesale Produce": 424480, "Veterinary Practice": 541940,
    "Auto Glass Repair": 811122, "Flooring Contractor": 238330,
    "Oil Well Services": 213112, "Pool Construction": 238990,
    "Self Storage": 531130, "Tree Service": 561730,
    "Financial Advisory": 523930, "Equine Services": 115210,
    "Seafood Processing": 311710, "Customs Broker": 488510,
    "Assisted Living": 623311, "Lumber & Building Materials": 444190,
    "Commercial Cleaning": 561720, "Electrical": 238210,
    "Excavation": 238910, "Glass Contractor": 238150,
    "Fence & Deck Contractor": 238990, "Lawn Service": 561730,
    "Paving Contractor": 237310, "Produce Packing": 311411,
    "Horse Transportation": 484220, "Family Medicine": 621111,
    "Citrus Processing": 311411, "Propane Distributor": 454312,
}

FRANCHISE_NAMES = [
    "SERVPRO", "SUBWAY", "JIFFY LUBE", "MEINEKE", "SERVICEMASTER",
    "ACE HARDWARE", "COMFORT KEEPERS",
]

RATIO_BY_SECTOR = {
    "72": 3.8, "23": 3.2, "62": 2.3, "56": 2.5, "48": 3.8,
    "44": 5.5, "45": 5.5, "42": 7.0, "54": 2.0, "81": 2.5,
    "53": 5.0, "31": 4.5, "32": 4.5, "33": 4.5, "52": 5.0,
}


def get_ratio(naics: int) -> float:
    s = str(naics)[:2]
    return RATIO_BY_SECTOR.get(s, 3.0)


def main():
    random.seed(42)
    conn = duckdb.connect()
    rows_by_state: dict[str, list] = {}

    with open(SAMPLE_CSV) as f:
        all_rows = list(csv.DictReader(f))

    for idx, row in enumerate(all_rows):
        company = row.get("Company", "").strip()
        city = row.get("City", "").strip()
        state = row.get("State", "").strip().upper()
        zip_code = row.get("Zip", "").strip()
        address = row.get("Address", "").strip()
        industry = row.get("Industry", "").strip()
        rev_str = row.get("Estimated Revenue", "").strip()

        if not company or not state:
            continue

        naics = NAICS_MAP.get(industry, 541990)
        rev = REVENUE_PARSE.get(rev_str, 1000000)
        ratio = get_ratio(naics)
        annual_payroll = rev / ratio

        # Vary the loan amount to create realistic revenue disagreements
        # Some will match closely, others will diverge significantly
        variation = random.choice([
            0.6,   # PPP implies much less revenue → SQ overestimates
            0.75,
            0.85,
            0.95,  # Close agreement
            1.0,   # Close agreement
            1.05,  # Close agreement
            1.15,
            1.3,
            1.6,   # PPP implies more revenue → SQ underestimates
            2.0,   # Big disagreement
        ])
        monthly_payroll = (annual_payroll * variation) / 12
        loan_amount = monthly_payroll * 2.5

        # Decide match quality tier for this lead
        # ~8 leads: no seed (will show as "Skip - No PPP match found")
        skip_indices = {5, 16, 23, 54, 66, 73, 82, 91}
        if idx in skip_indices:
            continue

        # ~8 leads: franchise flag
        franchise_indices = {10, 22, 40, 51, 60, 70, 80, 88}
        is_franchise = idx in franchise_indices
        franchise_name = random.choice(FRANCHISE_NAMES) if is_franchise else ""

        # ~6 leads: change of ownership
        ownership_indices = {15, 30, 45, 62, 75, 85}
        is_ownership_change = idx in ownership_indices

        # Name variation: exact match for ~65%, slight variation for rest
        # Exact names get High confidence, varied get Probable
        borr_name = company.upper()
        if idx % 5 == 3:
            # Slight name variation → will still match but at Probable
            words = borr_name.split()
            if len(words) > 2:
                borr_name = " ".join(words[:2]) + " " + words[-1]

        norm = normalize_name(borr_name).normalized

        biz_age = "Change of Ownership" if is_ownership_change else random.choice([
            "Existing or more than 2 years old",
            "Existing or more than 2 years old",
            "Existing or more than 2 years old",
            "Unanswered",
            "New Business or 2 years or less",
        ])

        jobs = max(2, int(annual_payroll / random.randint(55000, 90000)))

        rows_by_state.setdefault(state, []).append({
            "BorrowerName": borr_name,
            "BorrowerCity": city.upper(),
            "BorrowerState": state,
            "BorrowerZip": zip_code,
            "BorrowerAddress": address.upper(),
            "NAICSCode": naics,
            "LoanNumber": f"99{random.randint(10000, 99999)}",
            "ProcessingMethod": random.choice(["PPP", "PPP", "PPP", "PPS"]),
            "InitialApprovalAmount": round(loan_amount, 2),
            "CurrentApprovalAmount": round(loan_amount, 2),
            "PAYROLL_PROCEED": round(loan_amount * random.uniform(0.80, 0.95), 2),
            "JobsReported": jobs,
            "BusinessAgeDescription": biz_age,
            "BusinessType": "Limited  Liability Company(LLC)" if "LLC" in company else "Corporation",
            "FranchiseName": franchise_name,
            "ForgivenessAmount": round(loan_amount * random.uniform(0.9, 1.0), 2),
            "ForgivenessDate": random.choice(["05/2021", "07/2021", "09/2021", "12/2021"]),
            "LoanStatus": "Paid in Full or Charged Off",
            "normalized_name": norm,
            "RuralUrbanIndicator": random.choice(["U", "U", "U", "R"]),
            "Term": 60,
        })

    # Write seeded data into existing demo parquet
    for state, seed_rows in rows_by_state.items():
        demo_dir = DEMO_DIR / "ppp" / f"state={state}"
        if not demo_dir.exists():
            continue

        existing_parquet = demo_dir / "data.parquet"
        if not existing_parquet.exists():
            continue

        # Get schema from existing data
        cols = conn.execute(f"DESCRIBE (SELECT * FROM read_parquet('{existing_parquet}') LIMIT 1)").fetchall()
        col_names = [c[0] for c in cols]

        # Build seed dataframe matching schema
        seed_dicts = []
        for r in seed_rows:
            d = {}
            for c in col_names:
                d[c] = r.get(c, None)
            seed_dicts.append(d)

        df = pd.DataFrame(seed_dicts)
        conn.execute("CREATE OR REPLACE TABLE seed AS SELECT * FROM df")
        conn.execute(f"CREATE OR REPLACE TABLE existing AS SELECT * FROM read_parquet('{existing_parquet}')")

        # Remove any previous seeds (by loan number prefix 99)
        conn.execute("DELETE FROM existing WHERE CAST(LoanNumber AS VARCHAR) LIKE '99%'")

        conn.execute(f"""
            COPY (
                SELECT * FROM existing
                UNION ALL
                SELECT * FROM seed
            ) TO '{existing_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)

        count = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{existing_parquet}')").fetchone()[0]
        print(f"  PPP {state}: {len(seed_rows)} seeded + existing = {count} total")

    conn.close()
    print("\nDone. Demo data seeded with varied match quality.")


if __name__ == "__main__":
    main()
