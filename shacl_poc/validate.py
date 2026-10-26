"""Mini SHACL validation proof-of-concept for exp1_text_to_rdf output.

Validates one or more extracted Turtle graphs against shapes/gene_shapes.ttl
(see that file's header for where the constraints come from).

Usage:
    python validate.py ../exp1_text_to_rdf/runs/<timestamp>/merged.ttl
    python validate.py ../exp1_text_to_rdf/runs/<timestamp>/graphs/*.ttl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

SHAPES_PATH = Path(__file__).resolve().parent / "shapes" / "gene_shapes.ttl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate RDF graph(s) against the Hetionet-derived SHACL shapes.")
    parser.add_argument("data_files", nargs="+", help="Turtle file(s) to validate.")
    args = parser.parse_args()

    data_graph = Graph()
    for f in args.data_files:
        data_graph.parse(f, format="turtle")
    print(f"Loaded {len(args.data_files)} file(s), {len(data_graph)} triples total.\n")

    shapes_graph = Graph()
    shapes_graph.parse(SHAPES_PATH, format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference="none",
        abort_on_first=False,
    )

    print(results_text)
    print(f"\nConforms: {conforms}")
    sys.exit(0 if conforms else 1)


if __name__ == "__main__":
    main()
