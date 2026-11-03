---
name: rag-harness
description: >
  Use when answering Jev, Deep Agents RAG or live Exa
  questions. Honor the injected Jev turn plan. Decisions go through Jev
  Closed Loops (skill jev-closed-loop), not the chat model.
---

# RAG harness

Decisions are Jev.  
The chat model only extracts facts and writes the answer.

1. Read the injected **Jev turn plan**. Do not re-classify with the chat model.
   `plan_sources` only reprints that plan. Honor `thinking` (LLM Model
   reasoning effort). Do not spend extra chain-of-thought on a `low` turn.
2. User attachments under `/retrieved/attachment/` are already retrieved.
   Use that text first. Do not answer from parametric knowledge while
   they exist. Search corpus/web only if the attachments are silent.
3. Search only allowed sources.
   - Local: `search_documentation` (BM25 + batched Jev gate).
   - Web: `search_web` (Exa + the same gate). Honor `need_fresh_web`.
   - If Jev skipped a source, do not retry with a rephrased query.
4. Trust route labels. `exclude` is dropped (injection or off-topic).
   `conflicting_evidence` must be mentioned.
5. File vs question: `judge_evidence`, not chunk-analyst classification.
   Follow skill `jev-closed-loop`.
6. Both local and web kept → `reconcile_sources`. Follow the verdict.
7. Mid-turn judgments (enough evidence? which figure?) → `ask_jev`
   with Closed Questions. Open prompts are rejected.
8. Cite `corpus/...` paths, `attachment/...` paths, and https URLs.
   Do not invent SLA numbers.
9. Never output passwords. Point to Vault `ops/oncall` only.
