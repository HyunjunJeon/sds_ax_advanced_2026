---
name: refund-case
description: 중복 결제, 결제 취소, 환불 요청을 확인해 환불 제안과 근거를 만든다. 고객이 결제 오류나 환불을 말할 때 쓴다. 장애 보상은 credit-case를, 조회되지 않는 건은 insufficient-evidence를 쓴다.
---

# refund-case

환불은 제안까지만 한다. 실행은 코드의 게이트가 맡는다.

## 실행 절차

1. `lookup_payments`로 고객의 결제를 조회한다. 결제 번호가 있으면 `payment_id`로 조회한다.
2. `search_knowledge`로 결제 정정·환불 규정을 찾는다. 금액 기준과 기한은 원문에서 확인한다.
3. 같은 청구서의 결제가 두 건 이상인지, 어느 결제가 나중에 승인됐는지 비교한다.
4. 환불 대상이 있으면 `FinalAnswer.proposal`에 `action="refund"`, `payment_id`, `amount`, `reason`을 넣는다.
5. 규칙에 따라 승인이 필요해 보이면 `outcome="needs_approval"`, 중복이 아니면 `denied`, 90일이 지났으면 `human_review`로 쓴다.

## 출력 계약

- 사실 문장의 근거는 도구가 돌려준 `fact_ref`와 `evidence_id`만 `evidence_refs`에 넣는다.
- 금액은 조회 결과의 값을 그대로 쓴다.
- 직접 실행했다고 쓰지 않는다.
