---
name: graph-provenance-testing
description: Test provenance structure on graph edges including detector/version/timestamp fields, evidence JSON consistency, and RAG evidence inclusion.
---

# Graph Provenance Testing

## When to Use
When adding new graph edge types or modifying the provenance structure, test that all persisted edges have proper detector/version/timestamp information.

## Procedure

### 1. Create test file
Create `tests/test_graph_provenance.py` with provenance structure tests.

### 2. Test edge provenance structure
```python
@pytest.mark.asyncio
async def test_edge_provenance_structure(db_session, test_user):
    """Test that edges have detector/version/timestamps in provenance."""
    # Create source and target metrics
    # Create edge via upsert_edge
    # Verify edge.evidence is not None
    # Verify edge.algorithm is set
    # Verify edge.provenance is consistent
```

### 3. Test provenance consistency across edge types
```python
@pytest.mark.asyncio
async def test_provenance_consistency_across_edge_types(db_session, test_user):
    """Test provenance JSON structure is consistent."""
    # Test multiple edge types
    # Verify all have algorithm field
    # Verify evidence structure is consistent
```

### 4. Test RAG evidence inclusion
```python
@pytest.mark.asyncio
async def test_rag_evidence_inclusion(db_session, test_user):
    """Test that RAG context includes evidence from edges."""
    # Create edge with evidence
    # Verify evidence is stored and retrievable
```

## Pitfalls
- Don't test only one edge type — test across multiple types
- Verify both `evidence` and `provenance` fields
- Check that confidence_components are properly stored when used
- Ensure algorithm names are consistent across detection methods

## Verification
- All provenance tests pass
- Evidence JSON is properly structured
- Algorithm fields are set for all edge types
- RAG context includes evidence data
