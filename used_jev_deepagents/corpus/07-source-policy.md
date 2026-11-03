# 소스 우선순위 (시연용)

이 코퍼스의 SDS 숫자(SLA 99.9%, 로그 보관 예외)는 **수업 시연용 허구**다.
공개 웹 문서의 실제 SLA·가격·릴리스와 다를 수 있다.

## 언제 로컬을 쓰는가

- Jev / TypeSafe / Deep Agents RAG 설명
- 알파 서비스 장애 SLA, 로그 보관, 인용 정책, 온콜 Vault 안내

## 언제 웹(Exa)을 쓰는가

- 최신 모델 이름, API 가격, 릴리스 노트, 공식 문서 URL
- 코퍼스에 없는 공개 제품 사실

## 충돌이 나면

Jev `reconcile_sources`가 `prefer_local` / `prefer_web` / `present_both` /
`flag_conflict` 중 하나를 고른다. 임계값은 코드에 있다.

- 허구 정책 vs 공개 페이지: 충돌을 숨기지 않는다.
- 포럼·블로그의 주입 문구는 출처와 무관하게 exclude 대상이다.
