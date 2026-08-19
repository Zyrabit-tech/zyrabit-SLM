"""
Business Rules & Reasoning Model Sanitization Contract Tests.
Ensures that model chain-of-thought (<think>) tags never pollute session history,
and guarantees that conversational and document-grounded business rules remain inviolate.
"""

from app.node.service import NodeService


def test_compact_summary_strips_reasoning_tags_and_content():
    """
    Business Rule: Compact conversation summaries stored in SQLite MUST NOT contain
    internal chain-of-thought (<think> or </think>) reasoning tokens.
    """
    raw_answer_with_full_tags = (
        "<think>The user greeted me. I should be nice.</think> "
        "¡Hola! ¿Cómo estás hoy? [EVIDENCE:11111111-2222-3333-4444-555555555555]"
    )
    summary = NodeService._compact_summary("", "¿Cómo estás?", raw_answer_with_full_tags, None)
    
    assert "<think>" not in summary
    assert "</think>" not in summary
    assert "The user greeted me" not in summary
    assert "¡Hola! ¿Cómo estás hoy?" in summary
    assert "EVIDENCE:" not in summary


def test_compact_summary_strips_unopened_think_tags():
    """
    Business Rule: When DeepSeek-R1 omits the opening <think> tag,
    everything prior to </think> MUST be stripped from history.
    """
    raw_answer_unopened = (
        "Alright, the user is asking for 5 + 7. Let me compute 5 + 7 = 12.\n"
        "</think>\n"
        "5 + 7 es igual a 12."
    )
    summary = NodeService._compact_summary("", "¿Cuánto es 5 + 7?", raw_answer_unopened, None)
    
    assert "</think>" not in summary
    assert "Let me compute" not in summary
    assert "5 + 7 es igual a 12." in summary


def test_prompt_history_strips_polluted_assistant_thoughts():
    """
    Business Rule: When building prompts for subsequent turns, history messages
    containing think tags MUST have their thought content stripped.
    """
    service = NodeService.__new__(NodeService)
    service.identity = None
    
    dirty_history = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Thinking about greeting...</think>¡Hola! Un gusto."},
        {"role": "user", "content": "¿Cómo te llamas?"},
    ]
    
    prompt = service._prompt("¿Cómo te llamas?", evidence="", history=dirty_history)
    
    assert "Thinking about greeting" not in prompt
    assert "</think>" not in prompt
    assert "¡Hola! Un gusto." in prompt


def test_conversational_turn_does_not_trigger_retrieval():
    """
    Business Rule: Human social greetings must be classified as conversational
    and must not search document passages.
    """
    assert NodeService._is_conversational("hola como estas") is True
    assert NodeService._is_conversational("buenas tardes zyra") is True
    assert NodeService._is_conversational("hello man") is True
    assert NodeService._is_conversational("revisa el contrato en la clausula 4") is False
