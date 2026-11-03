# Deep Agents RAG: retrieve, offload, delegate

Deep Agents는 RAG를 한 번의 "검색 후 프롬프트에 붙이기"로 끝내지 않는다. 공식 튜토리얼은 **retrieve → offload → delegate → synthesize** 패턴을 권한다.

## 왜 오프로드가 필요한가

문서 코퍼스는 모델 컨텍스트에 다 들어가지 않는다. 들어가더라도 긴 검색 결과를 오케스트레이터 메시지에 그대로 두면 토큰이 빠르게 소모되고, 이후 도구 호출과 섞여 초점이 흐려진다.

그래서 `search_documentation` 도구는 유사도 검색 뒤 청크 전문을 에이전트 파일시스템(`/retrieved/`)에 쓴다. 오케스트레이터에게 돌려주는 것은 **파일 경로**뿐이다.

## 서브에이전트 위임

`chunk-analyst` 같은 서브에이전트는 `task()`로 한 파일씩 읽는다. 각 서브에이전트는 격리된 컨텍스트에서 `read_file`로 청크를 보고, 질문과 관련된 사실만 짧게 돌려준다. 본 에이전트는 요약만 모아 최종 답을 쓴다.

이 분리는 context quarantine이다. 검색 원문이 오케스트레이터를 오염시키지 않는다.

## 다른 RAG 패턴

Deep Agents는 같은 프리미티브로 다른 패턴도 조합한다.

- Skills-guided retrieval: 어떤 인덱스를 어떤 인용 형식으로 쓸지 스킬에 적어 두고 필요할 때만 읽는다.
- Rubric-checked grounding: 답이 근거에 묶여 있는지 채점 서브에이전트가 검사한다.
- Todo-driven investigation: 복잡한 질문을 검색 할 일 목록으로 나눈다.

이 데모는 retrieve-offload-delegate에 Jev 하네스를 얹는다. Jev가 질의 종류와 패시지 품질을 먼저 가르고, Deep Agents가 파일과 서브에이전트로 답을 만든다.
