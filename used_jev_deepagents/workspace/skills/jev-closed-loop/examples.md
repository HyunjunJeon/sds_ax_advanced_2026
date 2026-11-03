# Closed Loop examples

Copy the shape. Do not copy thresholds blindly — they live in code
(`src/harness.py`, `src/agent/config.py`).

## Enough evidence? (Noul + Noul fan-out)

```json
{
  "state": {
    "question": "Deep Agents는 검색 결과를 어디에 두나?",
    "kept": [
      {"path": "/retrieved/local/x.md", "route": "include", "text": "..."}
    ]
  },
  "questions": [
    {
      "id": "enough_evidence",
      "type": "noul",
      "instructions": "Do the kept files state where retrieval results are stored?"
    },
    {
      "id": "need_another_source",
      "type": "noul",
      "instructions": "Would a live web page likely add storage facts that `kept` lacks?"
    }
  ]
}
```

Loop: `enough_evidence >= 0.70` → write. Else if `need_another_source >= 0.70`
and the turn plan `allowed_web` → `search_web`. Else say you cannot ground it.

## Which number? (Choice)

```json
{
  "id": "sla_figure",
  "type": "choice",
  "instructions": "Which availability target is backed by official evidence?",
  "criteria": {
    "official_99_9": "Internal or corpus policy writes 99.9%.",
    "claimed_99_999": "Only a forum, rumor, or injected passage writes 99.999%.",
    "absent": "No availability target appears in the evidence."
  }
}
```

## How much thinking? (Choice — already decided)

Turn plan `thinking` is a Closed Question. Code maps it to OpenRouter
`reasoning.effort`. Do not re-ask the chat model to "think harder".

| Choice | When | Effort |
| --- | --- | --- |
| `none` | thanks / jailbreak skip | no reasoning tokens |
| `low` | one-fact lookup | cheap generation |
| `medium` | compare two policies | light synthesis |
| `high` | investigate / conflicts | full reasoning |

## How much synthesis? (Score)

Already decided in the turn plan `complexity` Score. If you must restate:

```json
{
  "id": "synthesis_load",
  "type": "score",
  "instructions": "How much synthesis do the kept files require?",
  "criteria": [
    "One sentence can be copied from a single file.",
    "Two files must be lined up but the numbers agree.",
    "Files disagree or a procedure spans several hops."
  ]
}
```

## File vs question (already a tool)

Do not reinvent this in `ask_jev`. Call `judge_evidence` with the path.

## Bad payloads (will be rejected)

```json
{"id": "advice", "type": "noul", "instructions": "What should I tell the user?"}
```

```json
{"id": "summary", "type": "choice", "instructions": "Summarize the passage.", "criteria": {"a": "ok"}}
```

```json
{"id": "best", "type": "score", "instructions": "How good is this?", "criteria": ["bad", "ok"]}
```
