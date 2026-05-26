"""Tests for the forecast renderer module."""

import pytest
from sim_user_insights.scripts.forecast_renderer import (
    render_forecast,
    build_historical_timeline,
)
from sim_user_insights.scripts.forecast_engine import ForecastResult, ForecastPoint


class FakeSummary:
    """Minimal fake HistoricalMealSummary for testing."""
    def __init__(self, matches_found=0, avg_peak_delta_mgdl=None, avg_peak_time_minutes=None):
        self.matches_found = matches_found
        self.avg_peak_delta_mgdl = avg_peak_delta_mgdl
        self.avg_peak_time_minutes = avg_peak_time_minutes


def test_render_forecast_basic():
    """Should render a forecast with no historical timeline."""
    forecast = ForecastResult(
        baseline_mg_dl=100,
        peak_mg_dl=140,
        peak_time_minutes=120,
        forecast_points=[
            ForecastPoint(hour=1, glucose_mg_dl=105),
            ForecastPoint(hour=2, glucose_mg_dl=130),
            ForecastPoint(hour=3, glucose_mg_dl=135),
            ForecastPoint(hour=4, glucose_mg_dl=115),
        ]
    )
    
    result = render_forecast(forecast)
    assert "Glucose Forecast" in result
    assert "1hr" in result
    assert "105 mg/dL" in result
    assert "130 mg/dL" in result
    assert "baseline" in result
    assert "predicted peak" in result


def test_render_forecast_with_historical():
    """Should include historical averages when provided."""
    forecast = ForecastResult(
        baseline_mg_dl=100,
        peak_mg_dl=140,
        peak_time_minutes=120,
        forecast_points=[
            ForecastPoint(hour=1, glucose_mg_dl=105),
            ForecastPoint(hour=2, glucose_mg_dl=130),
        ]
    )
    
    historical = [
        {"hours_after_meal": 1, "avg_glucose_rise_mgdl": 15.0},
        {"hours_after_meal": 2, "avg_glucose_rise_mgdl": 30.0},
    ]
    
    result = render_forecast(forecast, historical)
    assert "hist~avg +15 mg/dL" in result
    assert "hist~avg +30 mg/dL" in result


def test_render_forecast_no_points():
    """Should handle forecast with no points gracefully."""
    forecast = ForecastResult(
        baseline_mg_dl=100,
        peak_mg_dl=100,
        peak_time_minutes=0,
        forecast_points=[]
    )
    
    result = render_forecast(forecast)
    assert "No forecast data available" in result  # First check triggers this message


def test_render_forecast_outside_1_4_hour_window():
    """Should only show 1-4 hour points."""
    forecast = ForecastResult(
        baseline_mg_dl=100,
        peak_mg_dl=140,
        peak_time_minutes=120,
        forecast_points=[
            ForecastPoint(hour=6, glucose_mg_dl=150),  # Outside 1-4hr window
            ForecastPoint(hour=1, glucose_mg_dl=105),   # Inside
        ]
    )
    
    result = render_forecast(forecast)
    assert "1hr" in result
    assert "6hr" not in result


def test_build_historical_timeline_empty():
    """Should return empty list for no matches."""
    summary = FakeSummary(matches_found=0)
    result = build_historical_timeline(summary)
    assert result == []


def test_build_historical_timeline_with_data():
    """Should build timeline points for hours 1-4."""
    summary = FakeSummary(
        matches_found=5,
        avg_peak_delta_mgdl=60,
        avg_peak_time_minutes=90
    )
    
    result = build_historical_timeline(summary)
    assert len(result) == 4
    
    hours = [p["hours_after_meal"] for p in result]
    assert hours == [1, 2, 3, 4]
    
    # At 90 min peak, hour 1 should be before peak (rising)
    # Hour 2 should be at/after peak (peak at 1.5hr)
    for pt in result:
        assert "avg_glucose_rise_mgdl" in pt


def test_build_historical_timeline_none_summary():
    """Should handle None summary gracefully."""
    result = build_historical_timeline(None)
    assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])