"""
ReactHarness V2.0 — Orchestrates the ReAct loop with:
  - Lazy Tool Loading (keyword intent classifier)
  - Sliding Window (max 3 conversation turns)
  - Token Budget Validator (70% cap)
  - PII Sandwich (mask → execute → re-mask)
"""
import re
import json
import logging
import asyncio
from typing import Dict, Any, Tuple, List
from pydantic import BaseModel, Field

from app.domain.agent.prompt_builder import PromptBuilder
from app.domain.agent.tool_registry import ToolRegistry
from app.ports.inference_port import InferenceProviderPort, InferenceRequest
from app.core.security.pii_pipeline import deanonymize_text
from app.domain.services.context_manager import ContextManager

logger = logging.getLogger("zyrabit.agent.harness")


class ReActAction(BaseModel):
    thought: str = Field(description="Your reasoning about what to do next.")
    action: str = Field(description="The name of the tool to execute or 'final_answer'")
    action_input: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")


def clean_json_text(text: str) -> str:
    """Removes markdown wrappers or surrounding text to isolate the raw JSON block."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return cleaned


def restore_pii_recursive(val: Any, token_map: Dict[str, str]) -> Any:
    """Recursively restores masked PII tokens in any input arguments."""
    if isinstance(val, str):
        return deanonymize_text(val, token_map)
    elif isinstance(val, dict):
        return {k: restore_pii_recursive(v, token_map) for k, v in val.items()}
    elif isinstance(val, list):
        return [restore_pii_recursive(v, token_map) for v in val]
    return val


# ─────────────────────────────────────────────
# Intent Classification Map (Lazy Tool Loading)
# ─────────────────────────────────────────────
TOOL_GROUPS = {
    "radar": {
        "keywords": ["radar", "reporte", "briefing", "intelligence", "inteligencia", "zyra-radar"],
        "tools": ["generate_radar_report"]
    },
    "telegram": {
        "keywords": ["telegram", "notificación", "notification", "alerta", "alert", "notificar"],
        "tools": ["send_telegram_notification"]
    },
    "vault": {
        "keywords": ["vault", "importar", "import", "bóveda", "archivo"],
        "tools": ["import_to_vault", "list_vault_stats"]
    },
    "docker": {
        "keywords": ["docker", "contenedor", "container", "logs", "inspect"],
        "tools": ["docker_list_containers", "docker_get_logs", "docker_inspect_container"]
    },
    "obsidian": {
        "keywords": ["obsidian", "notas", "notes", "sync", "sincronizar", "reflective"],
        "tools": ["sync_obsidian_vault", "generate_reflective_note"]
    },
    "diagnostic": {
        "keywords": ["diagnóstico", "diagnostic", "health", "salud", "self-diagnostic"],
        "tools": ["run_self_diagnostic"]
    },
    "docs": {
        "keywords": ["api reference", "referencia api", "curl", "guía", "guide",
                     "install", "instalar", "quick start", "setup",
                     "arquitectura", "architecture", "troubleshoot",
                     "variables env", "compose", "template"],
        "tools": ["get_quick_start_guide", "get_api_reference",
                  "get_docker_compose_example", "get_architecture_overview",
                  "get_troubleshooting_guide", "get_environment_variables_reference"]
    },
}


def classify_intent(query: str) -> List[str]:
    """
    Keyword-based intent classifier (0ms, deterministic).
    Returns list of tool names relevant to the query.
    """
    query_lower = query.lower()
    matched_tools: set = set()

    for group in TOOL_GROUPS.values():
        if any(kw in query_lower for kw in group["keywords"]):
            matched_tools.update(group["tools"])

    # Fallback: if no specific intent matched, use general query tool
    if not matched_tools:
        matched_tools = {"secure_query"}

    return list(matched_tools)


class ReactHarness:
    """
    V2.0 Harness: Lean ReAct loop with token budget enforcement.
    """

    def __init__(
        self,
        inference_provider: InferenceProviderPort,
        tool_registry: ToolRegistry,
        gatekeeper: Any,
        max_iterations: int = 5
    ) -> None:
        self.inference_provider = inference_provider
        self.tool_registry = tool_registry
        self.gatekeeper = gatekeeper
        self.max_iterations = max_iterations
        self.context_manager = ContextManager()

    @staticmethod
    def _build_identity(soul: str, user_profile: dict, source: str) -> str:
        """Build a compact identity block (~100 tokens)."""
        name = user_profile.get("assistant_name", "Zyra") if user_profile else "Zyra"
        tone = user_profile.get("tone", "professional") if user_profile else "professional"
        user_name = user_profile.get("name", "Usuario") if user_profile else "Usuario"
        role = user_profile.get("role", "") if user_profile else ""

        return (
            f"Identidad: {name} — Cerebro soberano de Zyrabit.\n"
            f"{soul}\n"
            f"Canal: {source} | Tono: {tone.upper()}\n"
            f"Usuario: {user_name} | Rol: {role}"
        )

    async def execute(
        self,
        user_query: str,
        system_prompt: str,
        history: list,
        rag_docs: list,
        user_profile: dict,
        source: str,
        token_map: Dict[str, str],
        model_name: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Runs the lean ReAct loop with lazy tool loading and token budget enforcement.
        Returns: (final_answer, steps_history)
        """
        # ── 1. Classify Intent → Filter Tools ──
        relevant_names = classify_intent(user_query)
        all_tools = await self.tool_registry.get_tools_definition()
        filtered_tools = [t for t in all_tools if t["name"] in relevant_names]

        logger.info(
            f"🎯 Intent Classifier: Loaded {len(filtered_tools)} tools "
            f"(of {len(all_tools)} total): {relevant_names}"
        )

        # ── 2. Build Compact Identity ──
        identity = self._build_identity(system_prompt, user_profile, source)

        # ── 3. Build System Prompt with Filtered Tools ──
        sys_prompt = PromptBuilder.build_react_system_prompt(
            identity=identity, tools=filtered_tools, compact=True
        )

        # ── 4. Sliding Window: Trim History (max 3 turns → ~600 tokens) ──
        history_str = self.context_manager.trim_history(
            history, budget=self.context_manager.REACT_HISTORY_BUDGET
        )

        # ── 5. Trim RAG Context ──
        rag_str = self.context_manager.trim_rag_context(
            rag_docs, budget=self.context_manager.REACT_RAG_BUDGET
        )

        # ── 6. Token Budget Validation ──
        initial_user_prompt = PromptBuilder.build_react_user_prompt(
            user_query=user_query,
            history_str=history_str,
            rag_context=rag_str,
            react_history=""
        )
        budget = self.context_manager.estimate_react_budget(sys_prompt, initial_user_prompt)

        if budget["over_budget"]:
            logger.warning(
                f"⚠️ Token budget EXCEEDED ({budget['total']}/{budget['limit']}). "
                f"Emergency compaction: dropping RAG, trimming history."
            )
            rag_str = ""
            history_str = self.context_manager.trim_history(history, budget=200)
            # Re-check after compaction
            initial_user_prompt = PromptBuilder.build_react_user_prompt(
                user_query=user_query, history_str=history_str
            )
            budget = self.context_manager.estimate_react_budget(sys_prompt, initial_user_prompt)

        logger.info(
            f"🤖 ReAct Harness: Starting loop for query: '{user_query[:80]}...' "
            f"(Token budget: {budget['total']}/{budget['limit']})"
        )

        # ── 7. ReAct Loop ──
        react_steps: List[str] = []
        steps_log: List[Dict[str, Any]] = []

        for iteration in range(self.max_iterations):
            # Build per-iteration prompt
            # History & RAG only on first iteration to save tokens
            user_prompt = PromptBuilder.build_react_user_prompt(
                user_query=user_query,
                history_str=history_str if iteration == 0 else "",
                rag_context=rag_str if iteration == 0 else "",
                react_history="\n".join(react_steps)
            )

            request = InferenceRequest(
                model=model_name,
                prompt=user_prompt,
                system_prompt=sys_prompt,
                options={"format": "json"}
            )

            # Generate step
            try:
                response_obj = await asyncio.to_thread(
                    self.inference_provider.generate, request
                )
                response_text = response_obj.text
            except Exception as e:
                logger.error(f"Inference error during ReAct step: {e}")
                return f"Error: Inference provider failed to respond. {e}", steps_log

            # Parse JSON response
            cleaned_response = clean_json_text(response_text)
            try:
                action_obj = ReActAction.model_validate_json(cleaned_response)
            except Exception as e:
                logger.warning(
                    f"⚠️ ReAct: Format parsing failure on step {iteration}: {e}"
                )
                react_steps.append(
                    f"Observation: Format Error: {e}. Respond with valid JSON only."
                )
                steps_log.append({
                    "step": iteration,
                    "action": "format_error",
                    "error": str(e)
                })
                continue

            logger.info(f"🧠 Thought: {action_obj.thought}")
            logger.info(f"🛠️ Action: {action_obj.action} → {action_obj.action_input}")

            steps_log.append({
                "step": iteration,
                "thought": action_obj.thought,
                "action": action_obj.action,
                "input": action_obj.action_input
            })

            # ── Final Answer? ──
            if action_obj.action == "final_answer":
                ans = action_obj.action_input.get("answer", "")
                if not ans:
                    ans = cleaned_response
                return ans, steps_log

            # ── Execute Tool (PII Sandwich) ──
            tool_name = action_obj.action
            tool_args = action_obj.action_input

            # A. Restore PII for tool parameters (de-anonymize)
            real_args = restore_pii_recursive(tool_args, token_map)

            # B. Execute tool
            try:
                tool_output = await self.tool_registry.execute_tool(tool_name, real_args)
                tool_output_str = str(tool_output)
            except Exception as e:
                tool_output_str = f"Error executing tool {tool_name}: {e}"

            # C. Re-mask PII in tool output and merge new tokens
            masked_output, new_tokens = self.gatekeeper.mask_pii(tool_output_str)
            token_map.update(new_tokens)

            # D. Trim observation to keep context budget lean
            if len(masked_output) > 1500:
                masked_output = masked_output[:1500] + "... [truncated for context budget]"

            logger.info(f"👁️ Observation: {masked_output[:200]}...")

            # Append compact step to loop history
            react_steps.append(f"Thought: {action_obj.thought}")
            react_steps.append(
                f"Action: {tool_name}({json.dumps(tool_args)})"
            )
            react_steps.append(f"Observation: {masked_output}")

        # ── Loop exhausted (Graceful Degradation) ──
        logger.warning("⚠️ ReAct Harness: Maximum iterations reached without final_answer.")
        
        fallback_msg = (
            "Parece que me he enredado un poco procesando tanta información. "
            "¿Podrías replantear tu pregunta o darme instrucciones más específicas?"
        )
        if steps_log:
            # Reasoning traces are operational telemetry only; never expose them to users.
                
        return fallback_msg, steps_log
