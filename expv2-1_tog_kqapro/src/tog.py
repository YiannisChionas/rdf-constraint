"""Simplified Think-on-Graph loop over KQA Pro's local kb.json.

Not the literal ToG repo code (that expects a live Freebase/Wikidata
backend) — same method (prune relations -> score entities -> check if
evidence suffices -> answer), reimplemented against our local KB lookup
(src/kb.py). Relation names in kb.json are already plain English, so no
Freebase/Wikidata-style relation-name translation is needed.
"""
from __future__ import annotations

import re

from .kb import KB
from .llm import OllamaClient

PRUNE_PROMPT = """Question: {question}

You are exploring a knowledge graph starting from the entity "{entity}".
Below are relations connected to this entity. Pick the {k} relations most
likely to help answer the question. Reply with ONLY a comma-separated list
of the exact relation strings you picked, nothing else.

Relations:
{relations}
"""

SUFFICIENCY_PROMPT = """Question: {question}

Known facts (knowledge triplets) gathered so far:
{triplets}

Is this enough information to answer the question? Reply with ONLY "Yes"
or "No".
"""

ANSWER_PROMPT = """Question: {question}

Known facts (knowledge triplets):
{triplets}

Known attributes:
{attributes}

Using the facts above (and your own knowledge only to fill small gaps),
answer the question. End your response with the final answer on its own
line, in this exact format:
ANSWER: <answer>
The <answer> must be ONLY the bare answer itself (a name, number, date,
or yes/no) — do not restate the question or add any other words.
Example: if the question is "Which city is bigger?" and the answer is
Paris, write exactly "ANSWER: Paris", not "ANSWER: Paris is bigger".
"""

_ANSWER_RE = re.compile(r"ANSWER:\s*(.+)", re.IGNORECASE)


def _extract_answer(raw_content: str) -> str:
    matches = _ANSWER_RE.findall(raw_content)
    if matches:
        return matches[-1].strip().strip(".")
    return raw_content.strip().splitlines()[-1].strip() if raw_content.strip() else ""


def _fmt_triplets(triplets: list[tuple[str, str, str]]) -> str:
    if not triplets:
        return "(none)"
    return "\n".join(f"- {s} -> {p} -> {o}" for s, p, o in triplets)


def _fmt_attributes(attrs: list[tuple[str, str, object]]) -> str:
    if not attrs:
        return "(none)"
    return "\n".join(f"- {e}.{k} = {v}" for e, k, v in attrs)


def answer_with_tog(
    client: OllamaClient,
    model: str,
    kb: KB,
    question: str,
    max_hops: int = 2,
    k: int = 3,
) -> dict:
    calls = 0
    topic_entities = kb.find_topic_entities(question)
    if not topic_entities:
        # No linkable entity — fall back to answering with no KG evidence,
        # same prompt shape as the baseline, flagged in the result.
        result = client.chat(
            model=model,
            messages=[{"role": "user", "content": ANSWER_PROMPT.format(
                question=question, triplets="(none)", attributes="(none)")}],
            temperature=0.0, think=False,
        )
        calls += 1
        return {"answer": _extract_answer(result.content), "raw_content": result.content,
                "no_topic_entity": True, "llm_calls": calls, "triplets": [], "attributes": [],
                "trace": [], "topic_entities": []}

    frontier = [eid for _, eid in topic_entities]
    triplets: list[tuple[str, str, str]] = []
    attributes: list[tuple[str, str, object]] = []
    seen_entities = set(frontier)
    trace: list[dict] = []

    for e_name, eid in topic_entities:
        for a in kb.attributes(eid):
            attributes.append((e_name, a["key"], a["value"].get("value")))

    for hop in range(max_hops):
        next_frontier = []
        hop_pruned: dict[str, list[str]] = {}
        hop_new_triplets: list[tuple[str, str, str]] = []
        for eid in frontier:
            e_name = kb.name(eid)
            neighbors = kb.neighbors(eid)
            if not neighbors:
                continue
            distinct_rels = sorted({n["predicate"] for n in neighbors})
            if len(distinct_rels) > k:
                rel_list = "\n".join(f"- {r}" for r in distinct_rels)
                result = client.chat(
                    model=model,
                    messages=[{"role": "user", "content": PRUNE_PROMPT.format(
                        question=question, entity=e_name, k=k, relations=rel_list)}],
                    temperature=0.0, think=False,
                )
                calls += 1
                picked_rels = {r.strip() for r in result.content.split(",") if r.strip() in distinct_rels}
                if not picked_rels:
                    picked_rels = set(distinct_rels[:k])
            else:
                picked_rels = set(distinct_rels)
            hop_pruned[e_name] = sorted(picked_rels)

            for n in neighbors:
                if n["predicate"] not in picked_rels:
                    continue
                subj, obj = (e_name, n["target_name"]) if n["direction"] == "forward" else (n["target_name"], e_name)
                triplets.append((subj, n["predicate"], obj))
                hop_new_triplets.append((subj, n["predicate"], obj))
                if n["target_id"] not in seen_entities:
                    next_frontier.append(n["target_id"])
                    seen_entities.add(n["target_id"])

        if len(triplets) > 40:
            triplets = triplets[:40]

        result = client.chat(
            model=model,
            messages=[{"role": "user", "content": SUFFICIENCY_PROMPT.format(
                question=question, triplets=_fmt_triplets(triplets))}],
            temperature=0.0, think=False,
        )
        calls += 1
        sufficient = result.content.strip().lower().startswith("yes")
        trace.append({
            "hop": hop,
            "frontier_entities": [kb.name(eid) for eid in frontier],
            "pruned_relations": hop_pruned,
            "new_triplets": hop_new_triplets,
            "sufficiency_check": "Yes" if sufficient else "No",
        })
        if sufficient or hop == max_hops - 1 or not next_frontier:
            break
        frontier = next_frontier

    result = client.chat(
        model=model,
        messages=[{"role": "user", "content": ANSWER_PROMPT.format(
            question=question, triplets=_fmt_triplets(triplets), attributes=_fmt_attributes(attributes))}],
        temperature=0.0, think=False,
    )
    calls += 1
    return {
        "answer": _extract_answer(result.content),
        "raw_content": result.content,
        "no_topic_entity": False,
        "llm_calls": calls,
        "triplets": triplets,
        "attributes": attributes,
        "trace": trace,
        "topic_entities": [name for name, _ in topic_entities],
    }
