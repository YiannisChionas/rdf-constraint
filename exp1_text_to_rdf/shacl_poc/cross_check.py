"""Cross-check exp1's annotation.csv against per-question SHACL validation.

For every row in annotation.csv, checks whether that same question's own
graphs/<qid>.ttl gets flagged as a sh:Violation by gene_shapes.ttl for that
specific triple, and builds the 2x2 confusion matrix against the human
supported_by_text judgement:

                SHACL conforms   SHACL violation
supported            TN               FP   (SHACL wrongly flags a true fact)
unsupported          FN               TP   (SHACL catches a real error)

Validates per question (not merged) — see validate.py's docstring for why.

Usage (run from exp1_text_to_rdf/ as cwd):
    python shacl_poc/cross_check.py runs/<timestamp>
Writes shacl_catch.json and shacl_confusion.png into that run directory.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph
from rdflib.namespace import SH

SHAPES_PATH = Path(__file__).resolve().parent / "shapes" / "gene_shapes.ttl"
_UNSAFE_RE = re.compile(r"[^A-Za-z0-9_]")


def _local(uri) -> str:
    return str(uri).split("/")[-1].split("#")[-1]


def _slug_variants(name: str) -> set[str]:
    """We don't know the node's type here, so try both of to_rdf.slugify's casings."""
    base = name.strip().replace(" ", "_").replace("-", "")
    return {_UNSAFE_RE.sub("", base.upper()), _UNSAFE_RE.sub("", base.lower())}


def _violations_for_graph(data_graph: Graph, shapes_graph: Graph) -> set[tuple]:
    _, results_graph, _ = validate(data_graph, shacl_graph=shapes_graph, inference="none", abort_on_first=False)
    violations = set()
    for result in results_graph.subjects(predicate=SH.resultSeverity, object=SH.Violation):
        focus = results_graph.value(result, SH.focusNode)
        path = results_graph.value(result, SH.resultPath)
        value = results_graph.value(result, SH.value)
        violations.add((_local(focus) if focus else None, _local(path) if path else None, _local(value) if value else None))
    return violations


def _row_is_caught(row: dict, violations: set[tuple]) -> bool:
    subj_variants = _slug_variants(row["subject"])
    obj_variants = _slug_variants(row["object"])
    relation = row["relation"]
    for subj in subj_variants:
        for (focus, path, value) in violations:
            if focus == subj and path == relation:
                if value is None or value in obj_variants:
                    return True
    return False


def cross_check(run_dir: Path) -> dict:
    annotation_path = run_dir / "annotation.csv"
    with open(annotation_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    shapes_graph = Graph()
    shapes_graph.parse(SHAPES_PATH, format="turtle")

    caught_rows, not_caught_rows = [], []
    tn, fp = 0, 0  # supported & conforms / supported & violation
    violations_by_qid: dict[str, set[tuple]] = {}

    for row in rows:
        supported = (row.get("supported_by_text") or "").strip().lower() in ("y", "yes", "true", "1")
        unsupported = (row.get("supported_by_text") or "").strip().lower() in ("n", "no", "false", "0")
        if not supported and not unsupported:
            continue  # e.g. "partial" — excluded from the binary confusion matrix

        qid = row["question_id"]
        if qid not in violations_by_qid:
            data_graph = Graph()
            data_graph.parse(run_dir / "graphs" / f"{qid}.ttl", format="turtle")
            violations_by_qid[qid] = _violations_for_graph(data_graph, shapes_graph)
        caught = _row_is_caught(row, violations_by_qid[qid])

        if unsupported:
            (caught_rows if caught else not_caught_rows).append(row)
        else:  # supported
            if caught:
                fp += 1
            else:
                tn += 1

    return {
        "true_negative": tn,  # supported, SHACL conforms
        "false_positive": fp,  # supported, SHACL flags it anyway
        "false_negative": len(not_caught_rows),  # unsupported, SHACL misses it
        "true_positive": len(caught_rows),  # unsupported, SHACL catches it
        "total_unsupported": len(caught_rows) + len(not_caught_rows),
        "caught_by_shacl": len(caught_rows),
        "not_caught_by_shacl": len(not_caught_rows),
        "caught_rows": caught_rows,
        "not_caught_rows": not_caught_rows,
    }


def plot_confusion(result: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    matrix = np.array(
        [
            [result["true_negative"], result["false_positive"]],
            [result["false_negative"], result["true_positive"]],
        ]
    )
    fig, ax = plt.subplots(figsize=(5, 4.5))
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], ["SHACL conforms", "SHACL violation"])
    ax.set_yticks([0, 1], ["supported", "unsupported"])
    ax.set_xlabel("SHACL result")
    ax.set_ylabel("Manual annotation")
    ax.set_title("SHACL vs. manual annotation (all rows)")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(matrix[i, j]), ha="center", va="center", fontsize=16)
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    run_dir = Path(sys.argv[1])
    result = cross_check(run_dir)
    out_path = run_dir / "shacl_catch.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    chart_path = run_dir / "shacl_confusion.png"
    plot_confusion(result, chart_path)
    print(f"TN={result['true_negative']} FP={result['false_positive']} "
          f"FN={result['false_negative']} TP={result['true_positive']}")
    print(f"Wrote {out_path} and {chart_path}")


if __name__ == "__main__":
    main()
