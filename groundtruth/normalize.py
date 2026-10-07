import re
from dataclasses import dataclass


LEGAL_SUFFIXES = {
    "INC", "INCORPORATED", "LLC", "LC", "CORP", "CORPORATION",
    "CO", "COMPANY", "LTD", "LIMITED", "LP", "LLP", "PLLC", "PC",
    "PA", "DBA", "THE", "AND", "A",
}

ABBREVIATION_MAP = {
    "HTG": "HEATING",
    "HTNG": "HEATING",
    "SVCS": "SERVICES",
    "SVC": "SERVICE",
    "SRVCS": "SERVICES",
    "MFG": "MANUFACTURING",
    "CONSTR": "CONSTRUCTION",
    "CONSTRCTN": "CONSTRUCTION",
    "ASSOC": "ASSOCIATES",
    "ASSOCS": "ASSOCIATES",
    "MGMT": "MANAGEMENT",
    "INTL": "INTERNATIONAL",
    "NATL": "NATIONAL",
    "GRP": "GROUP",
    "EQUIP": "EQUIPMENT",
    "PLBG": "PLUMBING",
    "PLMB": "PLUMBING",
    "ELEC": "ELECTRIC",
    "MECH": "MECHANICAL",
    "VENT": "VENTILATION",
    "CLN": "CLEANING",
    "CLNG": "CLEANING",
    "MAINT": "MAINTENANCE",
    "MNTNC": "MAINTENANCE",
    "LANDSCP": "LANDSCAPING",
    "LDSCP": "LANDSCAPING",
    "DNTL": "DENTAL",
    "MED": "MEDICAL",
    "HOSP": "HOSPITAL",
    "GOVT": "GOVERNMENT",
    "TECH": "TECHNOLOGY",
    "ENVRNMNTL": "ENVIRONMENTAL",
    "ENVIRON": "ENVIRONMENTAL",
    "ENGRG": "ENGINEERING",
    "ENGR": "ENGINEERING",
    "AUTO": "AUTOMOTIVE",
    "TRANSP": "TRANSPORTATION",
    "TRANSPT": "TRANSPORTATION",
    "RSTRNT": "RESTAURANT",
    "REST": "RESTAURANT",
    "PROPS": "PROPERTIES",
    "PROP": "PROPERTY",
    "DEV": "DEVELOPMENT",
    "CTR": "CENTER",
    "CNTR": "CENTER",
}

_PUNCT_RE = re.compile(r"[^\w\s]")
_MULTI_SPACE_RE = re.compile(r"\s+")
_LLC_DOTS_RE = re.compile(r"\bL\s*\.?\s*L\s*\.?\s*C\s*\.?\b", re.IGNORECASE)
_APOSTROPHE_S_RE = re.compile(r"'[Ss]\b")


@dataclass(frozen=True)
class NormalizedName:
    normalized: str
    tokens: frozenset[str]


def normalize_name(raw: str) -> NormalizedName:
    if not raw:
        return NormalizedName(normalized="", tokens=frozenset())

    name = raw.strip()
    name = _APOSTROPHE_S_RE.sub("S", name)
    name = name.upper()
    name = _LLC_DOTS_RE.sub("LLC", name)
    name = name.replace("&", " AND ")
    name = _PUNCT_RE.sub(" ", name)
    name = _MULTI_SPACE_RE.sub(" ", name).strip()

    tokens = name.split()
    tokens = [t for t in tokens if t not in LEGAL_SUFFIXES]
    tokens = [ABBREVIATION_MAP.get(t, t) for t in tokens]

    normalized = " ".join(tokens)
    return NormalizedName(
        normalized=normalized,
        tokens=frozenset(tokens),
    )
