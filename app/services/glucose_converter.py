"""Glucose unit conversion utilities.

UK uses mmol/L. US uses mg/dL.
Conversion: mg/dL ÷ 18.0182 = mmol/L
"""

MGDL_TO_MMOL = 18.0182


def to_mmol(mgdl: float, decimals: int = 1) -> float:
    """Convert mg/dL to mmol/L."""
    return round(mgdl / MGDL_TO_MMOL, decimals)


def to_mgdl(mmol: float) -> float:
    """Convert mmol/L to mg/dL."""
    return round(mmol * MGDL_TO_MMOL, 1)


def format_glucose(value_mgdl: float, unit: str = "mg/dL") -> str:
    """Format a glucose value in the requested unit.
    
    Args:
        value_mgdl: Glucose value in mg/dL
        unit: "mg/dL" or "mmol/L"
        
    Returns:
        Formatted string like "126 mg/dL" or "7.0 mmol/L"
    """
    if unit == "mmol/L":
        return f"{to_mmol(value_mgdl)} mmol/L"
    return f"{int(round(value_mgdl))} mg/dL"