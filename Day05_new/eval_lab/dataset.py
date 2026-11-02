"""검수한 시나리오와 초기 상태를 로드하고 비교 조건의 해시를 고정한다."""

import hashlib
import json
from pathlib import Path

from eval_lab.contracts import Scenario

DATA = Path(__file__).resolve().parents[1] / "data"  # Day05_new/data
POLICY_VERSION = "order-policy-v1"


def fingerprint(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _read_cards(path: Path) -> list[Scenario]:
    return [Scenario.model_validate(row) for row in json.loads(path.read_text())]


def load_dataset(
    path: Path = DATA / "scenarios.json", *, split: str = "dev", approved_only: bool = False
) -> list[Scenario]:
    """검수 조건과 가족 단위 분할을 검사한다. 미검수 문항을 조용히 섞지 않는다.

    기본값(approved_only=False)은 엄격하다. 분할 안에 검수 전 카드가 하나라도 있으면 예외를 던진다.
    저자의 P3 측정은 이 기본값을 쓴다.
    approved_only=True는 수업 시연용이다. 검수 전 카드는 건너뛰고 approved 카드만 돌려준다.
    돌려주는 카드는 가족 분할, reviewer/source/review_reason, 정책 버전 검사를 모두 통과한다.
    """
    if split not in {"dev", "holdout"}:
        raise ValueError("split은 dev 또는 holdout입니다.")
    cards = _read_cards(path)
    ids, families = set(), {}
    for card in cards:
        meta = card.metadata
        if meta.scenario_id in ids:
            raise ValueError(f"중복 scenario_id: {meta.scenario_id}")
        ids.add(meta.scenario_id)
        if meta.family_id in families and families[meta.family_id] != meta.split:
            raise ValueError("같은 family_id가 dev와 holdout에 걸쳐 있습니다.")
        families[meta.family_id] = meta.split
    selected = [card for card in cards if card.metadata.split == split]
    if approved_only:
        selected = [card for card in selected if card.metadata.review_status == "approved"]
    if not selected:
        raise ValueError("선택한 분할에 시나리오가 없습니다.")
    for card in selected:
        meta = card.metadata
        if meta.review_status != "approved" or not all(
            text.strip() for text in (meta.reviewer, meta.source, meta.review_reason)
        ):
            raise ValueError(f"검수가 끝나지 않은 시나리오: {meta.scenario_id}")
        if meta.policy_version != POLICY_VERSION:
            raise ValueError("시나리오와 도구 정책 버전이 다릅니다.")
    return selected


def pending_ids(path: Path = DATA / "scenarios.json", *, split: str) -> list[str]:
    """분할 안에서 아직 approved가 아닌 카드의 scenario_id를 정렬해 돌려준다."""
    return sorted(
        card.metadata.scenario_id
        for card in _read_cards(path)
        if card.metadata.split == split and card.metadata.review_status != "approved"
    )


def load_fixtures(path: Path = DATA / "fixtures.json") -> dict:
    """fixture는 환경 구성만 포함한다. 기대 답변·평가 판정은 포함하지 않는다."""
    return json.loads(path.read_text())
