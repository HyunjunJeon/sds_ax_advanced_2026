## [0.7.18](https://github.com/langchain-ai/deepagents/compare/deepagents==0.7.17...deepagents==0.7.18) (2026-09-22)

### Bug Fixes

- Large tool result previews now more clearly explain when output was clipped or truncated, including byte-cap losses, per-line clipping, and showing truncation notices only when truncation occurs. Legacy large-result preview templates are preserved behind a deprecation path. ([#5567](https://github.com/langchain-ai/deepagents/pull/5567), [#5564](https://github.com/langchain-ai/deepagents/pull/5564), [#5563](https://github.com/langchain-ai/deepagents/pull/5563), [#5568](https://github.com/langchain-ai/deepagents/pull/5568))
- Task tool calls now reject unknown argument keys instead of silently dropping unexpected input. ([#6299](https://github.com/langchain-ai/deepagents/pull/6299))
- Correct `FileInfo.size` to represent the file size in bytes across backends. ([#6258](https://github.com/langchain-ai/deepagents/pull/6258))

