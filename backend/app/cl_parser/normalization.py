MM_PER_INCH = 25.4


def convert_value(value: float, source_units: str, target_units: str) -> float:
    if source_units == target_units:
        return value
    if source_units == "inch" and target_units == "mm":
        return value * MM_PER_INCH
    if source_units == "mm" and target_units == "inch":
        return value / MM_PER_INCH
    raise ValueError("Units could not be normalized")
