"""로컬 E5 임베딩. Anthropic에는 임베딩 API가 없어 transformers로 직접 계산한다."""
from __future__ import annotations

from functools import cached_property

import torch
from langchain_core.embeddings import Embeddings
from transformers import AutoModel, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

_BATCH_SIZE = 16
_MAX_LENGTH = 512  # E5의 최대 입력 길이다.


class LocalE5Embeddings(Embeddings):
    """E5 규약대로 질의에 'query: ', 문서에 'passage: '를 붙이고 평균 풀링 후 L2 정규화한다."""

    def __init__(self, model_name: str, *, device: str = "cpu"):
        self.model_name = model_name
        self.device = device

    @cached_property
    def _tokenizer(self) -> PreTrainedTokenizerBase:
        return AutoTokenizer.from_pretrained(self.model_name)

    @cached_property
    def _model(self) -> PreTrainedModel:
        return AutoModel.from_pretrained(self.model_name).to(self.device).eval()

    @torch.no_grad()
    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = self._tokenizer(texts[start:start + _BATCH_SIZE], padding=True, truncation=True,
                                    max_length=_MAX_LENGTH, return_tensors="pt").to(self.device)
            hidden = self._model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1)
            vectors += torch.nn.functional.normalize(pooled, dim=1).tolist()
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode([f"passage: {text}" for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._encode([f"query: {text}"])[0]
