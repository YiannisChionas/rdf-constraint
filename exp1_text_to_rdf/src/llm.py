"""Thin Ollama chat client used by both the agent and the converter.

Talks directly to the Ollama HTTP API (/api/chat) so we have full control
over `think`, `temperature` and structured-output `format` (JSON schema).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class ChatResult:
    content: str
    raw: dict[str, Any]
    latency_s: float


class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host.rstrip("/")

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        think: bool | None = None,
        format: dict | None = None,
    ) -> ChatResult:
        """Single-turn (non-streaming) chat call.

        Args:
            model: Ollama model tag, e.g. "qwen3:14b".
            messages: list of {"role": ..., "content": ...}.
            temperature: sampling temperature; None = model default.
            think: Qwen3 thinking mode toggle; None = model default.
            format: optional JSON schema dict to constrain the output
                    (Ollama structured outputs).
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if options:
            payload["options"] = options
        if think is not None:
            payload["think"] = think
        if format is not None:
            payload["format"] = format

        start = time.perf_counter()
        resp = requests.post(f"{self.host}/api/chat", json=payload, timeout=600)
        resp.raise_for_status()
        latency_s = time.perf_counter() - start

        data = resp.json()
        content = data.get("message", {}).get("content", "")
        return ChatResult(content=content, raw=data, latency_s=latency_s)
