"""저장소 루트에서 pytest를 실행해도 노트북과 똑같이 `import rag_lab`이 되게 한다."""
import json
import sys
from pathlib import Path

import pytest

DAY02_NEW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DAY02_NEW))

GROUNDED_SPEC = {"sections": [{"heading": "결론", "style": "paragraph"}, {"heading": "설명", "style": "paragraph"}],
                 "missing_heading": "추가 확인이 필요한 사항", "conflicts_heading": "상충하는 근거", "sources_heading": "근거"}
INSUFFICIENT_SPEC = {**GROUNDED_SPEC, "sections": [{"heading": "확인된 사실", "style": "paragraph"}]}


def write_skill(root: Path, name: str, spec: dict, body_lines: int = 3) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    body = "\n".join(f"절차 {i}" for i in range(body_lines))
    (folder / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name}의 답변 절차를 안내한다.\n---\n\n# {name}\n\n{body}\n", encoding="utf-8")
    (folder / "output.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return folder


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    """Day02_new/skills에 의존하지 않는 시험용 Skill 폴더. SKILL.md 본문은 기본 limit 100을 넘긴다."""
    root = tmp_path / "skills"
    write_skill(root, "grounded-qa", GROUNDED_SPEC, body_lines=150)
    write_skill(root, "insufficient-evidence", INSUFFICIENT_SPEC)
    return root
