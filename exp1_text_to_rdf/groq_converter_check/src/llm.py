"""Groq chat client (standalone copy of exp3/exp4/exp5's GroqClient — no
cross-folder import dependency, same convention as elsewhere in this repo).
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
    """Maps `format=<json_schema>` onto Groq's forced tool-use, since Groq's
    native JSON-schema response_format support varies by model. Requires the
    GROK_API_KEY environment variable. Never hardcode it here.
    """

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
