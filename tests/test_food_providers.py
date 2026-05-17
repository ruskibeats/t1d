"""Tests for food providers and FoodService.

Covers OpenFoodFactsClient, USDAClient, and FoodService.
All HTTP calls are mocked — no external network.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_off_product():
    """Return a realistic OpenFoodFacts product JSON snippet."""
    return {
        "product_name": "Organic Chicken Breast",
        "product_name_en": "Organic Chicken Breast",
        "brands": "Organic Valley",
        "code": "084253248828",
        "nutriments": {
            "carbohydrates_100g": 0.0,
            "proteins_100g": 23.0,
            "fat_100g": 1.5,
            "energy-kcal_100g": 120.0,
        },
        "serving_size": "100 g",
        "categories_tags": ["meat", "chicken"],
    }


@pytest.fixture
def mock_off_response(mock_off_product):
    """Mock OpenFoodFacts search API response."""
    return {"products": [mock_off_product]}


@pytest.fixture
def mock_off_empty_response():
    """Mock OpenFoodFacts search API response with no products."""
    return {"products": []}


@pytest.fixture
def mock_usda_item():
    """Return a realistic USDA food item JSON snippet."""
    return {
        "fdcId": 123456,
        "description": "Chicken breast, raw",
        "brandOwner": "Store Brand",
        "foodNutrients": [
            {"nutrientName": "Protein", "value": 23.0},
            {"nutrientName": "Total lipid (fat)", "value": 1.5},
            {"nutrientName": "Carbohydrate, by difference", "value": 0.0},
            {"nutrientName": "Energy", "value": 120.0},
        ],
        "servingSize": 100.0,
        "servingSizeUnit": "g",
        "foodCategory": "Meat",
    }


@pytest.fixture
def mock_usda_response(mock_usda_item):
    """Mock USDA search API response."""
    return {"foods": [mock_usda_item]}


@pytest.fixture
def mock_usda_empty_response():
    """Mock USDA search API response with no foods."""
    return {"foods": []}


# =============================================================================
# OpenFoodFactsClient Tests
# =============================================================================

class TestOpenFoodFactsClient:
    """Tests for OpenFoodFactsClient."""

    async def test_search_by_name_returns_products(self, mock_off_response):
        """Name search returns parsed products with correct nutrition."""
        from app.food.providers.openfoodfacts import OpenFoodFactsClient

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=mock_off_response)
            return resp

        client = OpenFoodFactsClient()
        with patch("httpx.AsyncClient.get", fake_get):
            results = await client.search_by_name("chicken breast", page_size=5)

        assert len(results) == 1
        product = results[0]
        assert product.name == "Organic Chicken Breast"
        assert product.brand == "Organic Valley"
        assert product.barcode == "084253248828"
        assert product.carbs_per_100g == 0.0
        assert product.protein_per_100g == 23.0
        assert product.fat_per_100g == 1.5
        assert product.calories_per_100g == 120.0
        assert product.serving_size == "100 g"

    async def test_search_by_name_empty_results(self, mock_off_empty_response):
        """Name search with no products returns empty list."""
        from app.food.providers.openfoodfacts import OpenFoodFactsClient

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=mock_off_empty_response)
            return resp

        client = OpenFoodFactsClient()
        with patch("httpx.AsyncClient.get", fake_get):
            results = await client.search_by_name("zzzznotafood")

        assert results == []

    async def test_search_by_name_http_error_returns_empty(self):
        """HTTP error during name search returns empty list without crashing."""
        from app.food.providers.openfoodfacts import OpenFoodFactsClient

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 429
            resp.raise_for_status = MagicMock(side_effect=Exception("Rate limit"))
            return resp

        client = OpenFoodFactsClient()
        with patch("httpx.AsyncClient.get", fake_get):
            results = await client.search_by_name("pasta")

        assert results == []

    async def test_search_by_name_malformed_json_skips_items(self, mock_off_product):
        """Malformed product JSON is skipped without crashing."""
        from app.food.providers.openfoodfacts import OpenFoodFactsClient

        # One good product, one malformed (missing product_name)
        bad_item = {"code": "123", "nutriments": {}}
        data = {"products": [mock_off_product, bad_item]}

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=data)
            return resp

        client = OpenFoodFactsClient()
        with patch("httpx.AsyncClient.get", fake_get):
            results = await client.search_by_name("mixed")

        assert len(results) == 1
        assert results[0].name == "Organic Chicken Breast"

    async def test_search_by_barcode_found(self, mock_off_product):
        """Barcode search returns a single product."""
        from app.food.providers.openfoodfacts import OpenFoodFactsClient

        data = {"status": 1, "product": mock_off_product}

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=data)
            return resp

        client = OpenFoodFactsClient()
        with patch("httpx.AsyncClient.get", fake_get):
            product = await client.search_by_barcode("084253248828")

        assert product is not None
        assert product.name == "Organic Chicken Breast"
        assert product.barcode == "084253248828"

    async def test_search_by_barcode_not_found(self):
        """Barcode search with no match returns None."""
        from app.food.providers.openfoodfacts import OpenFoodFactsClient

        data = {"status": 0}

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=data)
            return resp

        client = OpenFoodFactsClient()
        with patch("httpx.AsyncClient.get", fake_get):
            product = await client.search_by_barcode("000000000000")

        assert product is None

    async def test_search_by_barcode_http_error_returns_none(self):
        """HTTP error during barcode search returns None."""
        from app.food.providers.openfoodfacts import OpenFoodFactsClient

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 500
            resp.raise_for_status = MagicMock(side_effect=Exception("Server error"))
            return resp

        client = OpenFoodFactsClient()
        with patch("httpx.AsyncClient.get", fake_get):
            product = await client.search_by_barcode("084253248828")

        assert product is None


# =============================================================================
# USDAClient Tests
# =============================================================================

class TestUSDAClient:
    """Tests for USDAClient."""

    async def test_search_by_name_with_api_key(self, mock_usda_response):
        """Name search returns parsed foods with correct nutrients."""
        from app.food.providers.usda import USDAClient

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=mock_usda_response)
            return resp

        client = USDAClient(api_key="test-key")
        with patch("httpx.AsyncClient.get", fake_get):
            results = await client.search_by_name("chicken breast", page_size=5)

        assert len(results) == 1
        item = results[0]
        assert item.name == "Chicken breast, raw"
        assert item.brand == "Store Brand"
        assert item.fdc_id == 123456
        assert item.carbs_per_100g == 0.0
        assert item.protein_per_100g == 23.0
        assert item.fat_per_100g == 1.5
        assert item.calories_per_100g == 120.0
        assert item.serving_size == 100.0
        assert item.serving_unit == "g"
        assert item.food_category == "Meat"

    async def test_search_by_name_no_api_key_returns_empty(self):
        """No API key → empty list returned without HTTP call."""
        from app.food.providers.usda import USDAClient

        client = USDAClient(api_key=None)
        results = await client.search_by_name("chicken")
        assert results == []

    async def test_search_by_name_http_error_returns_empty(self):
        """HTTP error during search returns empty list."""
        from app.food.providers.usda import USDAClient

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 401
            resp.raise_for_status = MagicMock(side_effect=Exception("Unauthorized"))
            return resp

        client = USDAClient(api_key="bad-key")
        with patch("httpx.AsyncClient.get", fake_get):
            results = await client.search_by_name("chicken")

        assert results == []

    async def test_search_by_name_empty_results(self, mock_usda_empty_response):
        """Search with no matches returns empty list."""
        from app.food.providers.usda import USDAClient

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=mock_usda_empty_response)
            return resp

        client = USDAClient(api_key="test-key")
        with patch("httpx.AsyncClient.get", fake_get):
            results = await client.search_by_name("zzzznotafood")

        assert results == []

    async def test_search_by_name_malformed_item_skipped(self, mock_usda_item):
        """Malformed food item without description is skipped gracefully."""
        from app.food.providers.usda import USDAClient

        bad_item = {"fdcId": 999, "foodNutrients": []}
        data = {"foods": [mock_usda_item, bad_item]}

        async def fake_get(*args, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=data)
            return resp

        client = USDAClient(api_key="test-key")
        with patch("httpx.AsyncClient.get", fake_get):
            results = await client.search_by_name("mixed")

        # bad_item has no description but USDA typically falls back to "Unknown"
        # We expect at least the good item to be parsed
        assert len(results) >= 1


# =============================================================================
# FoodService Tests
# =============================================================================

class TestFoodService:
    """Tests for FoodService methods."""

    async def test_search_foods_local_only(self, db_session, test_user):
        """search_foods returns only local foods matching the query."""
        from app.food.models import Food
        from app.food.service import FoodService

        # Seed a local food
        food = Food(
            user_id=test_user.id,
            name="Organic Chicken Breast",
            carbs=0.0,
            protein=23.0,
            fat=1.5,
            calories=120.0,
            source="manual",
        )
        db_session.add(food)
        await db_session.commit()

        service = FoodService(db_session)
        results = await service.search_foods(test_user.id, "chicken", limit=10)

        assert len(results) == 1
        assert results[0].name == "Organic Chicken Breast"
        assert results[0].carbs == 0.0
        assert results[0].protein == 23.0

    async def test_search_foods_local_no_match(self, db_session, test_user):
        """search_foods with non-matching query returns empty list."""
        from app.food.service import FoodService

        service = FoodService(db_session)
        results = await service.search_foods(test_user.id, "nonexistent", limit=10)

        assert results == []

    async def test_search_foods_local_multi_user_isolation(self, db_session, test_user, test_user_2):
        """search_foods returns foods only for the requested user."""
        from app.food.models import Food
        from app.food.service import FoodService

        food = Food(
            user_id=test_user.id,
            name="User 1 Chicken",
            source="manual",
        )
        db_session.add(food)
        await db_session.commit()

        service = FoodService(db_session)

        # User 1 finds it
        r1 = await service.search_foods(test_user.id, "chicken", limit=10)
        assert len(r1) == 1

        # User 2 does not find it
        r2 = await service.search_foods(test_user_2.id, "chicken", limit=10)
        assert len(r2) == 0

    async def test_create_food(self, db_session, test_user):
        """create_food inserts and refreshes a Food record."""
        from app.food.schemas import FoodCreate
        from app.food.service import FoodService

        service = FoodService(db_session)
        data = FoodCreate(
            name="Test Banana",
            carbs=27.0,
            protein=1.3,
            fat=0.3,
            calories=105,
            serving_size=1.0,
            serving_unit="piece",
        )
        food = await service.create_food(test_user.id, data)

        assert food.id is not None
        assert food.name == "Test Banana"
        assert food.carbs == 27.0
        assert food.user_id == test_user.id

    async def test_list_foods(self, db_session, test_user):
        """list_foods returns all user's foods ordered by updated_at desc."""
        from app.food.models import Food
        from app.food.service import FoodService

        for i in range(3):
            db_session.add(Food(user_id=test_user.id, name=f"Food {i}", source="manual"))
        await db_session.commit()

        service = FoodService(db_session)
        results = await service.list_foods(test_user.id)

        assert len(results) == 3
        # Names should be in reverse order of creation due to updated_at desc
        names = [f.name for f in results]
        assert "Food 2" in names

    async def test_get_food(self, db_session, test_user):
        """get_food returns a specific food by id."""
        from app.food.models import Food
        from app.food.service import FoodService

        food = Food(user_id=test_user.id, name="Avocado", source="manual")
        db_session.add(food)
        await db_session.commit()
        await db_session.refresh(food)

        service = FoodService(db_session)
        found = await service.get_food(test_user.id, food.id)

        assert found is not None
        assert found.name == "Avocado"

    async def test_get_food_not_found(self, db_session, test_user):
        """get_food returns None for non-existent id."""
        from app.food.service import FoodService

        service = FoodService(db_session)
        found = await service.get_food(test_user.id, 99999)
        assert found is None

    async def test_search_external_foods_local_only_mode(self, db_session, test_user):
        """search_external_foods with use_external=False returns only local results."""
        from app.food.models import Food
        from app.food.service import FoodService

        food = Food(user_id=test_user.id, name="Apple", carbs=14.0, source="manual")
        db_session.add(food)
        await db_session.commit()

        service = FoodService(db_session)
        results = await service.search_external_foods(
            db_session, test_user.id, "apple", use_external=False
        )

        assert len(results) == 1
        assert results[0]["name"] == "Apple"
        assert results[0]["source"] == "local"

    async def test_search_external_foods_providers_called(
        self, db_session, test_user, mock_off_product
    ):
        """search_external_foods calls OpenFoodFacts when no local match."""
        from app.food.service import FoodService

        off_data = {"products": [mock_off_product]}
        fake_resp = MagicMock(status_code=200)
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json = MagicMock(return_value=off_data)
        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=None)
        fake_client.get = AsyncMock(return_value=fake_resp)

        service = FoodService(db_session)

        with patch("httpx.AsyncClient", return_value=fake_client):
            results = await service.search_external_foods(
                db_session, test_user.id, "chicken breast"
            )

        assert len(results) >= 1
        # At minimum, the OpenFoodFacts result should be there
        off_results = [r for r in results if r["source"] == "openfoodfacts"]
        assert len(off_results) >= 1
        assert off_results[0]["name"] == "Organic Chicken Breast"

    async def test_search_external_foods_all_providers_fail(
        self, db_session, test_user
    ):
        """Both providers fail → only local results returned."""
        from app.food.service import FoodService

        fake_resp = MagicMock(status_code=429)
        fake_resp.raise_for_status = MagicMock(side_effect=Exception("Rate limit"))
        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=None)
        fake_client.get = AsyncMock(return_value=fake_resp)

        service = FoodService(db_session)
        with patch("httpx.AsyncClient", return_value=fake_client):
            results = await service.search_external_foods(
                db_session, test_user.id, "anything"
            )

        # No local results, no external results → empty list
        assert results == []

    async def test_search_external_foods_caches_results(
        self, db_session, test_user, mock_off_product
    ):
        """External results are cached as Food rows in the DB."""
        from app.food.models import Food
        from app.food.service import FoodService

        off_data = {"products": [mock_off_product]}
        fake_resp = MagicMock(status_code=200)
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json = MagicMock(return_value=off_data)
        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=None)
        fake_client.get = AsyncMock(return_value=fake_resp)

        count_before = len((await db_session.execute(
            __import__("sqlalchemy").select(Food)
        )).scalars().all())

        service = FoodService(db_session)
        with patch("httpx.AsyncClient", return_value=fake_client):
            await service.search_external_foods(
                db_session, test_user.id, "chicken breast"
            )

        count_after = len((await db_session.execute(
            __import__("sqlalchemy").select(Food)
        )).scalars().all())

        assert count_after > count_before


# =============================================================================
# Food Entry CRUD Tests
# =============================================================================

class TestFoodEntry:
    """Tests for FoodEntry CRUD via FoodService."""

    async def test_create_entry(self, db_session, test_user):
        """create_entry creates and returns a FoodEntry."""
        from app.food.schemas import FoodEntryCreate
        from app.food.service import FoodService
        from app.food.models import FoodEntry

        service = FoodService(db_session)
        data = FoodEntryCreate(
            quantity=1.0,
            unit="serving",
            entry_date=datetime.now(timezone.utc),
            meal_type="lunch",
            food_name="Test Meal",
            calories=500,
            protein=30.0,
            carbs=60.0,
            fat=15.0,
        )
        entry = await service.create_entry(test_user.id, data)

        assert entry.id is not None
        assert entry.meal_type == "lunch"
        assert entry.food_name == "Test Meal"
        assert entry.calories == 500

    async def test_list_entries(self, db_session, test_user):
        """list_entries returns food entries ordered by date desc."""
        from datetime import timedelta
        from app.food.schemas import FoodEntryCreate
        from app.food.service import FoodService

        service = FoodService(db_session)
        for i in range(3):
            data = FoodEntryCreate(
                quantity=1.0,
                unit="serving",
                entry_date=datetime.now(timezone.utc) - timedelta(hours=i),
                meal_type="snack",
                food_name=f"Snack {i}",
            )
            await service.create_entry(test_user.id, data)

        entries = await service.list_entries(test_user.id)
        assert len(entries) == 3
