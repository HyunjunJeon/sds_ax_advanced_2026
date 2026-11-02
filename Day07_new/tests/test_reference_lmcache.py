"""저장된 LMCache 게이팅·저장 실행(data/reference_lmcache.json)을 읽어 형태와 part8 지원 표를 대조한다.

실제 클래스는 여기서 돌리지 않는다. 그래서 이 테스트에는 lmcache도 vllm도 필요 없다. 실행 방법과 범위는
docs/reference/lmcache.md에 있다. xfail은 쓰지 않는다. status가 not_run일 때만 건너뛴다.
"""
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "reference_lmcache.json"
PART8 = ROOT / "docs" / "sources" / "part8.md"
DOC = ROOT / "docs" / "reference" / "lmcache.md"

MODELS = {"GLM-5.3-Flash", "GLM-5.2", "DeepSeek-V4-Flash", "DeepSeek-V4.1-Flash", "Kimi-K3"}
CONNECTORS = {"LMCacheConnectorV1", "LMCacheMPConnector", "OffloadingConnector"}
FLAG_DEFAULT = "default"
FLAG_OFF = "--disable-hybrid-kv-cache-manager"
FLAG_ON = "--no-disable-hybrid-kv-cache-manager"
FLAGS = {FLAG_DEFAULT, FLAG_OFF, FLAG_ON}
COLUMN_CONNECTOR = {"LMCacheConnectorV1": "LMCacheConnectorV1", "LMCacheMPConnector": "LMCacheMPConnector",
                    "내장 offloading": "OffloadingConnector"}
LABELS = {"문서 검증", "코드 읽기", "코드가 막음", "미확인", "실제 클래스 호출"}

FACTORY_RAISE = "vllm/distributed/kv_transfer/kv_connector/factory.py:57"
PROMOTE_VALUE_RAISE = "vllm/v1/core/kv_cache_utils.py:1760"
PROMOTE_TYPE_RAISE = "vllm/v1/kv_cache_interface.py:138"
PROMOTE_CALLER = "vllm/v1/core/kv_cache_utils.py:1746"
# part8가 적은 줄 범위. 실행에서 올라온 줄이 이 안에 있어야 "코드가 막음" 칸의 인용이 맞다.
CITED_RANGES = {"factory.py": (56, 60), "kv_cache_utils.py": (1756, 1760)}

# part8 칸과 실행 결과가 어긋난 곳. 2026-11-02에 세 칸을 고쳐 지금은 비어 있다. 새로 어긋나면 실패하므로
# 남기려면 여기 적어야 한다. 고쳐서 목록에서 빠진 칸은 test_fixed_cells_cite_what_ran이 내용을 확인한다.
PART8_DIFFERS: set[tuple[str, str, str]] = set()


def _load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _doc() -> dict:
    doc = _load()
    if doc["status"] == "not_run":
        pytest.skip(f"reference_lmcache.json이 not_run입니다: {doc.get('reason')}")
    return doc


def _gate_rows(doc: dict, env: str = "lmrun_external") -> list[dict]:
    return doc["parts"]["gating"]["rows"][env]


def _gate(doc: dict, model: str, connector: str, flag: str, env: str = "lmrun_external") -> dict:
    matches = [row for row in _gate_rows(doc, env)
               if (row["model"], row["connector"], row["flag"]) == (model, connector, flag)]
    assert len(matches) == 1, (model, connector, flag, env)
    return matches[0]


def _case(doc: dict, name: str) -> dict:
    matches = [row for row in doc["parts"]["connector_construct"]["rows"] if row["case"] == name]
    assert len(matches) == 1, name
    return matches[0]


def _part8_cells() -> dict[tuple[str, str], str]:
    """모델별 지원 상태 표를 (모델, 열 이름) -> 칸 글자로 읽는다."""
    section = PART8.read_text(encoding="utf-8").split("## 모델별 지원 상태", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")]
    header = [cell.strip() for cell in rows[0].strip("|").split(" | ")]
    cells = {}
    for line in rows[2:]:
        parts = [cell.strip() for cell in line.strip().strip("|").split(" | ")]
        assert len(parts) == len(header), line[:80]
        for column, text in zip(header[1:], parts[1:]):
            cells[(parts[0].split(" ")[0], column)] = text
    return cells


def _labels(cell_text: str) -> set[str]:
    """칸 첫 콜론 앞의 표지만 읽는다. 뒤쪽 설명에 나오는 `코드가 막음` 같은 말은 칸의 상태가 아니다."""
    return set(re.findall(r"`([^`]+)`", cell_text.split(":", 1)[0])) & LABELS


def _raised(row: dict) -> str | None:
    return (row.get("exception") or {}).get("raised_at")


def _part8_differences(doc: dict) -> set[tuple[str, str, str]]:
    cells = _part8_cells()
    found = set()
    for cell in doc["cells"]:
        text = cells[(cell["model"], cell["column"])]
        labels = _labels(text)
        connector = COLUMN_CONNECTOR[cell["column"]]
        default_row = _gate(doc, cell["run_model"], connector, FLAG_DEFAULT)
        if "미확인" in labels and cell["result"] == "constructed":
            found.add((cell["model"], cell["column"], "미확인인데 생성됨"))
        if "미확인" in labels and default_row["outcome"] == "refused":
            found.add((cell["model"], cell["column"], "미확인인데 거부됨"))
        if ("코드가 막음" in labels and default_row["outcome"] == "refused"
                and _raised(default_row) == PROMOTE_TYPE_RAISE and "kv_cache_utils.py:1756-1760" in text):
            found.add((cell["model"], cell["column"], "인용 줄이 먼저 난 예외와 다름"))
    return found


def test_file_has_true_status():
    doc = _load()
    assert doc["status"] in ("ran", "partial", "not_run")
    assert doc["limit"] and doc["run"]["provenance"]
    if doc["status"] != "ran":
        assert doc["reason"]
    assert doc["versions"]["vllm"] == "v0.32.0" and doc["versions"]["vllm_commit"] == "5df63a7"
    assert doc["versions"]["lmcache"] == "v0.5.6"
    for name in ("install", "gating", "connector_construct", "block_size", "storage"):
        assert doc["parts"][name]["status"] in ("ran", "partial", "not_run"), name


def test_record_holds_no_machine_path_or_secret_shape():
    text = DATA.read_text(encoding="utf-8")
    for needle in ("/Users/", "/private/tmp", "claude-501", "sk-", "API_KEY"):
        assert needle not in text, needle


def test_install_records_the_pypi_block_and_the_build():
    attempts = _doc()["parts"]["install"]["attempts"]
    assert [a["status"] for a in attempts] == ["not_run", "ran"]
    assert "cupy-cuda13x" in attempts[0]["error_line"] and "no wheels" in attempts[0]["error_line"]
    assert attempts[1]["lmcache"] == "0.5.6" and attempts[1]["cupy_installed"] is False


def test_gating_covers_every_model_connector_flag():
    doc = _doc()
    rows = _gate_rows(doc)
    assert {(r["model"], r["connector"], r["flag"]) for r in rows} == {
        (m, c, f) for m in MODELS for c in CONNECTORS for f in FLAGS}
    assert len(rows) == len(MODELS) * len(CONNECTORS) * len(FLAGS)
    assert all(r["outcome"] in ("refused", "gate_passed") for r in rows)
    assert all(_raised(r) for r in rows if r["outcome"] == "refused")


def test_declarations_match_p8_13():
    declared = _doc()["parts"]["gating"]["declarations"]
    external = declared["lmrun_external"]
    assert external["LMCacheConnectorV1"]["supports_hma"] is False
    assert external["LMCacheMPConnector"]["supports_hma"] is True
    assert external["LMCacheMPConnector"]["class"] == "lmcache.integration.vllm.lmcache_mp_connector.LMCacheMPConnector"
    assert external["OffloadingConnector"]["supports_hma"] is True
    assert declared["lmrun_upstream_LMCacheMPConnector"]["supports_hma"] is False
    assert declared["lmrun_upstream_LMCacheMPConnector"]["class"].endswith("LMCacheMPConnectorUpstream")
    for name in ("SimpleCPUOffloadConnector", "NixlConnector", "MooncakeConnector", "MooncakeStoreConnector",
                 "HiSparseConnector", "MultiConnector"):
        assert external[name]["supports_hma"] is True, name
    for name in ("FlexKVConnectorV1", "HF3FSKVConnector"):
        assert external[name]["supports_hma"] is False, name


def test_mp_name_resolves_three_ways_p8_05():
    doc = _doc()
    gating = doc["parts"]["gating"]
    assert gating["refrun_differs_from_lmrun_only_for"] == ["LMCacheMPConnector"]
    assert "lmcache" in gating["declarations"]["refrun_LMCacheMPConnector"]["import_error"]
    missing = _gate(doc, "GLM-5.2", "LMCacheMPConnector", FLAG_ON, "refrun_LMCacheMPConnector")
    assert missing["exception"]["type"] == "ModuleNotFoundError"
    assert _raised(missing) == "vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py:11"
    fallback = gating["declarations"]["fallback_when_submodule_missing"]
    assert fallback["class"].endswith("LMCacheMPConnectorUpstream") and fallback["supports_hma"] is False


@pytest.mark.parametrize("env,connector,expected_default", [
    ("lmrun_external", "LMCacheConnectorV1", True),
    ("lmrun_external", "LMCacheMPConnector", False),
    ("lmrun_external", "OffloadingConnector", False),
    ("lmrun_upstream", "LMCacheMPConnector", True),
])
def test_three_flag_rule_p8_14(env, connector, expected_default):
    doc = _doc()
    for model in MODELS:
        assert _gate(doc, model, connector, FLAG_DEFAULT, env)["hma_disabled"] is expected_default, model
        assert _gate(doc, model, connector, FLAG_OFF, env)["hma_disabled"] is True, model
        explicit = _gate(doc, model, connector, FLAG_ON, env)
        assert explicit["hma_disabled"] is False, model
        if expected_default:  # HMA를 지원하지 않는 connector에 명시적으로 켜면 factory에서 멈춘다.
            assert explicit["stage"] == "create_connector" and _raised(explicit) == FACTORY_RAISE, model
            assert "does not support HMA but HMA is enabled" in explicit["exception"]["message"], model
        else:
            assert explicit["outcome"] == "gate_passed", model


@pytest.mark.parametrize("model", ["GLM-5.3-Flash", "Kimi-K3"])
def test_mamba_mix_stops_at_the_cited_value_error(model):
    doc = _doc()
    for connector in ("LMCacheConnectorV1", "LMCacheMPConnector", "OffloadingConnector"):
        row = _gate(doc, model, connector, FLAG_OFF)
        assert row["exception"]["type"] == "ValueError" and _raised(row) == PROMOTE_VALUE_RAISE, connector
        assert "Failed to promote" in row["exception"]["message"]


@pytest.mark.parametrize("model", ["DeepSeek-V4-Flash", "DeepSeek-V4.1-Flash"])
def test_sliding_window_mla_stops_earlier_with_type_error(model):
    doc = _doc()
    for connector in ("LMCacheConnectorV1", "LMCacheMPConnector", "OffloadingConnector"):
        row = _gate(doc, model, connector, FLAG_OFF)
        assert row["exception"]["type"] == "TypeError" and _raised(row) == PROMOTE_TYPE_RAISE, connector
        assert "bounded_replay" in row["exception"]["message"]
    # connector 없이 플래그만 줘도 같다. 즉 connector 탓이 아니다.
    alone = next(r for r in doc["parts"]["gating"]["no_connector"] if r["model"] == model)
    assert alone["exception"]["type"] == "TypeError"


def test_promotion_probes_separate_the_two_causes():
    probes = {p["case"]: p for p in _doc()["parts"]["gating"]["promotion_probes"]}
    for replay in ("False", "True"):
        row = probes[f"MLA + SlidingWindowMLA (bounded_replay {replay})"]
        assert row["exception"]["type"] == "TypeError"
        assert row["call_chain"] == [PROMOTE_CALLER, PROMOTE_TYPE_RAISE]
    assert probes["MLA + CircularBuffer (no sliding window)"]["exception"]["raised_at"] == PROMOTE_VALUE_RAISE
    assert probes["Full + SlidingWindow (non-MLA promotion)"]["outcome"] == "ok"


def test_constructor_refusals_match_the_ledger():
    doc = _doc()
    expected = {
        "GLM-5.3-Flash + --no-enable-prefix-caching (Mamba none)": "lmcache/integration/vllm/kv_cache_group_edits.py:168",
        "GLM-5.3-Flash + max_num_batched_tokens < N": "lmcache/integration/vllm/lmcache_mp_connector.py:421",
        "GLM-5.2 + lazy_offload + --no-enable-prefix-caching": "lmcache/integration/vllm/lmcache_mp_connector.py:722",
        "GLM-5.3-Flash + chunk 256 (default)": "lmcache/integration/vllm/vllm_multi_process_adapter.py:780",
        "reformat_block_ids with 2 groups": "vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py:78",
    }
    for name, raised in expected.items():
        row = _case(doc, name)
        assert row["outcome"] == "refused" and row["raised_at"] == raised, name
    assert _case(doc, "no server listening")["exception"]["type"] == "ConnectionError"


def test_constructors_that_ran_report_group_geometry():
    doc = _doc()
    glm = _case(doc, "GLM-5.3-Flash BLHNC + chunk = scheduler block + --separate-object-groups")
    assert glm["outcome"] == "constructed"
    assert glm["group_tokens_per_block"][-1] == 0, "scratch tail group은 저장하지 않는다 (P8-18)"
    assert glm["scheduler_block_size"] == max(glm["group_tokens_per_block"])
    assert glm["report_request_errors"] is True, "group이 둘 이상이면 요청 단위 보고 (P8-34)"
    assert _case(doc, "GLM-5.2 LBHNC + chunk = scheduler block + --separate-object-groups")["report_request_errors"] is False
    # P8-19의 셋째 조건: 플래그 없이도 생성자는 지나간다.
    assert _case(doc, "GLM-5.3-Flash BLHNC + chunk = scheduler block, no --separate-object-groups")["outcome"] == "constructed"
    v41 = _case(doc, "DeepSeek-V4.1-Flash BLHNC + chunk = scheduler block + --separate-object-groups")
    assert sorted(set(v41["group_tokens_per_block"])) == [0, 64], "bounded replay면 SWA는 scratch (P8-32)"
    v4 = _case(doc, "DeepSeek-V4-Flash BLHNC + chunk = scheduler block + --separate-object-groups")
    # 폭의 집합은 P8-21이 옮긴 코드 주석의 256/64/8/4와 같다. scheduler block은 그 최소공배수다.
    assert v4["scheduler_block_size"] == 256 and set(v4["group_tokens_per_block"]) == {4, 8, 64, 256}


def test_offloading_shortcut_p8_03_p8_06():
    doc = _doc()
    native = _case(doc, "--kv-offloading-size 2")
    assert native["kv_connector"] == "OffloadingConnector" and native["kv_role"] == "kv_both"
    assert native["extra"] == {"cpu_bytes_to_use": 2 * 1024 ** 3}
    lmcache = _case(doc, "--kv-offloading-size 2 --kv-offloading-backend lmcache")
    assert lmcache["kv_connector"] == "LMCacheMPConnector" and lmcache["extra"] == {}, "크기를 connector에 넘기지 않는다"
    assert _case(doc, "--kv-offloading-backend lmcache only")["kv_connector"] is None


def test_scratch_group_is_left_out_of_offloading():
    doc = _doc()
    glm = _case(doc, "OffloadingConnector SCHEDULER on GLM-5.3-Flash LBHNC")
    assert glm["outcome"] == "constructed"
    expected = [i for i, keep in enumerate(glm["prefix_cacheable"]) if keep]
    assert glm["offloading_group_ids"] == expected and len(expected) == glm["num_groups"] - 1


def test_native_adapter_does_not_load_with_this_lmcache():
    row = _case(_doc(), "LMCacheConnectorV1 SCHEDULER on GLM-5.2, use_native")
    assert row["exception"]["type"] == "ImportError" and "CudaIPCWrapper" in row["exception"]["message"]


def test_block_size_is_marked_as_not_the_gpu_value():
    block = _doc()["parts"]["block_size"]
    assert block["gpu_value"] is False and block["status"] == "partial"
    ran = [r for r in block["rows"] if r["status"] == "ran"]
    assert ran and all(r["backend"] == "FLASH_ATTN" for r in ran), "대역 backend만 돌았다"
    assert all("flashinfer" in r["error"] for r in block["rows"] if r["backend"] == "FLASHINFER_MLA")
    assert all(r["block_size"] % 128 == 0 for r in ran)


def test_layout_resolution_states_its_assumption():
    resolution = _doc()["parts"]["gating"]["layout_resolution"]
    assert "가정" in resolution["assumption"]


def test_storage_roundtrip_chunking_and_eviction():
    storage = _doc()["parts"]["storage"]
    assert storage["model_claim"] is None
    round_trip = storage["rows"]["roundtrip"]
    assert round_trip["outcome"] == "ran" and round_trip["hit_before_store"] == 0
    assert round_trip["stored_chunks"] == round_trip["hit_after_store"] == 3
    assert round_trip["trailing_partial_tokens_not_stored"] > 0, "온전한 chunk만 저장한다"
    assert [r["value"] for r in round_trip["retrieved"]] == [1.0, 17.0, 33.0], "저장한 값이 그대로 돌아와야 한다"
    assert round_trip["hit_other_salt"] == 0
    assert round_trip["hit_diverging_prefix"] == 1

    evict = storage["rows"]["eviction"]
    assert evict["outcome"] == "ran"
    assert evict["hit_first_before_pressure"] == 1 and evict["hit_first_after_pressure"] == 0
    assert evict["hit_last_after_pressure"] == 1
    assert evict["committed_chunks"] == evict["attempted_chunks"]
    # 축출은 초 단위 제어기라 살아남는 개수는 실행마다 다르다. 개수가 아니라 모양을 본다: 가장 최근 것들만 남는다.
    pattern = evict["presence_by_write_order"]
    survivors = sum(pattern)
    assert 0 < survivors < evict["attempted_chunks"] and survivors == evict["surviving_of_attempted"]
    assert pattern == [0] * (len(pattern) - survivors) + [1] * survivors, "LRU면 오래된 것부터 빠진다"
    assert evict["l1_after"]["memory_used_bytes"] <= evict["l1_after"]["memory_total_bytes"]

    assert storage["separate_object_groups_split_exercised"] is False
    assert storage["rows"]["separate_object_groups"]["outcome"] == "ran"
    assert storage["rows"]["chunk_size_zero"]["server_ready"] is True, "관찰 그대로 적는다. 거부되지 않았다"


def test_every_support_cell_is_answered():
    doc = _doc()
    cells = _part8_cells()
    assert {(c["model"], c["column"]) for c in doc["cells"]} == {
        (model, column) for model, column in cells if column in COLUMN_CONNECTOR}
    cases = {row["case"] for row in doc["parts"]["connector_construct"]["rows"]}
    for cell in doc["cells"]:
        assert cell["result"] in ("constructed", "refused", "gate_passed", "layout_contingent"), cell["model"]
        assert set(cell["proposed_labels"]) <= LABELS and cell["proposed_labels"], cell["model"]
        assert set(cell["evidence_cases"]) <= cases, cell["model"]
        assert cell["proposed_text"]


def test_recorded_label_matches_part8_or_was_fixed_by_an_allowed_move():
    """실행 시점 표지와 지금 part8 표지를 대조한다. 바뀌었다면 제안한 표지여야 한다."""
    doc = _doc()
    cells = _part8_cells()
    for cell in doc["cells"]:
        current = _labels(cells[(cell["model"], cell["column"])])
        assert current, (cell["model"], cell["column"])
        assert current in ({cell["part8_label_at_run"]}, set(cell["proposed_labels"])), (cell["model"], cell["column"], current)


def test_blocked_cells_are_refused_by_the_run():
    """part8에서 `코드가 막음`인 칸은 실제 호출이 기본값과 명시적 HMA 모두에서 거부되어야 한다."""
    doc = _doc()
    cells = _part8_cells()
    blocked = [c for c in doc["cells"] if "코드가 막음" in _labels(cells[(c["model"], c["column"])])]
    assert blocked
    for cell in blocked:
        connector = COLUMN_CONNECTOR[cell["column"]]
        assert _gate(doc, cell["run_model"], connector, FLAG_DEFAULT)["outcome"] == "refused", cell["model"]
        explicit = _gate(doc, cell["run_model"], connector, FLAG_ON)
        assert explicit["outcome"] == "refused" and _raised(explicit) == FACTORY_RAISE, cell["model"]


def test_cited_lines_in_blocked_cells_hold_where_the_run_raised_there():
    doc = _doc()
    for cell in doc["cells"]:
        if cell["result"] != "refused":
            continue
        for flag in (FLAG_DEFAULT, FLAG_ON):
            raised = _raised(_gate(doc, cell["run_model"], COLUMN_CONNECTOR[cell["column"]], flag))
            name, line = raised.rsplit("/", 1)[-1].split(":")
            if name in CITED_RANGES:
                low, high = CITED_RANGES[name]
                assert low <= int(line) <= high, (cell["model"], raised)


def test_part8_differences_are_exactly_the_known_list_or_fixed():
    found = _part8_differences(_doc())
    assert found <= PART8_DIFFERS, f"새로 어긋난 칸: {found - PART8_DIFFERS}"


def test_fixed_cells_cite_what_ran():
    """어긋남 목록에서 빠진 칸은 고쳐졌다는 뜻이므로, 고친 칸이 실제 예외 줄을 적었는지 본다."""
    doc = _doc()
    cells = _part8_cells()
    found = _part8_differences(doc)
    for model, column, kind in PART8_DIFFERS - found:
        text = cells[(model, column)]
        if kind == "미확인인데 거부됨" or kind == "인용 줄이 먼저 난 예외와 다름":
            assert "kv_cache_utils.py:1746" in text or "kv_cache_interface.py:138" in text, (model, column)
        if kind == "미확인인데 생성됨":
            assert "SCHEDULER" in text or "생성" in text, (model, column)


def test_constructed_is_never_called_a_working_model():
    doc = _doc()
    forbidden = re.compile(r"(모델|GLM|DeepSeek|Kimi).{0,40}(동작한다|작동한다|지원한다|돌아간다)")
    assert not forbidden.search(doc["limit"]), doc["limit"]
    assert "어떤 모델도" in doc["limit"]
    for cell in doc["cells"]:
        assert not forbidden.search(cell["proposed_text"]), cell["model"]
        if "실제 클래스 호출" in cell["proposed_labels"] and cell["result"] == "constructed":
            assert "생성" in cell["proposed_text"], "생성자까지라는 범위를 적어야 한다"


def test_not_run_list_names_what_was_left_out():
    items = " ".join(entry["item"] for entry in _doc()["parts"]["not_run"])
    for needle in ("worker-role", "FLASHINFER_MLA", "PyPI", "Kimi-K3", "separate-object-groups", "P8-26"):
        assert needle in items, needle
    assert all(entry["reason"] for entry in _doc()["parts"]["not_run"])


def test_every_correction_points_at_a_real_ledger_row():
    text = PART8.read_text(encoding="utf-8")
    corrections = _doc()["statement_corrections"]
    assert {c["id"] for c in corrections} >= {"P8-04", "P8-05", "P8-09", "P8-15", "P8-19"}
    for correction in corrections:
        assert f"| {correction['id']} |" in text, correction["id"]
        assert correction["observed"] and correction["evidence"]


def test_doc_states_scope_and_does_not_oversell():
    text = DOC.read_text(encoding="utf-8")
    for heading in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5."):
        assert heading in text, heading
    assert "실제 클래스 호출" in text and "코드 읽기" in text and "not_run" in text
    assert "가짜 텐서" in text and "어떤 모델" in text
    assert not re.search(r"(GLM|DeepSeek|Kimi)[^\n|]{0,40}LMCache[^\n|]{0,20}(동작한다|작동한다|지원한다)", text)
    for needle in ("TypeError", "kv_cache_utils.py:1746", "kv_cache_interface.py:138", "cupy-cuda13x", "NO_GPU_EXT"):
        assert needle in text, needle
