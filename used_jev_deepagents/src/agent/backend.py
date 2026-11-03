"""합성 백엔드: 검색 파일은 상태, 스킬만 디스크.

``/retrieved``는 상태에만 두고, ``/skills``만 workspace에서 읽는다.
"""

from __future__ import annotations

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from src.agent.config import Settings


def build_backend(settings: Settings) -> CompositeBackend:
    """``/retrieved``는 state, ``/skills``는 workspace/skills에서 제공한다."""
    return CompositeBackend(
        # 검색 산출물을 워크스페이스 디스크에 쓰지 않는다.
        default=StateBackend(),
        routes={
            "/skills/": FilesystemBackend(
                root_dir=settings.skills_dir,
                virtual_mode=True,
            )
        },
    )
