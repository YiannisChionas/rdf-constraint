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
- `../exp1_text_to_rdf/schema.yaml` — our Hetionet subset (same node
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
  `associatedWith` (→ Disease) and `interactsWith` (→ Gene).
- **CompoundShape** — `rdfs:label` cardinality; domain/range for `treats`
  (→ Disease) and `binds` (→ Gene).
- **DiseaseShape** — `rdfs:label` cardinality.

## Usage

```
pip install pyshacl
python validate.py <path/to/graph.ttl> [more .ttl files...]
```

Example, against an exp1 run:

```
python validate.py ../exp1_text_to_rdf/runs/20261026_161722/merged.ttl
```

## Result on `runs/20261026_161722/merged.ttl`

625 triples validated, **does not conform** — 32 results (see
`validation_report.txt` for the full pySHACL report):

| Count | Severity | Finding |
|---|---|---|
| 13 | Violation | `hetio:binds` triples pointing from a Compound to a **Disease** instead of a Gene (e.g. `aliskiren binds hypertension`) — the converter mislabeled what should likely be `treats` as `binds`. |
| 3 | Violation | Gene nodes (`ABCG5`, `ABCG8`, `SLC26A9`) extracted with no relation at all — isolated nodes that shouldn't exist under Hetionet's metagraph (a Gene only appears via a metaedge). |
| 16 | Warning | Gene labels that don't match the HGNC symbol pattern (e.g. `p53`, `p21`, `Nav1.1`, `HLA-DRB1*03:01`) — protein/common names extracted instead of the official gene symbol, consistent with the completeness gap already observed manually in `q01`. |

This confirms, mechanically and at scale, two failure modes that had only
been spotted by manual inspection before: (1) relation-type confusion
between `treats` and `binds`, and (2) gene naming inconsistency (symbol vs.
protein name).
