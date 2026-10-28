"""Experiment 3: live-Hetionet-grounded SHACL shapes, generated per question
by Groq-hosted openai/gpt-oss-120b (instead of exp2_shacl_agent's
qwen3:14b), validated against exp1_text_to_rdf's already-extracted graphs.
Same exp1 dataset, schema and evidence-gathering/rendering logic as exp2 -
only the LLM backend differs - so report.md here is directly comparable to
exp2's.

Usage:
    python -m src.run_experiment --exp1-run ../exp1_text_to_rdf/runs/<timestamp>

Requires the GROK_API_KEY environment variable to be set.
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
from datetime import datetime
from pathlib import Path

import groq
import yaml
from pyshacl import validate as shacl_validate
from rdflib import RDF, Graph
from rdflib.namespace import SH

from .evidence import format_evidence_block, gather_evidence
from .hetionet_client import HetionetClient
from .llm import GroqClient
from .shape_agent import generate_shapes


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def distinct_entities(parsed: dict) -> list[dict]:
    seen = set()
    out = []
    for node in parsed.get("nodes", []):
        key = (node.get("type"), str(node.get("name", "")).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append({"type": node.get("type"), "name": node.get("name")})
    return out


def new_run_dir(base_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base_dir / ts
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Experiment 3: Groq-generated SHACL shape generation + validation.")
    parser.add_argument("--exp1-run", required=True, help="Path to an exp1_text_to_rdf runs/<timestamp> directory.")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml.")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent.parent
    config = yaml.safe_load((here / args.config).read_text(encoding="utf-8"))

    exp1_run = Path(args.exp1_run)
    schema = yaml.safe_load((exp1_run / "schema.yaml").read_text(encoding="utf-8"))
    answers = load_jsonl(exp1_run / "answers.jsonl")
    extractions = load_jsonl(exp1_run / "extractions.jsonl")
    answers_by_id = {a["question_id"]: a for a in answers}

    run_dir = new_run_dir(here / config["paths"]["runs_dir"])
    (run_dir / "shapes").mkdir()
    (run_dir / "validation").mkdir()
    (run_dir / "evidence").mkdir()
    shutil.copy(here / args.config, run_dir / "config.yaml")
    with open(run_dir / "exp1_run_source.txt", "w", encoding="utf-8") as f:
        f.write(str(exp1_run.resolve()))

    llm_client = GroqClient(max_tokens=config["groq"]["max_tokens"])
    hetio_client = HetionetClient(uri=config["hetionet"]["bolt_uri"])

    results = []
    try:
        for rec in extractions:
            qid = rec["question_id"]
            parsed = rec.get("parsed")
            answer = answers_by_id.get(qid, {}).get("answer", "")
            question = answers_by_id.get(qid, {}).get("question", "")
            graph_path = exp1_run / "graphs" / f"{qid}.ttl"

            if not parsed or not graph_path.exists():
                results.append({"question_id": qid, "skipped": True, "reason": "no parsed extraction or graph"})
                continue

            entities = distinct_entities(parsed)
            evidence = gather_evidence(entities, hetio_client)
            (run_dir / "evidence" / f"{qid}.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            evidence_block = format_evidence_block(evidence)

            try:
                gen = generate_shapes(
                    llm_client,
                    model=config["shape_agent"]["model"],
                    schema=schema,
                    question=question,
                    answer=answer,
                    evidence_block=evidence_block,
                    temperature=config["shape_agent"]["temperature"],
                    think=config["shape_agent"]["think"],
                )
            except groq.APIStatusError as e:
                if e.status_code == 413:
                    results.append({
                        "question_id": qid, "skipped": True,
                        "reason": f"prompt too large for Groq free-tier TPM limit: {e}",
                    })
                    continue
                raise
            shapes_path = run_dir / "shapes" / f"{qid}.ttl"
            shapes_path.write_text(gen["shapes_turtle"], encoding="utf-8")

            n_found = sum(1 for e in evidence if e["lookup"]["found"])
            row = {
                "question_id": qid,
                "skipped": False,
                "n_entities": len(entities),
                "n_found_in_hetionet": n_found,
                "shapes_latency_s": gen["latency_s"],
                "shapes_parse_ok": False,
                "n_shapes": 0,
                "vacuous": None,
                "conforms": None,
                "n_violations": None,
            }

            try:
                shapes_graph = Graph()
                shapes_graph.parse(data=gen["shapes_turtle"], format="turtle")
                row["shapes_parse_ok"] = True
            except Exception as e:
                row["parse_error"] = str(e)
                results.append(row)
                continue

            n_shapes = len(list(shapes_graph.subjects(RDF.type, SH.NodeShape)))
            row["n_shapes"] = n_shapes
            row["vacuous"] = n_shapes == 0

            data_graph = Graph()
            data_graph.parse(graph_path, format="turtle")
            conforms, results_graph, results_text = shacl_validate(
                data_graph, shacl_graph=shapes_graph, inference="none", abort_on_first=False
            )
            (run_dir / "validation" / f"{qid}.txt").write_text(results_text, encoding="utf-8")
            row["conforms"] = conforms
            row["n_violations"] = results_text.count("Constraint Violation")
            results.append(row)
    finally:
        hetio_client.close()

    write_report(run_dir, config, results)
    print(f"Wrote exp3 results to {run_dir}")


def write_report(run_dir: Path, config: dict, results: list[dict]) -> None:
    lines = ["# Experiment 3 Report: Live-Hetionet-grounded SHACL shapes (Groq)\n"]
    lines.append("## Config\n```yaml")
    lines.append(yaml.dump(config, sort_keys=False).rstrip())
    lines.append("```\n")

    considered = [r for r in results if not r.get("skipped")]
    n = len(considered)
    parse_ok = sum(1 for r in considered if r.get("shapes_parse_ok"))
    conforms_n = sum(1 for r in considered if r.get("conforms") is True)
    vacuous_n = sum(1 for r in considered if r.get("vacuous") is True)
    non_vacuous_parsed = sum(1 for r in considered if r.get("shapes_parse_ok") and not r.get("vacuous"))
    violations = [r["n_violations"] for r in considered if r.get("n_violations") is not None]
    found_rates = [r["n_found_in_hetionet"] / r["n_entities"] for r in considered if r.get("n_entities")]

    lines.append("## Summary\n")
    lines.append(f"- Questions considered: {n}")
    lines.append(f"- Generated shapes that parsed as valid Turtle: {parse_ok}/{n}")
    lines.append(f"- Of those, vacuous (zero sh:NodeShape, trivially conforms): {vacuous_n}/{parse_ok if parse_ok else 0} "
                  f"- these happen when none of the live Hetionet evidence found for that question's entities "
                  f"maps onto our 4 relations (e.g. only SideEffect/PharmacologicClass edges were found); a vacuous "
                  f"'conforms=True' is NOT evidence the graph is correct, it means nothing was actually checked.")
    lines.append(f"- Non-vacuous shape sets (at least 1 real constraint): {non_vacuous_parsed}/{n}")
    lines.append(f"- Graphs that conform to their generated shapes: {conforms_n}/{parse_ok if parse_ok else 0}")
    lines.append(f"- Violations per question (where parsed): {violations}")
    lines.append(f"- Mean entity-grounding rate (found in Hetionet / total entities): "
                  f"{statistics.mean(found_rates) if found_rates else None}\n")

    lines.append("## Per-question results\n")
    lines.append("| question_id | entities | found_in_hetionet | shapes_parse_ok | n_shapes | vacuous | conforms | n_violations |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        if r.get("skipped"):
            lines.append(f"| {r['question_id']} | - | - | - | - | - | SKIPPED: {r['reason']} | - |")
        else:
            lines.append(
                f"| {r['question_id']} | {r['n_entities']} | {r['n_found_in_hetionet']} | "
                f"{r['shapes_parse_ok']} | {r.get('n_shapes')} | {r.get('vacuous')} | {r['conforms']} | {r['n_violations']} |"
            )

    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
