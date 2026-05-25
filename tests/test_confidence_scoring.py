"""Tests for the Confidence Scoring Service."""

import pytest
from app.services.confidence_scoring_service import (
    compute_confidence,
    score_and_narrate,
    _score_food_provenance,
    _score_historical_match,
    FoodProvenanceInput,
    HistoricalMatchInput,
    ConfidenceResult,
)


class TestFoodProvenanceScoring:
    def test_verified_barcode_high_score(self):
        fp = FoodProvenanceInput(
            has_barcode=True,
            trust_tier="verified",
            serving_certainty=0.9,
            quality_flag_count=0,
        )
        score = _score_food_provenance(fp)
        assert 0.7 <= score <= 1.0

    def test_estimated_no_barcode_low_score(self):
        fp = FoodProvenanceInput(
            has_barcode=False,
            trust_tier="estimated",
            serving_certainty=0.3,
            quality_flag_count=2,
        )
        score = _score_food_provenance(fp)
        assert score <= 0.6

    def test_missing_nutrients_penalized(self):
        fp_complete = FoodProvenanceInput(has_carbs=True, has_calories=True, has_fat=True, has_protein=True)
        fp_missing = FoodProvenanceInput(has_carbs=True, has_calories=False, has_fat=False, has_protein=False)
        assert _score_food_provenance(fp_complete) > _score_food_provenance(fp_missing)

    def test_quality_flags_penalize(self):
        fp_clean = FoodProvenanceInput(quality_flag_count=0)
        fp_dirty = FoodProvenanceInput(quality_flag_count=5)
        assert _score_food_provenance(fp_clean) > _score_food_provenance(fp_dirty)

    def test_score_clamped(self):
        fp = FoodProvenanceInput(
            has_barcode=True,
            trust_tier="verified",
            serving_certainty=1.0,
            quality_flag_count=0,
            has_carbs=True, has_calories=True, has_fat=True, has_protein=True,
        )
        score = _score_food_provenance(fp)
        assert 0.0 <= score <= 1.0


class TestHistoricalMatchScoring:
    def test_no_matches_zero_score(self):
        hm = HistoricalMatchInput(match_count=0)
        assert _score_historical_match(hm) == 0.0

    def test_many_matches_high_score(self):
        hm = HistoricalMatchInput(
            match_count=15,
            avg_similarity_score=0.9,
            has_peak_delta_data=True,
            has_peak_time_data=True,
            peak_delta_consistency=0.15,
        )
        score = _score_historical_match(hm)
        assert score >= 0.6

    def test_few_matches_moderate_score(self):
        hm = HistoricalMatchInput(
            match_count=3,
            avg_similarity_score=0.6,
            has_peak_delta_data=False,
            has_peak_time_data=False,
        )
        score = _score_historical_match(hm)
        assert 0.1 < score < 0.8

    def test_consistent_peaks_better(self):
        hm_consistent = HistoricalMatchInput(
            match_count=10,
            avg_similarity_score=0.7,
            has_peak_delta_data=True,
            peak_delta_consistency=0.1,
        )
        hm_inconsistent = HistoricalMatchInput(
            match_count=10,
            avg_similarity_score=0.7,
            has_peak_delta_data=True,
            peak_delta_consistency=0.9,
        )
        assert _score_historical_match(hm_consistent) > _score_historical_match(hm_inconsistent)

    def test_cgm_data_boosts_score(self):
        hm_with_cgm = HistoricalMatchInput(match_count=5, avg_similarity_score=0.5, has_peak_delta_data=True, has_peak_time_data=True)
        hm_no_cgm = HistoricalMatchInput(match_count=5, avg_similarity_score=0.5)
        assert _score_historical_match(hm_with_cgm) > _score_historical_match(hm_no_cgm)


class TestComputeConfidence:
    def test_high_confidence_all_good(self):
        result = compute_confidence(
            food_provenance=FoodProvenanceInput(
                has_barcode=True,
                trust_tier="verified",
                serving_certainty=0.9,
            ),
            historical_match=HistoricalMatchInput(
                match_count=12,
                avg_similarity_score=0.85,
                has_peak_delta_data=True,
                has_peak_time_data=True,
                peak_delta_consistency=0.2,
            ),
        )
        assert result.tier == "high"
        assert result.overall_score >= 0.6
        assert "high" in result.tier

    def test_low_confidence_no_history(self):
        result = compute_confidence()
        assert result.tier == "low"
        assert result.overall_score < 0.5
        assert result.narrative

    def test_moderate_confidence_some_history(self):
        result = compute_confidence(
            historical_match=HistoricalMatchInput(
                match_count=4,
                avg_similarity_score=0.6,
            ),
        )
        assert result.tier in ("low", "moderate")
        assert result.narrative

    def test_narrative_mentions_match_count(self):
        result = compute_confidence(
            historical_match=HistoricalMatchInput(match_count=5),
        )
        assert "5 similar meals" in result.narrative

    def test_narrative_mentions_no_matches(self):
        result = compute_confidence(
            historical_match=HistoricalMatchInput(match_count=0),
        )
        assert "No exact matches" in result.narrative

    def test_components_are_decomposed(self):
        result = compute_confidence(
            food_provenance=FoodProvenanceInput(trust_tier="verified", has_barcode=True),
            historical_match=HistoricalMatchInput(match_count=5),
        )
        assert "food_provenance" in result.components
        assert "historical_match" in result.components
        assert 0.0 <= result.components["food_provenance"] <= 1.0

    def test_recommendations_generated_for_low_confidence(self):
        result = compute_confidence()
        assert len(result.recommendations) >= 1
        assert any("Log this meal" in r for r in result.recommendations)

    def test_recommendations_generated_for_quality_flags(self):
        result = compute_confidence(
            food_provenance=FoodProvenanceInput(quality_flag_count=3),
        )
        quality_recs = [r for r in result.recommendations if "quality flags" in r]
        assert len(quality_recs) >= 1


class TestScoreAndNarrate:
    def test_convenience_function(self):
        result = score_and_narrate(
            match_count=8,
            avg_similarity=0.75,
            has_barcode=True,
            trust_tier="official",
        )
        assert isinstance(result, ConfidenceResult)
        assert result.overall_score > 0
        assert result.tier in ("low", "moderate", "high")

    def test_convenience_low_data(self):
        result = score_and_narrate(match_count=0)
        assert result.tier == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])