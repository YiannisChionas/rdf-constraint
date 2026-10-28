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
- Generated shapes that parsed as valid Turtle: 7/20
- Graphs that conform to their generated shapes: 5/7
- Violations per question (where parsed): [0, 0, 20, 19, 0, 0, 0]
- Mean entity-grounding rate (found in Hetionet / total entities): 0.6152253565148302

## Per-question results

| question_id | entities | found_in_hetionet | shapes_parse_ok | conforms | n_violations |
|---|---|---|---|---|---|
| q01 | 9 | 6 | False | None | None |
| q02 | 11 | 10 | False | None | None |
| q03 | 8 | 2 | True | True | 0 |
| q04 | 9 | 5 | False | None | None |
| q05 | 9 | 5 | True | True | 0 |
| q06 | 10 | 10 | False | None | None |
| q07 | 14 | 13 | False | None | None |
| q08 | 10 | 5 | True | False | 20 |
| q09 | 5 | 4 | False | None | None |
| q10 | 11 | 5 | False | None | None |
| q11 | 7 | 3 | False | None | None |
| q12 | 7 | 5 | False | None | None |
| q13 | 6 | 3 | True | False | 19 |
| q14 | 19 | 12 | False | None | None |
| q15 | 15 | 14 | False | None | None |
| q16 | 10 | 2 | True | True | 0 |
| q17 | 13 | 9 | True | True | 0 |
| q18 | 25 | 16 | False | None | None |
| q19 | 12 | 6 | False | None | None |
| q20 | 9 | 4 | True | True | 0 |