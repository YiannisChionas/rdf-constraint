# Experiment 1: Agent Answer -> RDF (Hetionet-derived schema)

Pipeline: `question -> agent (free text) -> converter (schema-constrained JSON) -> RDF (Turtle) -> metrics`.

## Setup

1. Install [Ollama](https://ollama.com) and make sure it is running (`ollama serve`, or the desktop app).
2. Pull the model used by default (`qwen3:14b`):
   ```
   ollama pull qwen3:14b
   ```
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

## Run

From this directory (`exp1_text_to_rdf/`):

```
python -m src.run_experiment
```

This runs the 20 questions in `data/questions.jsonl` through the agent and converter
(both `qwen3:14b` by default, see `config.yaml`), converts the extracted JSON to RDF,
and writes everything to a new `runs/<timestamp>/` directory:

- `answers.jsonl` — agent free-text answers (+ latency, raw response)
- `extractions.jsonl` — converter JSON output (raw + parsed, + latency, raw response)
- `graphs/<question_id>.ttl` — one RDF graph per answer
- `merged.ttl` — union of all graphs
- `report.md` — automatic metrics, example answers/extractions, failures
- `annotation.csv` — one row per extracted triple, for manual annotation
- `missed_facts.csv` — one row per answer, for logging missed facts
- `config.yaml`, `schema.yaml`, `few_shot.json` — copies of what was used

### Re-running the converter on cached answers

To re-run only the converter (e.g. after changing the converter prompt or model)
without re-generating agent answers:

```
python -m src.run_experiment --reuse-answers runs/20260101_120000
```

### Re-evaluating an existing run

```
python -m src.evaluate runs/20260101_120000
```

After manually filling in `annotation.csv` (`supported_by_text`: y/n) and
`missed_facts.csv` (`missed_facts`: free text), recompute precision / missed facts:

```
python -m src.evaluate runs/20260101_120000 --from-annotation
```

## Configuration

See `config.yaml`:

- `agent.model` / `converter.model` — can be different Ollama models.
- `converter.temperature` — kept at 0.0 for deterministic extraction.
- `converter.think` — set to `false` to disable Qwen3 thinking mode for the converter.
- `converter.num_few_shot` — number of few-shot examples from `few_shot.json` to include.

The vocabulary (node types, relations, namespaces) lives entirely in `schema.yaml`
and is used to build both the converter prompt and the JSON schema used for
Ollama structured outputs — extend it there without touching the code.

## Evaluation metrics vs. Text2KGBench

Text2KGBench (Mihindukulasooriya et al., 2023, *Text2KGBench: A Benchmark for
Ontology-Driven Knowledge Graph Generation from Text*, ISWC 2023,
[arXiv:2308.02357](https://arxiv.org/abs/2308.02357)) defines 7 metrics for
evaluating LLM-based, ontology-guided text-to-KG extraction. All 7 are covered
by `evaluate.py`, under different names (we don't have a fixed gold-triple set
per question, only answer text, so P/R/F1 are computed semi-manually via
annotation rather than against a pre-built gold KG):

| Text2KGBench metric | Our equivalent | Notes |
|---|---|---|
| Precision | `annotation.csv` → `compute_precision_from_annotation` | per-triple human judgment of "supported by the answer text", not a fixed gold KG |
| Recall | `missed_facts.csv` → `compute_missed_facts` | human-logged facts the converter missed, per answer |
| F1 | — | derivable from the two above once filled in |
| Ontology Conformance (OC) | `domain_range_correct_rate` | % of triples whose (source type, relation, target type) matches the schema |
| Relation Hallucination (RH) | `1 - domain_range_correct_rate` | RH is defined as the inverse of OC in the paper |
| Subject Hallucination (SH) | `subject_hallucination_rate` | does the relationship's subject name appear (case-insensitive substring) in the source answer text? |
| Object Hallucination (OH) | `object_hallucination_rate` | same check for the object |

SH/OH are automatic (pure string matching, no LLM/human needed) and catch a
failure mode the other metrics don't: entities invented by the converter that
aren't actually grounded in the text. On `runs/20261026_161722`: SH = 0.0,
OH ≈ 0.068 (5/13 flagged objects are false positives of the naive substring
check — e.g. "alpha2delta" vs. the text's "α2δ", or "breast cancer" when the
text only has the combined phrase "breast and ovarian cancers"). The remaining
flagged cases are genuine: the converter maps a described receptor/enzyme to a
*specific* official gene symbol not literally in the text (e.g. q14's asthma
answer says "muscarinic receptors" generically, but the converter extracted
`CHRM3`, a specific subtype choice not stated in the text) — i.e. real
knowledge injection beyond what the "do not infer from your own knowledge"
rule intends, not caught by any of our other metrics.

## Scope

This experiment covers only text -> RDF. No SHACL validation, no feedback loop,
no entity linking to Hetionet IDs, no OWL/reasoning. See the project spec for details.
