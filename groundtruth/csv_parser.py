"""
Parse and auto-map SaaSquatch CSV exports with schema tolerance.
"""
import csv
import io
import re
from dataclasses import dataclass

COLUMN_SYNONYMS: dict[str, list[str]] = {
    "company_name": [
        "company", "company name", "business", "business name", "name",
        "company_name", "business_name", "borrower", "borrower_name",
        "organization", "firm", "firm_name",
    ],
    "city": [
        "city", "borrower city", "borrowercity", "business_city",
    ],
    "state": [
        "state", "st", "borrower state", "borrowerstate", "business_state",
    ],
    "zip_code": [
        "zip", "zip code", "zipcode", "postal", "postal code",
        "borrower zip", "borrowerzip",
    ],
    "address": [
        "address", "street", "street address", "borrower address",
        "borroweraddress", "location", "business_address",
    ],
    "website": [
        "website", "web", "url", "domain", "web site", "homepage",
    ],
    "phone": [
        "phone", "telephone", "tel", "phone number", "contact",
    ],
    "industry": [
        "industry", "sector", "category", "naics", "sic", "business type",
        "industry_type", "vertical",
    ],
    "estimated_revenue": [
        "estimated revenue", "est. revenue", "est revenue", "revenue",
        "annual revenue", "yearly revenue", "sales", "annual sales",
        "estimated_revenue",
    ],
    "employee_count": [
        "employees", "employee count", "headcount", "staff", "team size",
        "employee_count", "num_employees", "emp count",
    ],
}

US_STATE_RE = re.compile(
    r"\b(A[LKSZR]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|"
    r"N[CDEHJMVY]|O[HKR]|P[AR]|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])\b"
)


@dataclass
class ColumnMapping:
    source_column: str
    mapped_to: str
    confidence: str


@dataclass
class ParsedRow:
    company_name: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    address: str = ""
    website: str = ""
    phone: str = ""
    industry: str = ""
    estimated_revenue: str = ""
    employee_count: str = ""
    raw: dict | None = None


def detect_mapping(headers: list[str]) -> dict[str, ColumnMapping]:
    mapping: dict[str, ColumnMapping] = {}
    used_headers: set[str] = set()

    for field_name, synonyms in COLUMN_SYNONYMS.items():
        best_match = None
        best_confidence = "low"

        for header in headers:
            if header.lower() in used_headers:
                continue
            header_lower = header.lower().strip()

            if header_lower in synonyms:
                best_match = header
                best_confidence = "high"
                break

            for syn in synonyms:
                if syn in header_lower or header_lower in syn:
                    if best_match is None:
                        best_match = header
                        best_confidence = "medium"

        if best_match:
            mapping[field_name] = ColumnMapping(
                source_column=best_match,
                mapped_to=field_name,
                confidence=best_confidence,
            )
            used_headers.add(best_match.lower())

    return mapping


def parse_address(address_str: str) -> dict[str, str]:
    """Parse a US address string into components."""
    parts: dict[str, str] = {"street": "", "city": "", "state": "", "zip": ""}

    zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", address_str)
    if zip_match:
        parts["zip"] = zip_match.group(1)

    state_match = US_STATE_RE.search(address_str)
    if state_match:
        parts["state"] = state_match.group(1)

    comma_parts = [p.strip() for p in address_str.split(",")]
    if len(comma_parts) >= 3:
        parts["street"] = comma_parts[0]
        parts["city"] = comma_parts[1]
    elif len(comma_parts) == 2:
        parts["street"] = comma_parts[0]
        remaining = comma_parts[1].strip()
        city_part = re.sub(r"\b[A-Z]{2}\b", "", remaining)
        city_part = re.sub(r"\b\d{5}(-\d{4})?\b", "", city_part).strip()
        if city_part:
            parts["city"] = city_part

    return parts


def parse_revenue_string(s: str) -> float | None:
    if not s or not s.strip():
        return None

    s = s.strip().upper()
    s = s.replace("$", "").replace(",", "").strip()

    range_match = re.match(r"([\d.]+)\s*[MK]?\s*[-–—]\s*\$?([\d.]+)\s*([MK])?", s)
    if range_match:
        lo = float(range_match.group(1))
        hi = float(range_match.group(2))
        suffix = range_match.group(3) or ""
        multiplier = {"M": 1_000_000, "K": 1_000}.get(suffix, 1)
        if "M" in s[:s.index("-")] if "-" in s else "M" in s:
            lo *= 1_000_000
        elif "K" in s[:s.index("-")] if "-" in s else "K" in s:
            lo *= 1_000
        hi *= multiplier
        return (lo + hi) / 2

    match = re.match(r"([\d.]+)\s*([MK])?", s)
    if match:
        value = float(match.group(1))
        suffix = match.group(2)
        if suffix == "M":
            value *= 1_000_000
        elif suffix == "K":
            value *= 1_000
        return value

    return None


def parse_csv(content: str, mapping: dict[str, ColumnMapping] | None = None) -> tuple[list[ParsedRow], dict[str, ColumnMapping]]:
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []

    if mapping is None:
        mapping = detect_mapping(headers)

    rows: list[ParsedRow] = []
    for raw_row in reader:
        row = ParsedRow(raw=dict(raw_row))

        for field_name, col_map in mapping.items():
            value = raw_row.get(col_map.source_column, "").strip()
            setattr(row, field_name, value)

        if not row.city and not row.state and row.address:
            addr_parts = parse_address(row.address)
            if not row.city:
                row.city = addr_parts["city"]
            if not row.state:
                row.state = addr_parts["state"]
            if not row.zip_code:
                row.zip_code = addr_parts["zip"]

        rows.append(row)

    return rows, mapping
