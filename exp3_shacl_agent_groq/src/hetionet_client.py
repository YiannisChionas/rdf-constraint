"""Thin wrapper around the public, read-only Hetionet Neo4j instance.

Identical to exp2_shacl_agent's hetionet_client.py (same evidence-gathering
fix: Cypher queries filtered to IN_VOCAB_RELATION_TYPES before LIMIT, see
exp2_shacl_agent/README.md "How we query Hetionet for evidence"). Kept as a
standalone copy, not a cross-folder import, so this experiment has no
dependency on exp2_shacl_agent's state (same convention as exp2's own copy
of exp1's llm.py).

Hetionet v1.0 is hosted, with anonymous read access, at bolt://neo4j.het.io:7687
(see https://neo4j.het.io and https://github.com/hetio/hetionet). No local
download of the dataset is needed - this queries it live.

Citation: Himmelstein, D.S. et al. (2017). Systematic integration of
biomedical knowledge prioritizes drugs for repurposing. eLife 6:e26726.
https://doi.org/10.7554/eLife.26726
"""
from __future__ import annotations

import time

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

# Our schema's node type names map 1:1 onto Hetionet's Neo4j labels.
OUR_TYPE_TO_HETIO_LABEL = {
    "Gene": "Gene",
    "Compound": "Compound",
    "Disease": "Disease",
}

MAX_RELATIONS_PER_ENTITY = 25

# Hetionet's own relationship-type names for the 4 relations our schema cares
# about (see shape_agent.py's mapping comment). These are a tiny minority of
# any given node's total edges - e.g. a Compound typically has far more
# CAUSES_CcSE (side effect) edges than TREATS_CtD/BINDS_CbG ones - so an
# unfiltered "first N edges" sample routinely misses them entirely. Filtering
# the Cypher query itself (rather than filtering after sampling) fixes this.
IN_VOCAB_RELATION_TYPES = ["TREATS_CtD", "BINDS_CbG", "ASSOCIATES_DaG", "INTERACTS_GiG"]


MAX_RETRIES = 3


class HetionetClient:
    def __init__(self, uri: str = "bolt://neo4j.het.io:7687"):
        self._uri = uri
        self._driver = GraphDatabase.driver(uri, auth=None, encrypted=False)

    def close(self) -> None:
        self._driver.close()

    def _reconnect(self) -> None:
        self._driver.close()
        self._driver = GraphDatabase.driver(self._uri, auth=None, encrypted=False)

    def _with_retry(self, fn):
        """The public, anonymous neo4j.het.io connection occasionally drops an
        idle connection (ConnectionResetError/ServiceUnavailable) between our
        LLM calls - a third-party infra flakiness, not a signal we're trying
        to measure, so reconnecting and retrying here is a legitimate fix."""
        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                return fn()
            except ServiceUnavailable as e:
                last_err = e
                self._reconnect()
                time.sleep(1)
        raise last_err

    def lookup_entity(self, name: str, expected_type: str) -> dict:
        return self._with_retry(lambda: self._lookup_entity(name, expected_type))

    def _lookup_entity(self, name: str, expected_type: str) -> dict:
        """Look up a node by name, preferring an exact (case-insensitive) match
        restricted to the expected label, falling back to a fuzzy CONTAINS
        match if nothing exact is found.

        Returns {"found": bool, "exact": bool, "hetio_type": str|None,
        "identifier": ..., "hetio_name": str|None, "candidates": [...]}.
        """
        label = OUR_TYPE_TO_HETIO_LABEL.get(expected_type)
        with self._driver.session() as session:
            if label:
                exact = session.run(
                    f"MATCH (n:`{label}`) WHERE toLower(n.name) = toLower($name) "
                    "RETURN n.name AS name, n.identifier AS id LIMIT 1",
                    name=name,
                ).single()
                if exact:
                    return {
                        "found": True,
                        "exact": True,
                        "hetio_type": expected_type,
                        "identifier": exact["id"],
                        "hetio_name": exact["name"],
                        "candidates": [],
                    }

            # No exact match in the expected label - try any label, exact name.
            any_label_exact = session.run(
                "MATCH (n) WHERE toLower(n.name) = toLower($name) "
                "RETURN labels(n) AS labels, n.name AS name, n.identifier AS id LIMIT 3",
                name=name,
            ).data()
            if any_label_exact:
                rec = any_label_exact[0]
                found_type = rec["labels"][0] if rec["labels"] else None
                return {
                    "found": True,
                    "exact": found_type == expected_type,
                    "hetio_type": found_type,
                    "identifier": rec["id"],
                    "hetio_name": rec["name"],
                    "candidates": any_label_exact,
                }

            # Fuzzy fallback.
            fuzzy = session.run(
                "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($name) "
                "RETURN labels(n) AS labels, n.name AS name, n.identifier AS id LIMIT 5",
                name=name,
            ).data()
            return {
                "found": False,
                "exact": False,
                "hetio_type": None,
                "identifier": None,
                "hetio_name": None,
                "candidates": fuzzy,
            }

    def get_sample_relations(self, identifier, hetio_type: str) -> list[dict]:
        return self._with_retry(lambda: self._get_sample_relations(identifier, hetio_type))

    def _get_sample_relations(self, identifier, hetio_type: str) -> list[dict]:
        """Sample of real relationships for a confirmed Hetionet node, by its
        identifier + label. Returns [{relation, direction, neighbor_type,
        neighbor_name}, ...].

        Queries are filtered to IN_VOCAB_RELATION_TYPES first, since those
        are rare relative to a node's total edges (see comment above the
        constant) and would otherwise almost never survive an unfiltered
        LIMIT. Only if literally none of our 4 relation types are present
        do we fall back to a small unfiltered sample, purely so the evidence
        block can still show the entity isn't isolated (just evidenced by
        out-of-vocabulary Hetionet edges)."""
        if identifier is None or hetio_type is None:
            return []
        with self._driver.session() as session:
            rows = session.run(
                f"MATCH (n:`{hetio_type}` {{identifier: $id}})-[r]->(m) "
                "WHERE type(r) IN $rel_types "
                "RETURN type(r) AS rel, 'forward' AS direction, labels(m) AS neighbor_labels, m.name AS neighbor_name "
                "LIMIT $limit",
                id=identifier,
                rel_types=IN_VOCAB_RELATION_TYPES,
                limit=MAX_RELATIONS_PER_ENTITY,
            ).data()
            rows += session.run(
                f"MATCH (n:`{hetio_type}` {{identifier: $id}})<-[r]-(m) "
                "WHERE type(r) IN $rel_types "
                "RETURN type(r) AS rel, 'backward' AS direction, labels(m) AS neighbor_labels, m.name AS neighbor_name "
                "LIMIT $limit",
                id=identifier,
                rel_types=IN_VOCAB_RELATION_TYPES,
                limit=MAX_RELATIONS_PER_ENTITY,
            ).data()
            if not rows:
                rows = session.run(
                    f"MATCH (n:`{hetio_type}` {{identifier: $id}})-[r]->(m) "
                    "RETURN type(r) AS rel, 'forward' AS direction, labels(m) AS neighbor_labels, m.name AS neighbor_name "
                    "LIMIT 5",
                    id=identifier,
                ).data()
                rows += session.run(
                    f"MATCH (n:`{hetio_type}` {{identifier: $id}})<-[r]-(m) "
                    "RETURN type(r) AS rel, 'backward' AS direction, labels(m) AS neighbor_labels, m.name AS neighbor_name "
                    "LIMIT 5",
                    id=identifier,
                ).data()
        return [
            {
                "relation": r["rel"],
                "direction": r["direction"],
                "neighbor_type": r["neighbor_labels"][0] if r["neighbor_labels"] else None,
                "neighbor_name": r["neighbor_name"],
            }
            for r in rows
        ]
