"""
ReactHarness — Orchestrates the 5-step ReAct loop with validation and PII Sandwich.
"""
import re
import json
import logging
import asyncio
from typing import Dict, Any, Tuple, List, Optional
from pydantic import BaseModel, Field

from app.domain.agent.prompt_builder import PromptBuilder
from app.domain.agent.tool_registry import ToolRegistry
from app.ports.inference_port import InferenceProviderPort, InferenceRequest
from app.core.security.pii_pipeline import deanonymize_text
from app.domain.services.context_manager import ContextManager

logger = logging.getLogger("zyrabit.agent.harness")


class ReActAction(BaseModel):
    thought: str = Field(description="Your reasoning and thoughts about the query and what action to take next.")
    action: str = Field(description="The name of the tool to execute or 'final_answer'")
    action_input: Dict[str, Any] = Field(default_factory=dict, description="Parameters dictionary for the action")


def clean_json_text(text: str) -> str:
    """Removes markdown wrappers or surrounding text to isolate the raw JSON block."""
    cleaned = text.strip()
    # Attempt to extract text inside ```json ... ```
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


class ReactHarness:
    """
    Harness executing the ReAct agentic loop.
    Enforces format constraints, manages context budgeting, and implements the PII Sandwich.
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

    async def execute(
        self,
        user_query: str,
        base_system_prompt: str,
        token_map: Dict[str, str],
        model_name: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Runs the ReAct loop.
        Returns: (final_answer, steps_history)
        """
        # 1. Discover tools and build initial prompt
        tools = await self.tool_registry.get_tools_definition()
        system_prompt = PromptBuilder.build_system_prompt(base_system_prompt, tools)

        # We construct the conversation history
        history: List[str] = []
        steps_log: List[Dict[str, Any]] = []

        logger.info(f"🤖 ReAct Harness: Starting loop for query: '{user_query}'")

        for iteration in range(self.max_iterations):
            # Compose the current prompt with history
            history_str = "\n".join(history)
            current_prompt = f"{user_query}\n\n{history_str}\n\nNext Step JSON:"

            # Prepare the inference request with strict JSON format options
            request = InferenceRequest(
                model=model_name,
                prompt=current_prompt,
                system_prompt=system_prompt,
                options={"format": "json"}
            )

            # Generate step (run in threadpool as adapter is synchronous)
            try:
                response_obj = await asyncio.to_thread(self.inference_provider.generate, request)
                response_text = response_obj.text
            except Exception as e:
                logger.error(f"Inference error during ReAct step: {e}")
                return f"Error: Inference provider failed to respond. {e}", steps_log

            # Clean and parse JSON
            cleaned_response = clean_json_text(response_text)
            try:
                action_obj = ReActAction.model_validate_json(cleaned_response)
            except Exception as e:
                # Format validation failed. Feed error back as observation to self-heal
                logger.warning(f"⚠️ ReAct Harness: Format parsing failure on step {iteration}: {e}")
                error_msg = f"Format Error: Output is not a valid JSON matching the schema. Error: {e}. Please try again."
                history.append(f"Observation: {error_msg}")
                steps_log.append({
                    "step": iteration,
                    "thought": "Failed to parse thought/action.",
                    "action": "format_error",
                    "error": str(e)
                })
                continue

            # Record successfully parsed step
            logger.info(f"🧠 Thought: {action_obj.thought}")
            logger.info(f"🛠️ Action: {action_obj.action} with input {action_obj.action_input}")

            steps_log.append({
                "step": iteration,
                "thought": action_obj.thought,
                "action": action_obj.action,
                "input": action_obj.action_input
            })

            # Check if we reached the final answer
            if action_obj.action == "final_answer":
                ans = action_obj.action_input.get("answer", "")
                if not ans:
                    # Fallback if final_answer was structured weirdly
                    ans = cleaned_response
                return ans, steps_log

            # Execute tool (PII Sandwich)
            tool_name = action_obj.action
            tool_args = action_obj.action_input

            # A. Restore PII for tool parameters
            real_args = restore_pii_recursive(tool_args, token_map)

            # B. Execute tool
            try:
                tool_output = await self.tool_registry.execute_tool(tool_name, real_args)
                tool_output_str = str(tool_output)
            except Exception as e:
                tool_output_str = f"Error executing tool {tool_name}: {e}"

            # C. Re-mask PII inside tool output (observation) and merge new tokens
            masked_output, new_tokens = self.gatekeeper.mask_pii(tool_output_str)
            token_map.update(new_tokens)

            # D. Budget context: trim observations if they are too long
            # (e.g. if logs are huge, we keep first 2000 chars)
            if len(masked_output) > 2000:
                masked_output = masked_output[:2000] + "... [Observation truncated for context budget]"

            logger.info(f"👁️ Observation: {masked_output}")

            # Append the thought and observation to the running history
            history.append(f'Thought: {action_obj.thought}')
            history.append(f'Action: {tool_name}({json.dumps(tool_args)})')
            history.append(f'Observation: {masked_output}')

        # If loop exited without hitting final_answer
        logger.warning("⚠️ ReAct Harness: Maximum iterations reached without final_answer.")
        return "Error: Maximum iterations reached without resolving query.", steps_log
