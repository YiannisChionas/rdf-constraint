"""Deterministic sample of N questions from val.json (has gold answers;
test.json does not). Ignores the 'choices' field on purpose — open-ended
generation, not multiple-choice (see README for why)."""
from __future__ import annotations

import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_sample(n: int = 30, seed: int = 0) -> list[dict]:
    val = json.loads((DATA_DIR / "val.json").read_text(encoding="utf-8"))
    rng = random.Random(seed)
    sample = rng.sample(val, n)
    return [{"question": r["question"], "answer": r["answer"]} for r in sample]


if __name__ == "__main__":
    for row in load_sample(5):
        print(row)
