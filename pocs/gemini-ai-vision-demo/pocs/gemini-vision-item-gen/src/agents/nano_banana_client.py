"""Nano Banana Pro (Gemini 3 Pro Image) 클라이언트

v3.0.0: 모델 기반 End-to-End 파이프라인
- generate_from_prompt(): LLM이 생성한 프롬프트를 직접 사용
- 하드코딩된 템플릿 대신 자연어 프롬프트 사용

이미지 생성 전용 모델을 사용하여 고품질 교육용 이미지를 생성합니다.
- 차트/그래프
- 기하 도형
- 다이어그램
"""

from pathlib import Path
from typing import Optional
import base64

from google import genai
from google.genai import types

from ..core.config import settings


class NanoBananaClient:
    """Nano Banana Pro (Gemini 3 Pro Image) 이미지 생성 클라이언트"""

    def __init__(self, api_key: Optional[str] = None):
        """클라이언트 초기화

        Args:
            api_key: Google API 키 (없으면 설정에서 로드)
        """
        self.api_key = api_key or settings.google_api_key
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = settings.nano_banana_model

    def generate_chart(
        self,
        chart_type: str,
        data: dict,
        title: str,
        style: str = "educational",
        size: str = "2K",
        aspect_ratio: str = "16:9"
    ) -> bytes:
        """차트 이미지 생성

        Args:
            chart_type: 차트 유형 (bar, line, pie, scatter 등)
            data: 차트 데이터 (예: {"1월": 83, "2월": 29, ...})
            title: 차트 제목
            style: 스타일 (educational, minimal, colorful)
            size: 이미지 크기 (1K, 2K, 4K)
            aspect_ratio: 비율 (16:9, 4:3, 1:1 등)

        Returns:
            이미지 바이트
        """
        # 데이터 포맷팅
        data_str = ", ".join([f"{k}: {v}" for k, v in data.items()])

        prompt = f"""
고품질 교육용 {chart_type} 차트를 생성해주세요.

**데이터:**
{data_str}

**제목:** {title}

**요구사항:**
- {style} 스타일
- 깔끔한 레이블과 범례
- 데이터 값 표시
- 한글 텍스트 선명하게 렌더링
- 흰색 배경
- 교과서/시험지에 적합한 스타일
"""

        return self._generate_image(prompt, size, aspect_ratio, thinking_level="MEDIUM")

    def generate_geometry(
        self,
        shape_type: str,
        vertices: dict,
        measurements: dict,
        angles: Optional[dict] = None,
        size: str = "2K"
    ) -> bytes:
        """기하 도형 이미지 생성

        Args:
            shape_type: 도형 유형 (triangle, rectangle, circle 등)
            vertices: 꼭짓점 정보 (예: {"A": "상단", "B": "좌측 하단", "C": "우측 하단"})
            measurements: 측정값 (예: {"AB": "15cm", "BC": "19cm"})
            angles: 각도 정보 (예: {"B": "60°"})
            size: 이미지 크기

        Returns:
            이미지 바이트
        """
        vertices_str = "\n".join([f"  - 꼭짓점 {k}: {v}" for k, v in vertices.items()])
        measurements_str = "\n".join([f"  - 변 {k} = {v}" for k, v in measurements.items()])
        angles_str = ""
        if angles:
            angles_str = "\n".join([f"  - 각 {k} = {v}" for k, v in angles.items()])

        prompt = f"""
교육용 기하학 다이어그램을 생성해주세요.

**도형:** {shape_type}

**꼭짓점:**
{vertices_str}

**변의 길이:**
{measurements_str}

{f"**각도:**{chr(10)}{angles_str}" if angles_str else ""}

**요구사항:**
- 깔끔한 검은색 선
- 꼭짓점은 큰 점으로 표시
- 변의 길이는 파란색으로 표시
- 각도는 빨간색 호로 표시
- 흰색 배경
- 교과서 스타일의 명확한 다이어그램
"""

        return self._generate_image(prompt, size, "1:1", thinking_level="HIGH")

    def generate_from_prompt(
        self,
        prompt: str,
        size: str = "2K",
        aspect_ratio: str = "1:1"
    ) -> bytes:
        """v3.0.0: LLM이 생성한 프롬프트를 직접 사용하여 이미지 생성

        Args:
            prompt: LLM이 생성한 이미지 생성 프롬프트 (visual_spec.image_prompt)
            size: 이미지 크기 (1K, 2K, 4K)
            aspect_ratio: 비율 (16:9, 4:3, 1:1 등)

        Returns:
            이미지 바이트
        """
        return self._generate_image(prompt, size, aspect_ratio, thinking_level="HIGH")

    def generate_from_specification(
        self,
        visual_spec: dict,
        size: str = "2K"
    ) -> bytes:
        """시각화 사양에서 이미지 생성

        v3.0.0: image_prompt 필드 지원 추가

        Args:
            visual_spec: 시각화 사양 딕셔너리
                - image_prompt: (v3.0.0) LLM이 생성한 이미지 프롬프트
                - type: 시각화 유형
                - description: 설명
                - rendering_instructions: 렌더링 지침

        Returns:
            이미지 바이트
        """
        # v3.0.0: image_prompt가 있으면 직접 사용
        if visual_spec.get("image_prompt"):
            prompt = visual_spec["image_prompt"]

            # 스타일 가이드 추가
            if visual_spec.get("style_guidance"):
                prompt += f"\n\n스타일: {visual_spec['style_guidance']}"

            # 과목/맥락 정보 추가
            if visual_spec.get("subject_context"):
                prompt += f"\n과목/맥락: {visual_spec['subject_context']}"

            aspect_ratio = "1:1"
            return self._generate_image(prompt, size, aspect_ratio, thinking_level="HIGH")

        # 레거시: rendering_instructions 기반
        vis_type = visual_spec.get("type", visual_spec.get("visual_type", "그래프"))
        description = visual_spec.get("description", "")
        instructions = visual_spec.get("rendering_instructions", "")

        prompt = f"""
다음 사양에 따라 교육용 시각 자료를 생성해주세요.

**유형:** {vis_type}

**설명:**
{description}

**렌더링 지침:**
{instructions}

**추가 요구사항:**
- 교과서/시험지에 적합한 스타일
- 모든 텍스트와 레이블은 명확하게
- 수학 기호와 한글 선명하게 렌더링
- 깔끔한 흰색 배경
"""

        # 그래프 유형에 따라 비율 조정
        aspect_ratio = "16:9" if "그래프" in vis_type else "1:1"

        return self._generate_image(prompt, size, aspect_ratio, thinking_level="HIGH")

    def generate_function_graph(
        self,
        function_expr: str,
        x_range: tuple,
        y_range: tuple,
        special_points: Optional[list] = None,
        regions: Optional[list] = None,
        size: str = "2K"
    ) -> bytes:
        """함수 그래프 이미지 생성

        Args:
            function_expr: 함수 표현식 (예: "x^3 - 3x^2 - 4x + 12")
            x_range: x축 범위 (min, max)
            y_range: y축 범위 (min, max)
            special_points: 특별한 점들 (예: [("O", 0, 0), ("P", 4, 12)])
            regions: 색칠할 영역들 (예: [{"label": "A", "color": "light gray"}])
            size: 이미지 크기

        Returns:
            이미지 바이트
        """
        points_str = ""
        if special_points:
            points_str = "\n".join([f"  - 점 {p[0]}({p[1]}, {p[2]})" for p in special_points])

        regions_str = ""
        if regions:
            regions_str = "\n".join([f"  - 영역 {r['label']}: {r.get('description', '')} ({r.get('color', 'gray')})" for r in regions])

        prompt = f"""
수학 함수 그래프를 생성해주세요.

**함수:** y = {function_expr}

**좌표 범위:**
- x축: [{x_range[0]}, {x_range[1]}]
- y축: [{y_range[0]}, {y_range[1]}]

{f"**표시할 점:**{chr(10)}{points_str}" if points_str else ""}

{f"**색칠 영역:**{chr(10)}{regions_str}" if regions_str else ""}

**요구사항:**
- 좌표평면에 그리드 라인
- 함수 곡선은 검은색 실선
- x축, y축은 화살표로 표시
- 점은 큰 점으로 표시하고 레이블 추가
- 영역은 지정된 색상으로 색칠
- 교과서 스타일
- 명확한 눈금과 숫자
"""

        return self._generate_image(prompt, size, "1:1", thinking_level="HIGH")

    def _generate_image(
        self,
        prompt: str,
        size: str = "2K",
        aspect_ratio: str = "16:9",
        thinking_level: str = "MEDIUM"
    ) -> bytes:
        """이미지 생성 공통 로직

        Args:
            prompt: 이미지 생성 프롬프트
            size: 이미지 크기 (1K, 2K, 4K)
            aspect_ratio: 비율 (16:9, 4:3, 1:1 등)
            thinking_level: Thinking 모드 레벨 (현재 미사용)

        Returns:
            이미지 바이트
        """
        # 이미지 생성 설정
        config = types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=size
            )
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )

        return self._extract_image(response)

    def _extract_image(self, response) -> bytes:
        """응답에서 이미지 추출

        Args:
            response: API 응답

        Returns:
            이미지 바이트
        """
        if not response.candidates:
            raise ValueError("이미지 생성 실패: 응답에 후보가 없습니다.")

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise ValueError("이미지 생성 실패: 응답에 콘텐츠가 없습니다.")

        for part in candidate.content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                return part.inline_data.data

        raise ValueError("이미지 생성 실패: 응답에 이미지가 없습니다.")

    def save_image(self, image_bytes: bytes, output_path: Path) -> Path:
        """이미지 저장

        Args:
            image_bytes: 이미지 바이트
            output_path: 저장 경로

        Returns:
            저장된 파일 경로
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(image_bytes)

        return output_path
