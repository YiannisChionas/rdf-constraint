"""CLI entry point: runs the full pipeline end to end.

    python -m src.run_experiment
    python -m src.run_experiment --reuse-answers runs/20260101_120000
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import yaml
from rdflib import Graph

from .agent import generate_answer
from .converter import convert_answer, load_few_shot, load_schema
from .evaluate import compute_metrics, load_jsonl, write_annotation_csv, write_missed_facts_csv, write_report
from .llm import OllamaClient
from .to_rdf import json_to_graph, serialize_graph


def load_questions(path: str | Path) -> list[dict]:
    questions = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


def new_run_dir(base_dir: str | Path) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path(base_dir) / ts
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Experiment 1: Agent Answer -> RDF")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument(
        "--reuse-answers",
        default=None,
        help="Path to an existing runs/<timestamp> dir; reuses its cached answers.jsonl instead of calling the agent.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = project_root / config_path
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    schema_path = project_root / config["paths"]["schema_file"]
    few_shot_path = project_root / config["paths"]["few_shot_file"]
    questions_path = project_root / config["paths"]["questions_file"]
    runs_dir = project_root / config["paths"]["runs_dir"]

    schema = load_schema(schema_path)
    few_shot_examples = load_few_shot(few_shot_path)
    questions = load_questions(questions_path)

    run_dir = new_run_dir(runs_dir)
    graphs_dir = run_dir / "graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)

    # Copy config + prompts used, for reproducibility.
    shutil.copy(config_path, run_dir / "config.yaml")
    shutil.copy(schema_path, run_dir / "schema.yaml")
    shutil.copy(few_shot_path, run_dir / "few_shot.json")

    client = OllamaClient(host=config["ollama"]["host"])

    # --- Step 1: agent answers (or reuse cached) ---
    if args.reuse_answers:
        reuse_path = Path(args.reuse_answers) / "answers.jsonl"
        answers = load_jsonl(reuse_path)
        print(f"Reusing {len(answers)} cached answers from {reuse_path}")
    else:
        agent_cfg = config["agent"]
        answers = []
        for q in questions:
            result = generate_answer(
                client,
                model=agent_cfg["model"],
                system_prompt=agent_cfg["system_prompt"],
                question=q["question"],
                temperature=agent_cfg.get("temperature"),
                think=agent_cfg.get("think"),
            )
            answers.append(
                {
                    "question_id": q["id"],
                    "question": q["question"],
                    "answer": result.content,
                    "latency_s": result.latency_s,
                    "raw": result.raw,
                }
            )
            print(f"[agent] {q['id']} done ({result.latency_s:.1f}s)")

    with open(run_dir / "answers.jsonl", "w", encoding="utf-8") as f:
        for a in answers:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    # --- Step 2: converter (answer text only, no question) ---
    conv_cfg = config["converter"]
    extractions = []
    for a in answers:
        conv_result = convert_answer(
            client,
            model=conv_cfg["model"],
            schema=schema,
            few_shot_examples=few_shot_examples,
            answer=a["answer"],
            num_few_shot=conv_cfg.get("num_few_shot", 2),
            temperature=conv_cfg.get("temperature", 0.0),
            think=conv_cfg.get("think", False),
        )
        extractions.append({"question_id": a["question_id"], **conv_result})
        status = "ok" if conv_result["parsed"] is not None else f"PARSE ERROR: {conv_result['parse_error']}"
        print(f"[converter] {a['question_id']} {status} ({conv_result['latency_s']:.1f}s)")

    with open(run_dir / "extractions.jsonl", "w", encoding="utf-8") as f:
        for e in extractions:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # --- Step 3: JSON -> RDF ---
    merged = Graph()
    for e in extractions:
        if e["parsed"] is None:
            continue
        g, warnings = json_to_graph(e["parsed"], schema)
        for w in warnings:
            print(f"[to_rdf] {e['question_id']}: {w}")
        serialize_graph(g, graphs_dir / f"{e['question_id']}.ttl")
        merged += g
    serialize_graph(merged, run_dir / "merged.ttl")

    # --- Step 4: evaluate ---
    metrics = compute_metrics(answers, extractions, schema, graphs_dir)
    answers_by_id = {a["question_id"]: a for a in answers}
    write_annotation_csv(extractions, answers_by_id, run_dir / "annotation.csv")
    write_missed_facts_csv(answers, run_dir / "missed_facts.csv")
    write_report(run_dir / "report.md", config, metrics, answers, extractions)

    print(f"\nRun complete: {run_dir}")


if __name__ == "__main__":
    main()
