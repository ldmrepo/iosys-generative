# Qwen3-VL 모델 사용 방식 검증 보고서

**작성일**: 2026-01-29
**목적**: 공식 문서 대비 현재 구현의 정확성 검증

---

## 1. Qwen3-VL-Embedding 모델

### 1.1 공식 사용 방법

**출처**: [HuggingFace Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B)

```python
from scripts.qwen3_vl_embedding import Qwen3VLEmbedder

model = Qwen3VLEmbedder(model_name_or_path="Qwen/Qwen3-VL-Embedding-2B")

inputs = [
    {"text": "문제 텍스트"},
    {"text": "문제 텍스트", "image": "/path/to/image.png"}
]

embeddings = model.process(inputs)
```

**핵심 특징:**
- Pooling 방식: **Last Token (EOS) Pooling**
  > "The model extracts the hidden state vector corresponding to the [EOS] token"
- 입력 형식: `{"text": ..., "image": ...}` 딕셔너리 리스트
- 출력: L2 정규화된 임베딩 벡터

### 1.2 현재 구현 방식

**파일**: `poc/scripts/generate_qwen_embeddings_multimodal_meanpool.py`

```python
from qwen3_vl_embedding import Qwen3VLForEmbedding

class Qwen3VLEmbedderMeanPool:
    def __init__(self, model_name_or_path, **kwargs):
        self.model = Qwen3VLForEmbedding.from_pretrained(...)

    def process(self, inputs):
        # Mean pooling (NOT last token pooling)
        embeddings = torch.sum(token_embeddings * mask, 1) / mask.sum(1)
        return embeddings
```

### 1.3 차이점 분석

| 항목 | 공식 방식 | 현재 구현 | 일치 |
|------|----------|----------|------|
| 클래스 | `Qwen3VLEmbedder` | `Qwen3VLForEmbedding` | ⚠️ |
| **Pooling** | **Last Token (EOS)** | **Mean Pooling** | ❌ |
| 입력 형식 | `{"text", "image"}` | `{"text", "image"}` | ✅ |
| 정규화 | L2 normalize | L2 normalize | ✅ |
| 이미지 전처리 | `qwen_vl_utils` | `qwen_vl_utils` | ✅ |

### 1.4 영향 분석

**Mean Pooling vs Last Token Pooling:**

1. **Mean Pooling** (현재 구현)
   - 모든 토큰의 평균 사용
   - 문장 전체의 의미를 균등하게 반영
   - 긴 문장에서 정보 손실 가능성 낮음

2. **Last Token (EOS) Pooling** (공식)
   - EOS 토큰의 hidden state만 사용
   - 최신 언어 모델에서 권장되는 방식
   - Instruction-following 모델에 최적화

**결론**: 현재 구현이 다르지만, **성능 평가 결과(Image GT 100%, Hybrid GT 85.2%)가 목표를 충족**하므로 실용적으로는 문제없음.

---

## 2. Qwen3-VL-Reranker 모델

### 2.1 공식 사용 방법

**출처**: [HuggingFace Qwen3-VL-Reranker-2B](https://huggingface.co/Qwen/Qwen3-VL-Reranker-2B)

```python
from scripts.qwen3_vl_reranker import Qwen3VLReranker

model = Qwen3VLReranker(model_name_or_path="Qwen/Qwen3-VL-Reranker-2B")

inputs = {
    "instruction": "Retrieve relevant documents for the query.",
    "query": {"text": "검색 쿼리"},
    "documents": [
        {"text": "문서 1"},
        {"text": "문서 2", "image": "image_url"}
    ],
    "fps": 1.0
}

scores = model.process(inputs)  # [0.86, 0.67, 0.81]
```

**핵심 특징:**
- 입력: query + documents 구조
- 출력: 각 문서의 관련성 점수 (0-1)
- 멀티모달 지원 (텍스트, 이미지, 비디오)

### 2.2 현재 구현 상태

POC에서 Reranker 테스트 결과:
- Top-10 Recall: +4.0%p 개선
- 이미지 문항에서 -5.7%p 하락 (텍스트 기반 한계)

**권장**: Reranker는 선택적 적용 (LaTeX 문항에서만 효과적)

---

## 3. 권장 사항

### 3.1 현재 상태 유지 (권장)

| 이유 | 설명 |
|------|------|
| 성능 달성 | Image GT 100%, Hybrid GT 85.2% (목표 80% 초과) |
| 검증 완료 | 176,443건 전체 임베딩 생성 및 검증 완료 |
| 안정성 | 프로덕션 적용 가능한 상태 |

### 3.2 향후 개선 옵션

공식 방식으로 전환 시 고려사항:

```python
# 공식 방식으로 전환
from scripts.qwen3_vl_embedding import Qwen3VLEmbedder

model = Qwen3VLEmbedder(
    model_name_or_path="Qwen/Qwen3-VL-Embedding-2B",
    torch_dtype=torch.float16,
    attn_implementation="flash_attention_2"
)

inputs = [{"text": text, "image": image_path} for text, image_path in items]
embeddings = model.process(inputs)
```

**전환 시 필요 작업:**
1. 새 임베딩 생성 (176,443건, ~13시간)
2. 성능 재평가
3. 기존 임베딩과 비교 검증

---

## 4. 결론

| 항목 | 상태 |
|------|------|
| Embedding 모델 | ⚠️ Pooling 방식 다름 (Mean vs Last Token) |
| 성능 목표 | ✅ 달성 (Top-5 Recall ≥ 80%) |
| 프로덕션 적용 | ✅ 가능 |
| 공식 방식 전환 | 선택사항 (현재 성능 충분) |

**최종 권장**: 현재 구현 유지. 성능 목표를 충족하므로 추가 작업 불필요.

---

## 참고 자료

- [Qwen3-VL-Embedding GitHub](https://github.com/QwenLM/Qwen3-VL-Embedding)
- [HuggingFace Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B)
- [HuggingFace Qwen3-VL-Embedding-8B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B)
- [HuggingFace Qwen3-VL-Reranker-2B](https://huggingface.co/Qwen/Qwen3-VL-Reranker-2B)
