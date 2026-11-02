"""로컬 교차 인코더 재정렬. 질문과 조각을 한 쌍으로 모델에 넣어 관련도 점수를 직접 얻는다."""
from __future__ import annotations

from functools import cached_property

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

_BATCH_SIZE = 16
_MAX_LENGTH = 512  # 질문과 조각을 합친 최대 입력 길이다. 넘는 부분은 잘린다.


class CrossEncoderReranker:
    """(질문, 조각) 쌍마다 점수 하나를 낸다. 점수는 클수록 관련이 높고 입력 순서를 그대로 지킨다."""

    def __init__(self, model_name: str, *, device: str = "cpu"):
        self.model_name = model_name
        self.device = device

    @cached_property
    def _tokenizer(self) -> PreTrainedTokenizerBase:
        return AutoTokenizer.from_pretrained(self.model_name)

    @cached_property
    def _model(self) -> PreTrainedModel:
        return AutoModelForSequenceClassification.from_pretrained(self.model_name).to(self.device).eval()

    @torch.no_grad()
    def score(self, query: str, texts: list[str]) -> list[float]:
        scores: list[float] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = self._tokenizer([query] * len(texts[start:start + _BATCH_SIZE]), texts[start:start + _BATCH_SIZE],
                                    padding=True, truncation=True, max_length=_MAX_LENGTH,
                                    return_tensors="pt").to(self.device)
            scores += self._model(**batch).logits.view(-1).float().tolist()
        return scores
