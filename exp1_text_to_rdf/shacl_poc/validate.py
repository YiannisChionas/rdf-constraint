"""Mini SHACL validation proof-of-concept for exp1_text_to_rdf output.

Validates each extracted Turtle graph against shapes/gene_shapes.ttl
(see that file's header for where the constraints come from).

Each question's graph is validated SEPARATELY, not merged into one big
graph. Merging turned out to introduce spurious violations that don't
reflect real converter errors (e.g. the same entity mentioned with
different capitalization in two different questions' answers gets merged
into one node with two conflicting rdfs:label values, tripping the
"exactly one label" shape) and, empirically, never catches anything a
per-question check wouldn't already catch on its own.

Usage (run from exp1_text_to_rdf/ as cwd):
    python shacl_poc/validate.py runs/<timestamp>/graphs/*.ttl
"""
from __future__ import annotations

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

SHAPES_PATH = Path(__file__).resolve().parent / "shapes" / "gene_shapes.ttl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate RDF graph(s) against the Hetionet-derived SHACL shapes.")
    parser.add_argument("data_files", nargs="+", help="Turtle file(s) to validate, one question's graph each.")
    args = parser.parse_args()

    shapes_graph = Graph()
    shapes_graph.parse(SHAPES_PATH, format="turtle")

    all_conform = True
    total_violations = 0
    total_warnings = 0

    for f in args.data_files:
        data_graph = Graph()
        data_graph.parse(f, format="turtle")

        conforms, results_graph, results_text = validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference="none",
            abort_on_first=False,
        )
        n_violations = results_text.count("Severity: sh:Violation")
        n_warnings = results_text.count("Severity: sh:Warning")
        total_violations += n_violations
        total_warnings += n_warnings
        all_conform = all_conform and conforms

        if n_violations or n_warnings:
            print(f"--- {f} ({len(data_graph)} triples): violations={n_violations} warnings={n_warnings} ---")
            print(results_text)

    print(f"\nFiles checked: {len(args.data_files)}")
    print(f"Total violations: {total_violations}")
    print(f"Total warnings: {total_warnings}")
    print(f"All conform: {all_conform}")
    sys.exit(0 if all_conform else 1)


if __name__ == "__main__":
    main()
