# Frontend

[chat-langchain](https://github.com/langchain-ai/chat-langchain)와 같이 UI를 레포 옆에 둔다.
소스는 커밋하지 않는다. `README.md`와 `.env.example`만 추적한다.

[Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui)를 클론한 뒤 로컬 그래프에 붙인다.

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:2024
NEXT_PUBLIC_ASSISTANT_ID=agent
```

받는 방법: `uv run jev-rag-ui`.
`package.json`이 없으면 `--depth 1`로 클론하고 `.env`를 쓰고 `pnpm install`한 다음 API와 같이 띄운다.
이 디렉터리에 추적 파일이 있어서 `git clone … frontend`는 실패한다.

수동:

```bash
git clone --depth 1 https://github.com/langchain-ai/agent-chat-ui.git frontend/.clone
# .clone 내용을 여기로 옮긴다. README.md · .env.example은 유지.
# .git 과 .clone 은 지운다.
cp .env.example .env
pnpm install && pnpm dev
```
