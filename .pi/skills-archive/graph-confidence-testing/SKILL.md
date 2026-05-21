---
name: graph-confidence-testing
description: Test confidence component calculations, threshold language mapping, and overall combined scoring for graph edges.
---

# Graph Confidence Testing

## When to Use
When adding or modifying confidence scoring for graph edges, test that confidence components are properly calculated and stored.

## Procedure

### 1. Create test file
Create `tests/test_graph_confidence.py` for confidence component tests.

### 2. Test confidence components JSON
```python
@pytest.mark.asyncio
async def test_confidence_components_json(db_session, test_user):
    """Test confidence_components JSON structure on edges."""
    # Create metrics
    # Create edge with ConfidenceComponents
    # Verify confidence_components dict is stored
    # Verify individual component values are correct
```

### 3. Test confidence threshold language
```python
@pytest.mark.asyncio
async def test_confidence_thresholds_language(db_session, test_user):
    """Test confidence thresholds map to language correctly."""
    # Test categorize_confidence for low/medium/high
    assert categorize_confidence(0.5) == "low"
    assert categorize_confidence(0.7) == "medium"
    assert categorize_confidence(0.9) == "high"
```

### 4. Test overall confidence calculation
```python
@pytest.mark.asyncio
async def test_confidence_overall_calculation(db_session, test_user):
    """Test combined_score calculation matches expected formula."""
    components = ConfidenceComponents(...)
    expected = (0.8 * 0.4 + 0.7 * 0.3 + ...)
    assert abs(components.combined_score() - expected) < 0.01
```

## Pitfalls
- Verify the weight formula matches the implementation
- Test edge cases (all low confidence, all high confidence)
- Ensure confidence_components JSON round-trips correctly
- Check that upsert_edge preserves confidence_components

## Verification
- All confidence tests pass
- Component values match expected calculations
- Threshold language mapping is correct
- Combined scores are within acceptable tolerance
