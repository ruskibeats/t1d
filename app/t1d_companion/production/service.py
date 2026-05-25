"""Core companion service — single consolidated LLM call + deterministic pipeline."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.t1d_companion.production.schemas import (
    AnchorType, CompanionRequest, CompanionResponse,
    Confidence, DatabaseMatch, Forecast, ForecastPoint,
    GlucoseContext, HistoricalMeal, Intent, NighttimePoint,
    ParsedFoodItem, SimUserProfile, Trend,
)
from app.t1d_companion.production.repositories import (
    FoodRepository, HistoryRepository, ProfileRepository,
    LRUCache,
)
from app.services.llm_service import LLMProvider, LLMService
from sim_user_insights.scripts.forecast_engine import (
    MealTotals, forecast_glucose,
)
from app.services.glucose_converter import format_glucose
from app.t1d_companion.local_loop import _load_prompt, _extract_json, ALIASES


class CompanionService:
    """Production-ready T1D companion.

    Single consolidated LLM call for parse + review + advice.
    Deterministic nutrition from Postgres OF.
    Pure-math forecast engine (<1ms).
    Redis-ready LRU cache for nutrition lookups.
    """

    def __init__(
        self,
        model: str = "deepseek/deepseek-v4-flash",
        food_cache: LRUCache | None = None,
    ):
        self.model = model
        self.llm = LLMService(provider=LLMProvider.OPENROUTER, model=model)
        self.food_repo = FoodRepository(cache=food_cache or LRUCache())
        self.profile_repo = ProfileRepository()
        self.history_repo = HistoryRepository()
        self._prompt = _load_prompt("consolidated.txt",
            "You are a T1D companion. Return JSON with foods, match_review, companion_advice.")
        self._stats = {"requests": 0, "llm_calls": 0}

    async def process(self, request: CompanionRequest) -> CompanionResponse:
        """Process a single companion request end-to-end."""
        start = time.time()
        self._stats["requests"] += 1

        # 1. Resolve profile
        anchor_key, profile = await self.profile_repo.get_profile(
            request.user_id if request.intent == Intent.FOOD_LOG else None
        )
        if request.anchor_type:
            anchor_key = request.anchor_type.value
            profile = await self.profile_repo.get_profile_by_anchor(anchor_key)

        pc = profile.get("patient_config", {})
        prof = profile.get("profile", {})

        # 2. Get CGM context
        if request.glucose_context:
            cg = request.glucose_context
        else:
            cg = GlucoseContext(
                current_glucose_mg_dl=_num(pc.get("basal_glucose_mean", 110)),
                trend=Trend.STEADY,
                insulin_on_board_units=0.0,
            )

        # 3. Single consolidated LLM call (parse + review + advice in one)
        self._last_scenario = request.scenario
        llm_raw = await self._call_llm(
            self._prompt,
            json.dumps({
                "scenario": request.scenario,
                "profile_anchor": anchor_key,
                "profile_description": prof.get("description", ""),
                "current_glucose_mg_dl": cg.current_glucose_mg_dl,
                "trend": cg.trend.value,
                "insulin_on_board": cg.insulin_on_board_units,
                "recent_meal": cg.recent_meal,
            }, indent=2)
        )

        parsed_foods, companion_advice = self._parse_llm_response(llm_raw)

        # 4. Database nutrition lookup
        db_matches, totals = await self._resolve_nutrition(parsed_foods)

        # 5. Forecast (pure math, <1ms)
        forecast = None
        if totals.get("carbs_g", 0) > 0:
            forecast = forecast_glucose(
                MealTotals.from_dict(totals),
                basal_mg_dl=_num(pc.get("basal_glucose_mean", 110)),
                carb_ratio=_num(profile.get("carb_ratio", 15)),
                insulin_sensitivity=_num(profile.get("insulin_sensitivity", 35)),
                fat_delay_hours=_num(pc.get("fat_delay_hours", 3)),
                exercise_drop_factor=_num(pc.get("exercise_drop_factor", 1.0)),
                anchor_type=anchor_key,
                hour=19,
            )

        # 6. Historical meal matching
        similar = []
        if parsed_foods:
            similar = self.history_repo.find_similar(parsed_foods, anchor_key)

        # 7. Safety filter
        safety = self._safety_check(companion_advice)

        # 7.5. Enrich advice with AI disclosure, profile badge, historical context, and confidence
        from app.config import get_settings
        glucose_unit = get_settings().glucose_units or "mmol/L"

        enrichment_parts = []

        # AI disclosure (EU AI Act Article 50 — transparency)
        enrichment_parts.append("🤖 I'm an AI assistant providing educational insights based on your data.")

        # Detect if user is manual-only (no CGM readings in last 24h)
        is_manual_user = cg.current_glucose_mg_dl <= 0 or not similar
        if is_manual_user:
            enrichment_parts.append(
                "📋 Manual logging mode — log each finger prick reading to build your history. "
                "Over time, patterns will emerge like with a CGM."
            )

        # Profile badge
        profile_label = prof.get("anchor_label", anchor_key)
        profile_desc = prof.get("description", "")[:80]
        enrichment_parts.append(f"📊 Your Profile: {profile_label}")
        enrichment_parts.append(f"   {profile_desc}")

        # Current glucose with correct units
        current_mgdl = cg.current_glucose_mg_dl
        enrichment_parts.append(f"📈 Current: {format_glucose(current_mgdl, glucose_unit)} ({cg.trend.value})")

        # Historical meal context
        if similar:
            avg_peak_mgdl = sum(
                m.peak_delta_mg_dl for m in similar if m.peak_delta_mg_dl
            ) / max(sum(1 for m in similar if m.peak_delta_mg_dl), 1)
            enrichment_parts.append(f"📖 Historical context: {len(similar)} similar meals found.")
            if avg_peak_mgdl > 0:
                enrichment_parts.append(f"   Average peak rise: ~{format_glucose(avg_peak_mgdl, glucose_unit)}.")
            # Check fat delay
            avg_fat = sum(m.fat_g for m in similar if m.fat_g) / max(len(similar), 1)
            if avg_fat >= 20:
                enrichment_parts.append(
                    "   ⚠️ Several matched meals were high in fat — "
                    "watch for a possible delayed spike 3-5 hours after eating."
                )
        else:
            enrichment_parts.append(
                "📖 No exact matches in your history — log this meal "
                "to improve future comparisons."
            )

        # Confidence score
        from app.services.confidence_scoring_service import score_and_narrate
        confidence = score_and_narrate(
            match_count=len(similar),
            has_cgm_data=any(m.peak_delta_mg_dl is not None for m in similar),
        )
        if confidence.tier == "high":
            enrichment_parts.append(f"✅ Confidence: {confidence.tier.upper()} — {confidence.narrative[:60]}")
        elif confidence.tier == "low":
            enrichment_parts.append(f"📊 Confidence: {confidence.tier.upper()} — {confidence.narrative[:80]}")
        else:
            enrichment_parts.append(f"📊 Confidence: {confidence.tier.upper()}")

        enrichment_text = "\n\n" + "\n".join(enrichment_parts)
        companion_advice = companion_advice + enrichment_text

        # 8. Build response
        elapsed = (time.time() - start) * 1000

        return CompanionResponse(
            request_id=request.request_id,
            sim_profile=SimUserProfile(
                anchor_type=anchor_key,
                label=prof.get("anchor_label", anchor_key),
                description=prof.get("description", ""),
                basal_glucose_mg_dl=_num(pc.get("basal_glucose_mean", 110)),
                carb_ratio=_num(profile.get("carb_ratio", 15)),
                insulin_sensitivity=_num(profile.get("insulin_sensitivity", 35)),
                fat_delay_hours=_num(pc.get("fat_delay_hours", 3)),
                exercise_drop_factor=_num(pc.get("exercise_drop_factor", 1.0)),
                hypo_risk=_num(pc.get("hypo_risk", 0.05)),
            ),
            current_glucose_mg_dl=round(cg.current_glucose_mg_dl),
            trend=cg.trend.value,
            insulin_on_board_units=round(cg.insulin_on_board_units, 2),
            parsed_foods=parsed_foods,
            database_matches=db_matches,
            meal_totals=totals,
            educational_bolus_estimate_units=round(
                totals.get("carbs_g", 0) / _num(profile.get("carb_ratio", 15)), 1
            ) if totals.get("carbs_g", 0) > 0 else None,
            forecast=Forecast(
                baseline_mg_dl=forecast.baseline_mg_dl,
                peak_mg_dl=forecast.peak_mg_dl,
                peak_time_minutes=forecast.peak_time_minutes,
                forecast_points=[ForecastPoint(hour=p.hour, glucose_mg_dl=p.glucose_mg_dl) for p in forecast.forecast_points],
                nighttime=[NighttimePoint(time=n.time, hours_after_meal=n.hours_after_meal, glucose_mg_dl=n.glucose_mg_dl, note=n.note) for n in forecast.nighttime],
                exercise_heat_modifier=forecast.exercise_heat_modifier,
            ) if forecast else None,
            historical_meals=similar,
            companion_advice=companion_advice,
            safety_check=safety,
            processing_time_ms=round(elapsed, 1),
        )

    async def _call_llm(self, system: str, user_content: str) -> str | None:
        self._stats["llm_calls"] += 1
        try:
            result = await self.llm.call_with_fallback(
                [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
                max_tokens=800,
            )
            return result.get("response") if result else None
        except Exception:
            return None

    def _parse_llm_response(self, raw: str | None) -> tuple[list[ParsedFoodItem], str]:
        """Extract foods and advice from consolidated LLM response.

        Tries JSON extraction first. Falls back to regex extraction
        from free-text responses (DeepSeek sometimes ignores JSON-only
        instructions).
        """
        foods: list[ParsedFoodItem] = []
        advice = "I wasn't able to process that request. Please try again."

        if not raw:
            return foods, advice

        # Try JSON extraction first
        try:
            data = _extract_json(raw)
            if isinstance(data, dict):
                items = data.get("foods", [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and item.get("item"):
                            foods.append(ParsedFoodItem(
                                item=str(item["item"]).lower().strip(),
                                quantity=_num(item.get("quantity"), 1.0),
                                unit=item.get("unit") or None,
                                serving_grams=_num(item.get("serving_grams")),
                            ))
                advice = data.get("companion_advice") or advice
                return foods, advice
        except Exception:
            pass

        # Fallback: use the fallback parser on the ORIGINAL scenario text
        from app.t1d_companion.local_loop import fallback_parse_scenario, ALIASES
        fb = fallback_parse_scenario(self._last_scenario)
        for f in fb:
            foods.append(ParsedFoodItem(
                item=f.item,
                quantity=f.quantity,
                unit=f.unit,
                serving_grams=100.0,
            ))
        # Also try to extract advice from the raw LLM output
        paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
        for p in reversed(paragraphs):
            if len(p) > 30:
                # Remove trailing irrelevant lines
                lines_clean = [l for l in p.split("\n") if not l.startswith("```") and "json.loads" not in l]
                if lines_clean:
                    advice = "\n".join(lines_clean)[:600]
                    break

        # Try to extract advice as the last substantive paragraph
        paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
        for p in reversed(paragraphs):
            if len(p) > 30 and not p.startswith("{"):
                advice = p
                break

        return foods, advice

    async def _resolve_nutrition(
        self, foods: list[ParsedFoodItem]
    ) -> tuple[list[DatabaseMatch], dict[str, float]]:
        """Resolve each food against OpenFoodFacts."""
        matches: list[DatabaseMatch] = []
        totals = {"carbs_g": 0.0, "fat_g": 0.0, "sugars_g": 0.0, "protein_g": 0.0, "kcal": 0.0}
        serving_rate = 100  # default per 100g

        for food in foods:
            # Search using aliases
            terms = ALIASES.get(food.item, [food.item])
            candidates: list[dict] = []
            seen_barcodes: set[str] = set()
            for term in terms:
                for c in await self.food_repo.search(term, limit=3):
                    bc = str(c.get("barcode", ""))
                    if bc and bc in seen_barcodes:
                        continue
                    if bc:
                        seen_barcodes.add(bc)
                    candidates.append(c)
                if candidates:
                    break

            if candidates:
                best = candidates[0]
                sg = food.serving_grams or 100
                carbs = _num(best.get("carbs_per_100g")) * sg / serving_rate
                fat = _num(best.get("fat_per_100g")) * sg / serving_rate
                protein = _num(best.get("protein_per_100g")) * sg / serving_rate
                kcal = _num(best.get("calories_per_100g")) * sg / serving_rate

                matches.append(DatabaseMatch(
                    food_name=food.item,
                    matched_name=best.get("name"),
                    matched_brand=best.get("brand"),
                    barcode=best.get("barcode"),
                    carbs_per_100g=_num(best.get("carbs_per_100g")),
                    fat_per_100g=_num(best.get("fat_per_100g")),
                    protein_per_100g=_num(best.get("protein_per_100g")),
                    kcal_per_100g=_num(best.get("calories_per_100g")),
                    serving_grams=sg,
                    computed_carbs_g=round(carbs, 1),
                    computed_fat_g=round(fat, 1),
                    computed_protein_g=round(protein, 1),
                    computed_kcal=round(kcal),
                    confidence=Confidence.HIGH if best.get("barcode") else Confidence.MEDIUM,
                ))
                totals["carbs_g"] += carbs
                totals["fat_g"] += fat
                totals["sugars_g"] += _num(best.get("sugars_per_100g")) * sg / serving_rate
                totals["protein_g"] += protein
                totals["kcal"] += kcal
            else:
                matches.append(DatabaseMatch(
                    food_name=food.item,
                    confidence=Confidence.NONE,
                ))

        totals = {k: round(v, 1) for k, v in totals.items()}
        return matches, totals

    def _safety_check(self, text: str) -> str:
        forbidden = [
            r"(?i)(take|give|administer)\s+.*\d+\.?\d*\s*units",
            r"(?i)split bolus",
            r"(?i)recommended bolus",
        ]
        for pat in forbidden:
            if re.search(pat, text):
                return f"FLAGGED: {pat}"
        return "passed"

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "requests": self._stats["requests"],
            "llm_calls": self._stats["llm_calls"],
            "cache_size": self.food_repo._cache.size,
            "db_lookups": self.food_repo.stats.get("lookups", 0),
            "cache_hits": self.food_repo.stats.get("cache_hits", 0),
        }


def _num(val: Any, default: float = 0.0) -> float:
    try:
        if val is None: return default
        return float(val)
    except (TypeError, ValueError):
        return default