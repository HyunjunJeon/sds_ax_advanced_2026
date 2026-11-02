"""Day05_new/.env의 키 값이 다른 파일에 새어 나가지 않았는지 확인한다. 값은 절대 출력하지 않는다.

사용: uv run --no-sync python Day05_new/tests/check_secrets.py [--env PATH] [--root PATH]
종료 코드: 새는 값이 없으면 0, 있으면 1.
"""
import argparse
import sys
from pathlib import Path

from dotenv import dotenv_values

DAY05_ROOT = Path(__file__).resolve().parents[1]
if str(DAY05_ROOT) not in sys.path:
    sys.path.insert(0, str(DAY05_ROOT))

from eval_lab.settings import (
    KEY_ENV_NAMES,
)

MIN_VALUE_LENGTH = 12  # 이보다 짧은 값은 우연히 일치하기 쉬워 검사에서 뺀다.
SKIPPED_DIRS = {".venv", "__pycache__", ".git"}


def load_secrets(env_path: Path) -> tuple[dict[str, bytes], int]:
    """키 이름 -> 값(bytes)과, 너무 짧아 건너뛴 개수를 돌려준다."""
    raw = dotenv_values(env_path)
    secrets: dict[str, bytes] = {}
    skipped_short = 0
    for name in KEY_ENV_NAMES:
        value = (raw.get(name) or "").strip()
        if not value:
            continue
        if len(value) < MIN_VALUE_LENGTH:
            skipped_short += 1
            continue
        secrets[name] = value.encode("utf-8")
    return secrets, skipped_short


def iter_files(root: Path, env_path: Path):
    """env 파일과 제외 폴더를 뺀 모든 일반 파일을 돌려준다."""
    env_resolved = env_path.resolve()
    for path in sorted(root.rglob("*")):
        if SKIPPED_DIRS.intersection(path.relative_to(root).parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if path.resolve() == env_resolved:
            continue
        yield path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="키 값 유출 검사. 값은 출력하지 않는다.")
    parser.add_argument("--env", type=Path, default=DAY05_ROOT / ".env")
    parser.add_argument("--root", type=Path, default=DAY05_ROOT)
    args = parser.parse_args(argv)

    if not args.env.is_file():
        print("secret scan: .env 없음")
        print("secret scan: files=0 values=0 skipped_short=0 leaks=0")
        return 0

    secrets, skipped_short = load_secrets(args.env)
    files = 0
    leaks: list[tuple[Path, str]] = []
    for path in iter_files(args.root, args.env):
        files += 1
        content = path.read_bytes()
        leaks.extend((path, name) for name, value in secrets.items() if value in content)

    for path, name in leaks:
        print(f"LEAK {path} {name}")
    print(f"secret scan: files={files} values={len(secrets)} skipped_short={skipped_short} leaks={len(leaks)}")
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
