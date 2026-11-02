from pathlib import Path

import pytest

from common.config import DAY02
from common.contracts import Request
from common.day02_bridge import load_corpus
from common.lab import LabConfig, settings_from
from common.provenance import run_provenance
from common.rag_backend import Backend
from common.runtime import Meter
from common.source_registry import Registry


def test_new_corpus_reuses_real_backend_and_retains_source_coordinates(tmp_path):
    settings = settings_from(LabConfig(corpus="official-2026-10", workspace=str(tmp_path)))
    registry = Registry(tmp_path / "registry.sqlite")
    backend = Backend(settings, registry, Meter(settings))
    try:
        backend.prepare()
        first = registry.snapshot()
        backend.prepare()
        assert first == registry.snapshot()
        assert len(registry.rows("internal")) == 9
        request = Request(question="OpenViking cosine score_threshold", entity="공통",
                          as_of="2026-10-02", thread="test")
        found = backend.retrieve(request.question, request)
        assert "openviking-cosine" in {e.doc_id for e in found}
        for evidence in found:
            record = next(r for r in registry.rows("internal") if r["uri"] == evidence.uri)
            lines = Path(record["path"]).read_text(encoding="utf-8").splitlines(keepends=True)
            assert evidence.quote in "".join(lines[evidence.start_line - 1:evidence.end_line])
    finally:
        backend.close()


def test_workspace_cannot_mix_business_and_official_corpus(tmp_path):
    settings_from(LabConfig(workspace=str(tmp_path)))
    with pytest.raises(ValueError, match="코퍼스"):
        settings_from(LabConfig(corpus="official-2026-10", workspace=str(tmp_path)))


def test_official_provenance_contains_selected_inputs_and_vendor_code():
    provenance = run_provenance("official-2026-10")
    corpus = load_corpus(DAY02, "official-2026-10")
    assert provenance["assets"]["corpus"] == corpus.provenance()
    assert "vendor/day02/src/day02/corpus.py" in provenance["files"]


def test_future_release_is_not_used_for_historical_request(tmp_path):
    settings = settings_from(LabConfig(corpus="official-2026-10", workspace=str(tmp_path)))
    backend = Backend(settings, Registry(tmp_path / "registry.sqlite"), Meter(settings))
    try:
        backend.prepare()
        request = Request(question="DeepAgents FilesystemMiddleware blob", entity="공통",
                          as_of="2026-09-02", thread="historical")
        assert all(e.doc_id == "deepagents-0.7.13" for e in backend.retrieve(request.question, request))
    finally:
        backend.close()
