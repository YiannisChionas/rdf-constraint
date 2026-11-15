"""Deterministic lookup layer over kb.json — no ToG-style live Freebase/
Wikidata backend, just in-memory dict lookups (see README for why).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_NAME_RE = re.compile(r"[a-z0-9]+")


class KB:
    def __init__(self):
        raw = json.loads((DATA_DIR / "kb.json").read_text(encoding="utf-8"))
        self.concepts: dict[str, dict] = raw["concepts"]
        self.entities: dict[str, dict] = raw["entities"]
        self._build_name_index()

    def _build_name_index(self) -> None:
        self._id_to_name: dict[str, str] = {}
        self._name_to_ids: dict[str, list[str]] = {}
        for store in (self.concepts, self.entities):
            for id_, obj in store.items():
                name = obj.get("name", "")
                self._id_to_name[id_] = name
                self._name_to_ids.setdefault(name.lower(), []).append(id_)

    def name(self, id_: str) -> str:
        return self._id_to_name.get(id_, id_)

    def find_topic_entities(self, question: str, max_entities: int = 4) -> list[tuple[str, str]]:
        """Heuristic, deterministic entity linking: longest known entity/concept
        names that appear as substrings of the question, case-insensitive."""
        q_lower = question.lower()
        candidates = [
            (name, ids[0])
            for name, ids in self._name_to_ids.items()
            if len(name) >= 3 and name in q_lower and ids[0] in self.entities
        ]
        candidates.sort(key=lambda t: len(t[0]), reverse=True)

        picked: list[tuple[str, str]] = []
        covered = [False] * len(question)
        for name, eid in candidates:
            start = q_lower.find(name)
            if start == -1:
                continue
            if any(covered[start:start + len(name)]):
                continue
            for i in range(start, start + len(name)):
                covered[i] = True
            picked.append((name, eid))
            if len(picked) >= max_entities:
                break
        return picked

    def neighbors(self, eid: str) -> list[dict]:
        """(predicate, direction, target_id, target_name) triples for this entity."""
        ent = self.entities.get(eid) or self.concepts.get(eid)
        if ent is None:
            return []
        out = []
        for rel in ent.get("relations", []):
            target = rel["object"]
            out.append({
                "predicate": rel["predicate"],
                "direction": rel["direction"],
                "target_id": target,
                "target_name": self.name(target),
            })
        return out

    def attributes(self, eid: str) -> list[dict]:
        ent = self.entities.get(eid) or self.concepts.get(eid)
        if ent is None:
            return []
        out = []
        for attr in ent.get("attributes", []):
            out.append({"key": attr["key"], "value": attr["value"]})
        return out
