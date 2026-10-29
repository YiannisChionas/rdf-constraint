# Evaluation Report

Critical review of the repository at commit `0aebbda` (Experiments 1–3 and
`shacl_poc`). Every quantitative claim below was re-checked against the
committed run artifacts; where a claim could not be verified, that is stated.

Runs examined:

| Component | Run |
|---|---|
| `exp1_text_to_rdf` | `runs/20261026_161722` |
| `shacl_poc` | `validation_report.txt` (on exp1's `merged.ttl`) |
| `exp2_shacl_agent` | `runs/20261028_135734` (final design) |
| `exp3_shacl_agent_groq` | `runs/20261028_160138` |

Severity scale: **Critical** = undermines a headline conclusion;
**Major** = a claim is wrong or confounded and must be fixed before it is
reported; **Minor** = correctness/hygiene issue with limited impact.

---

## Summary

| # | Severity | Finding |
|---|---|---|
| C1 | Critical | Exp2/Exp3: the LLM's only decision is information-free — a no-LLM baseline matches or beats both |
| C2 | Critical | No experiment measures whether the agent's answers are correct; manual P/R was never filled in |
| M1 | Major | Exp3 compares a non-reasoning 14B model against a reasoning 120B model; single run; hardest question skipped |
| M2 | Major | Exp2/Exp3 entity grounding: 36.5% "not found", mostly name-matching failures and Hetionet scope, not true absence |
| M3 | Major | `shacl_poc/README.md` error attribution has an arithmetic error and contradicts exp1's README |
| M4 | Major | Text2KGBench mapping: OC/RH are defined differently in the paper |
| M5 | Major | n = 20, one run per configuration, no variance reported |
| m1–m12 | Minor | See [Minor findings](#minor-findings) |

---

## Critical findings

### C1. Exp2/Exp3: the LLM gate adds no information

**What the code does.** In the final design, the LLM outputs only
`{"supported_relations": [...]}`, a subset of the 4 relations.
`render_shapes()` then derives every constraint (positive `sh:class` on the
source type, `sh:maxCount 0` on all other types) deterministically from
`schema.yaml`.

**Why this is a problem.** Those constraints are schema facts: "`binds`
goes Compound → Gene" holds whether or not Hetionet happens to contain a
CbG edge for the entities in a given question. Live Hetionet evidence
therefore cannot make a constraint *more correct*. The LLM can only
**remove** valid checks (false negatives); it can never add one.

**Evidence.** Rendering all 4 relations unconditionally (no LLM, no
Hetionet) and validating the same exp1 graphs:

| | No-LLM baseline | Exp2 (qwen3:14b) | Exp3 (gpt-oss-120b) |
|---|---|---|---|
| Questions evaluated | 20 | 20 | 18 (q06, q15 skipped) |
| Vacuous shape sets | **0** | 3 | 0 |
| Violations | q02: 1, q05: 1, q07: 13 | identical | identical |
| Conforming | 17/20 | 17/20 | 15/18 |

The baseline reproduces every finding of both experiments, with no vacuous
cases, and also covers q06/q15. The "zero false positives from the shape
agent" result is a property of the schema-derived rendering, not of the
LLM. Exp3's headline ("a larger model is not vacuous on q14/q19") measures
how well a model avoids degrading a deterministic rule set.

**Fix.**

1. Add the no-LLM baseline as a row in every Exp2/Exp3 `report.md`
   (snippet in [Appendix A](#appendix-a-no-llm-baseline)).
2. State the conclusion explicitly in the READMEs: each design iteration
   moved a decision from the LLM into deterministic code, and the end state
   needs no LLM for these constraints. That is a legitimate and reportable
   finding.
3. To give the LLM and Hetionet a real role, choose one:
   - **LLM-proposed constraints that are *not* derivable from the schema**
     (cardinalities, conditional rules, value patterns), accepted only if
     the corresponding Hetionet subgraph conforms to them (false-positive
     guard) and they flag at least one annotated error (usefulness guard).
   - **Instance-level fact verification**: use Hetionet to check whether
     each extracted triple exists (e.g. `aliskiren treats hypertension`).
     This is fact checking, not shape generation, but it is the signal the
     pipeline currently lacks (see C2).

### C2. Agent correctness is never measured

**What exists.**

- All automatic exp1 metrics measure the **converter** (parse rate, schema
  validity, domain/range, dangling refs, round-trip, SH/OH).
- `annotation.csv` (`supported_by_text`) measures converter **faithfulness**
  to the answer, not truth. A false statement in the answer, such as the
  agent's "asciminib (Blincyto)" (Blincyto is blinatumomab) in q05, would
  correctly be marked `y`.
- SHACL checks structure only.

**What is missing.**

- `annotation.csv`: 221 rows, **0 filled**. `missed_facts.csv`: **0
  filled**. No precision or recall value exists for any run.
- `exp1_text_to_rdf/README.md` states "All 7 [Text2KGBench metrics] are
  covered by `evaluate.py`". P, R and F1 are not computed (empty inputs),
  and F1 has no implementation.

**Fix.**

1. Fill `annotation.csv` and `missed_facts.csv` for at least one run, or
   change the README to "scaffolded, not yet computed".
2. Add an integer `n_missed` column to `missed_facts.csv` and compute
   recall = supported / (supported + n_missed) and F1 in
   `compute_precision_from_annotation`.
3. Add a separate `factually_correct` annotation column, or an automatic
   check against a reference KG, so that agent errors and converter errors
   are measured separately.

---

## Major findings

### M1. Exp3: confounded comparison

1. **Reasoning is not held constant.** `exp3_shacl_agent_groq/README.md` and
   `src/llm.py` state that `openai/gpt-oss-120b` "has no separate thinking
   mode exposed via this API". gpt-oss is a reasoning model with a
   `reasoning_effort` setting (low/medium/high). Third-party guides show
   that parameter used on Groq's Chat Completions API; Groq's own default
   was not verified here. Exp2 runs qwen3:14b with `think: false`. The
   comparison therefore changes model size **and** reasoning at once.
2. **`max_tokens: 2048` may include reasoning tokens.** If so, long
   reasoning could truncate the tool call. `finish_reason` and `usage` are
   computed in `GroqClient.chat()` but not written to the run directory, so
   this cannot be checked after the fact.
3. **One run.** Exp2 showed q14 returns empty 4 times out of 5 on qwen3:14b.
   A single non-empty result on gpt-oss-120b does not establish
   reliability.
4. **Biased subset.** q06 and q15 were skipped (413, 8k TPM limit); q15 is
   the hardest case from exp2. 18/18 is measured on the easier subset.

**Fix.**

- Re-run exp2 with `think: true`. This is the cheapest control and isolates
  reasoning from size.
- Set `reasoning_effort` explicitly in exp3 and record it in `config.yaml`.
- Persist `raw` (`finish_reason`, `usage`) per question.
- Run ≥ 5 repeats per question for both models and report the
  non-vacuous rate per question.
- Cap evidence per entity (e.g. ≤ 10 relations) in **both** experiments, so
  that q06/q15 fit the 8k limit and both models see identical prompts.

### M2. Entity grounding is weaker than reported

Of 219 distinct entities in exp2's final run, **80 (36.5%) are "not
found"** (Gene 32, Compound 29, Disease 19). The README says absent
entities "will correctly come back 'not found'. This is itself useful
signal, not a bug." Inspection of the evidence files shows most
"not found" cases fall into two other categories:

| Category | Examples |
|---|---|
| **Name-matching failure** (entity exists in Hetionet under another name) | `type 2 diabetes` (Hetionet: "type 2 diabetes mellitus"), `HER2` (ERBB2), `p21` (CDKN1A), `c-KIT` (KIT), `p73` (TP73), `DJ-1` (PARK7) |
| **Excluded by Hetionet's design** | Biologics: `adalimumab`, `etanercept`, `rituximab`, `cetuximab`, `tocilizumab` (Hetionet's Compound nodes are small molecules). Diseases outside Hetionet's 137-disease set: `cystic fibrosis`, `hyperlipidemia` |

In addition, 8 entities are counted as **found under the wrong label**:
`colorectal cancer` → SideEffect, `epilepsy` → SideEffect, `fever` →
Symptom, `benzodiazepines` → PharmacologicClass. `found` is set to `True`
for these. Their evidence is then drawn from SideEffect/Symptom edges,
which the prompt says must be ignored.

**Fix.**

- Report grounding in three categories: exact match / name mismatch /
  out of Hetionet's scope.
- Count only same-label matches as `found`.
- Add synonym resolution: HGNC aliases for genes, Disease Ontology synonyms
  for diseases, DrugBank synonyms for compounds.
- Revise the README sentence accordingly.

### M3. `shacl_poc/README.md` attribution

1. **Arithmetic.** The README says "Of the 34 results, 29 trace to real
   converter errors … the remaining 3 …". The listed categories sum to
   13 + 1 + 1 + 16 = **31**, and 31 + 3 = 34.
2. **q09 is incomplete.** The README attributes q09 to an over-strict
   shape. It omits that the agent's claim is factually wrong: ABCG5/ABCG8
   are sitosterolemia genes, not cystic fibrosis genes. It is also
   debatable whether a converter that withholds the relation should emit
   isolated Gene nodes at all.
3. **Contradiction with exp1.** The 16 label-pattern warnings (`p53` instead
   of `TP53`) are attributed to the converter for **not** normalizing names.
   `exp1_text_to_rdf/README.md` attributes `muscarinic receptors` → `CHRM3`
   to the converter for normalizing names (knowledge injection). Both stem
   from one prompt conflict: "use the official gene symbol" vs. "do NOT …
   infer facts from your own knowledge".

**Fix.** Replace the narrative with an attribution table with four columns:
agent / converter / shape design / prompt specification. Report the prompt
conflict as one finding, and resolve it with an explicit policy. The
recommended policy is to let the converter keep surface names and perform
symbol normalization deterministically in code (HGNC alias lookup), so that
no knowledge injection happens in the LLM.

### M4. Text2KGBench metric mapping

In Text2KGBench, a triple conforms to the ontology (OC) when **its relation
is one of the ontology's relations**, and RH checks relation membership
against the ontology. Neither involves domain/range. Because exp1's JSON
schema restricts `relation` to an `enum`, OC as defined in the paper is
**1.0 by construction** and RH is **0**. The README maps OC to
`domain_range_correct_rate`, which is a stricter, different metric.

**Fix.** Report both values: `OC_paper` (relation ∈ schema, trivially 1.0
here, with an explanation) and `OC_domain_range` (current metric, 0.905).
Rename the latter in `evaluate.py` and `report.md`, and do not call
`1 − domain_range_correct_rate` "RH".

### M5. Statistical validity

- 20 questions, one run per configuration, no variance or confidence
  intervals.
- The agent runs with `temperature: null` (model default), so answers are
  not reproducible beyond the cached `answers.jsonl`.
- Exp2 itself observed non-determinism at `temperature=0.0`.

**Fix.**

- ≥ 3–5 runs per configuration; report mean ± std, or bootstrap CIs over
  questions.
- Set an explicit `seed` in Ollama `options`.
- Grow the question set, e.g. by template-generating questions from
  Hetionet with known answer sets, split by entity into train/test.

---

## Minor findings

| # | Location | Issue | Fix |
|---|---|---|---|
| m1 | `exp1 evaluate.py` `_mentioned_in_text` | Substring match gives false "mentioned" hits (e.g. `ace` ⊂ "replace"). Measured impact on this run: **1** case (q17, `ovarian cancer`). | Whole-word regex: `(?<![a-z0-9])name(?![a-z0-9])`. |
| m2 | `exp2/exp3 run_experiment.py` | `n_violations = results_text.count("Constraint Violation")` depends on pySHACL's text format and ignores severity. | Count `sh:ValidationResult` nodes in `results_graph`, grouped by `sh:resultSeverity`. |
| m3 | `shacl_poc` shapes | `sh:maxCount 0` reports once per node, so 7 reversed `BCR-ABL` edges show as 1. | If counts are reported as a metric, use a SPARQL-based constraint (`sh:sparql`) that yields one result per edge. |
| m4 | `shacl_poc` HGNC pattern | `^[A-Z][A-Z0-9-]*[0-9A-Z]$` rejects valid symbols with lowercase letters, e.g. `C9orf72` → false warning. | Use the HGNC symbol list as the check, or relax the regex to allow `orf`. |
| m5 | `exp3 src/llm.py` | Docstring says "Retries once"; the code retries up to 5 times. | Fix the docstring. |
| m6 | `exp3 config.yaml` | Comment says `GROQ_API_KEY`; the code reads `GROK_API_KEY`. | Align, or read `GROQ_API_KEY` and fall back to `GROK_API_KEY`. |
| m7 | `exp3 runs/20261028_154406`, `…_155338` | Aborted runs committed without `report.md`. | Delete them, or list them in the README as aborted. |
| m8 | all `requirements.txt` | No version pins; Ollama model tag not pinned to a digest. | `pip freeze` per experiment; record `ollama show --modelfile` / digest in each run's `config.yaml`. |
| m9 | repo | No tests. | Unit tests for `slugify`, `json_to_graph`, `_domain_range_ok`, `render_shapes`, `build_json_schema`. |
| m10 | exp2/exp3 `src/` | `llm.py`, `hetionet_client.py`, `evidence.py` exist in multiple copies (intentional); drift risk. | Keep copies, but add a test or script that diffs the shared files; or move them into a shared package and copy the source into each run directory for reproducibility. |
| m11 | exp2/exp3 | Depend on the public `neo4j.het.io` server at run time. | Add `--reuse-evidence <run>` to re-run only the LLM step from cached `evidence/*.json`. |
| m12 | `exp1 few_shot.json` | Example 1 maps "acts through activation of AMPK" to `metformin binds PRKAA1`. That is indirect activation, looser than the schema's "binds / targets". No example covers protein names, drug classes ("ACE inhibitors such as…") or hedged claims, which are exactly the q07/q09 failure modes. | Replace example 1 with a direct-binding case; add examples for protein-name targets, drug classes, and hedged statements. Re-run with `--reuse-answers`. |
| m13 | `exp1 evaluate.py` `write_annotation_csv` | `answer_excerpt` truncated to 200 chars; `correct_types` column is never read. | Write the full answer (or the matching sentence); read `correct_types` or drop it. |

---

## Verified as correct

- Exp1 domain/range errors (21/221) coincide exactly with the SHACL
  domain/range findings (q07: 13, q05: 7, q02: 1).
- No URI collisions in `merged.ttl`: no node has more than one `rdf:type`
  or more than one `rdfs:label`.
- Exp2/Exp3 violation counts and conformance numbers match their
  `report.md` files.
- Exp2's `IN_VOCAB_RELATION_TYPES` fix is correct and well documented.
- Moving Turtle generation out of the LLM (JSON → deterministic rendering)
  is the right design, and the 0/20 → 20/20 parse result supports it.
- Design history and limitations are documented candidly throughout.

---

## Recommended order of work

1. **C1**: add the no-LLM baseline row to Exp2/Exp3 reports; update both
   READMEs' conclusions.
2. **M3, M4**: correct the arithmetic, attribution table and Text2KGBench
   mapping. These are text fixes, but they are claims a reviewer will check.
3. **C2**: fill the annotation for one run; add `n_missed`, recall and F1.
4. **M2**: same-label-only `found`, synonym resolution, grounding report by
   category.
5. **M1**: exp2 with `think: true`; exp3 with explicit `reasoning_effort`,
   repeats, persisted `finish_reason`.
6. **m12**: few-shot revision and converter re-run, the cheapest test of
   whether q07 is a prompt problem.
7. Remaining minor items.

---

## Appendix A: no-LLM baseline

Run from the repository root, with `pyshacl`, `rdflib`, `pyyaml` and
`requests` installed (the last is needed only because `shape_agent.py`
imports `llm.py`):

```python
import sys, yaml
from pathlib import Path
sys.path.insert(0, "exp2_shacl_agent")
from src.shape_agent import render_shapes
from pyshacl import validate
from rdflib import Graph

run = Path("exp1_text_to_rdf/runs/20261026_161722")
schema = yaml.safe_load((run / "schema.yaml").read_text(encoding="utf-8"))
ttl = render_shapes({"supported_relations": list(schema["relations"])}, schema)
shapes = Graph().parse(data=ttl, format="turtle")
for g in sorted((run / "graphs").glob("q*.ttl")):
    conforms, _, txt = validate(Graph().parse(g), shacl_graph=shapes, inference="none")
    print(g.stem, conforms, txt.count("Constraint Violation"))
```

Output: q02 = 1, q05 = 1, q07 = 13, all others 0 (17/20 conform).

## References

- Mihindukulasooriya et al. (2023). *Text2KGBench: A Benchmark for
  Ontology-Driven Knowledge Graph Generation from Text.* ISWC 2023.
  [arXiv:2308.02357](https://arxiv.org/abs/2308.02357)
- Himmelstein et al. (2017). *Systematic integration of biomedical knowledge
  prioritizes drugs for repurposing.* eLife 6:e26726.
  https://doi.org/10.7554/eLife.26726
- OpenAI, gpt-oss model card (reasoning effort levels):
  https://developers.openai.com/docs/models/gpt-oss
