# Nano Banana Pro (Gemini 3 Pro Image) 연구 문서

**문서 ID**: NANO-BANANA-PRO-RESEARCH-001
**버전**: v1.0.0
**작성일**: 2026-02-01
**목적**: Gemini 3 Pro Image 모델 연구 및 기술 분석

---

## 1. 모델 개요

### 1.1 명칭 및 버전

| 항목 | 내용 |
|------|------|
| **공식명** | Gemini 3 Pro Image |
| **코드명** | Nano Banana Pro |
| **모델 ID** | `gemini-3-pro-image-preview` |
| **상태** | Preview |
| **Knowledge Cutoff** | 2025년 1월 |

### 1.2 모델 계보

```
Gemini 2.0 Flash (Native Image Output)
          ↓
Gemini 2.5 Flash Image (Nano Banana)
    - Model ID: gemini-2.5-flash-image
    - 1024px 지원
          ↓
Gemini 3 Pro Image (Nano Banana Pro)
    - Model ID: gemini-3-pro-image-preview
    - 4K (4096px) 지원
```

---

## 2. 핵심 기능

### 2.1 이미지 생성 기능

| 기능 | 설명 |
|------|------|
| **Text-to-Image** | 텍스트 프롬프트로 이미지 생성 |
| **Image Editing** | 자연어 대화로 이미지 편집 |
| **Multi-turn Iteration** | 여러 턴에 걸친 대화형 이미지 개선 |
| **Reference Images** | 최대 14개 참조 이미지 지원 |
| **Text Rendering** | 이미지 내 텍스트 렌더링 (고품질) |
| **Google Search Grounding** | 실시간 정보 기반 이미지 생성 |

### 2.2 참조 이미지 지원

| 유형 | 최대 개수 | 용도 |
|------|----------|------|
| **Object Reference** | 6개 | 고충실도 객체 포함 |
| **Human Consistency** | 5개 | 캐릭터 일관성 유지 |
| **Style Reference** | 3개 | 스타일 전이 |

### 2.3 Thinking Mode

- **thinking_level** 파라미터로 추론 깊이 제어
- 지원 레벨: `low`, `medium`, `high` (기본값)
- 복잡한 이미지 생성 작업에서 품질 향상

---

## 3. 기술 사양

### 3.1 해상도

| 옵션 | 크기 | 용도 |
|------|------|------|
| **1K** | 1024 x 1024 | 기본값, 빠른 생성 |
| **2K** | 2048 x 2048 | 고품질 |
| **4K** | 4096 x 4096 | 전문가용, 인쇄물 |

### 3.2 Aspect Ratio

지원 비율:
```
"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
```

### 3.3 토큰 제한

| 항목 | 값 |
|------|-----|
| **Input Token** | 65,536 |
| **Output Token** | 32,768 |
| **Context Window** | 1M tokens |

### 3.4 출력 형식

- **Response Modalities**: `["TEXT", "IMAGE"]`
- **Image Format**: PNG (기본)
- **Watermark**: SynthID 워터마크 자동 포함

---

## 4. API 사용법

### 4.1 기본 설정

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")
```

### 4.2 이미지 생성 기본

```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents="교육용 이차함수 그래프를 생성하세요. y = x^2 - 4x + 3",
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
    )
)

for part in response.parts:
    if part.text is not None:
        print(part.text)
    elif image := part.as_image():
        image.save("output.png")
```

### 4.3 고급 설정 (해상도, 비율)

```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",
            image_size="2K"  # 1K, 2K, 4K
        )
    )
)
```

### 4.4 Google Search Grounding

```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents="2025년 1월 서울 날씨 차트를 생성하세요",
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        tools=[{"google_search": {}}]
    )
)
```

### 4.5 Thinking Mode 활성화

```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        thinking_config=types.ThinkingConfig(
            thinking_level="high"  # low, medium, high
        )
    )
)
```

### 4.6 참조 이미지 사용

```python
from PIL import Image

reference_image = Image.open("reference.png")

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[
        reference_image,
        "이 스타일을 유지하면서 삼각형 도형을 그려주세요"
    ],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
    )
)
```

---

## 5. 교육용 문항 이미지 생성

### 5.1 수학 그래프 생성

```python
prompt = """
교육용 수학 그래프를 생성하세요.

[요구사항]
- 함수: f(x) = x² - 2x - 3
- 좌표축 포함 (x, y축)
- 격자선 표시
- 꼭짓점, x절편, y절편 표시
- 교과서 스타일의 깔끔한 디자인
- 흰색 배경
- 모든 레이블은 한글로

[스타일]
- 선 두께: 적당함
- 색상: 그래프는 파란색, 축은 검정색
- 폰트: 명확하고 읽기 쉽게
"""

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        image_config=types.ImageConfig(
            aspect_ratio="1:1",
            image_size="2K"
        )
    )
)
```

### 5.2 도형 생성

```python
prompt = """
교육용 기하학 도형을 생성하세요.

[요구사항]
- 직각삼각형 ABC
- 꼭짓점 A에서 직각
- 변 AB = 3cm, AC = 4cm, BC = 5cm
- 각 꼭짓점에 A, B, C 레이블
- 변의 길이 표시
- 직각 기호 표시

[스타일]
- 깔끔한 흰색 배경
- 검정색 선
- 명확한 레이블
"""
```

### 5.3 데이터 시각화

```python
prompt = """
교육용 막대 그래프를 생성하세요.

[데이터]
- 1월: 45
- 2월: 52
- 3월: 48
- 4월: 61
- 5월: 55

[요구사항]
- 제목: "월별 판매량"
- x축: 월
- y축: 판매량 (단위: 개)
- 막대 색상: 파란색 계열
- 각 막대 위에 수치 표시
- 교과서 스타일
"""
```

---

## 6. 제한사항 및 주의점

### 6.1 기술적 제한

| 제한 | 내용 |
|------|------|
| **인물 생성** | 실존 인물 생성 제한 |
| **폭력/성인 콘텐츠** | 생성 불가 |
| **저작권 콘텐츠** | 유명 캐릭터 등 제한 |
| **워터마크** | SynthID 자동 삽입 (제거 불가) |

### 6.2 API 제한

| 항목 | Free Tier | 유료 |
|------|-----------|------|
| **일일 요청** | 500회 | 무제한 |
| **분당 토큰** | 250,000 | 상향 가능 |

### 6.3 Thought Signature

- 이미지 생성 시 Thought Signature 검증 필수
- 누락 시 400 오류 발생
- 공식 SDK 사용 시 자동 처리

### 6.4 SDK 버전 요구사항

```bash
# 최소 버전: 1.51.0
pip install google-genai>=1.51.0
```

---

## 7. 가격 정책

### 7.1 토큰 기반 가격 (1M 토큰당)

| 항목 | 가격 |
|------|------|
| **Input (텍스트)** | $2 |
| **Output (텍스트)** | $12~$18 |

### 7.2 이미지 생성 가격

| 해상도 | 예상 가격/이미지 |
|--------|-----------------|
| **1K** | ~$0.13 |
| **2K** | ~$0.18 |
| **4K** | ~$0.24 |

---

## 8. 비교: Nano Banana vs Nano Banana Pro

| 항목 | Nano Banana (2.5 Flash) | Nano Banana Pro (3 Pro) |
|------|------------------------|------------------------|
| Model ID | gemini-2.5-flash-image | gemini-3-pro-image-preview |
| 최대 해상도 | 1K (1024px) | 4K (4096px) |
| Thinking Mode | ❌ | ✅ |
| Search Grounding | ❌ | ✅ |
| 참조 이미지 | 제한적 | 최대 14개 |
| 텍스트 렌더링 | 기본 | 고급 |
| 속도 | 빠름 | 중간 |
| 가격 | 저렴 | 높음 |
| 용도 | 고속/대량 생성 | 전문가/고품질 |

---

## 9. 교육용 문항 생성 시 권장 설정

### 9.1 그래프/도형

```python
config = types.GenerateContentConfig(
    response_modalities=['TEXT', 'IMAGE'],
    image_config=types.ImageConfig(
        aspect_ratio="1:1",
        image_size="2K"
    ),
    thinking_config=types.ThinkingConfig(
        thinking_level="high"
    )
)
```

### 9.2 데이터 시각화

```python
config = types.GenerateContentConfig(
    response_modalities=['TEXT', 'IMAGE'],
    image_config=types.ImageConfig(
        aspect_ratio="16:9",
        image_size="2K"
    )
)
```

### 9.3 프롬프트 템플릿

```
교육용 {visual_type}을(를) 생성하세요.

[데이터/수식]
{data}

[요구사항]
- 교과서/시험지에 적합한 깔끔한 스타일
- 흰색 배경
- 모든 레이블과 텍스트는 선명하게
- 한글 사용
- {specific_requirements}

[스타일]
- 선 두께: 적당함
- 색상: {color_scheme}
- 전문적이고 교육적인 느낌
```

---

## 10. 참고 자료

### 공식 문서
- [Nano Banana Image Generation](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3)
- [Gemini Models Overview](https://ai.google.dev/gemini-api/docs/models)

### 관련 블로그
- [Experiment with Gemini 2.0 Flash native image generation](https://developers.googleblog.com/experiment-with-gemini-20-flash-native-image-generation/)
- [Introducing Gemini 2.5 Flash Image](https://developers.googleblog.com/introducing-gemini-2-5-flash-image/)

### Vertex AI
- [Generate and edit images with Gemini](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-generation)
- [Gemini 3 Pro Image Preview](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-3-pro-image-preview)

---

**문서 끝**
