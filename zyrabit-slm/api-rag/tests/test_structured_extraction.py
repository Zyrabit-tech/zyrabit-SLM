import pytest
from app.ports.inference_port import InferenceProviderPort, InferenceRequest, InferenceResult
from app.domain.services.structured_extraction_service import StructuredExtractionService


class MockExtractionProvider(InferenceProviderPort):
    def __init__(self, returned_text: str):
        self.returned_text = returned_text

    def generate(self, request: InferenceRequest) -> InferenceResult:
        return InferenceResult(
            text=self.returned_text,
            latency_seconds=0.1,
            provider="mock-qwen2.5:7b",
        )

    def health(self) -> dict:
        return {"ok": True}


def test_extract_json_from_raw_and_markdown():
    # 1. Plain JSON string
    raw = '{"name": "Patient Alpha", "triage_level": 1, "symptoms": ["fever", "cough"]}'
    assert StructuredExtractionService.extract_json_block(raw) == {
        "name": "Patient Alpha",
        "triage_level": 1,
        "symptoms": ["fever", "cough"],
    }

    # 2. Markdown fenced block
    fenced = """Here is the extracted clinical data:
```json
{
  "name": "Journalist Beta",
  "location": "Sector 4",
  "verified": true
}
```
Please let me know if you need anything else."""
    assert StructuredExtractionService.extract_json_block(fenced) == {
        "name": "Journalist Beta",
        "location": "Sector 4",
        "verified": True,
    }

    # 3. Text containing JSON with leading/trailing chatter
    chatter = 'Extracted record: {"id": "REP-992", "status": "critical"} - end of transmission'
    assert StructuredExtractionService.extract_json_block(chatter) == {
        "id": "REP-992",
        "status": "critical",
    }


def test_schema_validation():
    schema = {
        "type": "object",
        "required": ["patient_id", "severity"],
        "properties": {
            "patient_id": {"type": "string"},
            "severity": {"type": "integer"},
            "notes": {"type": "string"},
        },
    }

    # Valid
    valid_data = {"patient_id": "P-101", "severity": 3, "notes": "Stable"}
    ok, errors = StructuredExtractionService.validate_schema(valid_data, schema)
    assert ok is True
    assert errors == []

    # Missing required field
    missing_data = {"patient_id": "P-101"}
    ok, errors = StructuredExtractionService.validate_schema(missing_data, schema)
    assert ok is False
    assert any("severity" in err for err in errors)

    # Type mismatch
    mismatch_data = {"patient_id": "P-101", "severity": "HIGH"}
    ok, errors = StructuredExtractionService.validate_schema(mismatch_data, schema)
    assert ok is False
    assert any("invalid type" in err for err in errors)


@pytest.mark.asyncio
async def test_end_to_end_extraction():
    schema = {
        "type": "object",
        "required": ["incident_type", "severity", "coordinates"],
        "properties": {
            "incident_type": {"type": "string"},
            "severity": {"type": "string"},
            "coordinates": {"type": "string"},
            "casualties": {"type": "integer"},
        },
    }

    mock_llm_response = """```json
{
  "incident_type": "Artillery Shelling",
  "severity": "CRITICAL",
  "coordinates": "34.0522 N, 118.2437 W",
  "casualties": 3
}
```"""

    provider = MockExtractionProvider(mock_llm_response)
    service = StructuredExtractionService(provider)

    result = await service.extract(
        text="Artillery shelling reported near hospital sector. Coordinates 34.0522 N, 118.2437 W. 3 casualties confirmed.",
        schema=schema,
    )

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["data"]["incident_type"] == "Artillery Shelling"
    assert result["data"]["casualties"] == 3
    assert result["model"] == "mock-qwen2.5:7b"
