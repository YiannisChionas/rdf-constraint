"""Agent call (call 1): question -> free-text biomedical answer."""
from __future__ import annotations

from .llm import OllamaClient, ChatResult


def generate_answer(
    client: OllamaClient,
    model: str,
    system_prompt: str,
    question: str,
    temperature: float | None = None,
    think: bool | None = None,
) -> ChatResult:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    return client.chat(model=model, messages=messages, temperature=temperature, think=think)
