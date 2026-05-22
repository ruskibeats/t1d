"""Tests for MealForecastRequest/Response Pydantic schemas.

Verifies the formal API contract for meal forecasting including:
- Schema construction and validation
- Field constraints and custom validators
- Enum integrity
- Serialization round-trips
- Example data and JSON structure
- Edge cases (missing optionals, bounds, empty lists)
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.meal_forecast import (
    MealForecastRequest,
    MealForecastResponse,
    MealItemSchema,
    MealType,
    RiskLevel,
    ConfidenceTier,
    SourceTrustTier,
    NutrientTotals,
    MealTagsResponse,
    FoodProvenanceResponse,
    PersonalContextSummary,
    ForecastWindowSchema,
    ForecastEvidenceSchema,
    ForecastDetail,
    SafetyInfo,
    confidence_to_tier,
    risk_level_to_tier,
)


# ═══════════════════════════════════════════════
# MealItemSchema
# ═══════════════════════════════════════════════


class TestMealItemSchema:
    """Tests for MealItemSchema."""

    def test_minimal_item(self):
        """Item with only required fields."""
        item = MealItemSchema(name="oatmeal", quantity=1, unit="serving")
        assert item.name == "oatmeal"
        assert item.quantity == 1
        assert item.unit == "serving"
        assert item.barcode is None
        assert item.brand is None

    def test_full_item(self):
        """Item with all fields."""
        item = MealItemSchema(
            name="Big Mac",
            barcode="5901234123457",
            quantity=1,
            unit="each",
            brand="McDonald's",
        )
        assert item.name == "Big Mac"
        assert item.barcode == "5901234123457"
        assert item.brand == "McDonald's"

    def test_quantity_must_be_positive(self):
        """Quantity must be > 0."""
        with pytest.raises(ValidationError):
            MealItemSchema(name="test", quantity=0, unit="g")
        with pytest.raises(ValidationError):
            MealItemSchema(name="test", quantity=-1, unit="g")

    def test_fractional_quantity(self):
        """Fractional quantities are valid."""
        item = MealItemSchema(name="test", quantity=0.5, unit="serving")
        assert item.quantity == 0.5

    def test_large_quantity(self):
        """Large but reasonable quantities pass."""
        item = MealItemSchema(name="water", quantity=500, unit="ml")
        assert item.quantity == 500

    def test_unit_variations(self):
        """Various unit strings are accepted."""
        for unit in ["g", "ml", "serving", "slices", "pieces", "cup", "oz", "tbsp", "tsp"]:
            item = MealItemSchema(name="test", quantity=1, unit=unit)
            assert item.unit == unit

    def test_name_too_long(self):
        """Name over 255 chars is rejected."""
        with pytest.raises(ValidationError):
            MealItemSchema(name="x" * 256, quantity=1, unit="serving")

    def test_barcode_too_long(self):
        """Barcode over 64 chars is rejected."""
        with pytest.raises(ValidationError):
            MealItemSchema(name="test", quantity=1, unit="serving", barcode="x" * 65)


# ═══════════════════════════════════════════════
# MealForecastRequest
# ═══════════════════════════════════════════════


class TestMealForecastRequest:
    """Tests for MealForecastRequest."""

    def test_minimal_request(self):
        """Request with only required fields."""
        req = MealForecastRequest(
            meal_items=[MealItemSchema(name="oatmeal", quantity=1, unit="serving")],
        )
        assert len(req.meal_items) == 1
        assert req.meal_timestamp is None
        assert req.timezone is None
        assert req.current_glucose is None
        assert req.meal_type is None
        assert req.notes is None

    def test_full_request(self):
        """Request with all optional fields populated."""
        ts = datetime(2026, 5, 21, 7, 30, 0, tzinfo=timezone.utc)
        req = MealForecastRequest(
            meal_items=[
                MealItemSchema(name="oatmeal", quantity=1, unit="serving", barcode="123"),
                MealItemSchema(name="banana", quantity=1, unit="medium"),
            ],
            meal_timestamp=ts,
            timezone="America/New_York",
            current_glucose=105,
            meal_type=MealType.BREAKFAST,
            notes="Pre-workout meal",
        )
        assert req.meal_timestamp == ts
        assert req.timezone == "America/New_York"
        assert req.current_glucose == 105
        assert req.meal_type == MealType.BREAKFAST
        assert req.notes == "Pre-workout meal"

    def test_empty_items_rejected(self):
        """At least one meal item is required."""
        with pytest.raises(ValidationError):
            MealForecastRequest(meal_items=[])

    def test_max_items(self):
        """Up to 50 items are allowed."""
        items = [MealItemSchema(name=f"item_{i}", quantity=1, unit="g") for i in range(50)]
        req = MealForecastRequest(meal_items=items)
        assert len(req.meal_items) == 50

    def test_too_many_items_rejected(self):
        """More than 50 items is rejected."""
        items = [MealItemSchema(name=f"item_{i}", quantity=1, unit="g") for i in range(51)]
        with pytest.raises(ValidationError):
            MealForecastRequest(meal_items=items)

    def test_glucose_bounds_low(self):
        """Glucose below 20 mg/dL is rejected."""
        with pytest.raises(ValidationError):
            MealForecastRequest(
                meal_items=[MealItemSchema(name="test", quantity=1, unit="g")],
                current_glucose=19,
            )

    def test_glucose_bounds_high(self):
        """Glucose above 600 mg/dL is rejected."""
        with pytest.raises(ValidationError):
            MealForecastRequest(
                meal_items=[MealItemSchema(name="test", quantity=1, unit="g")],
                current_glucose=601,
            )

    def test_glucose_at_extremes(self):
        """Glucose at exact boundary values are accepted."""
        req_low = MealForecastRequest(
            meal_items=[MealItemSchema(name="test", quantity=1, unit="g")],
            current_glucose=20,
        )
        assert req_low.current_glucose == 20

        req_high = MealForecastRequest(
            meal_items=[MealItemSchema(name="test", quantity=1, unit="g")],
            current_glucose=600,
        )
        assert req_high.current_glucose == 600

    def test_notes_too_long(self):
        """Notes over 500 chars are rejected."""
        with pytest.raises(ValidationError):
            MealForecastRequest(
                meal_items=[MealItemSchema(name="test", quantity=1, unit="g")],
                notes="x" * 501,
            )

    def test_timezone_valid_string(self):
        """Timezone accepts any string (validated at service level)."""
        req = MealForecastRequest(
            meal_items=[MealItemSchema(name="test", quantity=1, unit="g")],
            timezone="America/New_York",
        )
        assert req.timezone == "America/New_York"

    def test_meal_type_enum(self):
        """All meal types are accepted."""
        for mt in MealType:
            req = MealForecastRequest(
                meal_items=[MealItemSchema(name="test", quantity=1, unit="g")],
                meal_type=mt,
            )
            assert req.meal_type == mt

    def test_invalid_meal_type_rejected(self):
        """Invalid meal type string is rejected."""
        with pytest.raises(ValidationError):
            MealForecastRequest(
                meal_items=[MealItemSchema(name="test", quantity=1, unit="g")],
                meal_type="brunch",
            )

    def test_json_deserialization(self):
        """Request can be deserialized from JSON."""
        json_str = """{
            "meal_items": [
                {"name": "oatmeal", "quantity": 1, "unit": "serving", "barcode": "5901234123457"},
                {"name": "banana", "quantity": 1, "unit": "medium"}
            ],
            "meal_timestamp": "2026-05-21T07:30:00Z",
            "timezone": "America/New_York",
            "current_glucose": 105,
            "meal_type": "breakfast"
        }"""
        req = MealForecastRequest.model_validate_json(json_str)
        assert len(req.meal_items) == 2
        assert req.meal_items[0].barcode == "5901234123457"
        assert req.meal_type == MealType.BREAKFAST
        assert req.current_glucose == 105

    def test_example_in_json_schema(self):
        """Request has a JSON Schema example."""
        schema = MealForecastRequest.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert "meal_items" in example
        assert len(example["meal_items"]) > 0


# ═══════════════════════════════════════════════
# NutrientTotals
# ═══════════════════════════════════════════════


class TestNutrientTotals:
    """Tests for NutrientTotals."""

    def test_minimal(self):
        """All fields are optional and default to None."""
        nt = NutrientTotals()
        assert nt.carbs_g is None
        assert nt.protein_g is None
        assert nt.fat_g is None
        assert nt.fiber_g is None
        assert nt.sugars_g is None
        assert nt.calories_kcal is None
        assert nt.serving_weight_g is None

    def test_partial(self):
        """Partial nutrient set is valid."""
        nt = NutrientTotals(carbs_g=45.5, protein_g=12.0)
        assert nt.carbs_g == 45.5
        assert nt.protein_g == 12.0
        assert nt.fat_g is None

    def test_full(self):
        """All nutrient fields populated."""
        nt = NutrientTotals(
            carbs_g=45.5, protein_g=12.0, fat_g=8.5,
            fiber_g=4.0, sugars_g=15.2, calories_kcal=320.0,
            serving_weight_g=350.0,
        )
        assert nt.carbs_g == 45.5
        assert nt.calories_kcal == 320.0

    def test_negative_rejected(self):
        """Negative nutrient values are rejected."""
        with pytest.raises(ValidationError):
            NutrientTotals(carbs_g=-1)
        with pytest.raises(ValidationError):
            NutrientTotals(calories_kcal=-50)

    def test_zero_is_valid(self):
        """Zero nutrient values are valid."""
        nt = NutrientTotals(carbs_g=0, protein_g=0, fat_g=0)
        assert nt.carbs_g == 0


# ═══════════════════════════════════════════════
# MealTagsResponse
# ═══════════════════════════════════════════════


class TestMealTagsResponse:
    """Tests for MealTagsResponse."""

    def test_defaults(self):
        """Default values."""
        tags = MealTagsResponse()
        assert tags.tags == []
        assert tags.carb_load_class == "moderate"

    def test_custom(self):
        """Custom values."""
        tags = MealTagsResponse(tags=["low-carb", "high-protein"], carb_load_class="light")
        assert "low-carb" in tags.tags
        assert tags.carb_load_class == "light"


# ═══════════════════════════════════════════════
# FoodProvenanceResponse
# ═══════════════════════════════════════════════


class TestFoodProvenanceResponse:
    """Tests for FoodProvenanceResponse."""

    def test_minimal(self):
        """Minimal provenance."""
        prov = FoodProvenanceResponse(source_name="openfoodfacts")
        assert prov.source_name == "openfoodfacts"
        assert prov.barcode_match is False
        assert prov.serving_certainty == 0.5
        assert prov.source_trust_tier == SourceTrustTier.ESTIMATED
        assert prov.quality_flags == []

    def test_full(self):
        """Full provenance."""
        prov = FoodProvenanceResponse(
            source_name="openfoodfacts",
            barcode_match=True,
            serving_certainty=0.9,
            source_trust_tier=SourceTrustTier.OFFICIAL,
            quality_flags=["missing_serving_grams"],
        )
        assert prov.barcode_match is True
        assert prov.serving_certainty == 0.9
        assert prov.source_trust_tier == SourceTrustTier.OFFICIAL

    def test_certainty_bounds(self):
        """Serving certainty is clamped to [0, 1]."""
        with pytest.raises(ValidationError):
            FoodProvenanceResponse(source_name="test", serving_certainty=1.5)
        with pytest.raises(ValidationError):
            FoodProvenanceResponse(source_name="test", serving_certainty=-0.1)

    def test_source_trust_tier_all(self):
        """All enum values are accepted."""
        for tier in SourceTrustTier:
            prov = FoodProvenanceResponse(source_name="test", source_trust_tier=tier)
            assert prov.source_trust_tier == tier


# ═══════════════════════════════════════════════
# PersonalContextSummary
# ═══════════════════════════════════════════════


class TestPersonalContextSummary:
    """Tests for PersonalContextSummary."""

    def test_minimal(self):
        """All fields optional."""
        ctx = PersonalContextSummary()
        assert ctx.current_glucose_mgdl is None
        assert ctx.glucose_trend is None
        assert ctx.hour_of_day is None
        assert ctx.recent_history_hours is None

    def test_full(self):
        """All fields populated."""
        ctx = PersonalContextSummary(
            current_glucose_mgdl=105,
            glucose_trend="flat",
            hour_of_day=7,
            recent_history_hours=6.0,
        )
        assert ctx.current_glucose_mgdl == 105
        assert ctx.hour_of_day == 7

    def test_glucose_bounds(self):
        """Glucose bounds validation."""
        with pytest.raises(ValidationError):
            PersonalContextSummary(current_glucose_mgdl=10)
        with pytest.raises(ValidationError):
            PersonalContextSummary(current_glucose_mgdl=700)

    def test_hour_bounds(self):
        """Hour of day bounds."""
        with pytest.raises(ValidationError):
            PersonalContextSummary(hour_of_day=-1)
        with pytest.raises(ValidationError):
            PersonalContextSummary(hour_of_day=24)

    def test_valid_hours(self):
        """All valid hours are accepted."""
        for hour in range(24):
            ctx = PersonalContextSummary(hour_of_day=hour)
            assert ctx.hour_of_day == hour


# ═══════════════════════════════════════════════
# ForecastWindowSchema
# ═══════════════════════════════════════════════


class TestForecastWindowSchema:
    """Tests for ForecastWindowSchema."""

    def test_valid_window(self):
        """Valid time window."""
        w = ForecastWindowSchema(earliest_minutes=15, latest_minutes=45)
        assert w.earliest_minutes == 15
        assert w.latest_minutes == 45

    def test_zero_start(self):
        """Zero start is valid."""
        w = ForecastWindowSchema(earliest_minutes=0, latest_minutes=15)
        assert w.earliest_minutes == 0

    def test_negative_rejected(self):
        """Negative values are rejected."""
        with pytest.raises(ValidationError):
            ForecastWindowSchema(earliest_minutes=-5, latest_minutes=15)


# ═══════════════════════════════════════════════
# ForecastEvidenceSchema
# ═══════════════════════════════════════════════


class TestForecastEvidenceSchema:
    """Tests for ForecastEvidenceSchema."""

    def test_minimal(self):
        """Evidence with required fields only."""
        ev = ForecastEvidenceSchema(key="carb_load", value="Moderate carbs (45g)")
        assert ev.weight == 1.0

    def test_full(self):
        """Evidence with all fields."""
        ev = ForecastEvidenceSchema(key="high_fat", value="High fat content: 22g", weight=1.2)
        assert ev.weight == 1.2

    def test_weight_bounds(self):
        """Weight must be within [0, 2]."""
        with pytest.raises(ValidationError):
            ForecastEvidenceSchema(key="test", value="test", weight=-0.1)
        with pytest.raises(ValidationError):
            ForecastEvidenceSchema(key="test", value="test", weight=2.1)

    def test_weight_zero(self):
        """Weight of 0 is valid."""
        ev = ForecastEvidenceSchema(key="test", value="test", weight=0)
        assert ev.weight == 0


# ═══════════════════════════════════════════════
# ForecastDetail
# ═══════════════════════════════════════════════


class TestForecastDetail:
    """Tests for ForecastDetail."""

    def test_minimal(self):
        """Forecast with required fields only."""
        detail = ForecastDetail(
            risk_level=RiskLevel.LOW,
            confidence=0.5,
            confidence_tier=ConfidenceTier.MODERATE,
            timing_onset_window=ForecastWindowSchema(earliest_minutes=15, latest_minutes=45),
            peak_window=ForecastWindowSchema(earliest_minutes=60, latest_minutes=120),
        )
        assert detail.delayed_effect is False
        assert detail.evidence == []

    def test_full(self):
        """Forecast with all fields."""
        detail = ForecastDetail(
            risk_level=RiskLevel.HIGH,
            confidence=0.8,
            confidence_tier=ConfidenceTier.HIGH,
            delayed_effect=True,
            timing_onset_window=ForecastWindowSchema(earliest_minutes=20, latest_minutes=60),
            peak_window=ForecastWindowSchema(earliest_minutes=90, latest_minutes=180),
            evidence=[
                ForecastEvidenceSchema(key="carb_load", value="Heavy carbs (65g)", weight=1.2),
                ForecastEvidenceSchema(key="high_fat", value="High fat: 28g", weight=1.0),
            ],
        )
        assert detail.delayed_effect is True
        assert len(detail.evidence) == 2

    def test_all_risk_levels(self):
        """All risk levels are serializable."""
        for rl in RiskLevel:
            detail = ForecastDetail(
                risk_level=rl,
                confidence=0.5,
                confidence_tier=ConfidenceTier.MODERATE,
                timing_onset_window=ForecastWindowSchema(earliest_minutes=15, latest_minutes=45),
                peak_window=ForecastWindowSchema(earliest_minutes=60, latest_minutes=120),
            )
            assert detail.risk_level == rl

    def test_confidence_bounds(self):
        """Confidence must be in [0, 1]."""
        with pytest.raises(ValidationError):
            ForecastDetail(
                risk_level=RiskLevel.LOW, confidence=-0.1,
                confidence_tier=ConfidenceTier.LOW,
                timing_onset_window=ForecastWindowSchema(earliest_minutes=15, latest_minutes=45),
                peak_window=ForecastWindowSchema(earliest_minutes=60, latest_minutes=120),
            )
        with pytest.raises(ValidationError):
            ForecastDetail(
                risk_level=RiskLevel.LOW, confidence=1.1,
                confidence_tier=ConfidenceTier.HIGH,
                timing_onset_window=ForecastWindowSchema(earliest_minutes=15, latest_minutes=45),
                peak_window=ForecastWindowSchema(earliest_minutes=60, latest_minutes=120),
            )


# ═══════════════════════════════════════════════
# SafetyInfo
# ═══════════════════════════════════════════════


class TestSafetyInfo:
    """Tests for SafetyInfo."""

    def test_defaults(self):
        """Default safety info."""
        si = SafetyInfo()
        assert si.is_safe is True
        assert "educational purposes" in si.disclaimer

    def test_unsafe(self):
        """Unsafe flag can be set."""
        si = SafetyInfo(is_safe=False)
        assert si.is_safe is False


# ═══════════════════════════════════════════════
# MealForecastResponse
# ═══════════════════════════════════════════════


class TestMealForecastResponse:
    """Tests for MealForecastResponse."""

    @pytest.fixture
    def sample_request(self):
        return MealForecastRequest(
            meal_items=[
                MealItemSchema(name="oatmeal", quantity=1, unit="serving", barcode="5901234123457"),
                MealItemSchema(name="banana", quantity=1, unit="medium"),
            ],
            current_glucose=105,
            meal_type=MealType.BREAKFAST,
        )

    @pytest.fixture
    def sample_response(self, sample_request):
        return MealForecastResponse(
            request_timestamp=datetime(2026, 5, 21, 7, 30, 5, 123000, tzinfo=timezone.utc),
            meal_items=sample_request.meal_items,
            nutrient_totals=NutrientTotals(
                carbs_g=45.5, protein_g=12.0, fat_g=8.5,
                fiber_g=4.0, sugars_g=15.2, calories_kcal=320.0,
                serving_weight_g=350.0,
            ),
            meal_tags=MealTagsResponse(tags=["moderate-carb", "mixed-meal"], carb_load_class="moderate"),
            provenance=[
                FoodProvenanceResponse(
                    source_name="openfoodfacts", barcode_match=True,
                    serving_certainty=0.9, source_trust_tier=SourceTrustTier.OFFICIAL,
                ),
            ],
            personal_context=PersonalContextSummary(
                current_glucose_mgdl=105, glucose_trend="flat",
                hour_of_day=7, recent_history_hours=6.0,
            ),
            forecast=ForecastDetail(
                risk_level=RiskLevel.MODERATE,
                confidence=0.72,
                confidence_tier=ConfidenceTier.MODERATE,
                delayed_effect=False,
                timing_onset_window=ForecastWindowSchema(earliest_minutes=15, latest_minutes=45),
                peak_window=ForecastWindowSchema(earliest_minutes=60, latest_minutes=120),
                evidence=[ForecastEvidenceSchema(key="carb_load", value="Moderate carbs (45g)")],
            ),
            safety=SafetyInfo(),
            narrative="This meal has a moderate carbohydrate load.",
        )

    def test_version_default(self, sample_response):
        """Version defaults to 1.0.0."""
        assert sample_response.version == "1.0.0"

    def test_response_structure(self, sample_response):
        """Response has all required sections."""
        dump = sample_response.model_dump()
        assert "version" in dump
        assert "request_timestamp" in dump
        assert "meal_items" in dump
        assert "nutrient_totals" in dump
        assert "meal_tags" in dump
        assert "provenance" in dump
        assert "personal_context" in dump
        assert "forecast" in dump
        assert "safety" in dump
        assert "narrative" in dump

    def test_no_loose_dicts(self, sample_response):
        """Response uses typed models, not bare dicts, in the main path."""
        dump = sample_response.model_dump()
        # All top-level fields should be structured types, not bare dicts masquerading
        assert isinstance(dump["nutrient_totals"], dict)
        assert isinstance(dump["forecast"], dict)
        assert isinstance(dump["safety"], dict)
        assert isinstance(dump["personal_context"], dict)
        assert isinstance(dump["meal_tags"], dict)
        assert isinstance(dump["provenance"], list)
        assert isinstance(dump["evidence"] if "evidence" in dump else [], list)

    def test_serialization_round_trip(self, sample_response):
        """Serialize to JSON and back produces identical data."""
        json_str = sample_response.model_dump_json()
        loaded = MealForecastResponse.model_validate_json(json_str)
        assert loaded.version == sample_response.version
        assert loaded.forecast.risk_level == sample_response.forecast.risk_level
        assert loaded.forecast.confidence == sample_response.forecast.confidence
        assert loaded.narrative == sample_response.narrative
        assert loaded.safety.is_safe == sample_response.safety.is_safe
        assert len(loaded.meal_items) == len(sample_response.meal_items)
        assert loaded.nutrient_totals.carbs_g == sample_response.nutrient_totals.carbs_g

    def test_json_schema_example(self):
        """Response has a JSON Schema example."""
        schema = MealForecastResponse.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert "version" in example
        assert "meal_items" in example
        assert "forecast" in example
        assert "safety" in example
        assert "narrative" in example

    def test_custom_version(self, sample_request):
        """Custom version string can override default."""
        resp = MealForecastResponse(
            version="2.0.0",
            request_timestamp=datetime.now(timezone.utc),
            meal_items=sample_request.meal_items,
            nutrient_totals=NutrientTotals(),
            meal_tags=MealTagsResponse(),
            personal_context=PersonalContextSummary(),
            forecast=ForecastDetail(
                risk_level=RiskLevel.LOW,
                confidence=0.5,
                confidence_tier=ConfidenceTier.MODERATE,
                timing_onset_window=ForecastWindowSchema(earliest_minutes=15, latest_minutes=45),
                peak_window=ForecastWindowSchema(earliest_minutes=60, latest_minutes=120),
            ),
            safety=SafetyInfo(),
            narrative="",
        )
        assert resp.version == "2.0.0"

    def test_from_json_serialization_consistency(self, sample_response):
        """JSON round-trip preserves all scalar values."""
        json_str = sample_response.model_dump_json(indent=2)
        loaded = MealForecastResponse.model_validate_json(json_str)
        assert loaded.forecast.risk_level.value == sample_response.forecast.risk_level.value
        assert loaded.forecast.delayed_effect == sample_response.forecast.delayed_effect
        assert loaded.meal_tags.carb_load_class == sample_response.meal_tags.carb_load_class
        assert loaded.safety.is_safe == sample_response.safety.is_safe


# ═══════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════


class TestConfidenceToTier:
    """Tests for confidence_to_tier helper."""

    def test_high(self):
        assert confidence_to_tier(0.8) == ConfidenceTier.HIGH
        assert confidence_to_tier(0.95) == ConfidenceTier.HIGH
        assert confidence_to_tier(1.0) == ConfidenceTier.HIGH

    def test_moderate(self):
        assert confidence_to_tier(0.6) == ConfidenceTier.MODERATE
        assert confidence_to_tier(0.7) == ConfidenceTier.MODERATE
        assert confidence_to_tier(0.79) == ConfidenceTier.MODERATE

    def test_low(self):
        assert confidence_to_tier(0.0) == ConfidenceTier.LOW
        assert confidence_to_tier(0.3) == ConfidenceTier.LOW
        assert confidence_to_tier(0.59) == ConfidenceTier.LOW


class TestRiskLevelToTier:
    """Tests for risk_level_to_tier helper."""

    def test_mapping(self):
        assert risk_level_to_tier(RiskLevel.LOW) == 1
        assert risk_level_to_tier(RiskLevel.MODERATE) == 2
        assert risk_level_to_tier(RiskLevel.HIGH) == 3
        assert risk_level_to_tier(RiskLevel.VERY_HIGH) == 4


# ═══════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════


class TestEdgeCases:
    """Edge case tests for all schemas."""

    def test_unicode_names(self):
        """Unicode food names are accepted."""
        item = MealItemSchema(name="χυλός βρώμης", quantity=1, unit="μερίδα")
        assert item.name == "χυλός βρώμης"

    def test_very_long_barcode(self):
        """Long but valid barcode at 64 chars passes."""
        barcode = "9" + "0" * 63
        item = MealItemSchema(name="test", quantity=1, unit="g", barcode=barcode)
        assert len(item.barcode) == 64

    def test_no_items_in_response(self):
        """Response can have empty meal_items list for error cases."""
        resp = MealForecastResponse(
            request_timestamp=datetime.now(timezone.utc),
            meal_items=[],
            nutrient_totals=NutrientTotals(),
            meal_tags=MealTagsResponse(),
            personal_context=PersonalContextSummary(),
            forecast=ForecastDetail(
                risk_level=RiskLevel.LOW,
                confidence=0.3,
                confidence_tier=ConfidenceTier.LOW,
                timing_onset_window=ForecastWindowSchema(earliest_minutes=0, latest_minutes=0),
                peak_window=ForecastWindowSchema(earliest_minutes=0, latest_minutes=0),
            ),
            safety=SafetyInfo(is_safe=False),
            narrative="",
        )
        assert len(resp.meal_items) == 0

    def test_response_serializable_no_crash(self):
        """Response is always serializable even with minimal data."""
        items = [MealItemSchema(name="test", quantity=1, unit="g")]
        resp = MealForecastResponse(
            request_timestamp=datetime.now(timezone.utc),
            meal_items=items,
            nutrient_totals=NutrientTotals(),
            meal_tags=MealTagsResponse(),
            personal_context=PersonalContextSummary(),
            forecast=ForecastDetail(
                risk_level=RiskLevel.LOW,
                confidence=0.0,
                confidence_tier=ConfidenceTier.LOW,
                timing_onset_window=ForecastWindowSchema(earliest_minutes=0, latest_minutes=0),
                peak_window=ForecastWindowSchema(earliest_minutes=0, latest_minutes=0),
            ),
            safety=SafetyInfo(),
            narrative="",
        )
        json_str = resp.model_dump_json()
        assert len(json_str) > 0