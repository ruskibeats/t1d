#!/usr/bin/env python3
"""Forecast visualization module for T1D Companion.

Extracted from companion_pipeline_v2.py to provide a clean seam for
rendering glucose forecasts with historical context.

This module is testable in isolation - just call render_forecast() with
fake ForecastResult and historical timeline data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Dict, Optional


@dataclass
class GlucoseTimelinePoint:
    """Single point on the glucose timeline."""
    hours_after_meal: int
    avg_glucose_rise_mgdl: float


def build_historical_timeline(summary: Any) -> List[Dict[str, Any]]:
    """Build time-relative glucose points from historical meal matches.
    
    Returns points for 1, 2, 3, 4 hours post-meal showing average rise.
    
    Args:
        summary: HistoricalMealSummary from the matcher (or None)
        
    Returns:
        List of dicts with hours_after_meal and avg_glucose_rise_mgdl
    """
    if not summary or not summary.matches_found or not summary.avg_peak_delta_mgdl:
        return []
    
    peak_min = summary.avg_peak_time_minutes or 90
    peak_hr = peak_min / 60
    
    timeline = []
    for hour_offset in [1, 2, 3, 4]:
        # Approximate the rise curve
        if hour_offset >= peak_hr:
            ratio = max(0, 1 - (hour_offset - peak_hr) / (peak_hr + 2))
        else:
            ratio = max(0, hour_offset / (peak_hr + 1))
        
        rise = summary.avg_peak_delta_mgdl * ratio
        timeline.append({
            "hours_after_meal": hour_offset,
            "avg_glucose_rise_mgdl": round(rise, 1),
        })
    
    return timeline


def render_forecast(forecast: Any, historical_timeline: Optional[List[Dict]] = None) -> str:
    """Render an ASCII graph of forecast and historical glucose over time.
    
    Shows 1-4 hours post-meal for the insulin action window.
    
    Args:
        forecast: ForecastResult object with forecast_points
        historical_timeline: Optional list of historical timeline points
        
    Returns:
        Formatted ASCII string ready for output
    """
    lines = []
    lines.append("\n📈 Glucose Forecast (1-4 hours post-meal)")
    lines.append("─" * 50)
    
    if not forecast or not forecast.forecast_points:
        lines.append("  (No forecast data available)")
        return "\n".join(lines)
    
    baseline = forecast.baseline_mg_dl
    peak = forecast.peak_mg_dl
    
    # Filter to 1-4 hour points
    points = [p for p in forecast.forecast_points if 1 <= p.hour <= 4]
    
    if not points:
        lines.append("  (No forecast points for 1-4 hour window)")
        return "\n".join(lines)
    
    # Build graph - scale to fit ~30 chars
    chart_width = 30
    max_val = max(peak, baseline + 50)
    min_val = max(50, baseline - 20)
    range_val = max_val - min_val
    
    for pt in points:
        hr = pt.hour
        g = pt.glucose_mg_dl
        
        hist_rise = None
        if historical_timeline:
            for ht in historical_timeline:
                if ht["hours_after_meal"] == hr:
                    hist_rise = ht["avg_glucose_rise_mgdl"]
                    break
        
        pos = int((g - min_val) / range_val * chart_width) if range_val > 0 else chart_width // 2
        pos = max(0, min(chart_width, pos))
        
        bar = "█" * pos + "▌" + "─" * (chart_width - pos)
        hist_str = f" | hist curve +{int(hist_rise)} mg/dL" if hist_rise else ""
        
        lines.append(f"  {hr}hr: {g:3.0f} mg/dL |{bar}|{hist_str}")
    
    lines.append(f"  {'baseline':7} |{baseline} mg/dL")
    lines.append(f"  {'predicted peak':7} |{peak} mg/dL @ {forecast.peak_time_minutes} min")
    if getattr(forecast, "uncertainty_band", None):
        band = forecast.uncertainty_band
        lines.append(
            f"  {'forecast range':7} |{band.peak_range_mg_dl[0]}–{band.peak_range_mg_dl[1]} mg/dL "
            f"@ {band.peak_time_range_minutes[0]}–{band.peak_time_range_minutes[1]} min"
        )
    
    # Do not average the approximated timeline points here: the true historical
    # peak-rise statistic is reported separately in the narrative/summary. An
    # average of the 1-4h curve samples is not the same clinical quantity and can
    # conflict with "avg peak rise" (e.g. +42 vs +74 mg/dL).
    
    lines.append("─" * 50)
    lines.append("  (Educational simulation only — actual results vary)")
    
    return "\n".join(lines)