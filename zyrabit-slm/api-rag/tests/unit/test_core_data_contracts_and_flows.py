"""
test_core_data_contracts_and_flows.py
Lock in core data contracts, ReAct agent parsing, intent classification,
token budgeting, PII sandwich recursion, and hardware inference provider resolution.
"""
import pytest

from app.domain.agent.react_harness import ReActAction, clean_json_text, restore_pii_recursive, classify_intent
from app.domain.services.context_manager import ContextManager
from app.infrastructure.inference.factory import InferenceProviderFactory
from app.infrastructure.inference.vllm_inference_adapter import VllmInferenceAdapter
from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter


def test_react_action_contract_valid_json():
    """Verify ReActAction schema contract parses valid JSON."""
    raw = '{"thought": "Need to check containers", "action": "docker_list_containers", "action_input": {}}'
    action = ReActAction.model_validate_json(raw)
    assert action.thought == "Need to check containers"
    assert action.action == "docker_list_containers"
    assert action.action_input == {}


def test_clean_json_text_strips_markdown_code_fences():
    """Verify markdown wrapped JSON is cleaned reliably without breaking."""
    wrapped = "```json\n{\"thought\": \"Done\", \"action\": \"final_answer\", \"action_input\": {\"answer\": \"Hello\"}}\n```"
    cleaned = clean_json_text(wrapped)
    action = ReActAction.model_validate_json(cleaned)
    assert action.action == "final_answer"
    assert action.action_input.get("answer") == "Hello"


def test_classify_intent_contract():
    """Verify intent classifier routes tools deterministically without overhead."""
    # Docker query
    assert "docker_list_containers" in classify_intent("Check docker container status")
    # Telegram query
    assert "send_telegram_notification" in classify_intent("Enviar notificación a telegram")
    # Radar query
    assert "generate_radar_report" in classify_intent("Generar radar briefing de inteligencia")
    # Generic conversational query returns empty tools (direct chat without hallucinations)
    assert classify_intent("hola como estas") == []


def test_restore_pii_recursive_contract():
    """Verify PII tokens in nested tool inputs are restored before execution."""
    token_map = {"<EMAIL_1>": "ceo@zyrabit.com", "<IP_1>": "192.168.1.100"}
    nested_args = {
        "recipient": "<EMAIL_1>",
        "server": {"host": "<IP_1>", "port": 8080},
        "tags": ["<EMAIL_1>", "admin"]
    }
    restored = restore_pii_recursive(nested_args, token_map)
    assert restored["recipient"] == "ceo@zyrabit.com"
    assert restored["server"]["host"] == "192.168.1.100"
    assert restored["tags"] == ["ceo@zyrabit.com", "admin"]


def test_context_manager_budget_enforcement():
    """Verify ContextManager enforces token budget ceilings to prevent memory overflow."""
    cm = ContextManager()
    
    # Trim history
    long_history = [{"role": "user", "content": "hello " * 200}] * 10
    trimmed = cm.trim_history(long_history, budget=300)
    assert len(trimmed) <= 300 * 4 + 100  # Character estimate safety check

    # Estimate ReAct budget
    sys_prompt = "You are a helpful assistant." * 50
    user_prompt = "Query test." * 50
    budget_info = cm.estimate_react_budget(sys_prompt, user_prompt)
    assert "total" in budget_info
    assert "limit" in budget_info
    assert isinstance(budget_info["over_budget"], bool)


def test_inference_provider_factory_hardware_resolution():
    """Verify InferenceProviderFactory resolves Tenstorrent, vLLM, and Ollama providers cleanly."""
    # Tenstorrent / vLLM provider resolution
    tt_provider = InferenceProviderFactory.create_sync_provider("tenstorrent", endpoint="http://localhost:8090/v1/chat/completions")
    assert isinstance(tt_provider, VllmInferenceAdapter)

    vllm_provider = InferenceProviderFactory.create_sync_provider("vllm", endpoint="http://localhost:8000/v1/chat/completions")
    assert isinstance(vllm_provider, VllmInferenceAdapter)

    # Ollama provider resolution
    ollama_provider = InferenceProviderFactory.create_sync_provider("ollama_host", endpoint="http://localhost:11434/api/generate")
    assert isinstance(ollama_provider, OllamaInferenceAdapter)
