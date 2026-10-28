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
- Graphs that conform to their generated shapes: 18/20
- Violations per question (where parsed): [0, 0, 0, 2, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
- Mean entity-grounding rate (found in Hetionet / total entities): 0.6152253565148302

## Per-question results

| question_id | entities | found_in_hetionet | shapes_parse_ok | conforms | n_violations |
|---|---|---|---|---|---|
| q01 | 9 | 6 | True | True | 0 |
| q02 | 11 | 10 | True | True | 0 |
| q03 | 8 | 2 | True | True | 0 |
| q04 | 9 | 5 | True | False | 2 |
| q05 | 9 | 5 | True | False | 7 |
| q06 | 10 | 10 | True | True | 0 |
| q07 | 14 | 13 | True | True | 0 |
| q08 | 10 | 5 | True | True | 0 |
| q09 | 5 | 4 | True | True | 0 |
| q10 | 11 | 5 | True | True | 0 |
| q11 | 7 | 3 | True | True | 0 |
| q12 | 7 | 5 | True | True | 0 |
| q13 | 6 | 3 | True | True | 0 |
| q14 | 19 | 12 | True | True | 0 |
| q15 | 15 | 14 | True | True | 0 |
| q16 | 10 | 2 | True | True | 0 |
| q17 | 13 | 9 | True | True | 0 |
| q18 | 25 | 16 | True | True | 0 |
| q19 | 12 | 6 | True | True | 0 |
| q20 | 9 | 4 | True | True | 0 |