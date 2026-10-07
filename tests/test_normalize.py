import pytest
from groundtruth.normalize import normalize_name


CASES = [
    ("Bob's HVAC, LLC", "BOBS HEATING VENTILATION AIR CONDITIONING"),
    ("BOBS HVAC L L C", "BOBS HEATING VENTILATION AIR CONDITIONING"),
    # Actually HVAC is not in abbreviation map - it stays as HVAC
    # Let me fix the test cases to be realistic
]

# Corrected cases
NORMALIZE_CASES = [
    # Basic legal suffix removal
    ("Smith & Sons Plumbing Inc", "SMITH AND SONS PLUMBING"),  # Wait AND is in suffix list
]

# Let me think about this more carefully. The prompt says to remove AND and &.
# But "Smith & Sons" -> "SMITH AND SONS" -> remove AND -> "SMITH SONS"
# That's wrong. Let me re-read: the prompt says remove "AND/&" as noise tokens.
# In practice "Smith & Sons" losing AND is bad. Let me look at the prompt again:
# "remove legal suffixes and noise tokens: INC ... AND/& ..."
# This means remove standalone AND or & as noise. But in "Smith & Sons" the & is
# meaningful. The normalize function replaces & with AND then removes AND tokens.
# This could be problematic but matches the spec. Let's test what the code does.


@pytest.mark.parametrize("raw,expected", [
    # Basic cleanup
    ("Bob's HVAC, LLC", "BOBS HVAC"),
    ("BOBS HVAC L.L.C.", "BOBS HVAC"),
    # Legal suffix removal
    ("ACME Plumbing Inc", "ACME PLUMBING"),
    ("ACME Plumbing Inc.", "ACME PLUMBING"),
    ("Johnson Corp.", "JOHNSON"),
    ("The Johnson Corporation", "JOHNSON"),
    # Abbreviation expansion
    ("ABC Mfg Co", "ABC MANUFACTURING"),
    ("XYZ Constr LLC", "XYZ CONSTRUCTION"),
    ("Smith Svcs Inc", "SMITH SERVICES"),
    ("Premier Mgmt Group", "PREMIER MANAGEMENT GROUP"),
    ("National Equip Ltd", "NATIONAL EQUIPMENT"),
    # & handling (replaced with AND, then AND removed as noise)
    ("Smith & Sons Plumbing Inc", "SMITH SONS PLUMBING"),
    # Whitespace and punctuation
    ("  ACME   Plumbing   ", "ACME PLUMBING"),
    ("A.B.C. Services", "B C SERVICES"),
    # L.L.C. variations
    ("Test L.L.C.", "TEST"),
    ("Test L L C", "TEST"),
    # DBA handling
    ("John Smith DBA Smith Heating", "JOHN SMITH SMITH HEATING"),
    # Empty / None-like
    ("", ""),
    # Multi abbreviation
    ("ABC Mfg & Constr Svcs", "ABC MANUFACTURING CONSTRUCTION SERVICES"),
    # Preserves non-suffix tokens
    ("RIVERSIDE LANDSCAPING LLC", "RIVERSIDE LANDSCAPING"),
    # LP removal
    ("ACME Partners LP", "ACME PARTNERS"),
])
def test_normalize_name(raw: str, expected: str):
    result = normalize_name(raw)
    assert result.normalized == expected, f"normalize({raw!r}) = {result.normalized!r}, expected {expected!r}"


@pytest.mark.parametrize("raw,expected_tokens", [
    ("Bob's HVAC, LLC", {"BOBS", "HVAC"}),
    ("Smith Svcs Inc", {"SMITH", "SERVICES"}),
])
def test_normalize_tokens(raw: str, expected_tokens: set[str]):
    result = normalize_name(raw)
    assert result.tokens == frozenset(expected_tokens)


def test_normalize_empty():
    result = normalize_name("")
    assert result.normalized == ""
    assert result.tokens == frozenset()


def test_normalize_deterministic():
    a = normalize_name("Bob's HVAC LLC")
    b = normalize_name("Bob's HVAC LLC")
    assert a == b
    assert a.normalized == b.normalized
    assert a.tokens == b.tokens
