---
tags: [fault, permission-denied]
max_turns: 8
allowed_tools: [Skill, "mcp__plugin_example-tasks_tasks__*"]
env:
  EVAL_CAPABILITY_FAULT: '{"permission_denied": ["add_task"]}'
---
할 일 "세금 계산서 정리하기"를 추가해 줘.
