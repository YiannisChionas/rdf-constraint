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

## Scope

This experiment covers only text -> RDF. No SHACL validation, no feedback loop,
no entity linking to Hetionet IDs, no OWL/reasoning. See the project spec for details.
