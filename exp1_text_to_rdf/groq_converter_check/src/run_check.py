"""Re-run the converter step (only) on exp1's existing agent answers, using
Groq instead of qwen3:14b, then check how many of the 43 missed facts
(../runs/20261102_125528/missed_facts.csv) a stronger model now catches.

Usage: python -m src.run_check   (run from groq_converter_check/ as cwd)
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import yaml

from .converter import build_json_schema, convert_answer, load_few_shot, load_schema
from .llm import GroqClient

RELATIONS = ["treats", "binds", "associatedWith", "interactsWith"]
_PAREN_RE = re.compile(r"\s*\(.*\)\s*$")


def load_jsonl(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def parse_fact(fact: str) -> tuple[str, str, str] | None:
    for rel in RELATIONS:
        marker = f" {rel} "
        if marker in fact:
            idx = fact.index(marker)
            subj = fact[:idx].strip()
            obj = _PAREN_RE.sub("", fact[idx + len(marker):]).strip()
            return subj, rel, obj
    return None


def _norm(s: str) -> str:
    return s.strip().lower()


def fact_is_caught(subj: str, rel: str, obj: str, relationships: list[dict], nodes_by_id: dict) -> bool:
    ns, no = _norm(subj), _norm(obj)
    for r in relationships:
        if r.get("relation") != rel:
            continue
        src = nodes_by_id.get(r.get("source"), {}).get("name", "")
        tgt = nodes_by_id.get(r.get("target"), {}).get("name", "")
        src_n, tgt_n = _norm(src), _norm(tgt)
        if (ns in src_n or src_n in ns) and (no in tgt_n or tgt_n in no):
            return True
    return False


def main() -> None:
    config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    base_run = Path(config["base_run"])

    schema = load_schema(base_run / "schema.yaml")
    few_shot_examples = load_few_shot(base_run / "few_shot.json")
    answers = load_jsonl(base_run / "answers.jsonl")

    with open(base_run / "missed_facts.csv", newline="", encoding="utf-8") as f:
        missed_rows = [r for r in csv.DictReader(f) if (r.get("missed_facts") or "").strip() not in ("", "—")]

    client = GroqClient(max_tokens=config["groq"]["max_tokens"])
    model = config["groq"]["model"]

    extractions = []
    for a in answers:
        result = convert_answer(
            client,
            model=model,
            schema=schema,
            few_shot_examples=few_shot_examples,
            answer=a["answer"],
            num_few_shot=config["groq"]["num_few_shot"],
            temperature=config["groq"]["temperature"],
        )
        extractions.append({"question_id": a["question_id"], **result})
        status = "ok" if result["parsed"] is not None else f"PARSE ERROR: {result['parse_error']}"
        print(f"[converter-groq] {a['question_id']} {status} ({result['latency_s']:.1f}s)")

    with open("extractions_groq.jsonl", "w", encoding="utf-8") as f:
        for e in extractions:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    extractions_by_qid = {e["question_id"]: e for e in extractions}

    caught, still_missing, unparseable = [], [], []
    for row in missed_rows:
        qid = row["question_id"]
        parsed = (extractions_by_qid.get(qid) or {}).get("parsed") or {}
        relationships = parsed.get("relationships", [])
        nodes_by_id = {n["id"]: n for n in parsed.get("nodes", [])}
        for fact in [f.strip() for f in row["missed_facts"].split(";") if f.strip()]:
            parsed_fact = parse_fact(fact)
            if parsed_fact is None:
                unparseable.append((qid, fact))
                continue
            subj, rel, obj = parsed_fact
            entry = f"{qid}: {fact}"
            if fact_is_caught(subj, rel, obj, relationships, nodes_by_id):
                caught.append(entry)
            else:
                still_missing.append(entry)

    total = len(caught) + len(still_missing) + len(unparseable)
    lines = [
        "# Groq converter check: missed facts re-extraction\n",
        f"- Total missed facts (qwen3:14b run): {total}",
        f"- Caught by Groq ({model}): {len(caught)}",
        f"- Still missing (Groq too): {len(still_missing)}",
        f"- Unparseable fact string (skipped): {len(unparseable)}\n",
        "## Caught by Groq (likely a qwen3:14b converter limitation, not fixed prompt/data — heuristic match, verify manually)\n",
    ]
    lines += [f"- {e}" for e in caught] or ["- none"]
    lines.append("\n## Still missing with Groq too (needs closer look — may be genuinely hard to extract)\n")
    lines += [f"- {e}" for e in still_missing] or ["- none"]
    if unparseable:
        lines.append("\n## Could not parse these fact strings automatically\n")
        lines += [f"- {qid}: {fact}" for qid, fact in unparseable]

    Path("comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nCaught by Groq: {len(caught)}/{total}")
    print(f"Still missing: {len(still_missing)}/{total}")
    print("Wrote extractions_groq.jsonl and comparison.md")


if __name__ == "__main__":
    main()
