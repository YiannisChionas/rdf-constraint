"""Thin Groq chat client, built to match exp2_shacl_agent's OllamaClient
interface exactly: chat(model, messages, temperature, think, format) ->
ChatResult(content, raw, latency_s). This lets shape_agent.py and
run_experiment.py stay unchanged beyond swapping which client class gets
instantiated - the same "LLM decides content, Python renders syntax" design
from exp2 carries over untouched.

Structured output: Groq's chat completions API is OpenAI-compatible.
Ollama's `format=<json_schema>` is mapped onto Groq's forced tool-use (same
approach as the abandoned Claude version of this experiment, since Groq's
JSON-schema response_format support varies by model) - a single tool whose
`parameters` is our json_schema, with `tool_choice` forcing that exact tool
to be called. The tool call's `arguments` (already a JSON string) is used
directly as ChatResult.content, so shape_agent.generate_shapes()'s existing
`json.loads(result.content)` call works unchanged.

`think` is accepted for interface parity but ignored: the model used here
(openai/gpt-oss-120b) has no separate "thinking" mode exposed via this API,
and every config in this project already sets think=false regardless of
backend, so this is a no-op either way.

Requires the GROK_API_KEY environment variable to be set, holding a Groq
(not xAI Grok) API key - named GROK_API_KEY rather than the groq SDK's
default GROQ_API_KEY because that is what was already set in this
project's environment; passed explicitly to the client below rather than
relying on the SDK's auto-detection of GROQ_API_KEY. Never hardcode it here.

Retries once on transient 429 rate-limit errors (free-tier tokens-per-minute
throttling recovers within a fraction of a second - the API itself reports
the wait time), distinct from the permanent 413 "request too large" case
(a single request exceeding the free tier's TPM budget outright), which
run_experiment.py catches separately and records as a skip, since no amount
of waiting/retrying fixes that one.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from groq import Groq, RateLimitError


@dataclass
class ChatResult:
    content: str
    raw: dict[str, Any]
    latency_s: float


class GroqClient:
    def __init__(self, max_tokens: int = 2048):
        self._client = Groq(api_key=os.environ["GROK_API_KEY"])
        self.max_tokens = max_tokens

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        think: bool | None = None,
        format: dict | None = None,
    ) -> ChatResult:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if format is not None:
            kwargs["tools"] = [{
                "type": "function",
                "function": {
                    "name": "emit_result",
                    "description": "Emit the structured result for this task.",
                    "parameters": format,
                },
            }]
            kwargs["tool_choice"] = {"type": "function", "function": {"name": "emit_result"}}

        start = time.perf_counter()
        for attempt in range(5):
            try:
                completion = self._client.chat.completions.create(**kwargs)
                break
            except RateLimitError:
                if attempt == 4:
                    raise
                time.sleep(2 * (attempt + 1))
        latency_s = time.perf_counter() - start

        choice = completion.choices[0]
        tool_calls = choice.message.tool_calls
        if tool_calls:
            content = tool_calls[0].function.arguments
        else:
            content = choice.message.content or ""

        usage = completion.usage
        raw = {
            "id": completion.id,
            "model": completion.model,
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
            } if usage else {},
        }
        return ChatResult(content=content, raw=raw, latency_s=latency_s)
