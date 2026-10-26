# RDF — MPhil Thesis Project

Research code for an MPhil thesis on converting free-text biomedical agent
answers into RDF, using a small Hetionet-derived schema, and validating the
results.

## Subprojects

### [`exp1_text_to_rdf/`](exp1_text_to_rdf/)

Experiment 1: `question -> agent (free text) -> converter (schema-constrained
JSON via Ollama structured outputs) -> RDF (Turtle) -> evaluation metrics`.

Uses a fixed Hetionet-derived vocabulary (node types `Gene`/`Compound`/`Disease`,
relations `treats`/`binds`/`associatedWith`/`interactsWith`). See its own
README for setup and usage.

### [`shacl_poc/`](shacl_poc/)

Side proof-of-concept, out of Experiment 1's scope: validates the RDF graphs
produced by `exp1_text_to_rdf` against hand-written SHACL shapes grounded in
Hetionet's published metagraph (Himmelstein et al. 2017, eLife). See its own
README for details and findings.

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com) running locally (used by `exp1_text_to_rdf`)

Each subproject has its own `requirements.txt`; install from within that
subproject's directory.
