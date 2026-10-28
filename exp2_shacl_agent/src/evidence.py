"""Gathers per-entity grounding evidence from live Hetionet for a set of
extracted (type, name) entities, and formats it as a text block for the
shape-generating agent's prompt.
"""
from __future__ import annotations

from .hetionet_client import HetionetClient


def gather_evidence(entities: list[dict], client: HetionetClient) -> list[dict]:
    """entities: [{"type": "Gene", "name": "PRKAA1"}, ...] (deduplicated).

    Returns one evidence record per entity: the lookup result plus a sample
    of real relations if the entity was found.
    """
    evidence = []
    for ent in entities:
        lookup = client.lookup_entity(ent["name"], ent["type"])
        relations = []
        if lookup["found"]:
            relations = client.get_sample_relations(lookup["identifier"], lookup["hetio_type"])
        evidence.append({"type": ent["type"], "name": ent["name"], "lookup": lookup, "relations": relations})
    return evidence


def format_evidence_block(evidence: list[dict]) -> str:
    lines = []
    for e in evidence:
        lookup = e["lookup"]
        if not lookup["found"]:
            cand_str = ""
            if lookup["candidates"]:
                cand_names = ", ".join(
                    f"{c['name']} ({c['labels'][0] if c.get('labels') else '?'})" for c in lookup["candidates"][:5]
                )
                cand_str = f" Similar names found in Hetionet (different entity): {cand_names}."
            lines.append(f"- {e['type']} \"{e['name']}\": NOT FOUND in Hetionet.{cand_str}")
            continue

        note = "" if lookup["exact"] else f" (found as Hetionet type '{lookup['hetio_type']}', not '{e['type']}')"
        rel_lines = []
        for r in e["relations"]:
            if r["direction"] == "forward":
                rel_lines.append(f"{e['name']} -{r['relation']}-> {r['neighbor_name']} ({r['neighbor_type']})")
            else:
                rel_lines.append(f"{r['neighbor_name']} ({r['neighbor_type']}) -{r['relation']}-> {e['name']}")
        rel_str = "; ".join(rel_lines) if rel_lines else "no relations found"
        lines.append(f"- {e['type']} \"{e['name']}\": FOUND in Hetionet{note}. Real relations: {rel_str}")
    return "\n".join(lines) if lines else "(no entities to ground)"
