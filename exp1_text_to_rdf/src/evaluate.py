"""Automatic metrics + manual-annotation scaffolding for a run.

Can be invoked standalone on an existing run directory:

    python -m src.evaluate runs/<timestamp>
    python -m src.evaluate runs/<timestamp> --from-annotation
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


def write_annotation_csv(extractions: list[dict], answers_by_id: dict, path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["question_id", "subject", "relation", "object", "answer_excerpt", "supported_by_text", "correct_types", "notes"]
        )
        for rec in extractions:
            parsed = rec.get("parsed")
            if not parsed:
                continue
            qid = rec.get("question_id")
            excerpt = (answers_by_id.get(qid, {}).get("answer", "") or "")[:200]
            nodes_by_id = {n.get("id"): n for n in parsed.get("nodes", [])}
            for rel in parsed.get("relationships", []):
                src = nodes_by_id.get(rel.get("source"))
                tgt = nodes_by_id.get(rel.get("target"))
                subj = src.get("name") if src else rel.get("source")
                obj = tgt.get("name") if tgt else rel.get("target")
                writer.writerow([qid, subj, rel.get("relation"), obj, excerpt, "", "", ""])


def write_missed_facts_csv(answers: list[dict], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["question_id", "answer_text", "missed_facts"])
        for a in answers:
            writer.writerow([a.get("question_id"), a.get("answer", ""), ""])


def write_report(
    path: str | Path,
    config: dict,
    metrics: dict,
    answers: list[dict],
    extractions: list[dict],
    n_examples: int = 5,
) -> None:
    answers_by_id = {a.get("question_id"): a for a in answers}
    lines: list[str] = []
    lines.append("# Experiment 1 Report: Agent Answer -> RDF\n")

    lines.append("## Config\n")
    lines.append("```yaml")
    lines.append(yaml.dump(config, sort_keys=False).rstrip())
    lines.append("```\n")

    lines.append("## Automatic metrics\n")
    lines.append(f"- Answers evaluated: {metrics['n_answers']}")
    lines.append(f"- Converter JSON parse success rate: {metrics['parse_success_rate']}")
    lines.append(f"- JSON-schema-valid rate: {metrics['json_schema_valid_rate']}")
    lines.append(f"- Domain/range correctness rate: {metrics['domain_range_correct_rate']}")
    lines.append(f"- Dangling references: {metrics['dangling_reference_count']}")
    lines.append(f"- Duplicate nodes: {metrics['duplicate_node_count']}")
    lines.append(f"- Turtle round-trip parse success rate: {metrics['turtle_roundtrip_success_rate']}")
    lines.append(f"- Nodes per answer: {metrics['nodes_per_answer']}")
    lines.append(f"- Triples per answer: {metrics['triples_per_answer']}")
    lines.append(f"- Relation counts: {metrics['relation_counts']}")
    lines.append(f"- % answers with zero extracted relationships: {metrics['pct_zero_relationships']}")
    lines.append(f"- Agent latency (s): {metrics['agent_latency_s']}")
    lines.append(f"- Converter latency (s): {metrics['converter_latency_s']}")
    lines.append(f"- Subject hallucination rate (Text2KGBench SH): {metrics['subject_hallucination_rate']}")
    lines.append(f"- Object hallucination rate (Text2KGBench OH): {metrics['object_hallucination_rate']}\n")

    lines.append("## Example answers and extractions\n")
    for rec in extractions[:n_examples]:
        qid = rec.get("question_id")
        a = answers_by_id.get(qid, {})
        lines.append(f"### {qid}")
        lines.append(f"**Question:** {a.get('question', '')}\n")
        lines.append(f"**Answer:** {a.get('answer', '')}\n")
        parsed = rec.get("parsed")
        if parsed is not None:
            lines.append("**Extracted JSON:**")
            lines.append("```json")
            lines.append(json.dumps(parsed, indent=2))
            lines.append("```\n")
        else:
            lines.append(f"**Parse error:** {rec.get('parse_error')}\n")

    lines.append("## Failures\n")
    failures = [
        f"- {rec.get('question_id')}: parse_error={rec.get('parse_error')}"
        for rec in extractions
        if rec.get("parsed") is None
    ]
    lines.extend(failures or ["- none"])

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
            if text:
                missed.append({"question_id": row.get("question_id"), "missed_facts": text})
    return missed


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a run of Experiment 1.")
    parser.add_argument("run_dir", help="Path to runs/<timestamp>")
    parser.add_argument("--from-annotation", action="store_true", help="Recompute precision from filled annotation.csv / missed_facts.csv")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)

    if args.from_annotation:
        result = compute_precision_from_annotation(run_dir / "annotation.csv")
        missed = compute_missed_facts(run_dir / "missed_facts.csv")
        print(f"Precision: {result['precision']} ({result['supported']}/{result['total']})")
        print(f"Unsupported (possibly hallucinated/self-corrected) triples: {len(result['unsupported'])}")
        for row in result["unsupported"]:
            print(f"  - {row}")
        print(f"Missed facts logged: {len(missed)}")
        for m in missed:
            print(f"  - {m['question_id']}: {m['missed_facts']}")
        return

    config = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8"))
    schema = yaml.safe_load((run_dir / "schema.yaml").read_text(encoding="utf-8"))
    answers = load_jsonl(run_dir / "answers.jsonl")
    extractions = load_jsonl(run_dir / "extractions.jsonl")
    graphs_dir = run_dir / "graphs"

    metrics = compute_metrics(answers, extractions, schema, graphs_dir)
    answers_by_id = {a.get("question_id"): a for a in answers}

    write_annotation_csv(extractions, answers_by_id, run_dir / "annotation.csv")
    write_missed_facts_csv(answers, run_dir / "missed_facts.csv")
    write_report(run_dir / "report.md", config, metrics, answers, extractions)

    print(f"Wrote report.md, annotation.csv, missed_facts.csv to {run_dir}")


if __name__ == "__main__":
    main()
