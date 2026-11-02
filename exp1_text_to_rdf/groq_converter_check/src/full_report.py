"""Builds graphs/*.ttl, runs per-question SHACL validation, writes empty
annotation.csv/missed_facts.csv templates, plots the recovery chart, and
writes the final report.md — everything that doesn't need a new Groq call.

Usage: python -m src.full_report   (run from groq_converter_check/ as cwd)
"""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

import yaml
from pyshacl import validate
from rdflib import Graph

from .run_check import fact_is_caught, load_jsonl, parse_fact
from .to_rdf import json_to_graph, serialize_graph

SHAPES_PATH = Path("../shacl_poc/shapes/gene_shapes.ttl")


def _stats(values: list[float]) -> dict | None:
    return {"mean": round(statistics.mean(values), 3), "min": round(min(values), 3), "max": round(max(values), 3)} if values else None


def build_graphs(extractions: list[dict], schema: dict) -> None:
    graphs_dir = Path("graphs")
    graphs_dir.mkdir(exist_ok=True)
    for e in extractions:
        if e.get("parsed") is None:
            continue
        g, warnings = json_to_graph(e["parsed"], schema)
        for w in warnings:
            print(f"[to_rdf] {e['question_id']}: {w}")
        serialize_graph(g, graphs_dir / f"{e['question_id']}.ttl")


def run_shacl() -> tuple[int, int]:
    shapes_graph = Graph()
    shapes_graph.parse(SHAPES_PATH, format="turtle")

    total_violations = total_warnings = 0
    lines = []
    for f in sorted(Path("graphs").glob("*.ttl")):
        data_graph = Graph()
        data_graph.parse(f, format="turtle")
        conforms, _, results_text = validate(data_graph, shacl_graph=shapes_graph, inference="none", abort_on_first=False)
        nv = results_text.count("Severity: sh:Violation")
        nw = results_text.count("Severity: sh:Warning")
        total_violations += nv
        total_warnings += nw
        if nv or nw:
            lines.append(f"--- {f} ({len(data_graph)} triples): violations={nv} warnings={nw} ---")
            lines.append(results_text)
    lines.append(f"\nFiles checked: {len(list(Path('graphs').glob('*.ttl')))}")
    lines.append(f"Total violations: {total_violations}")
    lines.append(f"Total warnings: {total_warnings}")
    Path("shacl_check.txt").write_text("\n".join(lines), encoding="utf-8")
    return total_violations, total_warnings


def write_annotation_template(extractions: list[dict]) -> None:
    path = Path("annotation.csv")
    if path.exists():
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["question_id", "subject", "relation", "object", "supported_by_text", "correct_types", "notes"])
        for rec in extractions:
            parsed = rec.get("parsed")
            if not parsed:
                continue
            qid = rec.get("question_id")
            nodes_by_id = {n.get("id"): n for n in parsed.get("nodes", [])}
            for rel in parsed.get("relationships", []):
                src = nodes_by_id.get(rel.get("source"))
                tgt = nodes_by_id.get(rel.get("target"))
                subj = src.get("name") if src else rel.get("source")
                obj = tgt.get("name") if tgt else rel.get("target")
                writer.writerow([qid, subj, rel.get("relation"), obj, "", "", ""])
    print(f"Wrote empty {path} — fill it in by hand if you want precision/SHACL-catch-rate numbers too.")


def write_missed_facts_template(extractions: list[dict]) -> None:
    path = Path("missed_facts.csv")
    if path.exists():
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["question_id", "missed_facts"])
        for e in extractions:
            writer.writerow([e["question_id"], ""])
    print(f"Wrote empty {path}.")


def plot_recovery_chart(by_qid: dict[str, dict[str, int]], path: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    qids = sorted(by_qid)
    recovered = [by_qid[q]["caught"] for q in qids]
    still_missing = [by_qid[q]["missing"] for q in qids]

    x = np.arange(len(qids))
    width = 0.4
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.bar(x - width / 2, recovered, width, label="recovered by Groq", color="seagreen")
    ax.bar(x + width / 2, still_missing, width, label="still missing", color="indianred")
    ax.set_xticks(x, qids)
    ax.set_xlabel("question_id")
    ax.set_ylabel("# of qwen3:14b's missed facts")
    ax.set_title("Of qwen3:14b's missed facts, how many does Groq recover? (per question)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    base_run = Path(config["base_run"])
    model = config["groq"]["model"]

    schema = yaml.safe_load((base_run / "schema.yaml").read_text(encoding="utf-8"))
    extractions = load_jsonl("extractions_groq.jsonl")
    extractions_by_qid = {e["question_id"]: e for e in extractions}

    build_graphs(extractions, schema)
    n_violations, n_warnings = run_shacl()
    write_annotation_template(extractions)
    write_missed_facts_template(extractions)

    # --- automatic metrics ---
    n = len(extractions)
    parse_ok = sum(1 for e in extractions if e.get("parsed") is not None)
    latencies = [e["latency_s"] for e in extractions if e.get("latency_s") is not None]
    total_relationships = sum(len((e.get("parsed") or {}).get("relationships", [])) for e in extractions)

    # --- missed-facts recovery, overall + by relation + by question ---
    with open(base_run / "missed_facts.csv", newline="", encoding="utf-8") as f:
        missed_rows = [r for r in csv.DictReader(f) if (r.get("missed_facts") or "").strip() not in ("", "—")]

    by_relation: dict[str, dict[str, int]] = {}
    by_qid: dict[str, dict[str, int]] = {}
    caught_list, missing_list = [], []
    for row in missed_rows:
        qid = row["question_id"]
        by_qid.setdefault(qid, {"caught": 0, "missing": 0})
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
                by_qid[qid]["caught"] += 1
                caught_list.append(entry)
            else:
                by_qid[qid]["missing"] += 1
                missing_list.append(entry)

    total = len(caught_list) + len(missing_list)
    all_qids = sorted({e["question_id"] for e in extractions})
    for q in all_qids:
        by_qid.setdefault(q, {"caught": 0, "missing": 0})
    plot_recovery_chart(by_qid, "recovery_chart.png")

    # --- report.md ---
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
        "## SHACL (structural, per-question — fully automatic, no annotation needed)\n",
        f"- Violations: {n_violations}",
        f"- Warnings: {n_warnings}",
        "- Full detail: `shacl_check.txt`\n",
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
        "\n**Reading this**: a high recall for a relation type means qwen3:14b's "
        "misses on that relation are mostly a *model-strength* limitation (a "
        "stronger model fixes them on the same text/prompt). A low recall means "
        "the misses persist regardless of model — more likely a prompt/schema/task "
        "limitation than a qwen3:14b weakness specifically.\n"
    )
    lines.append("![Recovery per question](recovery_chart.png)\n")

    lines.append("## Caught by Groq (heuristic name match — verify manually before citing)\n")
    lines += [f"- {e}" for e in caught_list] or ["- none"]
    lines.append("\n## Still missing with Groq too\n")
    lines += [f"- {e}" for e in missing_list] or ["- none"]

    lines.append(
        "\n## Note on annotation.csv/missed_facts.csv\n\n"
        "Written as empty templates (same format as exp1's). Filling them in "
        "would let us compute this run's own precision and SHACL-catch-rate "
        "confusion matrix, same as exp1's report — not done here since it "
        "needs a fresh human read of all 20 answers against Groq's own "
        "extractions, which is separate work from the missed-facts recovery "
        "check above."
    )

    Path("report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Violations={n_violations} Warnings={n_warnings}")
    print("Wrote report.md, shacl_check.txt, recovery_chart.png, graphs/, annotation.csv, missed_facts.csv")


if __name__ == "__main__":
    main()
