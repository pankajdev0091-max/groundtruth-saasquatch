"""
Derived signals from matched PPP/SBA records.
Revenue estimation, headcount, business age, SBA history, recommendations.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from groundtruth.match import MatchResult, SBALoanRecord

RATIOS_PATH = Path(__file__).resolve().parent.parent / "data" / "reference" / "census_ratios_2022.json"

_ratios_cache: dict | None = None


def _load_ratios() -> dict:
    global _ratios_cache
    if _ratios_cache is None:
        _ratios_cache = json.loads(RATIOS_PATH.read_text())
    return _ratios_cache


def _lookup_ratio(naics_code: str | int) -> tuple[float | None, int | None, float | None]:
    """Return (best_ratio, naics_level, parent_ratio) for revenue estimation range."""
    ratios = _load_ratios()
    naics_code = str(naics_code).strip()
    best_ratio = None
    best_level = None
    parent_ratio = None

    for length in range(min(6, len(naics_code)), 1, -1):
        prefix = naics_code[:length]
        if prefix in ratios:
            if best_ratio is None:
                best_ratio = ratios[prefix]["revenue_per_payroll_dollar"]
                best_level = length
            else:
                parent_ratio = ratios[prefix]["revenue_per_payroll_dollar"]
                break

    if best_ratio is None:
        two_digit = naics_code[:2]
        if two_digit in ratios:
            best_ratio = ratios[two_digit]["revenue_per_payroll_dollar"]
            best_level = 2

    return best_ratio, best_level, parent_ratio


@dataclass
class RevenueEstimate:
    annual_payroll: float | None = None
    payroll_formula: str = ""
    revenue_point: float | None = None
    revenue_low: float | None = None
    revenue_high: float | None = None
    revenue_formula: str = ""
    naics_ratio: float | None = None
    naics_level: int | None = None
    payroll_proceed_value: float | None = None
    payroll_proceed_note: str = ""


@dataclass
class SBAHistory:
    loans: list[dict] = field(default_factory=list)
    total_borrowed: float = 0.0
    maturing_within_12mo: bool = False
    maturing_details: str = ""
    earliest_approval: str = ""


@dataclass
class BusinessSignals:
    revenue: RevenueEstimate
    sba_history: SBAHistory
    headcount: int | None = None
    business_age: str = ""
    franchise_flag: bool = False
    franchise_name: str = ""
    change_of_ownership: bool = False
    recommendation: str = ""
    recommendation_rule: str = ""


CPI_2020_TO_2024 = 1.22


def compute_revenue(match: MatchResult) -> RevenueEstimate:
    c = match.candidate
    est = RevenueEstimate()

    naics = str(c.naics_code or "").strip()
    is_naics72_second = (
        c.processing_method == "PPS"
        and naics.startswith("72")
    )
    multiplier = 3.5 if is_naics72_second else 2.5

    if c.initial_amount and c.initial_amount > 0:
        est.annual_payroll = (c.initial_amount / multiplier) * 12
        est.payroll_formula = (
            f"PPP loan ${c.initial_amount:,.0f} ÷ {multiplier} × 12"
        )

    if c.payroll_proceed and c.payroll_proceed > 0:
        est.payroll_proceed_value = c.payroll_proceed * 12
        if est.annual_payroll:
            ratio = est.payroll_proceed_value / est.annual_payroll
            if 0.5 < ratio < 2.0:
                est.payroll_proceed_note = (
                    f"PAYROLL_PROCEED cross-check: ${est.payroll_proceed_value:,.0f}/yr "
                    f"({ratio:.1f}× loan-derived figure)"
                )
            else:
                est.payroll_proceed_note = (
                    f"PAYROLL_PROCEED ${est.payroll_proceed_value:,.0f}/yr diverges "
                    f"significantly from loan-derived ${est.annual_payroll:,.0f}/yr"
                )

    if est.annual_payroll and naics:
        ratio, level, parent_ratio = _lookup_ratio(naics)
        if ratio is not None:
            est.naics_ratio = ratio
            est.naics_level = level
            est.revenue_point = est.annual_payroll * ratio

            if parent_ratio is not None:
                low = min(est.annual_payroll * ratio, est.annual_payroll * parent_ratio)
                high = max(est.annual_payroll * ratio, est.annual_payroll * parent_ratio)
                est.revenue_low = low
                est.revenue_high = high
            else:
                est.revenue_low = est.revenue_point * 0.8
                est.revenue_high = est.revenue_point * 1.2

            est.revenue_formula = (
                f"payroll ${est.annual_payroll:,.0f} × {ratio:.2f} "
                f"(NAICS {naics[:level]}, {level}-digit)"
            )

    return est


def compute_sba_history(sba_loans: list[SBALoanRecord]) -> SBAHistory:
    history = SBAHistory()
    today = datetime.now()
    maturity_horizon = today + timedelta(days=365)

    for loan in sba_loans:
        loan_dict = {
            "borrower": loan.borrower_name,
            "program": loan.program,
            "amount": loan.gross_approval,
            "approval_date": str(loan.approval_date) if loan.approval_date else "",
            "term_months": int(loan.term_months) if loan.term_months else None,
            "lender": loan.bank_name,
            "status": loan.loan_status,
            "naics": str(loan.naics_code) if loan.naics_code else "",
        }
        history.loans.append(loan_dict)
        history.total_borrowed += loan.gross_approval

        if loan.approval_date and loan.term_months:
            try:
                if hasattr(loan.approval_date, 'year'):
                    app_date = datetime(loan.approval_date.year, loan.approval_date.month, loan.approval_date.day)
                else:
                    ad = str(loan.approval_date)[:10]
                    try:
                        app_date = datetime.strptime(ad, "%m/%d/%Y")
                    except ValueError:
                        app_date = datetime.strptime(ad, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            maturity = app_date + timedelta(days=loan.term_months * 30.44)
            if maturity <= maturity_horizon and loan.loan_status not in ("PIF", "CHGOFF", "CANCLD"):
                history.maturing_within_12mo = True
                history.maturing_details = (
                    f"${loan.gross_approval:,.0f} {loan.program} loan matures ~{maturity.strftime('%Y-%m')}"
                )

        if not history.earliest_approval and loan.approval_date:
            history.earliest_approval = loan.approval_date

    if sba_loans:
        dates = []
        for l in sba_loans:
            if l.approval_date:
                if hasattr(l.approval_date, 'isoformat'):
                    dates.append(str(l.approval_date))
                else:
                    dates.append(str(l.approval_date))
        if dates:
            history.earliest_approval = min(dates)

    history.loans.sort(key=lambda x: x.get("approval_date", ""), reverse=True)
    return history


def compute_recommendation(
    match: MatchResult | None,
    revenue: RevenueEstimate,
    franchise_flag: bool,
    change_of_ownership: bool,
    exclude_franchises: bool = False,
    min_revenue: float | None = None,
    max_revenue: float | None = None,
) -> tuple[str, str]:
    if match is None:
        return "Skip", "No PPP match found"

    if franchise_flag and exclude_franchises:
        return "Skip", "Franchise — excluded by filter"

    if revenue.revenue_point is not None:
        if min_revenue and revenue.revenue_point < min_revenue:
            return "Skip", f"Revenue ${revenue.revenue_point:,.0f} below minimum ${min_revenue:,.0f}"
        if max_revenue and revenue.revenue_point > max_revenue:
            return "Skip", f"Revenue ${revenue.revenue_point:,.0f} above maximum ${max_revenue:,.0f}"

    if match.tier in ("Weak", "Probable"):
        return "Verify first", f"Match confidence is {match.tier} ({match.confidence:.0%})"

    if change_of_ownership:
        return "Verify first", "Recent change of ownership detected"

    return "Worth a credit", f"High confidence match ({match.confidence:.0%})"


def compute_signals(
    match: MatchResult | None,
    sba_loans: list[SBALoanRecord],
    exclude_franchises: bool = False,
    min_revenue: float | None = None,
    max_revenue: float | None = None,
) -> BusinessSignals:
    revenue = compute_revenue(match) if match else RevenueEstimate()
    sba_history = compute_sba_history(sba_loans)

    franchise_flag = False
    franchise_name = ""
    if match and match.candidate.franchise_name:
        franchise_flag = True
        franchise_name = match.candidate.franchise_name
    if not franchise_flag:
        for loan in sba_loans:
            if loan.franchise_name and loan.franchise_name.strip():
                franchise_flag = True
                franchise_name = loan.franchise_name
                break

    change_of_ownership = False
    if match:
        if "change of ownership" in (match.candidate.business_age or "").lower():
            change_of_ownership = True
    for loan in sba_loans:
        if "change of ownership" in (loan.business_age or "").lower():
            change_of_ownership = True
        if "change of ownership" in (loan.business_type or "").lower():
            change_of_ownership = True

    recommendation, rule = compute_recommendation(
        match, revenue, franchise_flag, change_of_ownership,
        exclude_franchises, min_revenue, max_revenue,
    )

    business_age = ""
    if match:
        business_age = match.candidate.business_age
    if not business_age and sba_history.earliest_approval:
        try:
            ea = str(sba_history.earliest_approval)[:10]
            try:
                earliest = datetime.strptime(ea, "%m/%d/%Y")
            except ValueError:
                earliest = datetime.strptime(ea, "%Y-%m-%d")
            years = (datetime.now() - earliest).days / 365.25
            business_age = f"SBA history spans {years:.0f} years (since {earliest.year})"
        except (ValueError, TypeError):
            pass

    return BusinessSignals(
        revenue=revenue,
        headcount=match.candidate.jobs_reported if match else None,
        business_age=business_age,
        sba_history=sba_history,
        franchise_flag=franchise_flag,
        franchise_name=franchise_name,
        change_of_ownership=change_of_ownership,
        recommendation=recommendation,
        recommendation_rule=rule,
    )
