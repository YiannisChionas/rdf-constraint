# Experiment 3: Live-Hetionet-grounded SHACL shapes, generated via Groq

Same pipeline and design as `exp2_shacl_agent/`, with exactly one change: the
shape-generating LLM is **Groq-hosted `openai/gpt-oss-120b`** (via
Groq's free API tier, no billing required) instead of locally-hosted
**qwen3:14b** (via Ollama). Motivation: exp2 found that qwen3:14b, despite
having clear, unambiguous Hetionet evidence, returned empty/incomplete
results on 3/20 questions (q14, q15, q19 - the ones with the largest,
densest evidence blocks), and was not fully deterministic even at
`temperature=0.0`. This experiment tests whether a different, larger hosted
model avoids that specific reliability limitation, everything else held
constant.

(Two earlier backends were tried and abandoned before Groq: Claude via the
Anthropic API requires a separate paid key, not covered by a Claude.ai
subscription; Google's Gemini API free tier returned
`403 PERMISSION_DENIED` - Google restricts the free tier in the EEA/UK/CH,
requiring billing to be enabled even for free-tier usage there. Groq's free
tier has no such regional billing requirement.)

## What's identical to exp2

- Dataset: the same `exp1_text_to_rdf` run (`--exp1-run` argument), same
  `schema.yaml`, same extracted graphs.
- Evidence-gathering: `src/hetionet_client.py` and `src/evidence.py` are
  exact functional copies of exp2's (including the `IN_VOCAB_RELATION_TYPES`
  sampling fix - see exp2's README for that fix's history/rationale).
- Shape design: `src/shape_agent.py`'s prompt, JSON schema
  (`{"supported_relations": [...]}`), and `render_shapes()` are unchanged -
  the LLM makes exactly one judgment call per relation (evidence-supported,
  yes/no); direction is never part of its output and is instead derived
  deterministically from `schema.yaml`'s fixed `source`/`target` per
  relation (see exp2's README, "Design history: why direction was removed
  from the LLM's output", for why).
- `run_experiment.py`'s pipeline structure, validation (pySHACL), and
  `report.md` format - so this experiment's `report.md` is directly
  comparable to exp2's, row for row.

Per this project's convention (see exp2's `llm.py` docstring), code shared
with exp2 is duplicated here rather than imported across experiment folders,
so each experiment stays independently reproducible.

## What's different

- **LLM backend**: `src/llm.py`'s `GroqClient` replaces exp2's
  `OllamaClient`, matching its exact interface
  (`chat(model, messages, temperature, think, format) -> ChatResult`) so
  `shape_agent.py` and `run_experiment.py` needed no logic changes beyond
  swapping which client class is instantiated.
- **Structured output mechanism**: Ollama's native JSON-schema `format`
  parameter is mapped onto Groq's OpenAI-compatible **forced tool-use** -
  a single tool (`emit_result`) is declared with that schema as its
  `parameters`, and `tool_choice` forces Groq to call it, guaranteeing a
  schema-valid JSON object every time (the same pattern originally used for
  the abandoned Claude backend, kept here since Groq's native
  JSON-schema `response_format` support varies by model).
- **`think`**: accepted by `GroqClient.chat()` for interface parity but has
  no effect - `openai/gpt-oss-120b` has no separate "thinking" mode exposed
  via this API, and this project always runs with `think: false` anyway.
- **Model**: `openai/gpt-oss-120b` (`config.yaml`'s `shape_agent.model`) -
  `llama-3.3-70b-versatile`, the model originally picked for this
  experiment, was no longer offered on Groq by the time of the smoke test;
  `openai/gpt-oss-120b` was the largest chat-capable model this API key had
  access to (`client.models.list()`).
- **Cost/latency**: Groq's free tier has no billing requirement, but is
  rate-limited (requests/tokens per minute); a 20-question run makes one
  API call per question.

## Setup

Requires the `GROK_API_KEY` environment variable to be set in your own
shell (never stored in this repo or passed through chat) - get a free key
at https://console.groq.com/keys. Named `GROK_API_KEY` (not the groq SDK's
usual `GROQ_API_KEY` default) because that's what was already set in this
project's environment; `GroqClient` reads it explicitly rather than relying
on SDK auto-detection.

```
pip install -r requirements.txt
python -m src.run_experiment --exp1-run ../exp1_text_to_rdf/runs/<timestamp>
```

Writes `runs/<timestamp>/`, same layout as exp2:
- `evidence/<qid>.json` - raw Hetionet lookup/relations per entity
- `shapes/<qid>.ttl` - the LLM-generated SHACL shapes for that question
- `validation/<qid>.txt` - pySHACL report (only if the shapes parsed)
- `report.md` - summary: shape parse rate, conformance rate, per-question table

## Known limitation: Groq free-tier rate limits

Groq's free tier caps `openai/gpt-oss-120b` at 8000 tokens/minute (TPM),
**per request, not just cumulatively** - a single call whose prompt alone
exceeds 8000 tokens (q06, q15 - both large-evidence questions) gets a
permanent `413 "request too large"` that no retry fixes, regardless of
which model is picked (confirmed by testing `openai/gpt-oss-20b` and
`qwen/qwen3.8-27b` too - same org-wide 8000 TPM limit). `run_experiment.py`
catches this specifically and records the question as skipped (reason:
"prompt too large for Groq free-tier TPM limit"), rather than crashing the
whole run.

Separately, ordinary cumulative throttling (`429`, e.g. "Used 5418,
Requested 2591, try again in 67ms") is transient and *is* retried -
`GroqClient.chat()` retries up to 5 times with a short backoff on `429`
specifically, distinct from the permanent `413` case above.

## Result: comparison against exp2 (qwen3:14b)

`runs/20261028_160138`: **18/20 questions considered** (q06, q15 skipped -
see limitation above). Of those 18: **18/18 parsed, 0/18 vacuous, 15/18
conform**. The 3 non-conforming questions are the exact same genuine
exp1-data bugs exp2 found (q02's Disease-Disease `associatedWith`, q05's
reversed-direction `binds` on a Gene, q07's 13 `binds` Compound->Disease
violations) - zero false positives from the shape agent, same as exp2.

The headline result: **q14 and q19** - 2 of exp2's 3 vacuous questions
(qwen3:14b returned empty `supported_relations` despite clear evidence) -
are **not vacuous here** (`n_shapes: 3, conforms: True` for both), confirming
the experiment's hypothesis that a different, larger hosted model can
correctly use the same dense evidence qwen3:14b failed on. q15, the third
and largest-evidence vacuous case from exp2, could not be re-tested here at
all - it is one of the two questions permanently skipped by Groq's 8000 TPM
limit (see above), so the comparison on that specific question remains
open.

## Scope note

Same scope note as exp2 applies: this is a proof-of-concept measuring
whether an LLM can decide *usable*, evidence-grounded SHACL constraints, not
just whether the resulting validation verdict happens to be correct.
