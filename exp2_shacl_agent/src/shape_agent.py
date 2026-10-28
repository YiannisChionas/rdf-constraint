"""The shape-generating agent (LLM call 3): question + answer + live Hetionet
grounding evidence -> SHACL shapes, scoped to our hetio: vocabulary (same
namespace as exp1_text_to_rdf's extracted graphs).

Like exp1_text_to_rdf's converter, the LLM only produces schema-constrained
JSON (via Ollama structured outputs) - it decides WHICH domain/range and
cardinality constraints the evidence supports, but never writes Turtle syntax
itself. Turtle is then rendered deterministically in Python (render_shapes),
which guarantees syntactically valid SHACL on every run - free-text Turtle
generation was tried first and was unreliable (see README "Known risk" note
and runs/20261027_232313..20261027_233910 for the before/after).

The LLM's JSON output is deliberately limited to ONE judgment call per
relation: "does the live Hetionet evidence support this relation for at
least one entity in this question?" (yes/no). It is never asked to also
state which type is the source/target ("direction") - that is a fixed
structural fact already given to it verbatim in the prompt and already
known from schema.yaml, so asking the LLM to restate it adds no information
but does add a reliability risk: in practice the LLM sometimes reversed
direction even when it had read the evidence correctly (see
runs/20261028_133241, q01/q07). render_shapes() now derives the entire
shape - the positive sh:class constraint on the correct source type, and
the complementary sh:maxCount 0 "forbid" constraints on every other node
type - directly from schema["relations"][name]["source"/"target"], so a
direction error in the generated SHACL is no longer possible.
"""
from __future__ import annotations

from rdflib import BNode, Graph, Literal, Namespace, RDF
from rdflib.namespace import SH, XSD

from .llm import OllamaClient

SHAPE_AGENT_INSTRUCTIONS_TEMPLATE = """You decide which of our relations are justified by evidence, for an RDF
graph that uses ONLY the vocabulary below. The graph was extracted from the
"Answer" text by a separate process; you are not extracting facts, you are
deciding which validation rules apply to that graph's structure, grounded in
the live Hetionet evidence given below.

Vocabulary (this is what the graph being validated uses; direction is fixed
and not something you need to decide):
Node types: Gene, Compound, Disease
Relations (source type, relation, target type):
{relations_block}

How our relations map onto Hetionet's own real metaedges (for your reference
when reading the evidence below, which uses Hetionet's own relation names):
- treats <-> Hetionet CtD: Compound -treats-> Disease (same direction)
- binds <-> Hetionet CbG: Compound -binds-> Gene (same direction)
- associatedWith <-> Hetionet DaG: Disease -associates-> Gene in Hetionet,
  but in OUR schema the direction is reversed: Gene -associatedWith-> Disease
- interactsWith <-> Hetionet GiG: Gene -interacts-> Gene (same direction)

Question (context only, not part of the graph):
{question}

Answer (the text the graph was extracted from):
{answer}

Live Hetionet evidence for the entities mentioned (ground truth from the
public Hetionet knowledge graph, https://neo4j.het.io):
{evidence_block}

Task: for each of our 4 relations, decide if the evidence above shows a real
Hetionet edge of that type (translated via the mapping above) for at least
one of the entities found. Rules:
- Only mark a relation as supported if the evidence actually shows it.
  Do not invent support the evidence does not give.
- Evidence about Hetionet edge/node types outside our vocabulary (e.g.
  SideEffect, PharmacologicClass, Anatomy, BiologicalProcess) must be
  ignored entirely - it never justifies support.
- If no entity was found, or none of the evidence translates into one of
  our 4 relations, mark all relations as unsupported.
- You do not need to state which type is the source or target - that is
  fixed and already given above; just decide yes/no per relation.
"""


def build_prompt(schema: dict, question: str, answer: str, evidence_block: str) -> str:
    rel_lines = [
        f"- ({info['source']}, {name}, {info['target']})"
        for name, info in schema["relations"].items()
    ]
    relations_block = "\n".join(rel_lines)
    return SHAPE_AGENT_INSTRUCTIONS_TEMPLATE.format(
        relations_block=relations_block,
        question=question,
        answer=answer,
        evidence_block=evidence_block,
    )


def build_json_schema(schema: dict) -> dict:
    relation_names = list(schema["relations"].keys())
    return {
        "type": "object",
        "properties": {
            "supported_relations": {
                "type": "array",
                "items": {"type": "string", "enum": relation_names},
                "description": "Relation names the evidence supports (empty list if none).",
            },
        },
        "required": ["supported_relations"],
    }


SH_NS = SH
HETIO = Namespace("http://example.org/hetio/")
ENT = Namespace("http://example.org/hetio/entity/")


def render_shapes(parsed: dict, schema: dict) -> str:
    """Deterministically render the agent's JSON decision into valid Turtle.

    This is the step that replaces free-text Turtle generation. The LLM's
    only judgment call is WHICH relations the evidence supports
    (parsed["supported_relations"]); direction (source/target type) is never
    part of its output - for every supported relation, this function looks
    up the fixed source/target types straight from schema["relations"] and
    deterministically emits:
      (a) a positive sh:class constraint on the correct source type's shape,
          constraining the relation to point to the correct target type;
      (b) a complementary sh:maxCount 0 "forbid" constraint on every OTHER
          node type's shape, for that same relation path.
    Because direction never passes through the LLM, a direction error in the
    generated SHACL (as previously seen for treats/binds in some questions)
    is no longer possible.
    """
    g = Graph()
    g.bind("sh", SH_NS)
    g.bind("hetio", HETIO)
    g.bind("ent", ENT)
    g.bind("xsd", XSD)

    shape_nodes: dict[str, object] = {}
    node_type_names = list(schema["node_types"].keys())

    def get_shape_node(target_class: str):
        if target_class not in shape_nodes:
            node = HETIO[f"{target_class}Shape"]
            g.add((node, RDF.type, SH_NS.NodeShape))
            g.add((node, SH_NS.targetClass, HETIO[target_class]))
            shape_nodes[target_class] = node
        return shape_nodes[target_class]

    supported = [
        name for name in parsed.get("supported_relations", [])
        if name in schema["relations"]
    ]

    for path in supported:
        rel = schema["relations"][path]
        source_type, target_type = rel["source"], rel["target"]

        shape_node = get_shape_node(source_type)
        prop_node = BNode()
        g.add((shape_node, SH_NS.property, prop_node))
        g.add((prop_node, SH_NS.path, HETIO[path]))
        g.add((prop_node, SH_NS["class"], HETIO[target_type]))
        g.add((prop_node, SH_NS.message, Literal(
            f"hetio:{path} must point from a {source_type} to a {target_type}."
        )))

        for other_type in node_type_names:
            if other_type == source_type:
                continue
            other_shape_node = get_shape_node(other_type)
            forbid_node = BNode()
            g.add((other_shape_node, SH_NS.property, forbid_node))
            g.add((forbid_node, SH_NS.path, HETIO[path]))
            g.add((forbid_node, SH_NS.maxCount, Literal(0)))
            g.add((forbid_node, SH_NS.message, Literal(
                f"A {other_type} is never the subject of hetio:{path} "
                f"(confirmed direction: {source_type} -{path}-> ...)."
            )))

    return g.serialize(format="turtle")


def generate_shapes(
    client: OllamaClient,
    model: str,
    schema: dict,
    question: str,
    answer: str,
    evidence_block: str,
    temperature: float = 0.0,
    think: bool = False,
) -> dict:
    import json

    prompt = build_prompt(schema, question, answer, evidence_block)
    json_schema = build_json_schema(schema)
    result = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        think=think,
        format=json_schema,
    )
    parsed = None
    parse_error = None
    shapes_turtle = ""
    try:
        parsed = json.loads(result.content)
        shapes_turtle = render_shapes(parsed, schema)
    except Exception as e:
        parse_error = str(e)

    return {
        "prompt": prompt,
        "raw_content": result.content,
        "parsed": parsed,
        "parse_error": parse_error,
        "shapes_turtle": shapes_turtle,
        "latency_s": result.latency_s,
    }
