"""Runs both baseline (qwen alone) and qwen+ToG on the same sample of
val.json questions, scores both with EM/F1, writes results + report.

Usage: python -m src.run_experiment [n]   (run from expv2-1_tog_kqapro/ as cwd)
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from .baseline import answer_directly
from .kb import KB
from .llm import OllamaClient
from .metrics import exact_match, f1_score
from .sample_questions import load_sample
from .tog import answer_with_tog

MODEL = "qwen3:14b"


def _stats(values: list[float]) -> dict | None:
    return {"mean": round(statistics.mean(values), 3), "min": round(min(values), 3), "max": round(max(values), 3)} if values else None


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_dir = Path("runs") / time.strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True)

    client = OllamaClient()
    kb = KB()
    sample = load_sample(n)

    rows = []
    results_path = run_dir / "results.jsonl"
    with open(results_path, "w", encoding="utf-8") as results_f:
        for i, row in enumerate(sample, 1):
            q, gold = row["question"], row["answer"]
            base = answer_directly(client, MODEL, q)
            tog = answer_with_tog(client, MODEL, kb, q, max_hops=2)
            rec = {
                "question": q,
                "gold": gold,
                "baseline_answer": base["answer"],
                "baseline_em": exact_match(base["answer"], gold),
                "baseline_f1": f1_score(base["answer"], gold),
                "baseline_latency_s": base["latency_s"],
                "baseline_raw_content": base["raw_content"],
                "tog_answer": tog["answer"],
                "tog_em": exact_match(tog["answer"], gold),
                "tog_f1": f1_score(tog["answer"], gold),
                "tog_llm_calls": tog["llm_calls"],
                "tog_no_topic_entity": tog["no_topic_entity"],
                "tog_triplets": tog["triplets"],
                "tog_raw_content": tog["raw_content"],
                "tog_topic_entities": tog["topic_entities"],
                "tog_trace": tog["trace"],
            }
            rows.append(rec)
            results_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            results_f.flush()
            print(f"[{i}/{n}] base_em={rec['baseline_em']} tog_em={rec['tog_em']} "
                  f"no_topic={rec['tog_no_topic_entity']} | {q[:60]}")

    no_topic_rows = [r for r in rows if r["tog_no_topic_entity"]]
    with_topic_rows = [r for r in rows if not r["tog_no_topic_entity"]]

    def agg(rs: list[dict], prefix: str) -> dict:
        if not rs:
            return {"n": 0, "em": None, "f1": None}
        return {
            "n": len(rs),
            "em": round(sum(r[f"{prefix}_em"] for r in rs) / len(rs), 3),
            "f1": round(sum(r[f"{prefix}_f1"] for r in rs) / len(rs), 3),
        }

    overall_base = agg(rows, "baseline")
    overall_tog = agg(rows, "tog")
    sub_base = agg(with_topic_rows, "baseline")
    sub_tog = agg(with_topic_rows, "tog")
    base_latencies = [r["baseline_latency_s"] for r in rows]
    tog_calls = [r["tog_llm_calls"] for r in rows]

    lines = [
        "# expv2-1: qwen alone vs. qwen+ToG (over local KQA Pro kb.json)\n",
        f"- Model: {MODEL}",
        f"- Sample size: {n} questions from val.json (open-ended, 'choices' field ignored)",
        f"- Questions with no linkable topic entity (ToG falls back to no-KG): {len(no_topic_rows)}/{n}\n",
        "## Overall (all questions)\n",
        "| | EM | F1 |",
        "|---|---|---|",
        f"| Baseline (qwen alone) | {overall_base['em']} | {overall_base['f1']} |",
        f"| qwen + ToG | {overall_tog['em']} | {overall_tog['f1']} |\n",
        f"## Subset with a linkable topic entity (n={sub_base['n']}) — the only questions where ToG could actually use the KG\n",
        "| | EM | F1 |",
        "|---|---|---|",
        f"| Baseline (qwen alone) | {sub_base['em']} | {sub_base['f1']} |",
        f"| qwen + ToG | {sub_tog['em']} | {sub_tog['f1']} |\n",
        f"- Baseline latency (s): {_stats(base_latencies)}",
        f"- ToG LLM calls per question: {_stats([float(c) for c in tog_calls])}\n",
        "## Per-question detail\n",
    ]
    for r in rows:
        lines.append(
            f"- Q: {r['question']}\n"
            f"  gold={r['gold']!r} | baseline={r['baseline_answer']!r} (EM={r['baseline_em']}) | "
            f"tog={r['tog_answer']!r} (EM={r['tog_em']}, no_topic={r['tog_no_topic_entity']})"
        )

    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nOverall  baseline EM={overall_base['em']} F1={overall_base['f1']}  |  ToG EM={overall_tog['em']} F1={overall_tog['f1']}")
    print(f"With-topic-entity subset (n={sub_base['n']})  baseline EM={sub_base['em']} F1={sub_base['f1']}  |  ToG EM={sub_tog['em']} F1={sub_tog['f1']}")
    print(f"Wrote {run_dir}/results.jsonl and report.md")


if __name__ == "__main__":
    main()
