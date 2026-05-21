---
name: rag-evidence-contract-testing
description: Verify that retrieved graph edges provide proper evidence structure for LLM RAG context assembly, including confidence filtering and ordering.
---

# RAG Evidence Contract Testing

## When to Use
When modifying graph edge retrieval or RAG context assembly, verify that retrieved edges provide proper evidence for LLM responses.

## Procedure

### 1. Create test file
Create `tests/test_rag_graph_evidence.py` for RAG evidence contract tests.

### 2. Test graph context retrieval for LLM
```python
@pytest.mark.asyncio
async def test_graph_context_retrieval_for_llm(db_session, test_user):
    """Test that graph context is properly formatted for LLM retrieval."""
    # Create source and target metrics
    # Create edge with evidence
    # Verify edge.evidence is not None
    # Verify evidence fields are accessible
```

### 3. Test strongest edge context
```python
@pytest.mark.asyncio
async def test_strongest_edge_context(db_session, test_user):
    """Test that strongest edges provide meaningful context for LLM."""
    # Create multiple edges with different confidence scores
    # Retrieve strongest edges
    # Verify confidence thresholds are met
    # Verify evidence is included
```

### 4. Test evidence JSON structure
```python
@pytest.mark.asyncio
async def test_evidence_json_structure(db_session, test_user):
    """Test evidence JSON has expected structure."""
    # Create edge with specific evidence fields
    # Verify evidence dict has expected keys
    # Verify nested structures work
```

## Pitfalls
- Don't test only happy path — test edge cases (no edges, low confidence)
- Verify evidence fields match what pattern detectors produce
- Check that confidence_components are included when present
- Ensure edge ordering by confidence works correctly

## Verification
- RAG context includes evidence for all retrieved edges
- Strongest edges are correctly selected
- Evidence JSON structure matches detector output
- Confidence filtering works as expected
