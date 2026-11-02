# 공식 코퍼스 강사용 검수표

대상: `official-2026-10`, 2026-10-02. **AI가 저장된 원문과 대조한 검수 보조 자료이며 사람 검수는 미완료다.**
12개 질문과 기대 사실을 모두 대조했다. 이번 점검에서는 `cases.jsonl`·`gold.jsonl`을 변경하지 않았다.
사람의 확인 뒤 수정할 경우 양쪽 Day에 같은 자료를 반영하고 새 결과를 남긴다. 기존 실행 결과를 덮어쓰지 않는다.

## 좌표를 읽는 방법

아래 경로는 `Day02/data/official-2026-10/` 기준이다. `documents/` 행은 검색 대상의 좌표,
`원문 L`은 `manifest.json`에 기록된 전체 원문의 행이다. Day03의 동일 파일은
`vendor/day02/data/official-2026-10/` 아래에 있다. 발췌 시작 행에 로컬 행 번호 − 1을 더하면 원문 행이 된다.

## 사례별 대조

| 사례 | 기대 사실과 원문 대조 | 원문 위치 | 검수 시 확인할 조건·보완 제안 |
|---|---|---|---|
| `tech-blob` | FilesystemMiddleware의 backend blob 저장 지원이 직접 명시됨 | `documents/deepagents-0.7.21.md:5` · 원문 L9 | 지원 추가만 확인한다. 저장 형식·모든 backend의 세부 구현을 추정하지 않는다. |
| `tech-isolated` | SDK subagent mode의 handoff → isolated 이름 변경이 직접 명시됨 | `documents/deepagents-0.7.13.md:5` · 원문 L78 | “담당자 이전 패턴 전체가 제거됨”은 이 문장으로 뒷받침할 수 없다. 원문의 사실과 과도한 일반화 금지를 구분한다. |
| `tech-future-evidence` | 0.7.21의 공개일 9/30은 질문의 기준일 9/2 이후 | `documents/deepagents-0.7.21.md:1` · 원문 L5 | 해당 코퍼스에서 확정 불가라는 범위다. 세상에 정보가 전혀 없었다는 증명은 아니다. |
| `tech-context` | 0.7.14의 압축 복구 한계·입력 예산 검증, 0.7.18의 잘림 표시 개선 모두 명시됨 | `documents/deepagents-0.7.14.md:9` · 원문 L67; `documents/deepagents-0.7.18.md:5` · 원문 L29 | 잘림을 명확히 알리는 것과 잘림 자체를 방지하는 것을 구분한다. 구체적인 기본 한도 수치는 이 발췌에 없다. |
| `tech-state` | ID 없는 결과 offload의 고유 경로와 제공된 subagent middleware 상태 키 전달이 명시됨 | `documents/deepagents-0.7.15.md:5` 및 `:6` · 원문 L54–55 | 모든 상태가 무조건 공유된다고 확대하지 않는다. 두 수정 중 하나만 답하면 누락이다. |
| `tech-cosine` | 순수 cosine의 변환식·범위, 순위 불변, 수동 임계값 보정, 인덱스 재구축 불필요가 명시됨 | `documents/openviking-cosine.md:1` · 원문 L135 | local native C++/cuVS의 순수 cosine에 한정한다. 원시 0과 −0.6의 변환을 손으로 확인한다. |
| `tech-acl` | ACL 활성화 계정에서 restricted parent의 write만 가진 생성자는 ACL 없이 생성하면 write만 상속함 | `documents/openviking-acl.md:1`, `:6`, `:7` · 원문 L118, L123–124 | **질문 보완 제안:** “ACL 없이 생성한 뒤”를 명시한다. 생성 때 ACL을 전달하면 write만으로는 403이라 생성 성공 자체를 가정할 수 없다. |
| `tech-api` | used API/SDK 제거, 404, 호출 제거 조치, active_count 유지가 직접 명시됨 | `documents/openviking-session-api.md:1` · 원문 L94 | 이 사례의 404 원인은 삭제된 경로다. 모든 404가 버전 변경 때문이라고 일반화하지 않는다. |
| `tech-commit` | 재시도 후 파싱 불가·빈 응답은 failed, 모델이 변경 없음을 확인한 sdk.commit()은 성공 | `documents/openviking-commit-failure.md:1` · 원문 L102 | **기대 사실 보완 제안:** “모델이 변경 없음으로 확인한 경우”를 명시한다. 단순 추출 결과 0개를 성공과 같다고 취급하지 않는다. |
| `tech-parallel` | FileInfo.size의 바이트 단위와 순수 cosine 범위·IP/L2/sparse-fusion 예외가 명시됨 | `documents/deepagents-0.7.18.md:7` · 원문 L31; `documents/openviking-cosine.md:1` · 원문 L135 | 두 문서 모두 필요하다. 두 근거가 나왔다는 사실만으로 병렬 구조의 우수성을 주장하지 않는다. |
| `tech-followup` | IP·L2 점수 불변은 직접 명시됨. 앞선 질문과의 연결은 대화에서 확인 | `documents/openviking-cosine.md:1` · 원문 L135; `cases.jsonl:11` | 09는 마지막 질문 문자열만 검색한다. 여기서 recall=1이어도 실제 대화 기억·담당자 유지 검증은 아니다. |
| `tech-unannounced` | 제공된 고정 자료로 미래 API·벤치마크를 확정할 수 없어 보류 | `cases.jsonl:12`; `manifest.json`의 기준일·문서 집합 | **질문 보완 제안:** “10/20에 공개된다고 가정한 0.8.0…”으로 잘못된 전제를 명시한다. 현재 질문이 실제 발표 일정을 증명하지 않는다. |

`gold.jsonl:1`부터 `:12`까지 모두 `review_status=draft`다. 직접 명시된 내용과
코퍼스의 정보 부족에 따른 보류 판정을 구분했다. 사례별 판단을 사람이 확정하기 전 수치는 잠정치다.

## 사람이 남길 확인 기록

아래 상태를 실제 확인 후에만 바꾼다. AI의 재대조만으로 `reviewed`로 승격하지 않는다.

| 사례 | 담당자 | 검수일 | 승인 / 수정 / 보류 | 원문 대조·수정 이유 |
|---|---|---|---|---|
| tech-blob | | | 미검수 | |
| tech-isolated | | | 미검수 | |
| tech-future-evidence | | | 미검수 | |
| tech-context | | | 미검수 | |
| tech-state | | | 미검수 | |
| tech-cosine | | | 미검수 | |
| tech-acl | | | 미검수 | |
| tech-api | | | 미검수 | |
| tech-commit | | | 미검수 | |
| tech-parallel | | | 미검수 | |
| tech-followup | | | 미검수 | |
| tech-unannounced | | | 미검수 | |

검색 누락 원인은 [오프라인 검색 진단](OCTOBER_RETRIEVAL_AUDIT.md)을 함께 읽는다.
이 표와 gold는 강사용 사후 평가 자료다. Agent의 검색 코퍼스나 프롬프트에 추가하지 않는다.
