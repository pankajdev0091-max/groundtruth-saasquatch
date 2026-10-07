"""
Match SaaSquatch export rows to PPP/SBA loan records.
Blocking by state + city/zip prefix, scoring with rapidfuzz.
"""
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
from rapidfuzz import fuzz

from groundtruth.normalize import normalize_name, NormalizedName

import os
from collections import defaultdict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _data_dir() -> Path:
    if os.environ.get("GROUNDTRUTH_DATA_FULL"):
        return _PROJECT_ROOT / "data" / "processed"
    demo = _PROJECT_ROOT / "data" / "demo"
    if demo.exists():
        return demo
    return _PROJECT_ROOT / "data" / "processed"

_ppp_state_cache: dict[str, list[tuple]] = {}
_sba_state_cache: dict[str, list[tuple]] = {}

NAICS_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "11": ["agriculture", "farm", "ranch", "crop", "livestock"],
    "21": ["mining", "oil", "gas", "quarry"],
    "22": ["utility", "utilities", "electric", "water", "sewer"],
    "23": ["construction", "contractor", "builder", "roofing", "plumbing",
           "hvac", "electrical", "framing", "concrete", "excavation",
           "demolition", "painting", "flooring", "remodeling"],
    "31": ["manufacturing", "food", "beverage", "textile", "apparel",
           "wood", "paper", "printing", "chemical", "plastic", "rubber"],
    "32": ["manufacturing", "glass", "cement", "metal", "steel"],
    "33": ["manufacturing", "machinery", "computer", "electronic",
           "appliance", "vehicle", "furniture"],
    "42": ["wholesale", "distributor", "distribution"],
    "44": ["retail", "store", "shop", "dealer", "auto parts"],
    "45": ["retail", "sporting", "hobby", "book", "department store"],
    "48": ["transportation", "trucking", "freight", "transit", "taxi",
           "courier", "moving", "logistics"],
    "49": ["warehouse", "storage", "postal"],
    "51": ["information", "publishing", "software", "telecom", "broadcasting"],
    "52": ["finance", "banking", "insurance", "credit union", "investment"],
    "53": ["real estate", "property management", "rental", "leasing"],
    "54": ["professional", "legal", "accounting", "engineering",
           "architecture", "consulting", "advertising", "research"],
    "56": ["admin", "staffing", "janitorial", "landscaping", "security",
           "cleaning", "pest control", "waste", "facilities"],
    "61": ["education", "school", "training", "tutoring"],
    "62": ["healthcare", "medical", "dental", "physician", "hospital",
           "clinic", "nursing", "home health", "therapy", "optometry",
           "chiropractic", "veterinary", "pharmacy"],
    "71": ["arts", "entertainment", "recreation", "amusement", "sports",
           "fitness", "gym"],
    "72": ["restaurant", "food service", "hotel", "motel", "lodging",
           "bar", "catering", "cafe", "coffee"],
    "81": ["repair", "auto repair", "maintenance", "laundry", "dry cleaning",
           "salon", "barber", "funeral", "religious", "civic"],
}


@dataclass
class MatchCandidate:
    borrower_name: str
    city: str
    state: str
    zip_code: str
    address: str
    naics_code: str
    loan_number: str | None = None
    processing_method: str = ""
    initial_amount: float = 0.0
    current_amount: float = 0.0
    payroll_proceed: float | None = None
    jobs_reported: int | None = None
    business_age: str = ""
    business_type: str = ""
    franchise_name: str = ""
    forgiveness_amount: float | None = None
    forgiveness_date: str = ""
    loan_status: str = ""
    normalized_name: str = ""
    source: str = "ppp"


@dataclass
class MatchResult:
    confidence: float
    tier: str
    reasons: list[str]
    candidate: MatchCandidate
    name_score: float = 0.0


@dataclass
class SBALoanRecord:
    borrower_name: str
    city: str
    state: str
    zip_code: str
    address: str
    bank_name: str
    gross_approval: float
    approval_date: str
    approval_fy: str
    term_months: int | None
    naics_code: str
    naics_description: str
    franchise_code: str
    franchise_name: str
    business_type: str
    business_age: str
    loan_status: str
    jobs_supported: int | None
    program: str
    normalized_name: str = ""


@dataclass
class BusinessMatch:
    input_name: str
    input_city: str
    input_state: str
    ppp_matches: list[MatchResult] = field(default_factory=list)
    sba_loans: list[SBALoanRecord] = field(default_factory=list)
    best_match: MatchResult | None = None


def guess_naics_sector(industry_text: str | None) -> str | None:
    if not industry_text:
        return None
    text = industry_text.lower()
    best_sector = None
    best_count = 0
    for sector, keywords in NAICS_SECTOR_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_sector = sector
    return best_sector


def _score_match(
    query_norm: NormalizedName,
    query_city: str,
    query_zip: str,
    query_address: str,
    query_naics_sector: str | None,
    candidate_name: str,
    candidate_city: str,
    candidate_zip: str,
    candidate_address: str,
    candidate_naics: str,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    name_sim = fuzz.token_set_ratio(query_norm.normalized, candidate_name) / 100.0
    name_weight = 0.55
    score += name_sim * name_weight
    reasons.append(f"name {int(name_sim * 100)}% similar")

    if query_city and candidate_city:
        if query_city.upper() == candidate_city.upper():
            score += 0.10
            reasons.append("city matched")

    if query_zip and candidate_zip:
        if query_zip[:5] == candidate_zip[:5]:
            score += 0.15
            reasons.append(f"zip {candidate_zip[:5]} matched")
        elif query_zip[:3] == candidate_zip[:3]:
            score += 0.05
            reasons.append(f"zip prefix {candidate_zip[:3]} matched")

    if query_address and candidate_address:
        import re
        q_nums = re.findall(r"\d+", query_address)
        c_nums = re.findall(r"\d+", candidate_address)
        if q_nums and c_nums and q_nums[0] == c_nums[0]:
            score += 0.12
            reasons.append(f"street number {q_nums[0]} matched")

    if query_naics_sector and candidate_naics:
        cn = str(candidate_naics)
        if cn[:2] == query_naics_sector:
            score += 0.05
            reasons.append("industry sector consistent")
        elif cn[:2] != query_naics_sector:
            score -= 0.03
            reasons.append("industry sector inconsistent")

    distinctive_tokens = [t for t in query_norm.tokens if len(t) > 2]
    if len(distinctive_tokens) < 2:
        score -= 0.08
        reasons.append("generic name penalty")

    score = max(0.0, min(1.0, score))
    return score, reasons


def _tier(score: float) -> str:
    if score >= 0.85:
        return "High"
    if score >= 0.70:
        return "Probable"
    if score >= 0.55:
        return "Weak"
    return "No match"


def _load_ppp_state(state: str) -> dict:
    """Load PPP data for a state into memory, indexed by city and zip3."""
    if state in _ppp_state_cache:
        return _ppp_state_cache[state]

    ppp_dir = _data_dir() / "ppp" / f"state={state}"
    if not ppp_dir.exists():
        _ppp_state_cache[state] = {"by_city": {}, "by_zip3": {}}
        return _ppp_state_cache[state]

    conn = duckdb.connect()
    parquet_glob = str(ppp_dir / "*.parquet")
    try:
        rows = conn.execute(f"""
            SELECT
                BorrowerName, BorrowerCity, BorrowerState, BorrowerZip,
                BorrowerAddress, NAICSCode, LoanNumber, ProcessingMethod,
                InitialApprovalAmount, CurrentApprovalAmount, PAYROLL_PROCEED,
                JobsReported, BusinessAgeDescription, BusinessType,
                FranchiseName, ForgivenessAmount, ForgivenessDate,
                LoanStatus, normalized_name
            FROM read_parquet('{parquet_glob}')
        """).fetchall()
    except Exception:
        conn.close()
        _ppp_state_cache[state] = {"by_city": {}, "by_zip3": {}}
        return _ppp_state_cache[state]
    conn.close()

    by_city: dict[str, list] = defaultdict(list)
    by_zip3: dict[str, list] = defaultdict(list)
    for row in rows:
        city_key = str(row[1] or "").upper().strip()
        zip_val = str(row[3] or "")
        zip3 = zip_val[:3] if zip_val else ""
        if city_key:
            by_city[city_key].append(row)
        if zip3:
            by_zip3[zip3].append(row)

    _ppp_state_cache[state] = {"by_city": dict(by_city), "by_zip3": dict(by_zip3)}
    return _ppp_state_cache[state]


def find_ppp_matches(
    name: str,
    city: str,
    state: str,
    zip_code: str = "",
    address: str = "",
    industry: str | None = None,
    max_candidates: int = 10,
) -> list[MatchResult]:
    state = state.upper().strip()
    query_norm = normalize_name(name)
    if not query_norm.normalized:
        return []

    cache = _load_ppp_state(state)
    naics_sector = guess_naics_sector(industry)

    city_upper = city.upper().strip() if city else ""
    zip_prefix = zip_code[:3] if zip_code else ""

    candidates: set[int] = set()
    if city_upper and city_upper in cache["by_city"]:
        for row in cache["by_city"][city_upper]:
            candidates.add(id(row))
    if zip_prefix and zip_prefix in cache["by_zip3"]:
        for row in cache["by_zip3"][zip_prefix]:
            candidates.add(id(row))

    if not candidates:
        return []

    seen_ids = candidates
    rows = [r for r in cache["by_city"].get(city_upper, []) if id(r) in seen_ids]
    if zip_prefix:
        for r in cache["by_zip3"].get(zip_prefix, []):
            if id(r) not in {id(x) for x in rows}:
                rows.append(r)

    results: list[MatchResult] = []
    for row in rows:
        (borr_name, borr_city, borr_state, borr_zip, borr_addr,
         naics, loan_num, proc_method, init_amt, curr_amt,
         payroll, jobs, biz_age, biz_type, franchise,
         forgive_amt, forgive_date, loan_status, norm_name) = row

        score, reasons = _score_match(
            query_norm, city, zip_code, address, naics_sector,
            str(norm_name or ""), str(borr_city or ""), str(borr_zip or ""),
            str(borr_addr or ""), str(naics or ""),
        )

        tier = _tier(score)
        if tier == "No match":
            continue

        candidate = MatchCandidate(
            borrower_name=borr_name or "",
            city=borr_city or "",
            state=borr_state or "",
            zip_code=borr_zip or "",
            address=borr_addr or "",
            naics_code=naics or "",
            loan_number=loan_num,
            processing_method=proc_method or "",
            initial_amount=float(init_amt or 0),
            current_amount=float(curr_amt or 0),
            payroll_proceed=float(payroll) if payroll else None,
            jobs_reported=int(jobs) if jobs else None,
            business_age=biz_age or "",
            business_type=biz_type or "",
            franchise_name=franchise or "",
            forgiveness_amount=float(forgive_amt) if forgive_amt else None,
            forgiveness_date=forgive_date or "",
            loan_status=loan_status or "",
            normalized_name=norm_name or "",
            source="ppp",
        )
        results.append(MatchResult(
            confidence=score,
            tier=tier,
            reasons=reasons,
            candidate=candidate,
            name_score=fuzz.token_set_ratio(query_norm.normalized, norm_name or "") / 100.0,
        ))

    results.sort(key=lambda r: r.confidence, reverse=True)
    return results[:max_candidates]


def find_sba_loans(
    name: str,
    city: str,
    state: str,
    zip_code: str = "",
) -> list[SBALoanRecord]:
    state = state.upper().strip()
    results: list[SBALoanRecord] = []
    query_norm = normalize_name(name)

    for dataset in ["sba7a", "sba504"]:
        data_dir = _data_dir() / dataset / f"state={state}"
        if not data_dir.exists():
            continue

        conn = duckdb.connect()
        city_upper = city.upper().strip() if city else ""

        blocking_clauses = []
        if city_upper:
            blocking_clauses.append(f"UPPER(BorrCity) = '{city_upper}'")
        if zip_code:
            blocking_clauses.append(f"SUBSTRING(BorrZip, 1, 3) = '{zip_code[:3]}'")

        blocking_where = " OR ".join(blocking_clauses) if blocking_clauses else "1=1"
        parquet_glob = str(data_dir / "*.parquet")

        lender_col = "BankName" if dataset == "sba7a" else "CDC_Name"
        try:
            rows = conn.execute(f"""
                SELECT
                    BorrName, BorrCity, BorrState, BorrZip, BorrStreet,
                    {lender_col}, GrossApproval, ApprovalDate, ApprovalFY,
                    TermInMonths, NaicsCode, NaicsDescription,
                    FranchiseCode, FranchiseName, BusinessType, BusinessAge,
                    LoanStatus, JobsSupported, ProcessingMethod, Program,
                    normalized_name
                FROM read_parquet('{parquet_glob}')
                WHERE ({blocking_where})
            """).fetchall()
        except Exception:
            conn.close()
            continue

        for row in rows:
            (borr_name, borr_city, borr_state, borr_zip, borr_street,
             bank, gross, app_date, app_fy, term, naics, naics_desc,
             fran_code, fran_name, biz_type, biz_age,
             status, jobs, proc, program, norm_name) = row

            name_sim = fuzz.token_set_ratio(
                query_norm.normalized, norm_name or ""
            ) / 100.0
            if name_sim < 0.70:
                continue

            results.append(SBALoanRecord(
                borrower_name=borr_name or "",
                city=borr_city or "",
                state=borr_state or "",
                zip_code=borr_zip or "",
                address=borr_street or "",
                bank_name=bank or "",
                gross_approval=float(gross or 0),
                approval_date=app_date or "",
                approval_fy=app_fy or "",
                term_months=int(term) if term else None,
                naics_code=naics or "",
                naics_description=naics_desc or "",
                franchise_code=fran_code or "",
                franchise_name=fran_name or "",
                business_type=biz_type or "",
                business_age=biz_age or "",
                loan_status=status or "",
                jobs_supported=int(jobs) if jobs else None,
                program=program or "",
                normalized_name=norm_name or "",
            ))
        conn.close()

    return results


def collapse_ppp_loans(matches: list[MatchResult]) -> list[MatchResult]:
    """Collapse multiple PPP loans for the same borrower into one record."""
    by_name: dict[str, list[MatchResult]] = {}
    for m in matches:
        key = m.candidate.normalized_name or m.candidate.borrower_name
        by_name.setdefault(key, []).append(m)

    collapsed: list[MatchResult] = []
    for name, group in by_name.items():
        best = max(group, key=lambda m: m.confidence)
        if len(group) > 1:
            total_amount = sum(m.candidate.initial_amount for m in group)
            draws = len(group)
            best.reasons.append(f"{draws} PPP draws totaling ${total_amount:,.0f}")
            best.candidate.initial_amount = total_amount
        collapsed.append(best)

    collapsed.sort(key=lambda r: r.confidence, reverse=True)
    return collapsed


def match_business(
    name: str,
    city: str,
    state: str,
    zip_code: str = "",
    address: str = "",
    industry: str | None = None,
) -> BusinessMatch:
    ppp_matches = find_ppp_matches(name, city, state, zip_code, address, industry)
    ppp_matches = collapse_ppp_loans(ppp_matches)
    sba_loans = find_sba_loans(name, city, state, zip_code)

    best = ppp_matches[0] if ppp_matches else None

    return BusinessMatch(
        input_name=name,
        input_city=city,
        input_state=state,
        ppp_matches=ppp_matches,
        sba_loans=sba_loans,
        best_match=best,
    )
