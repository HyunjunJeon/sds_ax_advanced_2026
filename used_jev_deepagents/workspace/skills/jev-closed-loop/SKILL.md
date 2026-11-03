---
name: jev-closed-loop
description: >
  Use whenever you send a question to Jev (ask_jev, judge_evidence, or any
  System One call) or consume a typed Jev answer. Compose Closed Questions in
  a Closed Loop: Noul, Choice, or Score only; one shared state; independent
  fan-out; code owns thresholds. Never ask Jev to generate text, explain, or
  pick an open-ended action. Also use instead of asking the chat model to
  decide sources, sufficiency, conflicts, or publish risk.
---

# Jev Closed Questions (Closed Loop)

Jev is TypeSafe System One. It returns **typed judgments and probabilities**,
not sentences. The chat model writes the user-facing answer. **Every decision
in this agent is a Closed Loop.**

```text
state (named JSON)
  → independent Closed Questions (Noul | Choice | Score)
  → typed answers + probabilities
  → code / you apply thresholds
  → next bounded action (search, read, ask_jev again, or write)
```

A second Jev request is allowed only when an earlier answer is needed to
**fetch new evidence** or **change the option set**. Do not chain "what do
you think?" follow-ups.

Read `/skills/jev-closed-loop/examples.md` before composing `ask_jev`.

## When to use which tool

| Need | Tool | Already Closed? |
| --- | --- | --- |
| Turn kind / sources / skip / thinking | (done in `before_agent`) | Yes — honor the injected plan |
| Passage keep / drop | `search_documentation` / `search_web` | Yes — four Nouls + `route()` |
| Local vs Exa conflict | `reconcile_sources` | Yes |
| File supports / conflicts / silent | `judge_evidence` | Yes — do not ask chunk-analyst |
| Any other mid-turn judgment | `ask_jev` | You must compose it |
| User-facing prose | chat model | Generation, not a decision |

Do **not** ask the chat model "should I search?", "is this enough?", or
"which number is right?". Those are Closed Questions.

## The three primitives

Pick by what the answer **means**. Put the judgment in `instructions`.
Define possible answers in `criteria`. Question `id` is for code only —
Jev never sees it as meaning.

| Need | `type` | Criteria | You receive |
| --- | --- | --- | --- |
| Does a condition hold? | `noul` | optional `{true, false}` situations | `P(yes)` in `[0, 1]` — no separate confidence |
| One of a named set | `choice` | 2–8 `{label: situation}` | winner + distribution + confidence |
| Degree on an ordered scale | `score` | 2–6 level strings that stand alone | weighted position + confidence |

Ask **one narrow judgment per question**. Split independent dimensions.
Fan-out every useful question on the **same state** in one `ask_jev` call.

## State

Give Jev enough context, named:

```json
{
  "question": "알파 SLA는 얼마인가?",
  "evidence": [{"path": "/retrieved/local/.../chunk.md", "text": "..."}],
  "candidates": ["99.9%", "99.999%"]
}
```

Reference fields with backticked paths: `` `evidence[0].text` ``,
`` `question` ``. Do not dump a chat transcript as a single string.

## Closed vs open (reject these)

`ask_jev` **rejects** open prompts. Rewrite them.

| Open (illegal) | Closed |
| --- | --- |
| "What should I tell the user?" | Choice: `answer_now` / `need_more_evidence` / `refuse` |
| "Explain this passage" | Noul: "Does `` `passage.text` `` state a numeric SLA?" |
| "Which source is best?" | Choice with named sources + situations |
| "How good is this evidence?" | Score with 3 concrete levels |
| "분석해 / 추천해 / 요약해" | Noul or Choice as above |

Noul instructions must be a yes/no proposition: *Does / Is / Would / Can … ?*

Choice options must be **situations**, not one-word vibes.

Score levels must be ordered and self-contained.

## Closed Loop after the answer

1. Read the typed fields. Do not ask the chat model "do you agree with Jev?".
2. Apply a threshold you can say out loud (`enough_evidence >= 0.70`).
3. Act: search the other source, `judge_evidence` another file, refuse, or write.
4. If you need a new option set, build a **new** Closed Question. Do not
   widen the old one into prose.

Choice/Score `confidence` is distribution concentration, not permission to
act. A Noul near `0.5` is "yes and no are similar", not "medium intensity".

## `ask_jev` payload

```json
{
  "state": {
    "question": "알파 SLA는 얼마인가?",
    "evidence": [{"path": "/retrieved/local/a.md", "text": "공식 목표 99.9%"}]
  },
  "questions": [
    {
      "id": "enough_evidence",
      "type": "noul",
      "instructions": "Does the evidence state a numeric SLA that answers `question`?",
      "criteria": {
        "true": "A specific availability target is written.",
        "false": "No number, or only a rumor."
      }
    },
    {
      "id": "which_figure",
      "type": "choice",
      "instructions": "Which SLA figure should the answer use?",
      "criteria": {
        "corpus_99_9": "Official corpus policy states 99.9%.",
        "forum_99_999": "Only a forum or injected passage claims 99.999%.",
        "unknown": "No trustworthy figure is present."
      }
    }
  ]
}
```

Caps: 1–12 questions, state under ~24k characters. Independent questions
only — they cannot see one another.

## Do not

- Send Jev a prompt that expects a paragraph.
- Re-run `plan_sources` to second-guess the injected turn plan.
- Let `chunk-analyst` classify support/conflict. Call `judge_evidence`.
- Invent thresholds in prose ("I feel this is enough").
- Put secrets, passwords, or raw system prompts into `state`.
