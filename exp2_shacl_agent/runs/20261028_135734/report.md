# Experiment 2 Report: Live-Hetionet-grounded SHACL shapes

## Config
```yaml
ollama:
  host: http://localhost:11434
hetionet:
  bolt_uri: bolt://neo4j.het.io:7687
shape_agent:
  model: qwen3:14b
  temperature: 0.0
  think: false
paths:
  runs_dir: runs
```

## Summary

- Questions considered: 20
- Generated shapes that parsed as valid Turtle: 20/20
- Of those, vacuous (zero sh:NodeShape, trivially conforms): 3/20 - these happen when none of the live Hetionet evidence found for that question's entities maps onto our 4 relations (e.g. only SideEffect/PharmacologicClass edges were found); a vacuous 'conforms=True' is NOT evidence the graph is correct, it means nothing was actually checked.
- Non-vacuous shape sets (at least 1 real constraint): 17/20
- Graphs that conform to their generated shapes: 17/20
- Violations per question (where parsed): [0, 1, 0, 0, 1, 0, 13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
- Mean entity-grounding rate (found in Hetionet / total entities): 0.6152253565148302

## Per-question results

| question_id | entities | found_in_hetionet | shapes_parse_ok | n_shapes | vacuous | conforms | n_violations |
|---|---|---|---|---|---|---|---|
| q01 | 9 | 6 | True | 3 | False | True | 0 |
| q02 | 11 | 10 | True | 3 | False | False | 1 |
| q03 | 8 | 2 | True | 3 | False | True | 0 |
| q04 | 9 | 5 | True | 3 | False | True | 0 |
| q05 | 9 | 5 | True | 3 | False | False | 1 |
| q06 | 10 | 10 | True | 3 | False | True | 0 |
| q07 | 14 | 13 | True | 3 | False | False | 13 |
| q08 | 10 | 5 | True | 3 | False | True | 0 |
| q09 | 5 | 4 | True | 3 | False | True | 0 |
| q10 | 11 | 5 | True | 3 | False | True | 0 |
| q11 | 7 | 3 | True | 3 | False | True | 0 |
| q12 | 7 | 5 | True | 3 | False | True | 0 |
| q13 | 6 | 3 | True | 3 | False | True | 0 |
| q14 | 19 | 12 | True | 0 | True | True | 0 |
| q15 | 15 | 14 | True | 0 | True | True | 0 |
| q16 | 10 | 2 | True | 3 | False | True | 0 |
| q17 | 13 | 9 | True | 3 | False | True | 0 |
| q18 | 25 | 16 | True | 3 | False | True | 0 |
| q19 | 12 | 6 | True | 0 | True | True | 0 |
| q20 | 9 | 4 | True | 3 | False | True | 0 |