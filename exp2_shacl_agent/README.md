# Experiment 2: Live-Hetionet-grounded SHACL shapes

Instead of hand-written SHACL shapes (`shacl_poc/`) or a static schema file,
this experiment uses an LLM agent to **write SHACL shapes on the fly**, per
question, grounded in real Hetionet facts retrieved live over the network -
then validates `exp1_text_to_rdf`'s already-extracted RDF graphs against
those freshly generated shapes.

## Pipeline

```
exp1 run (question, answer, extracted graph)
        |
        v
for each distinct entity in the extracted graph:
        query live Hetionet (bolt://neo4j.het.io) -> does it exist? real relations?
        |
        v
evidence block (question + answer + real Hetionet facts for these entities)
        |
        v
shape-generating agent (LLM) -> SHACL shapes (Turtle), scoped to hetio: vocabulary
        |
        v
pySHACL validates the exp1 graph against these generated shapes
```

## On Hetionet access

No local download of the dataset is used. Hetionet v1.0 is hosted, read-only,
with anonymous access, at `bolt://neo4j.het.io:7687` (confirmed reachable;
see https://neo4j.het.io and the `hetionet.adoc` guide in
https://github.com/hetio/hetionet). `src/hetionet_client.py` queries it
directly via the official `neo4j` Python driver - no API key, no download.

Citation: Himmelstein, D.S. et al. (2017). *Systematic integration of
biomedical knowledge prioritizes drugs for repurposing.* eLife 6:e26726.
https://doi.org/10.7554/eLife.26726

Note: Hetionet is a curated snapshot (~2015-era DrugBank/Disease Ontology
coverage), not an exhaustive drug/disease database - entities genuinely
absent from it (e.g. some drugs not in DrugBank at the time, or diseases
named differently than their Disease Ontology label) will correctly come
back "not found". This is itself useful signal, not a bug.

## How we query Hetionet for evidence (and a sampling bug we fixed)

`src/hetionet_client.py`'s `get_sample_relations()` runs two Cypher queries
per entity (one per edge direction), `MATCH (n)-[r]->(m) ... LIMIT 25`. The
**first version of this query had no `WHERE type(r) IN [...]` filter at
all**. This silently biased the sample toward whichever Hetionet edge type a
node happens to have the *most* of - for a Compound, that is almost always
`CAUSES_CcSE` (side effects, often hundreds per drug), not the rare
`TREATS_CtD`/`BINDS_CbG` edges we actually care about - so the first 25 rows
in either direction were routinely 100% out-of-vocabulary, even when
in-vocabulary edges existed deeper in the node's edge list. This was a
sampling/query-design bug in *our own tool*, not a Hetionet data-coverage
gap, so fixing it does not cross the "don't fix away what we're trying to
measure" line (see `shacl_poc`'s README for that principle, which applies to
the *converter* being validated, not to our own evidence-retrieval code).

**Fix**: added `IN_VOCAB_RELATION_TYPES = ["TREATS_CtD", "BINDS_CbG",
"ASSOCIATES_DaG", "INTERACTS_GiG"]` and filter both direction queries with
`WHERE type(r) IN $rel_types` before the `LIMIT`, falling back to a small
unfiltered sample only if the filtered query returns zero rows (so the
evidence block can still say "found, but no in-vocab edges" instead of
nothing). Verified by hand before the costly LLM re-run: calling the fixed
client directly (no LLM) against the 7 previously-vacuous questions
recovered 134-554 in-vocabulary relation rows per question, where before
there had been 0. Re-running the full pipeline after this fix
(`runs/20261028_130135`) went from 7/20 vacuous to **0/20 vacuous**, and for
the first time produced a real, correct violation (q02's Disease-Disease
`associatedWith`, matching `shacl_poc`'s independent hand-written-shape
finding exactly) instead of either nothing or a hallucinated constraint.

## What the generated shapes constrain

The agent is instructed to only mark a relation as evidence-supported if the
live evidence actually shows a corresponding Hetionet edge (translated
through the Hetionet-metaedge <-> our-relation mapping given in the prompt,
see `src/shape_agent.py`). It is explicitly told not to invent support the
evidence doesn't give, and not to reference entities that weren't found.
This keeps it at the same level as `shacl_poc`'s hand-written shapes
(generic, type-level structural rules) rather than hard-coding the specific
gold triples of each question as constraints.

The agent never writes Turtle itself: like exp1_text_to_rdf's converter, it
only produces schema-constrained JSON (Ollama structured outputs). A first
version that let the model write free-text Turtle directly was unreliable
(0/20 parsed - invented namespaces, invalid SHACL predicates, Hetionet's own
metaedge-abbreviation names); switching to structured JSON + deterministic
Turtle rendering (`render_shapes()`, via rdflib) fixed parsing completely
(20/20) and has stayed at 20/20 through every change described below.

**The LLM's JSON output asks for exactly one judgment call per relation: is
it evidence-supported, yes or no** (`{"supported_relations": [...]}`,
an array of relation names). It is never asked to also state *which* type is
the source/target ("direction") - `render_shapes()` looks that up directly
from `schema.yaml`'s fixed `source`/`target` per relation and derives the
entire shape deterministically: a positive `sh:class` constraint on the
correct source type, plus a complementary `sh:maxCount 0` "forbid"
constraint on every other node type for that same relation path. This design
replaced an earlier version where the LLM's JSON *also* had to state
`target_class`/`forbid` per property (i.e. direction) - see "Design history"
below for why that was removed.

## Design history: why direction was removed from the LLM's output

Early versions asked the LLM to decide, per relation, not just whether it
was supported but *also* which type was the correct source (effectively,
direction) - even though direction is a fixed structural fact already stated
to the LLM verbatim in its own prompt (e.g. "binds <-> Hetionet CbG:
Compound -binds-> Gene") and already known from `schema.yaml`. This surfaced
three problems, in order:

1. **Low constraint density** (`runs/20261028_130135`): because the agent
   only emitted a constraint for the *one* source type it decided on, each
   question ended up with 1-3 constraints total, with no complementary
   "forbid" constraints on the other types - so a relation pointing from the
   *wrong* type (the actual kind of bug we want to catch) often went
   unconstrained simply because nothing was ever asserted about non-source
   types.
2. **Fix attempt ("Option 1", `runs/20261028_133241`)**: `render_shapes()`
   was changed to automatically derive the complementary `maxCount 0`
   "forbid" constraints on every other type, from whichever source type the
   LLM had stated. This raised density to 3 constraints/question for all 20
   questions and correctly reproduced `shacl_poc`'s q07 finding (13 real
   `binds` Compound->Disease violations) for the first time - but it also
   amplified a pre-existing, previously-harmless LLM reliability issue: the
   LLM sometimes reversed direction even when it had read the evidence
   correctly (q01 - it assigned `treats` to `DiseaseShape` and `binds` to
   `GeneShape`, both backwards). Once the forbid-complement derived from that
   wrong direction, it produced 8 **false-positive** violations against
   exp1's correct data.
3. **Final fix (current code, `runs/20261028_135734`)**: removed direction
   from the LLM's output entirely, as described above. This eliminated the
   q01 false positives completely (0 violations, conforms=True) while
   *keeping* every real finding: q07's 13 violations, q02's Disease-Disease
   bug, and a newly-caught q05 violation (`BCR-ABL`, a Gene, as the subject
   of `binds` - a reversed-direction bug in exp1's extracted graph that
   `shacl_poc`'s hand-written shapes had also found independently). Overall:
   0/20 vacuous, 17/20 conform, and all 3 non-conforming questions (q02, q05,
   q07) are genuine, previously-known bugs in exp1's data - zero false
   positives from the shape agent itself.

## Known limitation: LLM reliability on large, dense evidence blocks

After the fix above, 3/20 questions (q14, q15, q19) still came back vacuous
- but **not** for the old reason (missing/out-of-vocabulary evidence). These
are exactly the 3 questions with the most distinct entities (19, 15, 12),
whose evidence blocks are correspondingly large (8.9k-21.8k characters, one
very long line per entity listing up to ~50 sampled relations). Manually
re-running `generate_shapes()` (no code changes, same prompt, temperature
0.0) directly against these cases confirmed the evidence itself is
plentiful and unambiguous - e.g. q15's evidence shows dozens of
`APC -INTERACTS_GiG-> ...` and `... -ASSOCIATES_DaG-> APC` edges - yet the
model still returned an empty `supported_relations` list.

Repeating the identical call 5 times for q14 produced an empty list 4 times
and a partial, still-incomplete non-empty list once
(`["interactsWith", "binds"]`, missing `treats`/`associatedWith` despite
equally clear evidence for those). **This shows qwen3:14b is not fully
deterministic even at `temperature=0.0`** (a known characteristic of
batched/concurrent GPU inference, where floating-point reduction order can
vary run to run) - and, more importantly, that it has a genuine reliability
limit when the per-entity evidence lines are this dense/long, independent of
determinism. This is a model-capacity limitation surfaced by the experiment,
not a bug in our evidence-gathering or rendering code, and is left
undocumented-as-"fixed" deliberately (same principle as throughout this
project: let validation/generation-layer problems surface as measured
findings rather than engineering them away). A real fix would mean either
summarizing/capping evidence per entity before it reaches the prompt, or
enabling `think: true`, both out of scope for this run.

## Usage

```
pip install -r requirements.txt
python -m src.run_experiment --exp1-run ../exp1_text_to_rdf/runs/<timestamp>
```

Writes `runs/<timestamp>/`:
- `evidence/<qid>.json` - raw Hetionet lookup/relations per entity
- `shapes/<qid>.ttl` - the LLM-generated SHACL shapes for that question
- `validation/<qid>.txt` - pySHACL report (only if the shapes parsed)
- `report.md` - summary: shape parse rate, conformance rate, per-question table

## Scope note

This experiment is a proof-of-concept: it measures whether an LLM can decide
*usable*, evidence-grounded SHACL constraints, not just whether the
resulting validation verdict happens to be correct. `report.md` tracks
`shapes_parse_ok` (now 20/20 after the JSON-structured-output fix above),
`n_shapes`/`vacuous` (how often nothing was actually checked), and
`conforms`/`n_violations` - read all three together, since a high
conformance rate on its own is not a success metric here (see "Known
limitation" above).
