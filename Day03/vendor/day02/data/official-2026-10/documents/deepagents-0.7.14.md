## [0.7.14](https://github.com/langchain-ai/deepagents/compare/deepagents==0.7.13...deepagents==0.7.14) (2026-09-13)

### Features

- Updated `read_file` output formatting. ([#5648](https://github.com/langchain-ai/deepagents/pull/5648))

### Bug Fixes

- Bounded compaction recovery and added validation for input budgets. ([#6267](https://github.com/langchain-ai/deepagents/pull/6267))
- Fixed invalid partial tool-call patching and updated imputed `ToolMessage` content in `PatchToolCallsMiddleware`. ([#5430](https://github.com/langchain-ai/deepagents/pull/5430), [#6277](https://github.com/langchain-ai/deepagents/pull/6277))
- Rejected empty `old_string` values in `edit_file` paths. ([#5747](https://github.com/langchain-ai/deepagents/pull/5747))
- Fixed character counting in `ls` and `glob` output. ([#6204](https://github.com/langchain-ai/deepagents/pull/6204))
- Improved `glob` tool results to suggest populating `path` when appropriate. ([#6199](https://github.com/langchain-ai/deepagents/pull/6199))
- Prevented blank read windows from triggering the empty-file warning. ([#5050](https://github.com/langchain-ai/deepagents/pull/5050))

