import pytest
from groundtruth.csv_parser import (
    detect_mapping, parse_revenue_string, parse_address, parse_csv,
)


class TestDetectMapping:
    def test_saasquatch_headers(self):
        headers = ["Company", "Industry", "Address", "City", "State",
                    "Zip", "Phone", "Website", "BBB Rating", "Estimated Revenue"]
        mapping = detect_mapping(headers)
        assert mapping["company_name"].source_column == "Company"
        assert mapping["industry"].source_column == "Industry"
        assert mapping["estimated_revenue"].source_column == "Estimated Revenue"

    def test_alternate_headers(self):
        headers = ["Business Name", "Sector", "Street Address", "Tel", "Domain"]
        mapping = detect_mapping(headers)
        assert mapping["company_name"].source_column == "Business Name"
        assert mapping["website"].source_column == "Domain"


class TestParseRevenue:
    @pytest.mark.parametrize("raw,expected", [
        ("$1.2M", 1_200_000),
        ("$1,200,000", 1_200_000),
        ("2.5M", 2_500_000),
        ("500K", 500_000),
        ("$500K", 500_000),
        ("750000", 750_000),
        ("", None),
        ("N/A", None),
    ])
    def test_parse_revenue(self, raw, expected):
        result = parse_revenue_string(raw)
        if expected is None:
            assert result is None
        else:
            assert result == pytest.approx(expected, rel=0.01)


class TestParseAddress:
    def test_full_address(self):
        parts = parse_address("123 Main St, Los Angeles, CA 90001")
        assert parts["street"] == "123 Main St"
        assert parts["city"] == "Los Angeles"
        assert parts["state"] == "CA"
        assert parts["zip"] == "90001"


class TestParseCsv:
    def test_sample_csv(self):
        csv_content = (
            "Company,City,State,Zip,Industry,Estimated Revenue\n"
            "Bob's HVAC LLC,Phoenix,AZ,85001,HVAC,$1.5M\n"
            "Smith Plumbing Inc,Tucson,AZ,85701,Plumbing,$800K\n"
        )
        rows, mapping = parse_csv(csv_content)
        assert len(rows) == 2
        assert rows[0].company_name == "Bob's HVAC LLC"
        assert rows[0].state == "AZ"
        assert rows[1].estimated_revenue == "$800K"
