"""Mapeamento de siglas de disciplina pra nomes plenos."""

DISCIPLINE_ALIASES: dict[str, str] = {
    "ELE": "Elétrico",
    "HID": "Hidráulico",
    "HIS": "Hidráulico",
    "PCI": "Preventivo",
    "CLI": "Climatização",
    "COM": "Comunicação",
    "SDR": "Sanitário/Drenagem",
    "SAN": "Sanitário",
    "SPDA": "SPDA",
    "FUR": "Furação",
    "PIS": "Piscina",
}


def all_discipline_codes() -> list[str]:
    return list(DISCIPLINE_ALIASES.keys())


def normalize_discipline(value: str | None) -> str | None:
    if value is None:
        return None
    upper = value.strip().upper()
    if not upper:
        return None
    if upper in DISCIPLINE_ALIASES:
        return upper
    for code, full in DISCIPLINE_ALIASES.items():
        if upper == full.upper():
            return code
    return None


def discipline_full_name(code: str) -> str:
    return DISCIPLINE_ALIASES.get(code.upper(), code)
