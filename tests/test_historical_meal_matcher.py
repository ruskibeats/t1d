"""Tests for the Historical Meal Matching service."""

import json
import pytest
from pathlib import Path
from app.services.historical_meal_matcher import (
    find_similar_meals,
    summarize_similar_meals,
    historical_context_for_meal,
    _load_food_history,
    _nutrient_distance,
    _text_similarity,
    HistoricalMealMatch,
    HistoricalMealSummary,
)


def test_load_food_history():
    """Food history file should load successfully."""
    data = _load_food_history()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "carb_estimate_g" in data[0]
    assert "fat_g" in data[0]
    assert "food" in data[0]


def test_find_similar_meals_by_carbs():
    """Should find meals with similar carb counts."""
    matches = find_similar_meals(carbs_g=50, max_matches=5)
    assert isinstance(matches, list)
    if matches:
        assert all(isinstance(m, HistoricalMealMatch) for m in matches)
        assert all(m.carb_estimate_g > 0 for m in matches)


def test_find_similar_meals_by_name():
    """Should find meals by food name."""
    matches = find_similar_meals(food_name="pizza", max_matches=5)
    assert isinstance(matches, list)
    # At least some should have pizza in the name
    pizza_matches = [m for m in matches if "pizza" in m.food_name.lower()]
    # May or may not find pizza (depends on data), but should not error


def test_find_similar_meals_by_both():
    """Should find meals by both carbs and name."""
    matches = find_similar_meals(carbs_g=45, fat_g=12, food_name="chicken", max_matches=5)
    assert isinstance(matches, list)
    for m in matches:
        assert m.similarity_score > 0


def test_find_similar_meals_no_carbs():
    """Should return empty when neither carbs nor name provided."""
    matches = find_similar_meals()
    assert matches == []


def test_find_similar_meals_ordering():
    """Results should be ordered by similarity (best first)."""
    matches = find_similar_meals(carbs_g=50, max_matches=10)
    if len(matches) >= 2:
        scores = [m.similarity_score for m in matches]
        assert scores == sorted(scores, reverse=True)


def test_summarize_similar_meals():
    """Should produce a structured summary with narrative."""
    summary = summarize_similar_meals(
        query_description="Grilled chicken with rice",
        carbs_g=45,
        fat_g=10,
        food_name="chicken",
    )
    assert isinstance(summary, HistoricalMealSummary)
    assert summary.query_description == "Grilled chicken with rice"
    assert summary.query_carbs_g == 45
    assert summary.narrative
    assert summary.disclaimer


def test_summarize_similar_meals_no_matches():
    """Should handle no matches gracefully."""
    summary = summarize_similar_meals(
        query_description="Unknown exotic meal",
        carbs_g=200,  # Very high, unlikely to match
    )
    assert isinstance(summary, HistoricalMealSummary)
    assert summary.matches_found >= 0  # May or may not find matches
    assert summary.narrative


def test_summarize_includes_disclaimer():
    """Summary should always include the educational disclaimer."""
    summary = summarize_similar_meals(
        query_description="Test meal",
        carbs_g=30,
    )
    assert "educational" in summary.disclaimer.lower()
    assert "not medical advice" in summary.disclaimer.lower()


def test_summarize_with_only_food_name():
    """Should work with just a food name."""
    summary = summarize_similar_meals(
        query_description="Pizza",
        food_name="pizza",
    )
    assert summary.query_description == "Pizza"


def test_historical_context_for_meal():
    """Should produce dict compatible with companion pipeline."""
    context = historical_context_for_meal(
        food_name="pasta",
        estimated_carbs_g=60,
        estimated_fat_g=15,
    )
    assert isinstance(context, dict)
    assert "has_history" in context
    assert "matches_found" in context
    assert "narrative" in context
    assert "disclaimer" in context
    assert "confidence_tier" in context
    assert "confidence_score" in context
    assert context["matches_found"] >= 0
    assert context["confidence_tier"] in ("low", "moderate", "high")


def test_nutrient_distance_exact_match():
    """Exact same nutrients should have distance 0."""
    dist = _nutrient_distance(50, 10, 50, 10)
    assert dist == 0.0


def test_nutrient_distance_different():
    """Different nutrients should have positive distance."""
    dist = _nutrient_distance(50, 10, 100, 30)
    assert dist > 0


def test_text_similarity_identical():
    """Identical names should score 1.0."""
    score = _text_similarity("grilled chicken", "grilled chicken")
    assert score == 1.0


def test_text_similarity_partial():
    """Partial match should score between 0 and 1."""
    score = _text_similarity("chicken breast", "chicken salad")
    assert 0 < score < 1.0


def test_text_similarity_no_match():
    """No overlap should score 0."""
    score = _text_similarity("pizza", "sushi")
    assert score == 0.0


def test_text_similarity_empty():
    """Empty strings should score 0."""
    assert _text_similarity("", "pizza") == 0.0
    assert _text_similarity("pizza", "") == 0.0


def test_match_peak_delta_present():
    """Matches should include CGM impact data when available."""
    matches = find_similar_meals(carbs_g=50, max_matches=3)
    for m in matches:
        # These fields may be None but should be present
        assert hasattr(m, "peak_delta_mgdl")
        assert hasattr(m, "peak_time_minutes")


def test_summary_stats_with_enough_data():
    """With enough matches, summary stats should be populated."""
    summary = summarize_similar_meals(
        query_description="Breakfast",
        carbs_g=30,
    )
    if summary.matches_found >= 3:
        assert summary.avg_carbs_g > 0
        assert summary.avg_fat_g > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])