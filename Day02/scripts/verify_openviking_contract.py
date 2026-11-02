"""새 OpenViking의 HTTP 계약을 실제 서버 + 로컬 모형 모델로 검사한다.

유료 API·사용자 .env·기존 서버를 사용하지 않는다. 임시 저장소에서 인증→적재→원문
조회→검색을 검사한다. 합성 임베딩/요약이므로 검색 품질이나 LLM 성능 검증이 아니다.
"""
from __future__ import annotations

import hashlib
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from day02.evidence import Metadata
from day02.ingestion.pipeline import ingest
from day02.openviking import server
from day02.openviking.client import VikingClient
from day02.settings import Settings, write_json

ROOT = Path(__file__).resolve().parents[1]


class SyntheticModel(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("/embeddings"):
            inputs = request["input"]
            inputs = [inputs] if isinstance(inputs, str) else inputs
            result = {"object": "list", "model": "contract-test", "data": [
                {"object": "embedding", "index": i, "embedding": [
                    (b + 1) / 256 for b in hashlib.sha256(str(text).encode()).digest()[:8]
                ]} for i, text in enumerate(inputs)
            ], "usage": {"prompt_tokens": 1, "total_tokens": 1}}
        elif self.path.endswith("/chat/completions"):
            result = {"id": "contract-test", "object": "chat.completion", "created": 0,
                      "model": "contract-test", "choices": [{"index": 0, "finish_reason": "stop",
                      "message": {"role": "assistant", "content": "Synthetic contract document for API verification."}}],
                      "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        else:
            self.send_error(404)
            return
        payload = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    model = ThreadingHTTPServer(("127.0.0.1", 0), SyntheticModel)
    worker = threading.Thread(target=model.serve_forever, daemon=True)
    worker.start()
    try:
        with TemporaryDirectory(prefix="day02-contract-") as directory:
            root = Path(directory).resolve()
            (root / "runtime").mkdir()
            (root / "runtime/openviking").symlink_to(ROOT / "runtime/openviking", target_is_directory=True)
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            settings = Settings(root=root, api_key="local-contract-only", api_base=f"http://127.0.0.1:{model.server_port}/v1",
                                model="contract-test", vision_model="contract-test", embedding_model="contract-test",
                                embedding_dimension=8, port=port)
            source = root / "contract.md"
            source.write_text("# Contract probe\n\nSynthetic contract document for API verification.\n", encoding="utf-8")
            metadata = Metadata(doc_id="contract", title="Contract probe", source="contract.md").model_dump(mode="json")
            catalog = root / "catalog.json"
            write_json(catalog, [{"path": "contract.md", "metadata": metadata}])
            try:
                server.start(settings)
                with VikingClient.configured(settings) as client:
                    first = ingest(settings, client, catalog, namespace="contract")
                    second = ingest(settings, client, catalog, namespace="contract")
                    uri = next(iter(first["documents"]))
                    assert client.read(uri).strip() == source.read_text().strip()
                    assert second["reused"] == 1
                    assert client.find("Contract probe", first["target_uri"])
                    assert client.grep("Synthetic", uri)
                print(json.dumps({"openviking": server.SERVER_VERSION, "mode": "synthetic-contract",
                                  "auth": "passed", "ingest": "passed", "read": "passed",
                                  "reuse": "passed", "find": "passed", "grep": "passed"}))
            except Exception as exc:
                # 모형 키만 썼지만 로그 전체를 출력하지 않는다. 오류 종류로 실패를 알린다.
                print(json.dumps({"openviking": server.SERVER_VERSION, "mode": "synthetic-contract",
                                  "status": "failed", "error_type": type(exc).__name__,
                                  "error": settings.redact(str(exc))}, ensure_ascii=False))
                raise
            finally:
                server.stop(settings)
    finally:
        model.shutdown()
        model.server_close()
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
