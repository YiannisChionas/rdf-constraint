"""Thin Ollama chat client (standalone copy of exp1_text_to_rdf/src/llm.py,
kept duplicated so this experiment has no cross-folder import dependency).

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
