"""RunPod vLLM (GLM-5.3-Flash, H200 x4) via langchain-openai.

uv run python runpod_model_call.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def _base_url() -> str:
    load_dotenv(Path(__file__).with_name(".env"))
    url = os.environ.get("RUNPOD_BASE_URL", "").strip()
    if not url:
        print(
            "RUNPOD_BASE_URL 이 설정되지 않았다. 강사가 공지한 주소를 "
            "https://<POD_ID>-8000.proxy.runpod.net/v1 형태로 Day07/.env 에 넣는다 "
            "(.env.example 참고).",
            file=sys.stderr,
        )
        sys.exit(1)
    return url


llm = ChatOpenAI(
    model="GLM-5.3-Flash",
    base_url=_base_url(),
    api_key="EMPTY",
    # RunPod 프록시는 100초에서 연결을 끊으므로 긴 응답은 streaming=True로 받는다.
    timeout=95,
    extra_body={
        # 각 모델마다 Chat Template 이 다르기 때문에
        # Reasoning On/Off 요청을 전달하는 방식도 모두 다름.
        "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": True},
    },
)

if __name__ == "__main__":
    print(llm.invoke("한 줄로 자기소개 해줘.").content)
