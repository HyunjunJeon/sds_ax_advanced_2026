---
name: insufficient-evidence
description: 조회되지 않는 결제, 근거를 찾지 못한 규정, 현재 고객 범위 밖의 질문에 찾은 것과 못 찾은 것을 나눠 답한다. 도구 결과로 답을 뒷받침할 수 없을 때 쓴다.
---

# insufficient-evidence

모른다고 말하는 것도 정상 결과다.

## 실행 절차

1. 무엇을 어떤 도구로 찾았는지 정리한다.
2. 찾지 못한 항목을 `uncertainty`에 쓴다. 일반 지식으로 채우지 않는다.
3. 다른 고객의 계약을 묻는 질문이면 `outcome="out_of_scope"`, 근거가 없으면 `outcome="insufficient"`로 쓴다.
4. `proposal`을 만들지 않는다.
