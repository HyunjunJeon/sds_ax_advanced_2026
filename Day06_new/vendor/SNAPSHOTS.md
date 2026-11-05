# vendor/ 스냅샷

두 폴더는 아래 커밋을 내려받아 `.git`만 지운 **읽기 전용** 사본이다. 수업에서는 읽기만 하고 실행하지 않는다(`../AGENTS.md` 2장).
파일 목록이 원본 커밋의 `git ls-files`와 같은 것을 2026-11-05에 확인했다. 이 저장소의 `.gitignore`에 걸리는 파일은 없었다.

| 폴더 | 원본 | 커밋 | 커밋 일시 | 라이선스 |
|---|---|---|---|---|
| `mini-coding-agent/` | https://github.com/rasbt/mini-coding-agent | `717cae4ff10d01773bd12951f62a575825053414` | 2026-04-07 | Apache-2.0 (`mini-coding-agent/LICENSE`) |
| `autonomous-coding/` | https://github.com/anthropics/claude-quickstarts 의 `autonomous-coding/` 폴더 | `8ef47d719eba5379ff8f38133f5defcc499e856f` | 2026-11-02 | 저장소 루트 LICENSE(MIT)를 `autonomous-coding/LICENSE`로 함께 복사했다. 아래 주의 참고 |

## 주의

- `autonomous-coding/README.md:163`의 License 절은 "Internal Anthropic use."라고 적는다. 저장소 전체의 라이선스는 MIT다(GitHub API 값과 루트 LICENSE). 두 표기가 다르다. 저자는 2026-11-05에 저장소 라이선스(MIT)를 기준으로 사본을 그대로 두기로 결정했다(`../docs/DESIGN.md` 4절).
- `autonomous-coding/`은 Anthropic Engineering 글 "Effective harnesses for long-running agents"(2025-11-26)가 동반 예제로 링크한 폴더다(`../docs/sources/web.md` 2절 항목 12).
- `mini-coding-agent/`의 모델 백엔드는 Ollama다(`mini-coding-agent/README.md:18`). Sebastian Raschka의 글 "Components of A Coding Agent"(2026-04-04)의 예제 코드다(`../docs/sources/web.md` 7절).

## 다시 받는 방법 (저자 작업)

```bash
git clone --depth 1 https://github.com/rasbt/mini-coding-agent.git && git -C mini-coding-agent checkout 717cae4f
git clone --depth 1 --filter=blob:none --sparse https://github.com/anthropics/claude-quickstarts.git cq
git -C cq sparse-checkout set autonomous-coding   # 그다음 cq/LICENSE를 autonomous-coding/LICENSE로 복사
```

커밋을 바꾸면 Part 2·3 카드와 `../docs/SOURCES.md`의 줄 번호를 다시 확인한다.
