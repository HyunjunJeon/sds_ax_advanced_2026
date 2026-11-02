---
name: credit-case
description: 장애 보상, 서비스 크레딧 금액, 신청 기한을 계산하고 답한다. 고객이 장애 보상이나 크레딧을 물을 때 쓴다. 결제 환불은 refund-case를 쓰며, 둘 다 물으면 두 Skill을 모두 읽는다.
---

# credit-case

크레딧은 가용률, 계약 구간, 기본 이용료 세 가지로 정해진다.

## 실행 절차

1. `lookup_availability`로 해당 월 가용률을 조회한다.
2. `search_knowledge`로 그 고객의 SLA와 개별 추가 약정을 찾는다. 추가 약정이 있으면 그 조항이 우선한다.
3. `lookup_payments`에서 해당 월 청구서의 `base_fee_part`를 읽는다. 사용량 초과 요금과 세금은 계산 기준에 넣지 않는다.
4. 구간표에서 비율을 고르고 `calculate_credit(base_fee, credit_percent)`로 계산한다. 암산하지 않는다.
5. 신청 기한은 추가 약정을 먼저 확인해 달력 날짜로 쓴다.

## 출력 계약

- 비율은 `evidence_id`로, 가용률과 이용료는 `fact_ref`로, 금액은 계산 도구의 `fact_ref`로 인용한다.
- 환불과 크레딧은 별개로 쓴다.
