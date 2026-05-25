from app.t1d_companion.local_loop import (
    ParsedFood,
    _candidate_score,
    calculate_food_evidence,
    fallback_parse_scenario,
)


def test_fallback_parse_coke_units_and_donut_quantity():
    foods = fallback_parse_scenario("I want 2 donuts and 3 cans of coke")
    by_item = {food.item: food for food in foods}

    assert by_item["donut"].quantity == 2
    assert by_item["coke"].quantity == 3
    assert by_item["coke"].unit == "can"


def test_candidate_scoring_prefers_regular_coke_over_zero_carb():
    food = ParsedFood(item="coke", quantity=3, unit="can", search_terms=["coke"])
    regular = {"name": "Coca Cola", "brand": "Coca-Cola", "carbs_per_100g": 10.6, "fat_per_100g": 0, "serving_size": "330 ml"}
    zero = {"name": "Coke Zero", "brand": "Coca-Cola", "carbs_per_100g": 0, "fat_per_100g": 0, "serving_size": "330 ml"}

    assert _candidate_score(food, regular) > _candidate_score(food, zero)


def test_candidate_scoring_prefers_standard_donut_over_tiny_fibre_bar():
    food = ParsedFood(item="donut", quantity=2, search_terms=["donut"])
    standard = {"name": "Donut", "brand": "Bakery", "carbs_per_100g": 53, "fat_per_100g": 11, "serving_size": "1 donut (71 g)"}
    fibre = {"name": "Donut", "brand": "Fibre one", "carbs_per_100g": 37, "fat_per_100g": 21, "serving_size": "23 g"}

    assert _candidate_score(food, standard) > _candidate_score(food, fibre)


def test_calculate_food_evidence_uses_can_serving_for_coke():
    food = ParsedFood(item="coke", quantity=3, unit="can", search_terms=["coke"])
    candidate = {
        "name": "Coca Cola",
        "brand": "Coca-Cola",
        "barcode": "x",
        "carbs_per_100g": 10.6,
        "sugars_per_100g": 10.6,
        "fat_per_100g": 0,
        "protein_per_100g": 0,
        "calories_per_100g": 42,
        "serving_size": "250 ml",
    }

    evidence = calculate_food_evidence(food, [candidate])

    assert evidence.assumed_serving_g_or_ml == 990
    assert evidence.computed["carbs_g"] == 104.9
