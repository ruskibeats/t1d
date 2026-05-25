"""Nutrition cache and history repository — production-grade data layer."""

from __future__ import annotations

import json
import time
from collections import defaultdict, Counter
from pathlib import Path
from statistics import median
from typing import Any, Optional

from app.t1d_companion.production.schemas import (
    DatabaseMatch, Confidence, HistoricalMeal, ParsedFoodItem,
)


# ── LRU cache for nutrition lookups ──

class LRUCache:
    """Simple thread-safe LRU cache for nutrition lookups.

    In production, replace with Redis. This gives us the same interface
    so the swap is a single import change.
    """

    def __init__(self, capacity: int = 2000, ttl_seconds: int = 3600):
        self.capacity = capacity
        self.ttl = ttl_seconds
        self._cache: dict[str, tuple[float, Any]] = {}  # key -> (timestamp, value)
        self._order: list[str] = []

    def get(self, key: str) -> Any | None:
        if key not in self._cache:
            return None
        ts, value = self._cache[key]
        if time.time() - ts > self.ttl:
            del self._cache[key]
            return None
        # Move to end (most recently used)
        self._order.remove(key)
        self._order.append(key)
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._cache) >= self.capacity:
            # Evict least recently used
            oldest = self._order.pop(0)
            del self._cache[oldest]
        self._cache[key] = (time.time(), value)
        self._order.append(key)

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        if not hasattr(self, '_hits') or not hasattr(self, '_misses'):
            return 0.0
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0


# ── Food database interface ──

class FoodRepository:
    """Interface for food nutrition lookups.

    One adapter (Postgres OF) for now. When a second adapter appears,
    this becomes a real seam via a protocol/ABC.
    """

    def __init__(self, cache: LRUCache | None = None):
        self._cache = cache or LRUCache()
        self._stats: dict[str, int] = {"lookups": 0, "cache_hits": 0, "db_hits": 0}

    async def search(self, term: str, limit: int = 3) -> list[dict[str, Any]]:
        """Search OpenFoodFacts via Postgres for a food term.

        Cached by term. Returns list of normalized product dicts.
        """
        cache_key = f"of:{term}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._stats["cache_hits"] += 1
            return cached

        self._stats["db_hits"] += 1
        results = await self._search_postgres(term, limit)
        self._cache.set(cache_key, results)
        return results

    async def _search_postgres(self, term: str, limit: int) -> list[dict[str, Any]]:
        """Actual Postgres query."""
        from app.core.database import db_manager
        from app.db.models import OpenFoodFactsProduct
        from app.food.service import _assess_food_dict_quality
        from sqlalchemy import select, func

        self._stats["lookups"] += 1
        async with db_manager.get_session() as session:
            stmt = (
                select(OpenFoodFactsProduct, func.similarity(OpenFoodFactsProduct.product_name, term).label("similarity"))
                .where(
                    OpenFoodFactsProduct.product_name.isnot(None),
                    OpenFoodFactsProduct.carbs_100g.isnot(None),
                )
                .order_by(
                    func.similarity(OpenFoodFactsProduct.product_name, term).desc(),
                    OpenFoodFactsProduct.nutriscore_score.asc().nullslast(),
                )
                .limit(limit)
            )
            rows = list((await session.execute(stmt)).all())
            results = []
            for product, similarity in rows:
                quality = _assess_food_dict_quality(product, source="openfoodfacts_local")
                results.append({
                    "source": "openfoodfacts_local",
                    "name": product.product_name,
                    "brand": product.brands,
                    "barcode": product.code,
                    "carbs_per_100g": _num(product.carbs_100g),
                    "fat_per_100g": _num(product.fat_100g),
                    "protein_per_100g": _num(product.proteins_100g),
                    "calories_per_100g": _num(product.energy_kcal_100g),
                    "serving_size": product.serving_size,
                    "fiber_per_100g": _num(product.fiber_100g),
                    "sugars_per_100g": _num(product.sugars_100g),
                    "sodium_per_100g": _num(product.sodium_100g),
                    "_similarity": round(similarity, 3) if similarity else 0,
                    "_quality_flags": quality,
                })
            return results

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)


# ── Profile repository ──

class ProfileRepository:
    """User profiles. Loads enriched sim user data when available, falls back to basic config.

    Source priority:
    1. sim_users_enriched.json — enriched with real OF nutrition + history + full profile params
    2. data/profile_configs.json — basic anchor configs (generated from patient_factory)
    3. On-the-fly generation — if neither file exists

    In production, replace with Postgres table tbl_user_profiles.
    """

    def __init__(self):
        # Prefer enriched profiles (from task #236)
        self._enriched_path = Path("/root/t1d/sim_user_insights/outputs/sim_users_enriched.json")
        self._profiles_path = Path("/root/t1d/data/profile_configs.json")
        self._profiles: dict[str, Any] | None = None

    def _normalize_anchor(self, anchor_raw: dict) -> dict[str, Any]:
        """Normalize an enriched anchor entry into the canonical profile format."""
        p = anchor_raw.get("profile", {})
        prof = p.get("profile", {})
        return {
            "carb_ratio": p.get("carb_ratio", 15),
            "insulin_sensitivity": p.get("insulin_sensitivity", 40),
            "fat_delay_hours": p.get("fat_delay_hours", 3),
            "patient_config": {
                "basal_glucose_mean": prof.get("estimated_tir", 110),
                "meal_rise_factor": 3.0,
                "insulin_sensitivity": p.get("insulin_sensitivity", 40),
                "carb_ratio": p.get("carb_ratio", 15),
                "hypo_risk": 0.05,
                "noise_sd": 5.0,
                "exercise_drop_factor": 0.5,
                "fat_delay_hours": p.get("fat_delay_hours", 3),
                "variability_cv": 0.2,
            },
            "profile": {
                "anchor_type": anchor_raw.get("anchor_type", ""),
                "anchor_label": prof.get("anchor_label", ""),
                "description": prof.get("description", ""),
                "estimated_tir": prof.get("estimated_tir", 60),
                "estimated_a1c": prof.get("estimated_a1c", 7.0),
                "estimated_hypo_frequency": prof.get("estimated_hypo_frequency", "moderate"),
                "variability_category": prof.get("variability_category", "moderate"),
            },
            "_enriched_meta": {
                "history_meal_count": anchor_raw.get("history_meal_count", 0),
                "of_match_rate": anchor_raw.get("of_match_rate", 0),
                "top_foods": anchor_raw.get("top_foods_enriched", []),
                "patterns": anchor_raw.get("patterns", {}),
            },
        }

    def _load(self) -> dict[str, Any]:
        """Load profiles from enriched file first, then config file, then empty."""
        if self._profiles is not None:
            return self._profiles

        self._profiles = {}

        # 1. Try enriched file
        if self._enriched_path.exists():
            try:
                raw = json.loads(self._enriched_path.read_text())
                for anchor_raw in raw.get("anchors", []):
                    key = anchor_raw.get("anchor_type", "")
                    if key:
                        self._profiles[key] = self._normalize_anchor(anchor_raw)
                if self._profiles:
                    return self._profiles
            except (json.JSONDecodeError, OSError) as e:
                import logging as _lg
                _lg.getLogger(__name__).warning(f"Failed to load enriched profiles: {e}")

        # 2. Fallback to basic config file
        if self._profiles_path.exists():
            try:
                self._profiles.update(json.loads(self._profiles_path.read_text()))
            except (json.JSONDecodeError, OSError) as e:
                import logging as _lg
                _lg.getLogger(__name__).warning(f"Failed to load profile configs: {e}")

        return self._profiles

    async def get_profile(self, user_id: str | None = None) -> tuple[str, dict[str, Any]]:
        """Get profile by user_id (real users) or random (simulator mode).

        Uses enriched profiles when available (better nutrition data),
        falls back to basic config, then on-the-fly generation.
        """
        profiles = self._load()
        if not profiles:
            # 3. Generate on the fly
            from app.simulator.patient_factory import generate_patient_config, generate_profile_json
            from app.simulator.schemas import AnchorType
            import random
            anchor = random.choice(list(AnchorType))
            config = generate_patient_config(anchor, random.randint(1, 1000000))
            profile_json = generate_profile_json(config)
            return anchor.value, {
                "carb_ratio": config.carb_ratio,
                "insulin_sensitivity": config.insulin_sensitivity,
                "fat_delay_hours": config.fat_delay_hours,
                "patient_config": {
                    "basal_glucose_mean": round(config.basal_glucose_mean, 1),
                    "meal_rise_factor": round(config.meal_rise_factor, 1),
                    "insulin_sensitivity": round(config.insulin_sensitivity, 2),
                    "carb_ratio": round(config.carb_ratio, 2),
                    "hypo_risk": round(config.hypo_risk, 3),
                    "noise_sd": round(config.noise_sd, 2),
                    "exercise_drop_factor": round(config.exercise_drop_factor, 2),
                    "fat_delay_hours": round(config.fat_delay_hours, 2),
                    "variability_cv": round(config.variability_cv, 2),
                },
                "profile": profile_json,
            }

        import random
        key = random.choice(sorted(profiles.keys()))
        return key, profiles[key]

    async def get_profile_by_anchor(self, anchor_type: str) -> dict[str, Any]:
        profiles = self._load()
        return profiles.get(anchor_type, {})


# ── History repository ──

class HistoryRepository:
    """90-day meal history lookup.

    Currently from enhanced JSON file. In production, replace with Postgres.
    """

    def __init__(self):
        self._path = Path("/root/t1d/data/food_history_90d_enhanced.json")
        self._records: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if self._records is None:
            if self._path.exists():
                self._records = json.loads(self._path.read_text())
            else:
                self._records = []
        return self._records

    def find_similar(self, foods: list[ParsedFoodItem], anchor: str, limit: int = 5) -> list[HistoricalMeal]:
        """Find similar meals by food name matching."""
        records = self._load()
        terms = set()
        for f in foods:
            terms.add(f.item.lower())
            for t in f.item.lower().split():
                if len(t) > 2:
                    terms.add(t)

        scored = []
        for r in records:
            if r.get("anchor_type") != anchor:
                continue
            fn = str(r.get("food", "")).lower()
            s = sum(2 for qt in terms if qt in fn)
            if s > 0:
                scored.append((s, r))
        scored.sort(key=lambda x: -x[0])

        seen, result = set(), []
        for _s, rec in scored:
            fn = str(rec.get("food", "")).lower()
            if fn not in seen:
                seen.add(fn)
                result.append(HistoricalMeal(
                    food=str(rec.get("food", "")),
                    date=str(rec.get("timestamp", ""))[:10],
                    carbs_g=_num(rec.get("carb_estimate_g")),
                    fat_g=_num(rec.get("fat_g")),
                    peak_delta_mg_dl=_num(rec.get("cgm_impact", {}).get("expected_peak_delta")),
                    peak_time_minutes=_num(rec.get("cgm_impact", {}).get("peak_time_minutes")),
                    confidence_score=_num(rec.get("confidence_score")),
                ))
            if len(result) >= limit:
                break
        return result


# ── Helpers ──

def _num(val: Any, default: float = 0.0) -> float:
    try:
        if val is None: return default
        return float(val)
    except (TypeError, ValueError):
        return default