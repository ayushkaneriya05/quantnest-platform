"""Provider boundary: SDK messages and continuation state never leave this module.

An adapter creates a conversation with ``step(results, final_only, feedback)``. Each step
returns text, normalized calls and reported usage. The workflow knows no SDK types.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from .schemas import ResearchResult

logger = logging.getLogger(__name__)


class ResearchError(ValueError):
    """Safe message for the application; SDK details belong in service logs."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ProviderStep:
    text: str = ""
    calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


class Conversation(Protocol):
    async def step(self, results: list[dict], *, final_only: bool, feedback: str = "") -> ProviderStep: ...


class Provider(Protocol):
    name: str
    model: str

    def conversation(self, request, instruction: str) -> Conversation: ...
    async def close(self) -> None: ...


def normalize_usage(usage):
    """The reported total already includes cached/reasoning tokens; never add them."""
    total = getattr(usage, "total_tokens", None)
    result = {
        "requests": 1,
        "complete": type(total) is int and total >= 0,
        "total_tokens": total if type(total) is int and total >= 0 else 0,
    }
    for key in (
        "total_input_tokens",
        "total_output_tokens",
        "total_thought_tokens",
        "total_cached_tokens",
        "total_tool_use_tokens",
    ):
        value = getattr(usage, key, None)
        if type(value) is int and value >= 0:
            result[key] = value
    return result


def gemini_schema(schema: dict) -> dict:
    """Keep the JSON shape; application validators enforce size/value bounds.

    Nested bounds can make Gemini's constrained decoder too expensive to compile
    or cause a 'too many states' rejection when tools and structured output combine.
    """
    constraints = {
        "title",
        "default",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
    }
    result = {key: value for key, value in schema.items() if key not in constraints}
    for key in ("properties", "$defs"):
        if key in result:
            result[key] = {name: gemini_schema(value) for name, value in result[key].items()}
    for key in ("items", "additionalProperties"):
        if isinstance(result.get(key), dict):
            result[key] = gemini_schema(result[key])
    for key in ("anyOf", "oneOf", "allOf"):
        if key in result:
            result[key] = [gemini_schema(value) for value in result[key]]
    return result


class GeminiProvider:
    name = "gemini"

    def __init__(self, model):
        from google import genai
        from google.genai import types

        self.model = model
        self.response_schema = gemini_schema(ResearchResult.model_json_schema())
        self.timeout = float(os.environ.get("RESEARCH_PROVIDER_TIMEOUT_SECONDS", "60"))
        self.thinking_level = os.environ.get("GEMINI_THINKING_LEVEL", "low")
        if self.timeout <= 0 or self.thinking_level not in {
            "minimal",
            "low",
            "medium",
            "high",
        }:
            raise RuntimeError("Set a positive provider timeout and a supported Gemini thinking level.")
        # This adapter owns retries. SDK retries otherwise multiply our attempts
        # and hide timeouts, costs and long waits from the research workflow.
        self.client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(
                timeout=int(self.timeout * 1000),
                retry_options=types.HttpRetryOptions(attempts=0),
            ),
        )
        # google-genai 2.28 changes attempts=0 to 1 during initialization,
        # then Interactions treats it as one retry. Disable that resource's
        # retry configuration explicitly so only the loop below can retry.
        self.client.aio.interactions.sdk_configuration.retry_config = None

    def conversation(self, request, instruction):
        return GeminiConversation(self, request, instruction)

    async def close(self):
        await self.client.aio.aclose()
        self.client.close()


class GeminiConversation:
    def __init__(self, provider, request, instruction):
        self.provider = provider
        self.instruction = instruction
        self.tools = [
            {"type": "function", **tool.model_dump(), "parameters": gemini_schema(tool.parameters)}
            for tool in request.tools
        ]
        self.history = []
        for turn in request.history:
            self.history.extend(
                [
                    {
                        "type": "user_input",
                        "content": [{"type": "text", "text": turn["prompt"]}],
                    },
                    {
                        "type": "model_output",
                        "content": [{"type": "text", "text": turn["answer"]}],
                    },
                    {
                        "type": "user_input",
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {key: value for key, value in turn.items() if key not in {"prompt", "answer"}}
                                ),
                            }
                        ],
                    },
                ]
            )
        self.history.append(
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "as_of": request.as_of,
                                "selected_context": request.context,
                                "prompt": request.prompt,
                            }
                        ),
                    }
                ],
            }
        )

    async def step(self, results, *, final_only, feedback=""):
        for result in results:
            self.history.append(
                {
                    "type": "function_result",
                    "name": result["name"],
                    "call_id": result["id"],
                    "result": [{"type": "text", "text": json.dumps(result["result"])}],
                }
            )
        if feedback:
            self.history.append({"type": "user_input", "content": [{"type": "text", "text": feedback}]})
        if final_only:
            self.history.append(
                {
                    "type": "user_input",
                    "content": [
                        {
                            "type": "text",
                            "text": "Return the final structured answer now from the available evidence. Explain any missing evidence; do not request more tools.",
                        }
                    ],
                }
            )
        arguments = dict(
            model=self.provider.model,
            input=self.history,
            system_instruction=self.instruction,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": self.provider.response_schema,
            },
            # A technical output bound, not a cumulative customer budget.
            generation_config={
                "max_output_tokens": 16384,
                "thinking_level": self.provider.thinking_level,
            },
            store=False,
            timeout=self.provider.timeout,
        )
        if self.tools and not final_only:
            arguments["tools"] = self.tools
        retried = False
        started = time.monotonic()
        try:
            # A wall-clock limit includes connection, generation, backoff and retry.
            # The overall research deadline still permits multiple model/tool rounds.
            async with asyncio.timeout(self.provider.timeout):
                for attempt in range(2):
                    try:
                        interaction = await self.provider.client.aio.interactions.create(**arguments)
                        break
                    except Exception as exc:
                        code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                        logger.warning(
                            "Gemini request failed category=%s status=%s attempt=%s duration_ms=%d",
                            type(exc).__name__,
                            code,
                            attempt + 1,
                            (time.monotonic() - started) * 1000,
                        )
                        cause = exc.__cause__
                        if isinstance(exc, (TimeoutError, httpx.TimeoutException)) or isinstance(
                            cause, httpx.TimeoutException
                        ):
                            raise TimeoutError from exc
                        if attempt == 0 and code in (429, 500, 502, 503, 504):
                            retried = True
                            await asyncio.sleep(1)
                            continue
                        if code in (401, 403):
                            message = "The AI provider rejected its credentials or project permissions. Check the research service configuration."
                        elif code == 400:
                            message = "The AI provider rejected the model parameters or research schema. Check the research service configuration."
                        elif code == 429:
                            message = (
                                "The AI provider is rate limited or its project quota is exhausted. Please retry later."
                            )
                        elif code in (500, 502, 503, 504):
                            message = "The AI provider is temporarily unavailable. Please retry."
                        else:
                            message = "The AI provider could not complete the request. Check the research service logs and provider configuration."
                        raise ResearchError(message) from exc
        except TimeoutError as exc:
            logger.warning(
                "Gemini request timed out model=%s duration_ms=%d",
                self.provider.model,
                (time.monotonic() - started) * 1000,
            )
            raise ResearchError(
                f"The AI provider did not respond within {self.provider.timeout:g} seconds. Please retry."
            ) from exc
        steps = interaction.steps or []
        self.history.extend(step.model_dump(mode="json", exclude_none=True) for step in steps)
        usage = normalize_usage(interaction.usage)
        # A failed transport attempt may have consumed tokens without reporting them.
        if retried:
            usage["complete"] = False
        text = interaction.output_text or "".join(
            content.text
            for step in steps
            if step.type == "model_output"
            for content in step.content
            if content.type == "text"
        )
        calls = [ToolCall(step.id, step.name, step.arguments) for step in steps if step.type == "function_call"]
        logger.info(
            "Gemini response model=%s duration_ms=%d tools=%d tokens=%d thought_tokens=%d retried=%s",
            self.provider.model,
            (time.monotonic() - started) * 1000,
            len(calls),
            usage["total_tokens"],
            usage.get("total_thought_tokens", 0),
            retried,
        )
        return ProviderStep(text=text, calls=calls, usage=usage)


PROVIDERS = {"gemini": GeminiProvider}


def create_provider():
    name = os.environ.get("RESEARCH_PROVIDER", "gemini")
    if name not in PROVIDERS:
        raise RuntimeError(f"Unsupported research provider: {name}")
    return PROVIDERS[name](os.environ.get("RESEARCH_MODEL", "gemini-3.5-flash"))
