import json
import os
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from google.genai import interactions
from .main import app
from .provider import research_events
from .schemas import ResearchRequest


def request():
    schema = {name: [{"value": value}] for name, value in {"OperandType": "CLOSE", "CandleTimeframe": "1D", "ComparisonOperator": "GT"}.items()}
    return ResearchRequest(prompt="Compare", run_token="signed", as_of="2026-10-03T00:00:00Z", context={"instrument_ids": [1]}, builder_schema=schema)


class ProviderTests(IsolatedAsyncioTestCase):
    @patch.dict(os.environ, {"RESEARCH_SERVICE_TOKEN": "private", "GEMINI_API_KEY": "mock"})
    async def test_stateless_tool_history_and_structured_result(self):
        tool_step = {"type": "function_call", "id": "call1", "name": "get_strategy_snapshot", "arguments": {}}
        first = interactions.Interaction.model_validate({"status": "completed", "steps": [tool_step]})
        result = {"answer": "Evidence [E1]", "evidence_ids": ["E1"], "draft_evidence_id": None, "next_steps": [], "limitations": []}
        final = interactions.Interaction.model_validate({"status": "completed", "steps": [{"type": "model_output", "content": [{"type": "text", "text": json.dumps(result)}]}]})
        calls = []
        async def create(**kwargs):
            calls.append(json.loads(json.dumps(kwargs)))
            return [first, final, final][len(calls) - 1]
        client = SimpleNamespace(aio=SimpleNamespace(interactions=SimpleNamespace(create=create)))
        gateway = AsyncMock()
        gateway.__aenter__.return_value = gateway
        response = SimpleNamespace(status_code=200, json=lambda: {"evidence_id": "E1", "data": {"name": "Saved"}})
        gateway.post.return_value = response
        with patch("research_service.provider.httpx.AsyncClient", return_value=gateway):
            events = [event async for event in research_events(request(), client)]
        self.assertEqual({key: events[-1]["result"][key] for key in result}, result)
        self.assertEqual(events[-1]["result"]["proposed_actions"], [])
        self.assertTrue(all(call["store"] is False for call in calls))
        self.assertIn(tool_step, calls[1]["input"])
        self.assertEqual(calls[1]["input"][-1]["type"], "function_result")
        self.assertEqual(gateway.post.call_args.kwargs["headers"]["X-Research-Run-Token"], "signed")
        self.assertIn("response_format", calls[-1])


class ServiceTests(TestCase):
    @patch.dict(os.environ, {"RESEARCH_SERVICE_TOKEN": "private", "GEMINI_API_KEY": "mock"})
    def test_private_auth_and_stream(self):
        async def events(payload, client):
            yield {"type": "progress", "message": "Calculating"}
            yield {"type": "result", "result": {"answer": "Complete", "evidence_ids": []}}
        with patch("research_service.main.research_events", events), TestClient(app) as client:
            self.assertEqual(client.post("/research", json=request().model_dump()).status_code, 403)
            response = client.post("/research", json=request().model_dump(), headers={"X-Research-Service-Token": "private"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual([json.loads(line)["type"] for line in response.text.splitlines()], ["progress", "result"])
