"""Food search facade.

Unifies lexical (ILIKE + trigram) and semantic (pgvector) search behind one interface.
Search strategies are adapters; the facade merges and deduplicates results.

Usage:
    search = FoodSearch(service)
    candidates = await search.search(food, limit=20)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SearchStrategy:
    """Interface for food search strategies."""

    async def search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Return candidate dicts with nutrition fields."""
        ...

    @property
    def name(self) -> str:
        ...


class LexicalStrategy(SearchStrategy):
    """ILIKE + trigram index search via FoodService._search_local_off."""

    def __init__(self, service: Any):
        self._service = service

    @property
    def name(self) -> str:
        return "lexical"

    async def search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        return await self._service._search_local_off(query, limit=limit)


class SemanticStrategy(SearchStrategy):
    """pgvector embedding search via FoodService._search_local_off_semantic."""

    def __init__(self, service: Any, embed_call=None):
        self._service = service
        self._embed_call = embed_call

    @property
    def name(self) -> str:
        return "semantic"

    async def search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        if self._embed_call is None:
            return []
        return await self._service._search_local_off_semantic(
            query, limit=limit, embed_call=self._embed_call
        )


class FoodSearch:
    """Unified food search facade.

    Runs one or more search strategies, merges results by barcode,
    and returns deduplicated candidates sorted by relevance.

    Usage:
        search = FoodSearch(service)
        candidates = await search.search(food, limit=20)

        # With semantic search:
        search = FoodSearch(service, embed_call=my_embed_fn)
        candidates = await search.search(food, limit=20)
    """

    def __init__(
        self,
        service: Any,
        embed_call=None,
        strategies: list[str] | None = None,
    ):
        self._service = service
        self._embed_call = embed_call
        self._strategies: list[SearchStrategy] = []

        # Register strategies in priority order
        available = {
            "semantic": lambda: SemanticStrategy(service, embed_call),
            "lexical": lambda: LexicalStrategy(service),
        }
        order = strategies or ["semantic", "lexical"]
        for name in order:
            if name in available:
                self._strategies.append(available[name]())

    async def search(self, food: Any, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for a food item using all registered strategies.

        Args:
            food: ParsedFood-like object with .item and .search_terms
            limit: Max results to return

        Returns:
            Deduplicated candidate dicts sorted by _candidate_score
        """
        by_barcode: Dict[str, Dict[str, Any]] = {}

        # Build query strings: primary item name + alias terms
        terms = [food.item]
        alias_terms = (food.search_terms or [])[:2]
        for at in alias_terms:
            if at != food.item:
                terms.append(at)

        # Run each strategy
        for strategy in self._strategies:
            for term in terms:
                try:
                    results = await strategy.search(term, limit=limit)
                    for candidate in results:
                        barcode = str(
                            candidate.get("barcode") or candidate.get("name") or ""
                        )
                        if barcode and barcode not in by_barcode:
                            # Tag with semantic similarity if available
                            if strategy.name == "semantic" and "_semantic_similarity" not in candidate:
                                distance = candidate.get("_distance", 0)
                                candidate["_semantic_similarity"] = 1.0 / (1.0 + distance)
                            by_barcode[barcode] = candidate
                except Exception as e:
                    logger.debug(f"Search strategy {strategy.name} failed for '{term}': {e}")
                    continue

        return list(by_barcode.values())

    @property
    def strategy_names(self) -> list[str]:
        return [s.name for s in self._strategies]
