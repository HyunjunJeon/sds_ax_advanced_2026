"""최신 원문을 바꿔도 같은 실험으로 오인하지 않는지 검증한다. 네트워크 호출 없음."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from day02.corpus import load_corpus
from day02.settings import ROOT


def copy_snapshot(tmp_path):
    folder = tmp_path / "data/official-2026-10"
    shutil.copytree(ROOT / "data/official-2026-10", folder)
    return folder


def test_snapshot_is_verbatim_and_has_no_future_sources():
    corpus = load_corpus(ROOT, "official-2026-10")
    records = corpus.catalog()
    assert len(records) == 9
    assert corpus.provenance()["as_of"] == "2026-10-02"
    assert {r["metadata"]["extraction_method"] for r in records} == {"verbatim-release-excerpt"}


@pytest.mark.parametrize("relative", ["documents/openviking-cosine.md", "sources/deepagents-changelog.md"])
def test_tampered_source_or_excerpt_is_rejected(tmp_path, relative):
    folder = copy_snapshot(tmp_path)
    path = folder / relative
    path.write_text(path.read_text(encoding="utf-8") + "\n변조\n", encoding="utf-8")
    with pytest.raises(ValueError, match="해시"):
        load_corpus(tmp_path, "official-2026-10")


def test_catalog_metadata_changes_require_a_new_snapshot(tmp_path):
    folder = copy_snapshot(tmp_path)
    path = folder / "catalog.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    records[0]["metadata"]["valid_from"] = "2020-01-01"
    path.write_text(json.dumps(records), encoding="utf-8")
    with pytest.raises(ValueError, match="catalog 해시"):
        load_corpus(tmp_path, "official-2026-10")


def test_runtime_snapshot_verification_does_not_read_gold(monkeypatch):
    original = Path.read_bytes

    def guarded(path):
        if path.name == "gold.jsonl":
            raise AssertionError("정답표가 실행 경로에 노출됨")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    corpus = load_corpus(ROOT, "official-2026-10")
    assert corpus.provenance()["documents"]


def test_historical_query_cannot_retrieve_future_release():
    spec = importlib.util.spec_from_file_location("day02_compare_test", ROOT / "09_compare.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    corpus = load_corpus(ROOT, "official-2026-10")
    permitted = module.scope_filter(corpus.catalog(), {"entity": "공통", "as_of": "2026-09-02"})
    assert set(permitted) == {"deepagents-0.7.13"}


def test_corpus_name_cannot_escape_data_directory():
    with pytest.raises(ValueError, match="이름"):
        load_corpus(ROOT, "../official-2026-10")
