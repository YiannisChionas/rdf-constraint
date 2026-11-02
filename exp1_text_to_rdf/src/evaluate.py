"""Automatic metrics + manual-annotation scaffolding for a run.

Can be invoked standalone on an existing run directory, after annotation.csv
and missed_facts.csv have been filled in by hand:

    python -m src.evaluate runs/<timestamp>
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

import jsonschema
import yaml

from .converter import build_json_schema
from .to_rdf import validate_turtle_roundtrip


def load_jsonl(path: str | Path) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _domain_range_ok(rel: dict, nodes_by_id: dict, schema: dict) -> bool:
    spec = schema["relations"].get(rel.get("relation"))
    if spec is None:
        return False
    src = nodes_by_id.get(rel.get("source"))
    tgt = nodes_by_id.get(rel.get("target"))
    if src is None or tgt is None:
        return False
    return src.get("type") == spec["source"] and tgt.get("type") == spec["target"]


def _stats(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "min": None, "max": None}
    return {"mean": statistics.mean(values), "min": min(values), "max": max(values)}


def _mentioned_in_text(name: str, text: str) -> bool:
    """Text2KGBench-style hallucination check: does this entity name appear
    (case-insensitive substring) in the source text it was extracted from?"""
    name = (name or "").strip().lower()
    if not name:
        return False
    return name in (text or "").lower()


def compute_metrics(answers: list[dict], extractions: list[dict], schema: dict, graphs_dir: str | Path) -> dict:
    n = len(extractions)
    json_schema = build_json_schema(schema)

    parse_ok = 0
    schema_valid = 0
    total_relationships = 0
    domain_range_ok_count = 0
    dangling_count = 0
    duplicate_count = 0
    zero_rel_answers = 0
    nodes_per_answer: list[int] = []
    triples_per_answer: list[int] = []
    relation_counts: dict[str, int] = {}
    ttl_roundtrip_ok = 0
    ttl_roundtrip_total = 0
    subject_hallucinated = 0
    object_hallucinated = 0
    hallucination_checked = 0

    answers_by_id = {a.get("question_id"): a for a in answers}

    for rec in extractions:
        parsed = rec.get("parsed")
        qid = rec.get("question_id")
        answer_text = answers_by_id.get(qid, {}).get("answer", "")
        if parsed is not None:
            parse_ok += 1
        else:
            nodes_per_answer.append(0)
            triples_per_answer.append(0)
            zero_rel_answers += 1
            continue

        try:
            jsonschema.validate(parsed, json_schema)
            schema_valid += 1
        except jsonschema.ValidationError:
            pass

        nodes = parsed.get("nodes", [])
        rels = parsed.get("relationships", [])
        nodes_by_id = {node.get("id"): node for node in nodes}

        nodes_per_answer.append(len(nodes))
        triples_per_answer.append(len(rels))
        total_relationships += len(rels)
        if len(rels) == 0:
            zero_rel_answers += 1

        seen = set()
        for node in nodes:
            key = (node.get("type"), str(node.get("name", "")).strip().lower())
            if key in seen:
                duplicate_count += 1
            else:
                seen.add(key)

        for rel in rels:
            relation_counts[rel.get("relation")] = relation_counts.get(rel.get("relation"), 0) + 1
            if rel.get("source") not in nodes_by_id or rel.get("target") not in nodes_by_id:
                dangling_count += 1
                continue
            if _domain_range_ok(rel, nodes_by_id, schema):
                domain_range_ok_count += 1

            src_name = nodes_by_id[rel.get("source")].get("name", "")
            tgt_name = nodes_by_id[rel.get("target")].get("name", "")
            hallucination_checked += 1
            if not _mentioned_in_text(src_name, answer_text):
                subject_hallucinated += 1
            if not _mentioned_in_text(tgt_name, answer_text):
                object_hallucinated += 1

        ttl_path = Path(graphs_dir) / f"{qid}.ttl"
        if ttl_path.exists():
            ttl_roundtrip_total += 1
            if validate_turtle_roundtrip(ttl_path):
                ttl_roundtrip_ok += 1

    agent_latencies = [a.get("latency_s") for a in answers if a.get("latency_s") is not None]
    converter_latencies = [e.get("latency_s") for e in extractions if e.get("latency_s") is not None]
    valid_rel_count = total_relationships - dangling_count

    return {
        "n_answers": n,
        "parse_success_rate": parse_ok / n if n else None,
        "json_schema_valid_rate": schema_valid / n if n else None,
        "domain_range_correct_rate": (domain_range_ok_count / valid_rel_count) if valid_rel_count else None,
        "dangling_reference_count": dangling_count,
        "duplicate_node_count": duplicate_count,
        "turtle_roundtrip_success_rate": (ttl_roundtrip_ok / ttl_roundtrip_total) if ttl_roundtrip_total else None,
        "nodes_per_answer": _stats(nodes_per_answer),
        "triples_per_answer": _stats(triples_per_answer),
        "relation_counts": relation_counts,
        "pct_zero_relationships": zero_rel_answers / n if n else None,
        "agent_latency_s": _stats(agent_latencies),
        "converter_latency_s": _stats(converter_latencies),
        "subject_hallucination_rate": (subject_hallucinated / hallucination_checked) if hallucination_checked else None,
        "object_hallucination_rate": (object_hallucinated / hallucination_checked) if hallucination_checked else None,
    }


def write_annotation_csv(extractions: list[dict], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["question_id", "subject", "relation", "object", "supported_by_text", "correct_types", "notes"]
        )
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


def write_missed_facts_csv(answers: list[dict], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["question_id", "missed_facts"])
        for a in answers:
            writer.writerow([a.get("question_id"), ""])


def _round3(x):
    if isinstance(x, float):
        return round(x, 3)
    if isinstance(x, dict):
        return {k: _round3(v) for k, v in x.items()}
    return x


def write_report(
    path: str | Path,
    metrics: dict,
    extractions: list[dict],
    annotation_result: dict | None = None,
    missed_facts: list[dict] | None = None,
    shacl_catch: dict | None = None,
    missed_facts_chart: str | None = None,
    shacl_confusion_chart: str | None = None,
) -> None:
    lines: list[str] = []
    lines.append("# Experiment 1 Report: Agent Answer -> RDF\n")

    lines.append("## Automatic metrics\n")
    lines.append(f"- Answers evaluated: {metrics['n_answers']}")
    lines.append(f"- Converter JSON parse success rate: {_round3(metrics['parse_success_rate'])}")
    lines.append(f"- JSON-schema-valid rate: {_round3(metrics['json_schema_valid_rate'])}")
    lines.append(f"- Domain/range correctness rate: {_round3(metrics['domain_range_correct_rate'])}")
    lines.append(f"- Dangling references: {metrics['dangling_reference_count']}")
    lines.append(f"- Duplicate nodes: {metrics['duplicate_node_count']}")
    lines.append(f"- Turtle round-trip parse success rate: {_round3(metrics['turtle_roundtrip_success_rate'])}")
    lines.append(f"- Nodes per answer: {_round3(metrics['nodes_per_answer'])}")
    lines.append(f"- Triples per answer: {_round3(metrics['triples_per_answer'])}")
    lines.append(f"- Relation counts: {metrics['relation_counts']}")
    lines.append(f"- % answers with zero extracted relationships: {_round3(metrics['pct_zero_relationships'])}")
    lines.append(f"- Agent latency (s): {_round3(metrics['agent_latency_s'])}")
    lines.append(f"- Converter latency (s): {_round3(metrics['converter_latency_s'])}")
    lines.append(f"- Subject hallucination rate (Text2KGBench SH): {_round3(metrics['subject_hallucination_rate'])}")
    lines.append(f"- Object hallucination rate (Text2KGBench OH): {_round3(metrics['object_hallucination_rate'])}\n")

    lines.append("## Failures\n")
    failures = [
        f"- {rec.get('question_id')}: parse_error={rec.get('parse_error')}"
        for rec in extractions
        if rec.get("parsed") is None
    ]
    lines.extend(failures or ["- none"])

    if annotation_result is not None:
        lines.append("\n## Manual annotation (annotation.csv)\n")
        lines.append(
            f"- Precision: {_round3(annotation_result['precision'])} "
            f"({annotation_result['supported']}/{annotation_result['total']})"
        )
        lines.append(f"- Unsupported triples: {len(annotation_result['unsupported'])}")
        for row in annotation_result["unsupported"]:
            lines.append(
                f"  - {row.get('question_id')}: {row.get('subject')} {row.get('relation')} "
                f"{row.get('object')} — {row.get('notes')}"
            )

    if shacl_catch is not None:
        lines.append("\n## SHACL catch rate (of the unsupported triples above)\n")
        total = shacl_catch["total_unsupported"]
        caught = shacl_catch["caught_by_shacl"]
        not_caught = shacl_catch["not_caught_by_shacl"]
        rate = caught / total if total else None
        lines.append(f"- Caught structurally by SHACL: {caught}/{total} ({_round3(rate)})")
        lines.append(f"- NOT caught (needs fact-check, structurally valid): {not_caught}/{total}")
        lines.append(
            f"\n- Confusion matrix (all annotation.csv rows): "
            f"TN={shacl_catch['true_negative']} FP={shacl_catch['false_positive']} "
            f"FN={shacl_catch['false_negative']} TP={shacl_catch['true_positive']}"
        )
        if shacl_confusion_chart is not None:
            lines.append(f"\n![SHACL vs annotation confusion matrix]({shacl_confusion_chart})")
        for row in shacl_catch["not_caught_rows"]:
            lines.append(f"  - {row.get('question_id')}: {row.get('subject')} {row.get('relation')} {row.get('object')}")

    if missed_facts is not None:
        lines.append("\n## Missed facts (missed_facts.csv)\n")
        total_extracted = sum(len((e.get("parsed") or {}).get("relationships", [])) for e in extractions)
        total_missed = sum(len([f for f in m["missed_facts"].split(";") if f.strip()]) for m in missed_facts)
        recall = total_extracted / (total_extracted + total_missed) if (total_extracted + total_missed) else None
        lines.append(f"- Extracted relationships: {total_extracted}")
        lines.append(f"- Missed facts: {total_missed}")
        lines.append(f"- Recall ≈ extracted / (extracted + missed): {_round3(recall)}")
        lines.append(f"- Questions with missed facts: {len(missed_facts)}")
        for m in missed_facts:
            lines.append(f"  - {m['question_id']}: {m['missed_facts']}")
        if missed_facts_chart is not None:
            lines.append(f"\n![Missed facts per question]({missed_facts_chart})")

    Path(path).write_text("\n".join(lines), encoding="utf-8")


def compute_precision_from_annotation(path: str | Path) -> dict:
    total = 0
    supported = 0
    unsupported_rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            val = (row.get("supported_by_text") or "").strip().lower()
            if val in ("y", "yes", "true", "1"):
                supported += 1
            elif val in ("n", "no", "false", "0"):
                unsupported_rows.append(row)
    precision = supported / total if total else None
    return {"total": total, "supported": supported, "precision": precision, "unsupported": unsupported_rows}


def compute_missed_facts(path: str | Path) -> list[dict]:
    missed = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("missed_facts") or "").strip()
            if text and text != "—":
                missed.append({"question_id": row.get("question_id"), "missed_facts": text})
    return missed


def plot_missed_facts_chart(
    missed_facts: list[dict],
    question_ids: list[str],
    path: str | Path,
    extracted_counts: dict[str, int] | None = None,
) -> None:
    """Bar chart of # missed facts per question, x-axis = every question_id
    (including those with zero missed facts), sorted q01..q<last>.

    If extracted_counts is given (# relationships the converter DID extract,
    per question), plots it as a second bar next to the missed-facts one, so
    the two can be compared directly per question."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    missed_by_qid = {qid: 0 for qid in question_ids}
    for m in missed_facts:
        n = len([f for f in m["missed_facts"].split(";") if f.strip()])
        missed_by_qid[m["question_id"]] = n

    qids_sorted = sorted(missed_by_qid)
    missed_counts = [missed_by_qid[q] for q in qids_sorted]

    fig, ax = plt.subplots(figsize=(12, 4.5))

    if extracted_counts is not None:
        extracted = [extracted_counts.get(q, 0) for q in qids_sorted]
        x = np.arange(len(qids_sorted))
        width = 0.4
        ax.bar(x - width / 2, extracted, width, label="extracted (caught)", color="steelblue")
        ax.bar(x + width / 2, missed_counts, width, label="missed", color="indianred")
        ax.set_xticks(x, qids_sorted)
        ax.legend()
    else:
        ax.bar(qids_sorted, missed_counts, color="steelblue")

    ax.set_xlabel("question_id")
    ax.set_ylabel("# facts")
    ax.set_title("Extracted vs. missed facts per question")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a run of Experiment 1. Run this after filling in "
        "annotation.csv / missed_facts.csv so the report includes them."
    )
    parser.add_argument("run_dir", help="Path to runs/<timestamp>")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)

    schema = yaml.safe_load((run_dir / "schema.yaml").read_text(encoding="utf-8"))
    answers = load_jsonl(run_dir / "answers.jsonl")
    extractions = load_jsonl(run_dir / "extractions.jsonl")
    graphs_dir = run_dir / "graphs"

    metrics = compute_metrics(answers, extractions, schema, graphs_dir)

    annotation_path = run_dir / "annotation.csv"
    if annotation_path.exists():
        annotation_result = compute_precision_from_annotation(annotation_path)
    else:
        annotation_result = None
        write_annotation_csv(extractions, annotation_path)
        print(f"Wrote empty {annotation_path} — fill it in, then re-run this command.")

    missed_facts_path = run_dir / "missed_facts.csv"
    missed_facts_chart_name = None
    if missed_facts_path.exists():
        missed_facts = compute_missed_facts(missed_facts_path)
        question_ids = sorted({a["question_id"] for a in answers})
        extracted_counts = {
            e["question_id"]: len((e.get("parsed") or {}).get("relationships", [])) for e in extractions
        }
        missed_facts_chart_name = "missed_facts.png"
        plot_missed_facts_chart(missed_facts, question_ids, run_dir / missed_facts_chart_name, extracted_counts)
    else:
        missed_facts = None
        write_missed_facts_csv(answers, missed_facts_path)
        print(f"Wrote empty {missed_facts_path} — fill it in, then re-run this command.")

    shacl_catch_path = run_dir / "shacl_catch.json"
    shacl_catch = json.loads(shacl_catch_path.read_text(encoding="utf-8")) if shacl_catch_path.exists() else None
    shacl_confusion_chart_name = "shacl_confusion.png" if (run_dir / "shacl_confusion.png").exists() else None
    if shacl_catch is None:
        print(
            f"No {shacl_catch_path} found — run "
            f"`python shacl_poc/cross_check.py {run_dir}` first to include SHACL catch rate."
        )

    write_report(
        run_dir / "report.md",
        metrics,
        extractions,
        annotation_result,
        missed_facts,
        shacl_catch,
        missed_facts_chart_name,
        shacl_confusion_chart_name,
    )
    print(f"Wrote {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
