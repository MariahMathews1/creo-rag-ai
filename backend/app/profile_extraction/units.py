UNIT_ALIASES = {
    "in": "inch", "inches": "inch", "inch": "inch", "mm": "mm",
    "rpm": "rpm", "ipm": "ipm", "in/min": "ipm",
    "inch/min": "ipm", "inches/min": "ipm",
    "inch per minute": "ipm", "inches per minute": "ipm",
    "mm/min": "mm/min", "mm per min": "mm/min",
    "hp": "hp", "kw": "kW", "n·m": "N·m", "nm": "N·m",
    "lb-ft": "lb-ft", "kg": "kg", "kilograms": "kg",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "degree": "degrees", "degrees": "degrees", "deg": "degrees",
    "degree/min": "degrees/min", "degrees/min": "degrees/min", "deg/min": "degrees/min",
}


def normalize_unit(raw: str | None) -> str | None:
    if raw is None:
        return None
    return UNIT_ALIASES.get(raw.strip().lower())


def normalize_physical_value(value: float, unit: str | None) -> dict:
    normalized_unit = normalize_unit(unit)
    normalized = value
    formula = "identity"
    if normalized_unit == "inch":
        normalized, normalized_unit, formula = value * 25.4, "mm", "inch × 25.4"
    elif normalized_unit == "ipm":
        normalized, normalized_unit, formula = value * 25.4, "mm/min", "ipm × 25.4"
    elif normalized_unit == "hp":
        normalized, normalized_unit, formula = value * 0.745699872, "kW", "hp × 0.745699872"
    return {
        "original_value": value, "original_unit": normalize_unit(unit),
        "normalized_value": round(normalized, 6),
        "normalized_unit": normalized_unit, "conversion_formula": formula,
    }
