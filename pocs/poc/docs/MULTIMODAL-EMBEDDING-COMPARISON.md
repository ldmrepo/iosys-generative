# 멀티모달 임베딩 모델 비교 분석

**작성일**: 2026-01-29
**목적**: Qwen3-VL-Embedding과 경쟁 모델 비교 분석

---

## 1. 주요 멀티모달 임베딩 모델 비교

| 모델 | 파라미터 | MMEB-V2 | 특징 | 라이선스 |
|------|---------|---------|------|---------|
| **Qwen3-VL-Embedding-8B** | 8B | **77.8** (1위) | 텍스트+이미지+비디오, 30+언어 | Open |
| **Qwen3-VL-Embedding-2B** | 2B | **73.2** | 경량화, 현재 POC 사용 | Open |
| VLM2Vec-V2 (Qwen2VL-7B) | 7B | 65.8 | ICLR 2025 발표 | Open |
| RzenEmbed-8B | 8B | 72.9 | - | Open |
| jina-embeddings-v4 | 3.8B | - | Qwen2.5-VL 기반, Multi-vector 지원 | Open |
| voyage-multimodal-3 | - | - | 문서 스크린샷 특화, API 전용 | Proprietary |
| ColPali | - | - | Late-interaction, 문서 검색 | Open |
| jina-clip-v2 | 865M | - | 89개 언어 지원 | Open |
| CLIP (OpenAI) | 400M+ | - | 원조 멀티모달 임베딩 | Open |
| SigLIP (Google) | 400M+ | - | Sigmoid loss, 효율적 학습 | Open |

---

## 2. MMEB-V2 벤치마크

### 2.1 벤치마크 개요

MMEB-V2 (Massive Multimodal Embedding Benchmark V2)는 TIGER-Lab에서 개발한 종합 멀티모달 임베딩 평가 벤치마크입니다.

**평가 영역:**
- Image: 이미지-텍스트 검색, 분류, QA
- Video: 비디오 검색, 분류, 시간 그라운딩
- Visual Document: 문서 스크린샷 검색

**태스크 수:** 9개 메타 태스크, 78개 세부 태스크

### 2.2 Qwen3-VL-Embedding-8B 성능

| 도메인 | 점수 |
|--------|------|
| Image | 80.1 |
| Video | 67.1 |
| Visual Document | 82.4 |
| **Overall** | **77.8** |

> 이전 최고 오픈소스 모델 대비 **+6.7% 향상** (2025년 1월 8일 기준)

### 2.3 모델별 MMEB-V2 점수 비교

| 순위 | 모델 | Overall | Image | Video | VisDoc |
|------|------|---------|-------|-------|--------|
| 1 | Qwen3-VL-Embedding-8B | 77.8 | 80.1 | 67.1 | 82.4 |
| 2 | Qwen3-VL-Embedding-2B | 73.2 | - | - | - |
| 3 | RzenEmbed-8B | 72.9 | - | - | - |
| 4 | VLM2Vec-V2 (7B) | 65.8 | - | - | - |
| 5 | VLM2Vec (2B) | 60.1 | - | - | - |

---

## 3. 모델별 특성 비교

### 3.1 입력 모달리티 지원

| 특성 | Qwen3-VL | jina-v4 | voyage-mm-3 | ColPali | CLIP/SigLIP |
|------|----------|---------|-------------|---------|-------------|
| 텍스트 | ✅ | ✅ | ✅ | ❌ | ✅ |
| 이미지 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 비디오 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 문서 스크린샷 | ✅ | ✅ | ✅ | ✅ | ❌ |
| 인터리브 입력 | ✅ | ✅ | ✅ | ❌ | ❌ |

### 3.2 기능 지원

| 특성 | Qwen3-VL | jina-v4 | voyage-mm-3 | ColPali | CLIP/SigLIP |
|------|----------|---------|-------------|---------|-------------|
| 다국어 (30+) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Reranker 제공 | ✅ | ❌ | ❌ | ❌ | ❌ |
| Matryoshka 차원 | ✅ | ✅ | ❌ | ❌ | ❌ |
| Multi-vector | ❌ | ✅ | ❌ | ✅ | ❌ |
| 오픈소스 | ✅ | ✅ | ❌ | ✅ | ✅ |

---

## 4. 아키텍처 비교

| 모델 | 백본 | 임베딩 차원 | Pooling | 컨텍스트 길이 |
|------|------|-----------|---------|--------------|
| Qwen3-VL-Embedding | Qwen3-VL | 2048 (64-2048 조절) | Last Token | 32K |
| jina-embeddings-v4 | Qwen2.5-VL-3B | 2048 (Matryoshka) | - | - |
| jina-clip-v2 | XLM-RoBERTa + EVA02 | 1024 (64-1024) | - | 8K |
| CLIP | ViT + Transformer | 512/768 | CLS Token | 77 |
| SigLIP | ViT + Text Encoder | 768/1024 | - | - |
| ColPali | PaliGemma | Multi-vector | Late Interaction | - |

---

## 5. 모델별 상세 분석

### 5.1 Qwen3-VL-Embedding (Alibaba)

**강점:**
- MMEB-V2 1위 (77.8)
- 텍스트+이미지+비디오 통합 처리
- 30+ 언어 지원 (한국어 포함)
- Reranker 모델 제공 (Two-stage 검색)
- 2B/8B 크기 선택 가능
- Matryoshka 임베딩 지원

**약점:**
- 8B 모델은 높은 GPU 요구사항
- Image-Only 검색 미지원 (텍스트 필수)

**출처:** [GitHub](https://github.com/QwenLM/Qwen3-VL-Embedding) | [Paper](https://arxiv.org/abs/2601.04720)

### 5.2 jina-embeddings-v4 (Jina AI)

**강점:**
- Qwen2.5-VL-3B 기반 통합 모델
- Single-vector + Multi-vector 지원
- 89개 언어 지원
- 문서 검색 특화 (ViDoRe 90.17)
- 3개 태스크별 LoRA 어댑터

**약점:**
- 비디오 미지원
- MMEB-V2 공식 점수 미공개

**출처:** [Jina AI](https://jina.ai/models/jina-embeddings-v4/) | [Paper](https://arxiv.org/abs/2506.18902)

### 5.3 voyage-multimodal-3 (Voyage AI)

**강점:**
- 문서 스크린샷 검색 최고 성능
- 인터리브 텍스트+이미지 처리
- 복잡한 문서 파싱 불필요
- 경쟁 모델 대비 +19.63% 향상

**약점:**
- API 전용 (오픈소스 아님)
- 비디오 미지원
- 다국어 제한적

**출처:** [Voyage AI Blog](https://blog.voyageai.com/2024/11/12/voyage-multimodal-3/)

### 5.4 ColPali

**강점:**
- Late-interaction 아키텍처
- 문서 검색 특화
- 시각적 복잡한 문서 처리

**약점:**
- 텍스트 전용 쿼리 미지원
- Re-ranking 용도 권장
- 일반 이미지 검색 약함

**출처:** [ICLR 2025](https://openreview.net/forum?id=TE0KOzWYAF)

### 5.5 jina-clip-v2 (Jina AI)

**강점:**
- 89개 언어 지원
- Flickr30k 98.0% 정확도
- Matryoshka 차원 축소 (1024→64)
- 865M 파라미터 (경량)

**약점:**
- 비디오 미지원
- 문서 스크린샷 약함

**출처:** [Jina AI](https://jina.ai/news/jina-clip-v2-multilingual-multimodal-embeddings-for-text-and-images/)

### 5.6 VLM2Vec (TIGER-Lab)

**강점:**
- MMEB 벤치마크 개발팀
- Qwen2VL 기반
- ICLR 2025 발표

**약점:**
- Qwen3-VL-Embedding 대비 낮은 성능 (65.8 vs 77.8)

**출처:** [TIGER-Lab](https://tiger-ai-lab.github.io/VLM2Vec/) | [GitHub](https://github.com/TIGER-AI-Lab/VLM2Vec)

### 5.7 CLIP / SigLIP

**CLIP (OpenAI):**
- 원조 멀티모달 임베딩 모델
- Softmax contrastive loss
- 대규모 배치 필요

**SigLIP (Google DeepMind):**
- Sigmoid loss (Binary classification)
- 소규모 배치에서 효율적
- CLIP 대비 학습 효율 개선

**출처:** [CLIP vs SigLIP 비교](https://blog.ritwikraha.dev/choosing-between-siglip-and-clip-for-language-image-pretraining)

---

## 6. 현재 POC 대비 분석

### 6.1 현재 사용 모델: Qwen3-VL-Embedding-2B

| 항목 | 값 |
|------|-----|
| 파라미터 | 2B |
| MMEB-V2 | 73.2 |
| 임베딩 차원 | 2048 |
| GPU 요구사항 | RTX 2070 8GB |
| 처리 속도 | ~3.9 items/sec |

### 6.2 대안 모델 비교

| 모델 | 장점 | 단점 | 전환 권장 |
|------|------|------|----------|
| Qwen3-VL-Embedding-8B | +4.6 MMEB 점수 | 더 큰 GPU 필요 | 성능 중요시 |
| jina-embeddings-v4 | Multi-vector, 문서 특화 | 비디오 미지원 | 문서 검색 시 |
| voyage-multimodal-3 | 문서 스크린샷 최고 | API 비용 발생 | 비용 허용 시 |

### 6.3 현재 선택 타당성

**Qwen3-VL-Embedding-2B 선택 이유:**

1. **성능 목표 달성**: Hybrid GT Top-5 80.9% (목표 80%)
2. **리소스 효율**: RTX 2070 8GB로 운영 가능
3. **비디오 지원**: 향후 비디오 문항 대응 가능
4. **한국어 지원**: 30+ 언어 중 한국어 포함
5. **오픈소스**: 상용화 가능, API 비용 없음
6. **Reranker 제공**: Two-stage 검색 파이프라인 가능

---

## 7. 결론 및 권장사항

### 7.1 현재 선택 유지 권장

| 평가 항목 | 결과 |
|----------|------|
| 벤치마크 순위 | MMEB-V2 2위 (2B 기준) |
| 성능 목표 | ✅ 달성 (80.9%) |
| 비용 효율 | ✅ 오픈소스, GPU 1장 |
| 확장성 | ✅ 비디오/다국어 지원 |

### 7.2 향후 고려사항

1. **8B 모델 전환**: GPU 업그레이드 시 성능 향상 가능
2. **jina-v4 테스트**: 문서 스크린샷 검색 필요시
3. **voyage-mm-3**: 예산 확보 시 API 테스트

---

## 8. 참고 자료

### 공식 문서
- [Qwen3-VL-Embedding GitHub](https://github.com/QwenLM/Qwen3-VL-Embedding)
- [Qwen3-VL-Embedding Paper](https://arxiv.org/abs/2601.04720)
- [MMEB Leaderboard](https://huggingface.co/spaces/TIGER-Lab/MMEB-Leaderboard)

### 경쟁 모델
- [jina-embeddings-v4](https://jina.ai/models/jina-embeddings-v4/)
- [jina-clip-v2](https://jina.ai/news/jina-clip-v2-multilingual-multimodal-embeddings-for-text-and-images/)
- [voyage-multimodal-3](https://blog.voyageai.com/2024/11/12/voyage-multimodal-3/)
- [VLM2Vec - TIGER-Lab](https://tiger-ai-lab.github.io/VLM2Vec/)
- [ColPali](https://huggingface.co/vidore/colpali)

### 벤치마크
- [MMEB-V2 Dataset](https://huggingface.co/datasets/TIGER-Lab/MMEB-V2)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)

### 아키텍처 비교
- [CLIP vs SigLIP 비교](https://blog.ritwikraha.dev/choosing-between-siglip-and-clip-for-language-image-pretraining)
- [Multi-modal Representation Learning](https://vizuara.substack.com/p/multi-modal-representation-learning)
