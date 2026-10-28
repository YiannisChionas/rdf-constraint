# Experiment 3 Report: Live-Hetionet-grounded SHACL shapes (Groq)

## Config
```yaml
groq:
  max_tokens: 2048
hetionet:
  bolt_uri: bolt://neo4j.het.io:7687
shape_agent:
  model: openai/gpt-oss-120b
  temperature: 0.0
  think: false
paths:
  runs_dir: runs
```

## Summary

- Questions considered: 18
- Generated shapes that parsed as valid Turtle: 18/18
- Of those, vacuous (zero sh:NodeShape, trivially conforms): 0/18 - these happen when none of the live Hetionet evidence found for that question's entities maps onto our 4 relations (e.g. only SideEffect/PharmacologicClass edges were found); a vacuous 'conforms=True' is NOT evidence the graph is correct, it means nothing was actually checked.
- Non-vacuous shape sets (at least 1 real constraint): 18/18
- Graphs that conform to their generated shapes: 15/18
- Violations per question (where parsed): [0, 1, 0, 0, 1, 13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
- Mean entity-grounding rate (found in Hetionet / total entities): 0.576176322053515

## Per-question results

| question_id | entities | found_in_hetionet | shapes_parse_ok | n_shapes | vacuous | conforms | n_violations |
|---|---|---|---|---|---|---|---|
| q01 | 9 | 6 | True | 3 | False | True | 0 |
| q02 | 11 | 10 | True | 3 | False | False | 1 |
| q03 | 8 | 2 | True | 3 | False | True | 0 |
| q04 | 9 | 5 | True | 3 | False | True | 0 |
| q05 | 9 | 5 | True | 3 | False | False | 1 |
| q06 | - | - | - | - | - | SKIPPED: prompt too large for Groq free-tier TPM limit: Error code: 413 - {'error': {'message': 'Request too large for model `openai/gpt-oss-120b` in organization `org_01m61bvarxehar08472dve2227` service tier `on_demand` on tokens per minute (TPM): Limit 8000, Requested 8024, please reduce your message size and try again. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}} | - |
| q07 | 14 | 13 | True | 3 | False | False | 13 |
| q08 | 10 | 5 | True | 3 | False | True | 0 |
| q09 | 5 | 4 | True | 3 | False | True | 0 |
| q10 | 11 | 5 | True | 3 | False | True | 0 |
| q11 | 7 | 3 | True | 3 | False | True | 0 |
| q12 | 7 | 5 | True | 3 | False | True | 0 |
| q13 | 6 | 3 | True | 3 | False | True | 0 |
| q14 | 19 | 12 | True | 3 | False | True | 0 |
| q15 | - | - | - | - | - | SKIPPED: prompt too large for Groq free-tier TPM limit: Error code: 413 - {'error': {'message': 'Request too large for model `openai/gpt-oss-120b` in organization `org_01m61bvarxehar08472dve2227` service tier `on_demand` on tokens per minute (TPM): Limit 8000, Requested 11216, please reduce your message size and try again. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}} | - |
| q16 | 10 | 2 | True | 3 | False | True | 0 |
| q17 | 13 | 9 | True | 3 | False | True | 0 |
| q18 | 25 | 16 | True | 3 | False | True | 0 |
| q19 | 12 | 6 | True | 3 | False | True | 0 |
| q20 | 9 | 4 | True | 3 | False | True | 0 |