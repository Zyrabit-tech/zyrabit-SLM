import pytest
from app.infrastructure.adapters.bge_reranker_adapter import BGEReRankerAdapter
from app.infrastructure.adapters.sliding_window_memory_adapter import SlidingWindowMemoryAdapter
from langchain_core.documents import Document

def test_bge_reranker_adapter():
    adapter = BGEReRankerAdapter()
    
    # Create test documents
    doc1 = Document(page_content="Manual de operaciones estandar para la aerolinea ejecutiva y roles de la tripulacion.", metadata={"source": "manual.pdf"})
    doc2 = Document(page_content="Plan de captura de valor y proyecciones financieras para el Q3 y Q4.", metadata={"source": "plan.pdf"})
    
    # Query related to aerolinea
    query = "Dame un resumen del manual de aerolineas ejecutivas"
    
    ranked = adapter.rerank(query, [doc1, doc2])
    
    # Assert doc1 is ranked higher than doc2
    assert len(ranked) == 2
    assert ranked[0][0].metadata["source"] == "manual.pdf"
    assert ranked[0][1] > ranked[1][1]
    
    # Assert score for doc1 is relatively high and doc2 is low
    assert ranked[0][1] >= 0.6
    assert ranked[1][1] < 0.6

def test_sliding_window_memory_adapter():
    adapter = SlidingWindowMemoryAdapter()
    
    # Test short history
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"}
    ]
    trimmed = adapter.get_context_window(history, max_turns=4)
    assert trimmed == history
    
    # Test history exceeding 4 turns (8 messages)
    long_history = [
        {"role": "user", "content": f"msg {i}"} if i % 2 == 0 else {"role": "assistant", "content": f"reply {i}"}
        for i in range(12)
    ]
    
    trimmed_long = adapter.get_context_window(long_history, max_turns=4)
    # max_turns=4 means 8 messages max
    assert len(trimmed_long) == 8
    # Should contain the last 8 messages (from index 4 to 11)
    assert trimmed_long == long_history[-8:]
