"""
PromptBuilder — Generates System Prompts for strict ReAct JSON loops.
V2.0: Supports compact mode and separated prompt composition.
"""
import json
from typing import List, Dict, Any


class PromptBuilder:
    """
    Constructs the ReAct agent system prompt with inlined dynamic tools schema
    and output formatting instructions.
    """

    @staticmethod
    def build_react_system_prompt(
        identity: str,
        tools: List[Dict[str, Any]],
        compact: bool = True
    ) -> str:
        """
        Build a token-efficient system prompt for the ReAct loop.
        compact=True renders tools as one-liners (saves ~800 tokens).
        compact=False includes full JSON Schema per tool.
        """
        if compact:
            tools_str = "\n".join(
                [f"- {t['name']}: {(t.get('description') or '')[:120]}" for t in tools]
            )
        else:
            tools_str = ""
            for t in tools:
                schema = t.get("inputSchema") or {}
                schema_str = json.dumps(schema, indent=2)
                tools_str += f"- {t['name']}: {t['description']}\n  Parameters: {schema_str}\n"

        return f"""{identity}

You MUST respond with a single valid JSON object for each turn:
{{"thought": "your reasoning", "action": "tool_name or final_answer", "action_input": {{}}}}

Available Tools:
{tools_str}
- final_answer: Use when ready to respond. Input: {{"answer": "your response to the user"}}

Rules:
- Your ENTIRE output must be a single parseable JSON object.
- NO markdown, NO code blocks, NO conversational text outside JSON.
- If the user's request maps directly to a tool, use it immediately.
- Use final_answer once you have all the information needed."""

    @staticmethod
    def build_react_user_prompt(
        user_query: str,
        history_str: str = "",
        rag_context: str = "",
        react_history: str = ""
    ) -> str:
        """
        Build the per-iteration user prompt for the ReAct loop.
        Keeps context minimal: history and RAG are only injected on the first iteration.
        """
        parts = []
        if history_str:
            parts.append(f"Conversation History:\n{history_str}")
        if rag_context:
            parts.append(f"Relevant Knowledge:\n{rag_context}")
        parts.append(f"User Query: {user_query}")
        if react_history:
            parts.append(f"\nPrevious Steps:\n{react_history}")
        parts.append("\nNext Step JSON:")
        return "\n\n".join(parts)

    # --- Legacy Method (kept for backward compatibility) ---
    @staticmethod
    def build_system_prompt(base_prompt: str, tools: List[Dict[str, Any]]) -> str:
        """Legacy builder used by older code paths. Prefer build_react_system_prompt()."""
        tools_str = ""
        for t in tools:
            schema = t.get("inputSchema") or {}
            schema_str = json.dumps(schema, indent=2)
            tools_str += f"- Tool Name: {t['name']}\n"
            tools_str += f"  Description: {t['description']}\n"
            tools_str += f"  Parameters (JSON Schema):\n{schema_str}\n\n"

        react_instructions = f"""
You are a sovereign agent operating in a Zero-Trust, air-gapped environment.
You MUST solve the user's request step-by-step using a ReAct (Reasoning and Acting) loop.

For every turn, you MUST respond with a single, valid JSON object containing exactly these keys:
1. "thought": Your reasoning about what to do next.
2. "action": The name of the tool to execute, OR "final_answer" if you have all the information required.
3. "action_input": A dictionary of arguments matching the tool's JSON Schema, OR a dictionary containing {{"answer": "your final message to the user"}} if the action is "final_answer".

DO NOT output any conversational text or markdown code blocks (like ```json) before or after the JSON.
Your entire response must be a single parseable JSON object.

Available Tools:
{tools_str}
- Tool Name: final_answer
  Description: Use this action when you have gathered all necessary information to respond to the user.
  Parameters (JSON Schema):
  {{
    "type": "object",
    "properties": {{
      "answer": {{
        "type": "string",
        "description": "The final markdown response for the user"
      }}
    }},
    "required": ["answer"]
  }}
"""
        return f"{base_prompt}\n{react_instructions}"
