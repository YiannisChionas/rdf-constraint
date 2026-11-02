# SHACL validation proof-of-concept (Hetionet-derived schema)

Mini, standalone proof-of-concept: validate the RDF graphs produced by
`exp1_text_to_rdf` against SHACL shapes, to see whether extracted facts
respect the Hetionet metagraph's own structural rules.

This is explicitly a side proof-of-concept, not part of Experiment 1's
scope (which excludes SHACL validation — see `exp1_text_to_rdf/README.md`).

## On the source of the constraints

No ready-made SHACL shapes for Hetionet were found online — Hetionet is
distributed as a Neo4j export / TSV files, not as RDF, and no community
RDF/OWL/SHACL port of it exists (checked: generic web search, GitHub
search for "hetionet shacl" / "hetionet rdf shacl").

The shapes in `shapes/gene_shapes.ttl` are therefore hand-written, but
every class, relation, domain/range and cardinality rule is taken directly
from Hetionet's own published metagraph, not invented ad hoc:

- Himmelstein, D.S. et al. (2017). *Systematic integration of biomedical
  knowledge prioritizes drugs for repurposing.* eLife 6:e26726.
  https://doi.org/10.7554/eLife.26726 — defines the Hetionet metagraph
  (node types Gene/Compound/Disease/..., metaedges CbG, CtD, DaG, GiG,
  and that Gene nodes are identified by official HGNC symbols).
- `../schema.yaml` — our Hetionet subset (same node
  types + the same four metaedges, renamed treats/binds/associatedWith/
  interactsWith).

"Ready-made" in this PoC means the SHACL *language and engine* (W3C SHACL
+ [pySHACL](https://github.com/RDFLib/pySHACL)), not a borrowed shapes
file — since none exists for Hetionet.

## Shapes included

`shapes/gene_shapes.ttl` defines:

- **GeneShape** — `rdfs:label` cardinality; a soft (`sh:Warning`) pattern
  check that the label looks like an HGNC symbol (e.g. `TP53`) rather than
  a protein/enzyme name; a hard constraint that every Gene participates in
  at least one `binds`/`associatedWith`/`interactsWith` relation (a Gene
  only exists in Hetionet because of a metaedge); domain/range checks for
  `associatedWith` (→ Disease) and `interactsWith` (→ Gene); a Gene is
  never the subject of `binds` (catches reversed CbG edges).
- **CompoundShape** — `rdfs:label` cardinality; domain/range for `treats`
  (→ Disease) and `binds` (→ Gene).
- **DiseaseShape** — `rdfs:label` cardinality; a Disease is never the
  subject of any relation (it is only ever a target in our schema).

## Usage

Run from `exp1_text_to_rdf/` as cwd:

```
pip install -r shacl_poc/requirements.txt
python shacl_poc/validate.py runs/<timestamp>/graphs/*.ttl
python shacl_poc/cross_check.py runs/<timestamp>   # cross-check vs. annotation.csv
```

Each question's graph (`graphs/<qid>.ttl`) is validated separately, not
merged into one big graph — merging a full run's graphs into one turned
out to both manufacture spurious violations (e.g. the same entity named
with different capitalization in two answers gets merged into one node
with two conflicting `rdfs:label` values) and hide real ones (a wrong
relation can "borrow" legitimacy from an unrelated answer's correct
mention of the same entity). See `validate.py`'s docstring.

## Result on the first exp1 run (historical)

The paragraph below describes the *first* validation ever run on this
project, against a single merged `merged.ttl` graph (625 triples) — a
methodology since dropped (see "Usage" above). That run (and the agent
answers it used — contaminated by a schema/few-shot data-leak bug since
fixed, see exp1's git history) was deleted once its findings were fully
captured here and in commit messages; re-validating the same graphs
per-question (not merged) gave 19 violations / 16 warnings instead of 34
— 1 more violation than below, because per-question validation also
catches an isolation error the merged graph had been hiding.

**Original (merged, now superseded) result**: 625 triples validated,
**does not conform** — 34 results (see `validation_report.txt` for the
full pySHACL report):

| Count | Severity | Finding |
|---|---|---|
| 13 | Violation | `hetio:binds` triples pointing from a Compound to a **Disease** instead of a Gene (e.g. `aliskiren binds hypertension`, all from `q07`). The agent's answer names the targets explicitly ("ACE (e.g., lisinopril)"), so this is a converter error: it skipped the Gene nodes and attached `binds` to the disease. |
| 3 | Violation | Gene nodes (`ABCG5`, `ABCG8`, `SLC26A9`) extracted with no relation at all (`q09`). The agent's answer hedges here — *"rare cases ... **may involve** mutations in other genes, such as SLC26A9 or ABCG5/ABCG8"* — vs. the categorical claim for CFTR. The converter correctly declined to assert a confident `associatedWith` for a hedged claim; **this is a shape-design fault, not a converter error** — the hard "every Gene needs ≥1 relation" constraint doesn't account for epistemic hedging in natural language. |
| 1 | Violation | `BCR-ABL` (Gene) is the subject of `binds` — 7 reversed edges `BCR-ABL binds <drug>` in `q05`, reported once since `sh:maxCount` is checked per node. |
| 1 | Violation | `breast cancer` (Disease) is the subject of `associatedWith` → `ovarian cancer` (`q02`): a Disease–Disease relation the schema doesn't have. |
| 16 | Warning | Gene labels that don't match the HGNC symbol pattern (e.g. `p53`, `p21`, `Nav1.1`, `HLA-DRB1*03:01`) — protein/common names extracted instead of the official gene symbol, consistent with the completeness gap already observed manually in `q01`. |

This confirms, mechanically and at scale, failure modes that had only been
spotted by manual inspection before: (1) relation-type confusion between
`treats` and `binds`, (2) reversed or out-of-schema relation direction, and
(3) gene naming inconsistency (symbol vs. protein name). Violations do not
by themselves say whether the agent, the converter, or our shapes are at
fault; that needs a look at the answer text. Of the 34 results, 29 trace to
real converter errors on categorical (non-hedged) text — the `binds`/
`treats` confusion, the reversed `BCR-ABL` edges, the `breast cancer`/
`ovarian cancer` domain violation, and the 16 label-pattern warnings. The
remaining 3 (`ABCG5`/`ABCG8`/`SLC26A9`) trace to hedged ("may involve")
source text that the converter handled appropriately by withholding a
confident relation — here the SHACL shape itself is too strict, not the
converter. SHACL also cannot catch factual errors that are structurally
valid (e.g. the agent's "asciminib (Blincyto)" in `q05`).
