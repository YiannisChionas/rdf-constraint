"""Converter JSON -> rdflib Graph -> Turtle.

Node URIs: ent:<slug> with rdf:type hetio:<Type> and rdfs:label "<name>".
Relationship: ent:<src> hetio:<relation> ent:<tgt>.

Slug rule: lowercase, spaces -> "_", strip unsafe characters.
Gene symbols are kept uppercase (per schema convention).
"""
from __future__ import annotations

import re
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, RDFS

_UNSAFE_RE = re.compile(r"[^A-Za-z0-9_]")


def slugify(name: str, node_type: str) -> str:
    s = name.strip()
    s = s.upper() if node_type == "Gene" else s.lower()
    s = s.replace(" ", "_")
    s = _UNSAFE_RE.sub("", s)
    return s or "unknown"


def json_to_graph(data: dict, schema: dict) -> tuple[Graph, list[str]]:
    """Convert one extraction JSON object into an rdflib Graph.

    Returns (graph, warnings). Warnings cover duplicate nodes merged and
    dangling relationship references (source/target id not defined).
    """
    hetio = Namespace(schema["namespaces"]["hetio"])
    ent = Namespace(schema["namespaces"]["ent"])

    g = Graph()
    g.bind("hetio", hetio)
    g.bind("ent", ent)

    warnings: list[str] = []
    id_to_uri: dict[str, object] = {}
    seen_keys: dict[tuple[str, str], object] = {}  # (type, normalized name) -> uri

    for node in data.get("nodes", []):
        nid = node.get("id")
        ntype = node.get("type")
        name = node.get("name", "")
        key = (ntype, name.strip().lower())

        if key in seen_keys:
            uri = seen_keys[key]
            warnings.append(f"duplicate node merged: id={nid} type={ntype} name={name!r}")
        else:
            slug = slugify(name, ntype)
            uri = ent[slug]
            seen_keys[key] = uri
            g.add((uri, RDF.type, hetio[ntype]))
            g.add((uri, RDFS.label, Literal(name)))

        id_to_uri[nid] = uri

    for rel in data.get("relationships", []):
        src_id = rel.get("source")
        relation = rel.get("relation")
        tgt_id = rel.get("target")

        if src_id not in id_to_uri or tgt_id not in id_to_uri:
            warnings.append(f"dangling reference: {src_id} -{relation}-> {tgt_id}")
            continue

        g.add((id_to_uri[src_id], hetio[relation], id_to_uri[tgt_id]))

    return g, warnings


def serialize_graph(g: Graph, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(path), format="turtle")


def validate_turtle_roundtrip(path: str | Path) -> bool:
    """Re-parse a written .ttl file to confirm it is valid Turtle."""
    try:
        Graph().parse(str(path), format="turtle")
        return True
    except Exception:
        return False
