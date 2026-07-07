"""
PromptBuilder — Generates System Prompts for strict ReAct JSON loops.
"""
import json
from typing import List, Dict, Any


class PromptBuilder:
    """
    Constructs the ReAct agent system prompt with inlined dynamic tools schema
    and output formatting instructions.
    """

    @staticmethod
    def build_system_prompt(base_prompt: str, tools: List[Dict[str, Any]]) -> str:
        # Build tools description string with parameter specifications
        tools_str = ""
        for t in tools:
            # Format inputSchema nicely
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
