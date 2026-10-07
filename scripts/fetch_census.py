"""Fetch Census Economic Census payroll-to-revenue ratios and cache locally.

The Census Bureau API now requires a free API key (https://api.census.gov/data/key_signup.html).
The cached file data/reference/census_ratios_2022.json is the authoritative source at runtime;
this script only needs to run if you want to refresh from the API with your own key.
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request

API_URL_TEMPLATE = (
    "https://api.census.gov/data/2022/ecnbasic"
    "?get=NAICS2022,NAICS2022_LABEL,PAYANN,RCPTOT,ESTAB,EMP&for=us:*&key={key}"
)

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "reference" / "census_ratios_2022.json"


def load_cached_ratios() -> dict:
    if not OUTPUT.exists():
        print(f"ERROR: cached ratios file not found at {OUTPUT}", file=sys.stderr)
        print("  Run this script with --api-key YOUR_KEY to fetch from Census API.", file=sys.stderr)
        sys.exit(1)
    return json.loads(OUTPUT.read_text())


def fetch_and_compute(api_key: str) -> dict:
    url = API_URL_TEMPLATE.format(key=api_key)
    print("Fetching Census Economic Census data...")
    req = Request(url, headers={"User-Agent": "GroundTruth/1.0"})
    with urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode())

    header = raw[0]
    rows = raw[1:]
    print(f"  Got {len(rows)} rows")

    ratios: dict[str, dict] = {}
    for row in rows:
        rec = dict(zip(header, row))
        naics = rec["NAICS2022"]
        payann = rec["PAYANN"]
        rcptot = rec["RCPTOT"]

        if not naics or not payann or not rcptot:
            continue
        try:
            payann_val = float(payann)
            rcptot_val = float(rcptot)
        except (ValueError, TypeError):
            continue

        if payann_val <= 0:
            continue

        ratio = rcptot_val / payann_val
        ratios[naics] = {
            "naics": naics,
            "label": rec.get("NAICS2022_LABEL", ""),
            "payann_thousands": payann_val,
            "rcptot_thousands": rcptot_val,
            "establishments": rec.get("ESTAB"),
            "employees": rec.get("EMP"),
            "revenue_per_payroll_dollar": round(ratio, 4),
            "naics_level": len(naics.rstrip("-")),
        }

    return ratios


def lookup_ratio(ratios: dict, naics_code: str) -> tuple[float | None, int | None]:
    for length in range(min(6, len(naics_code)), 1, -1):
        prefix = naics_code[:length]
        if prefix in ratios:
            return ratios[prefix]["revenue_per_payroll_dollar"], length
    two_digit = naics_code[:2]
    if two_digit in ratios:
        return ratios[two_digit]["revenue_per_payroll_dollar"], 2
    return None, None


def main():
    parser = argparse.ArgumentParser(description="Fetch or verify Census NAICS ratios")
    parser.add_argument("--api-key", help="Census API key to refresh from the API")
    parser.add_argument("--verify", action="store_true", help="Verify cached file with sample lookups")
    args = parser.parse_args()

    if args.api_key:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        ratios = fetch_and_compute(args.api_key)
        OUTPUT.write_text(json.dumps(ratios, indent=2))
        print(f"  Wrote {len(ratios)} NAICS ratios to {OUTPUT}")
    else:
        ratios = load_cached_ratios()
        print(f"Using cached ratios ({len(ratios)} NAICS codes)")

    examples = ["722511", "238220", "621210", "484110", "561730"]
    for code in examples:
        ratio, level = lookup_ratio(ratios, code)
        label = ratios.get(code, {}).get("label", "?")
        print(f"  {code} ({label}): ratio={ratio}, matched at {level}-digit")


if __name__ == "__main__":
    main()
