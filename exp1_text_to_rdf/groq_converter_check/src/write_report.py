"""Write report.md from the already-saved extractions_groq.jsonl + the base
run's missed_facts.csv — no new Groq calls (reuses run_check's logic).

Usage: python -m src.write_report   (run from groq_converter_check/ as cwd)
"""
from __future__ import annotations

import csv
import statistics
from pathlib import Path

import yaml

from .run_check import fact_is_caught, load_jsonl, parse_fact


def _stats(values: list[float]) -> dict:
    return {"mean": round(statistics.mean(values), 3), "min": round(min(values), 3), "max": round(max(values), 3)} if values else None


def main() -> None:
    config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    base_run = Path(config["base_run"])
    model = config["groq"]["model"]

    extractions = load_jsonl("extractions_groq.jsonl")
    extractions_by_qid = {e["question_id"]: e for e in extractions}

    with open(base_run / "missed_facts.csv", newline="", encoding="utf-8") as f:
        missed_rows = [r for r in csv.DictReader(f) if (r.get("missed_facts") or "").strip() not in ("", "—")]

    # --- automatic metrics for the Groq converter pass itself ---
    n = len(extractions)
    parse_ok = sum(1 for e in extractions if e.get("parsed") is not None)
    latencies = [e["latency_s"] for e in extractions if e.get("latency_s") is not None]
    total_relationships = sum(len((e.get("parsed") or {}).get("relationships", [])) for e in extractions)

    # --- missed-facts cross-check, broken down by relation type ---
    by_relation: dict[str, dict[str, int]] = {}
    caught_list, missing_list = [], []
    for row in missed_rows:
        qid = row["question_id"]
        parsed = (extractions_by_qid.get(qid) or {}).get("parsed") or {}
        relationships = parsed.get("relationships", [])
        nodes_by_id = {node["id"]: node for node in parsed.get("nodes", [])}
        for fact in [f.strip() for f in row["missed_facts"].split(";") if f.strip()]:
            parsed_fact = parse_fact(fact)
            if parsed_fact is None:
                continue
            subj, rel, obj = parsed_fact
            by_relation.setdefault(rel, {"total": 0, "caught": 0})
            by_relation[rel]["total"] += 1
            entry = f"{qid}: {fact}"
            if fact_is_caught(subj, rel, obj, relationships, nodes_by_id):
                by_relation[rel]["caught"] += 1
                caught_list.append(entry)
            else:
                missing_list.append(entry)

    total = len(caught_list) + len(missing_list)

    lines = [
        "# Groq converter check — report\n",
        "## Purpose\n",
        "Same 20 agent answers as `../runs/20261102_125528/answers.jsonl` "
        "(qwen3:14b agent, unchanged), same schema.yaml/few_shot.json, same "
        "prompt — only the converter model changes, from qwen3:14b (Ollama) "
        f"to `{model}` (Groq). Checks how many of the 43 facts qwen3:14b's "
        "converter missed (`missed_facts.csv`, manually annotated) a "
        "stronger model catches.\n",
        "## Automatic metrics (Groq converter pass)\n",
        f"- Answers converted: {n}",
        f"- Parse success rate: {round(parse_ok / n, 3) if n else None}",
        f"- Total relationships extracted: {total_relationships} (qwen3:14b extracted 234 on the same answers)",
        f"- Converter latency (s): {_stats(latencies)}\n",
        "## Missed-facts recovery, by relation type\n",
        "| relation | total missed (qwen) | caught by Groq | recall |",
        "|---|---|---|---|",
    ]
    for rel in sorted(by_relation):
        d = by_relation[rel]
        rate = round(d["caught"] / d["total"], 3) if d["total"] else None
        lines.append(f"| {rel} | {d['total']} | {d['caught']} | {rate} |")
    overall_rate = round(len(caught_list) / total, 3) if total else None
    lines.append(f"| **all** | **{total}** | **{len(caught_list)}** | **{overall_rate}** |")

    lines.append(
        "\n**Reading this**: a high recall for a relation type here means qwen3:14b's "
        "misses on that relation are mostly a *model-strength* limitation (a "
        "stronger model fixes them on the same text/prompt). A low recall means "
        "the misses persist regardless of model — more likely a prompt/schema/task "
        "limitation than a qwen3:14b weakness specifically.\n"
    )

    lines.append("## Caught by Groq (heuristic name match — verify manually before citing)\n")
    lines += [f"- {e}" for e in caught_list] or ["- none"]
    lines.append("\n## Still missing with Groq too\n")
    lines += [f"- {e}" for e in missing_list] or ["- none"]

    Path("report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote report.md")


if __name__ == "__main__":
    main()
