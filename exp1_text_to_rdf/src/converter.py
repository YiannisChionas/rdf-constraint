"""Converter call (call 2): answer text -> schema-constrained JSON -> (later) RDF.

The converter never sees the original question, only the answer text.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .llm import OllamaClient

CONVERTER_INSTRUCTIONS_TEMPLATE = """You convert a text into a knowledge graph using ONLY the schema below.

Allowed node types:
{node_types_block}

Allowed relationships (source type, relation, target type):
{relations_block}

Rules:
- Extract ONLY facts that are explicitly stated in the text.
- Do NOT add, correct, or infer facts from your own knowledge, even if the text is wrong.
- If a fact in the text does not fit the schema, ignore it.
- Every relationship must respect the (source type, target type) of its relation.
- Use one node per distinct entity; do not create duplicate nodes.
- If nothing in the text fits the schema, return empty lists.

{few_shot_block}

Text:
{answer}
"""


def load_schema(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_few_shot(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_json_schema(schema: dict) -> dict:
    """JSON schema used as Ollama structured-output `format`.

    Node types and relation names are constrained via enum, directly from
    schema.yaml, so it can be extended without touching this code.
    """
    node_type_names = list(schema["node_types"].keys())
    relation_names = list(schema["relations"].keys())
    return {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string", "enum": node_type_names},
                        "name": {"type": "string"},
                    },
                    "required": ["id", "type", "name"],
                },
            },
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "relation": {"type": "string", "enum": relation_names},
                        "target": {"type": "string"},
                    },
                    "required": ["source", "relation", "target"],
                },
            },
        },
        "required": ["nodes", "relationships"],
    }


def build_prompt(
    schema: dict,
    few_shot_examples: list[dict],
    answer: str,
    num_few_shot: int,
) -> str:
    node_lines = []
    for name, info in schema["node_types"].items():
        examples = ", ".join(info.get("examples", []))
        suffix = f" (e.g. {examples})" if examples else ""
        node_lines.append(f"- {name}: {info['description']}{suffix}")
    node_types_block = "\n".join(node_lines)

    rel_lines = [
        f"- ({info['source']}, {name}, {info['target']})"
        for name, info in schema["relations"].items()
    ]
    relations_block = "\n".join(rel_lines)

    examples_to_use = few_shot_examples[:num_few_shot]
    example_blocks = [
        f'Example {i}\nText: "{ex["text"]}"\nOutput:\n{json.dumps(ex["output"], indent=2)}'
        for i, ex in enumerate(examples_to_use, start=1)
    ]
    few_shot_block = "\n\n".join(example_blocks)

    return CONVERTER_INSTRUCTIONS_TEMPLATE.format(
        node_types_block=node_types_block,
        relations_block=relations_block,
        few_shot_block=few_shot_block,
        answer=answer,
    )


def convert_answer(
    client: OllamaClient,
    model: str,
    schema: dict,
    few_shot_examples: list[dict],
    answer: str,
    num_few_shot: int = 2,
    temperature: float = 0.0,
    think: bool = False,
) -> dict:
    prompt = build_prompt(schema, few_shot_examples, answer, num_few_shot)
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
    try:
        parsed = json.loads(result.content)
    except json.JSONDecodeError as e:
        parse_error = str(e)

    return {
        "prompt": prompt,
        "raw_content": result.content,
        "parsed": parsed,
        "parse_error": parse_error,
        "latency_s": result.latency_s,
    }
