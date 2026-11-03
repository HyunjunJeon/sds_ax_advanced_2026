"""단위 테스트는 Langfuse로 나가지 않는다."""

import os

os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
