"""Baseline: qwen answers the question directly, no KG at all."""
from __future__ import annotations

import re

from .llm import OllamaClient

SYSTEM_PROMPT = (
    "Answer the question. End your response with the final answer on its "
    "own line, in this exact format:\n"
    "ANSWER: <answer>\n"
    "The <answer> must be ONLY the bare answer itself (a name, number, "
    "date, or yes/no) — do not restate the question or add any other "
    "words. Example: if the question is \"Which city is bigger?\" and the "
    "answer is Paris, write exactly \"ANSWER: Paris\", not \"ANSWER: Paris "
    "is bigger\"."
)

_ANSWER_RE = re.compile(r"ANSWER:\s*(.+)", re.IGNORECASE)


def extract_answer(raw_content: str) -> str:
    matches = _ANSWER_RE.findall(raw_content)
    if matches:
        return matches[-1].strip().strip(".")
    return raw_content.strip().splitlines()[-1].strip() if raw_content.strip() else ""


def answer_directly(client: OllamaClient, model: str, question: str) -> dict:
    result = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
        think=False,
    )
    return {
        "raw_content": result.content,
        "answer": extract_answer(result.content),
        "latency_s": result.latency_s,
    }
