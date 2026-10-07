import pytest
from groundtruth.match import MatchCandidate, MatchResult, SBALoanRecord
from groundtruth.signals import compute_revenue, compute_sba_history, compute_recommendation


def _make_match(
    initial_amount: float = 100000,
    processing_method: str = "PPP",
    naics_code: str = "238220",
    payroll_proceed: float | None = None,
    jobs_reported: int | None = 10,
    franchise_name: str = "",
    business_age: str = "Existing or more than 2 years old",
    confidence: float = 0.90,
    tier: str = "High",
) -> MatchResult:
    return MatchResult(
        confidence=confidence,
        tier=tier,
        reasons=["name 95% similar"],
        candidate=MatchCandidate(
            borrower_name="TEST BUSINESS",
            city="Los Angeles",
            state="CA",
            zip_code="90001",
            address="123 Main St",
            naics_code=naics_code,
            loan_number="1234567",
            processing_method=processing_method,
            initial_amount=initial_amount,
            current_amount=initial_amount,
            payroll_proceed=payroll_proceed,
            jobs_reported=jobs_reported,
            business_age=business_age,
            business_type="Corporation",
            franchise_name=franchise_name,
            loan_status="Paid in Full",
            normalized_name="TEST BUSINESS",
        ),
        name_score=0.95,
    )


class TestRevenueComputation:
    def test_basic_payroll_derivation(self):
        match = _make_match(initial_amount=100000)
        rev = compute_revenue(match)
        # 100000 / 2.5 * 12 = 480000
        assert rev.annual_payroll == pytest.approx(480000)

    def test_naics72_second_draw_multiplier(self):
        match = _make_match(
            initial_amount=100000,
            processing_method="PPS",
            naics_code="722511",
        )
        rev = compute_revenue(match)
        # 100000 / 3.5 * 12 = 342857.14
        assert rev.annual_payroll == pytest.approx(100000 / 3.5 * 12, rel=0.01)

    def test_naics72_first_draw_normal_multiplier(self):
        match = _make_match(
            initial_amount=100000,
            processing_method="PPP",
            naics_code="722511",
        )
        rev = compute_revenue(match)
        # First draw always uses 2.5, even for NAICS 72
        assert rev.annual_payroll == pytest.approx(480000)

    def test_payroll_proceed_crosscheck(self):
        match = _make_match(
            initial_amount=100000,
            payroll_proceed=35000,
        )
        rev = compute_revenue(match)
        assert rev.payroll_proceed_value == pytest.approx(420000)
        assert "cross-check" in rev.payroll_proceed_note

    def test_revenue_estimate_with_naics_ratio(self):
        match = _make_match(initial_amount=100000, naics_code="238220")
        rev = compute_revenue(match)
        assert rev.revenue_point is not None
        assert rev.revenue_point > 0
        assert rev.naics_ratio is not None
        assert rev.revenue_formula != ""

    def test_zero_loan_amount(self):
        match = _make_match(initial_amount=0)
        rev = compute_revenue(match)
        assert rev.annual_payroll is None


class TestSBAHistory:
    def test_empty_loans(self):
        history = compute_sba_history([])
        assert history.total_borrowed == 0
        assert not history.maturing_within_12mo
        assert history.loans == []

    def test_total_borrowed(self):
        loans = [
            SBALoanRecord(
                borrower_name="TEST", city="LA", state="CA", zip_code="90001",
                address="", bank_name="BANK", gross_approval=500000,
                approval_date="01/15/2020", approval_fy="2020", term_months=120,
                naics_code="238220", naics_description="", franchise_code="",
                franchise_name="", business_type="Corp", business_age="",
                loan_status="EXEMPT", jobs_supported=10, program="7(a)",
            ),
            SBALoanRecord(
                borrower_name="TEST", city="LA", state="CA", zip_code="90001",
                address="", bank_name="BANK2", gross_approval=200000,
                approval_date="06/01/2022", approval_fy="2022", term_months=60,
                naics_code="238220", naics_description="", franchise_code="",
                franchise_name="", business_type="Corp", business_age="",
                loan_status="EXEMPT", jobs_supported=12, program="7(a)",
            ),
        ]
        history = compute_sba_history(loans)
        assert history.total_borrowed == 700000
        assert len(history.loans) == 2


class TestRecommendation:
    def test_no_match(self):
        from groundtruth.signals import RevenueEstimate
        rec, rule = compute_recommendation(
            None, RevenueEstimate(), False, False
        )
        assert rec == "Skip"

    def test_high_confidence(self):
        match = _make_match(confidence=0.90, tier="High")
        rev = compute_revenue(match)
        rec, rule = compute_recommendation(match, rev, False, False)
        assert rec == "Worth a credit"

    def test_weak_match_verify(self):
        match = _make_match(confidence=0.60, tier="Weak")
        rev = compute_revenue(match)
        rec, rule = compute_recommendation(match, rev, False, False)
        assert rec == "Verify first"

    def test_franchise_excluded(self):
        match = _make_match(confidence=0.90, tier="High")
        rev = compute_revenue(match)
        rec, rule = compute_recommendation(
            match, rev, True, False, exclude_franchises=True
        )
        assert rec == "Skip"
        assert "Franchise" in rule

    def test_revenue_below_minimum(self):
        match = _make_match(initial_amount=50000)
        rev = compute_revenue(match)
        rec, rule = compute_recommendation(
            match, rev, False, False, min_revenue=5000000
        )
        assert rec == "Skip"
        assert "below" in rule
