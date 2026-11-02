# 원본 출처

이 폴더는 아래 저장소의 스냅샷입니다. 원본 업데이트는 자동으로 반영되지 않습니다.

- 원본: https://github.com/braincrew-lab/langgraph-v1-tutorial
- 커밋: `aca51ad2db7e4ff91f25bfea14d3eeb4e13798c7`

원본에서 바꾼 것 (설치를 저장소 루트로 통합하기 위한 변경):

- `pyproject.toml`: 프로젝트 이름, `requires-python`을 3.13으로 변경, `[tool.uv]`의 override를 루트로 이동
- `uv.lock`, `.python-version`: 삭제 (루트 파일을 사용)
- `README.md`: 설치 안내를 저장소 루트 기준으로 변경
