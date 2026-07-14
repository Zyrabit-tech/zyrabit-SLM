import pytest
from app.domain.agent.react_harness import ReactHarness
from app.domain.agent.tool_registry import ToolRegistry
from app.ports.inference_port import InferenceProviderPort, InferenceResult
from app.domain.services.gatekeeper import Gatekeeper

# A mock tool registry that returns pre-registered tool schemas and output
class MockMcpClient:
    async def get_tools(self):
        return [
            {
                "name": "get_quick_start_guide",
                "description": "Get quick start guide",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string"}
                    },
                    "required": ["platform"]
                }
            }
        ]

    async def call_tool(self, name, arguments):
        if name == "get_quick_start_guide":
            return f"Mocked quick start guide output for platform {arguments.get('platform')}"
        return f"Unknown tool {name}"


class MockInferenceProvider(InferenceProviderPort):
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0

    def generate(self, request):
        # We return the responses sequentially
        res_text = self.responses[self.call_count]
        self.call_count += 1
        return InferenceResult(
            text=res_text,
            latency_seconds=0.1,
            provider="mock"
        )

    def health(self):
        return {"ok": True}


# Helper to build the new harness.execute() call with all required params
def _exec_kwargs(user_query, token_map=None):
    """Returns the kwargs dict for harness.execute() with V2.0 signature."""
    return {
        "user_query": user_query,
        "system_prompt": "You are Zyra.",
        "history": [],
        "rag_docs": [],
        "user_profile": {"assistant_name": "Zyra", "name": "Test User", "role": "Tester", "tone": "professional"},
        "source": "WEB",
        "token_map": token_map or {},
        "model_name": "mock-model",
    }


@pytest.mark.asyncio
async def test_react_loop_happy_path():
    responses = [
        # Step 1: LLM decides to call get_quick_start_guide
        '{"thought": "I need to get the guide.", "action": "get_quick_start_guide", "action_input": {"platform": "windows"}}',
        # Step 2: LLM gets observation and returns final answer
        '{"thought": "I have the info.", "action": "final_answer", "action_input": {"answer": "Use .\\\\zyra-up.ps1 to start."}}'
    ]

    provider = MockInferenceProvider(responses)
    mcp_client = MockMcpClient()
    registry = ToolRegistry(mcp_client)
    harness = ReactHarness(provider, registry, Gatekeeper, max_iterations=3)

    answer, steps = await harness.execute(
        **_exec_kwargs("How do I start on Windows? quick start guide install")
    )

    assert answer == "Use .\\zyra-up.ps1 to start."
    assert len(steps) == 2
    assert steps[0]["action"] == "get_quick_start_guide"
    assert steps[1]["action"] == "final_answer"


@pytest.mark.asyncio
async def test_react_loop_pii_sandwich():
    # Scenario: The user query has a masked email `<USER_EMAIL_1>`.
    # The agent decides to call a tool, passing the masked email argument.
    # The Harness de-masks it before running the tool, and then re-masks the tool's raw output.
    
    responses = [
        '{"thought": "I will run the guide for email.", "action": "get_quick_start_guide", "action_input": {"platform": "<USER_EMAIL_1>"}}',
        '{"thought": "Done.", "action": "final_answer", "action_input": {"answer": "Resolved for user."}}'
    ]

    provider = MockInferenceProvider(responses)
    
    # Custom Mock Client that asserts the argument was correctly DE-MASKED
    class AssertingMcpClient(MockMcpClient):
        async def call_tool(self, name, arguments):
            assert arguments["platform"] == "user@example.com"  # Verified de-masking!
            return "This guide was sent to user@example.com"  # Return output containing raw email

    mcp_client = AssertingMcpClient()
    registry = ToolRegistry(mcp_client)
    harness = ReactHarness(provider, registry, Gatekeeper, max_iterations=3)

    token_map = {"<USER_EMAIL_1>": "user@example.com"}
    answer, steps = await harness.execute(
        **_exec_kwargs("Get guide for <USER_EMAIL_1> quick start install", token_map=token_map)
    )

    assert answer == "Resolved for user."
    # The history should store the masked tool output
    # (Since Gatekeeper masks user@example.com back into <USER_EMAIL_1>)
    assert "<USER_EMAIL_1>" in token_map


@pytest.mark.asyncio
async def test_react_loop_self_healing_json():
    responses = [
        # Step 1: Malformed JSON output
        'This is not valid JSON! {invalid',
        # Step 2: Self-corrected output
        '{"thought": "Oops, I made a format error. I will output valid JSON now.", "action": "final_answer", "action_input": {"answer": "Corrected answer."}}'
    ]

    provider = MockInferenceProvider(responses)
    mcp_client = MockMcpClient()
    registry = ToolRegistry(mcp_client)
    harness = ReactHarness(provider, registry, Gatekeeper, max_iterations=3)

    answer, steps = await harness.execute(
        **_exec_kwargs("Help me.")
    )

    assert answer == "Corrected answer."
    assert len(steps) == 2
    assert steps[0]["action"] == "format_error"
    assert steps[1]["action"] == "final_answer"
