"""Agentic Vision 클라이언트

Gemini의 code_execution 기능을 활용한 동적 이미지 분석
Think-Act-Observe 프레임워크 구현
"""

import base64
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from ..core.config import settings
from ..core.schemas import (
    AgenticLog, AgenticStep, BoundingBox,
    ExtractedItem, ItemType, PageLayout, PassageInfo
)


class AgenticVisionClient:
    """Agentic Vision 클라이언트

    code_execution 도구를 활용하여 이미지를 동적으로 분석합니다.
    모델이 스스로 Python 코드를 작성하여 zoom, crop 등을 수행합니다.
    """

    def __init__(self, api_key: Optional[str] = None):
        """클라이언트 초기화

        Args:
            api_key: Google API 키 (없으면 설정에서 로드)
        """
        self.api_key = api_key or settings.google_api_key
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")

        # Gemini 클라이언트 초기화
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = settings.gemini_model
        self.agentic_logs: list[AgenticLog] = []

        # 프롬프트 캐시
        self._prompt_cache: dict[str, str] = {}

    def _load_prompt(self, prompt_name: str) -> str:
        """프롬프트 파일 로드

        Args:
            prompt_name: 프롬프트 파일명 (확장자 제외)

        Returns:
            프롬프트 텍스트
        """
        if prompt_name in self._prompt_cache:
            return self._prompt_cache[prompt_name]

        prompt_path = settings.prompts_dir / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        self._prompt_cache[prompt_name] = prompt
        return prompt

    def analyze_page_layout(
        self,
        page_image: bytes,
        page_number: int
    ) -> PageLayout:
        """페이지 레이아웃 분석

        Args:
            page_image: 페이지 이미지 바이트
            page_number: 페이지 번호

        Returns:
            페이지 레이아웃 정보
        """
        prompt = """
이 시험지 페이지의 레이아웃을 분석하세요.

분석 항목:
1. 단 구성 (1단 또는 2단)
2. 문항 번호 패턴 (예: "1.", "[1]", "문1" 등)
3. 페이지 크기 (픽셀)

필요하다면 특정 영역을 확대(zoom)하여 정확히 파악하세요.

JSON 형식으로 응답:
{
    "columns": 2,
    "item_number_pattern": "숫자.",
    "width": 1654,
    "height": 2339
}
"""

        response = self._call_with_code_execution(prompt, page_image)

        # JSON 추출
        json_data = self._extract_json(response)

        return PageLayout(
            page_number=page_number,
            columns=json_data.get("columns", 2),
            width=json_data.get("width", 1654),
            height=json_data.get("height", 2339),
            item_number_pattern=json_data.get("item_number_pattern", "")
        )

    def extract_items_from_page(
        self,
        page_image: bytes,
        page_number: int,
        width: int,
        height: int
    ) -> tuple[list[ExtractedItem], list[PassageInfo]]:
        """페이지에서 지문과 문항 추출

        Args:
            page_image: 페이지 이미지 바이트
            page_number: 페이지 번호
            width: 이미지 너비
            height: 이미지 높이

        Returns:
            (추출된 문항 목록, 공유 지문 목록)
        """
        # 외부 프롬프트 파일 로드
        prompt = self._load_prompt("item_extraction")

        response = self._call_vision_detection(prompt, page_image)

        # 로그 기록
        self._record_agentic_log(page_number, response)

        # JSON 추출
        json_data = self._extract_json(response)

        # 문항 파싱 (정규화 좌표 → 실제 픽셀 변환)
        items = []
        for item_data in json_data.get("items", []):
            box_2d = item_data.get("box_2d", item_data.get("bbox", [0, 0, 1000, 1000]))
            item_num = str(item_data.get("item_number", ""))

            # 정규화 좌표를 실제 픽셀로 변환
            bbox = self._convert_box_2d(box_2d, width, height)

            # passage_ref 처리
            passage_ref = item_data.get("passage_ref")
            item_type = ItemType.PASSAGE_GROUP if passage_ref else ItemType.STANDALONE

            items.append(ExtractedItem(
                item_number=item_num,
                page_number=page_number,
                bbox=bbox,
                item_type=item_type,
                passage_ref=passage_ref,
                confidence=1.0
            ))

        # 지문 파싱
        passages = []
        for passage_data in json_data.get("passages", []):
            # 메인 bbox
            box_2d = passage_data.get("box_2d", passage_data.get("bbox", [0, 0, 1000, 1000]))
            main_bbox = self._convert_box_2d(box_2d, width, height)

            # 다중 bbox (단 넘김 시)
            bbox_list = []
            box_2d_list = passage_data.get("box_2d_list", [])
            for box in box_2d_list:
                bbox_list.append(self._convert_box_2d(box, width, height))

            passages.append(PassageInfo(
                passage_id=passage_data.get("passage_id", ""),
                page_number=page_number,
                bbox=main_bbox,
                bbox_list=bbox_list if bbox_list else [main_bbox],
                item_range=passage_data.get("item_range", "")
            ))

        return items, passages

    def _convert_box_2d(
        self,
        box_2d: list,
        width: int,
        height: int
    ) -> BoundingBox:
        """정규화 좌표(0-1000)를 실제 픽셀로 변환

        Args:
            box_2d: [ymin, xmin, ymax, xmax] 정규화 좌표
            width: 이미지 너비
            height: 이미지 높이

        Returns:
            BoundingBox 객체
        """
        y1 = int(box_2d[0] / 1000 * height)
        x1 = int(box_2d[1] / 1000 * width)
        y2 = int(box_2d[2] / 1000 * height)
        x2 = int(box_2d[3] / 1000 * width)
        return BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)

    def _call_vision_detection(
        self,
        prompt: str,
        image_bytes: bytes
    ) -> str:
        """Gemini Vision API로 객체 감지 호출

        Args:
            prompt: 프롬프트
            image_bytes: 이미지 바이트

        Returns:
            모델 응답 텍스트
        """
        # JSON 응답 형식 지정
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        )

        # 이미지와 프롬프트 구성
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="image/png",
                            data=image_bytes
                        )
                    ),
                    types.Part(text=prompt)
                ]
            )
        ]

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )

        # 응답 텍스트 추출
        return self._extract_response_text(response)

    def _call_with_code_execution(
        self,
        prompt: str,
        image_bytes: bytes
    ) -> str:
        """code_execution 도구와 함께 모델 호출

        Args:
            prompt: 프롬프트
            image_bytes: 이미지 바이트

        Returns:
            모델 응답 텍스트
        """
        # 이미지를 base64로 인코딩
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        # Agentic Vision: code_execution으로 이미지 분석
        config = types.GenerateContentConfig(
            tools=[types.Tool(code_execution=types.ToolCodeExecution())],
            temperature=0.1,
        )

        # 이미지와 프롬프트 구성
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="image/png",
                            data=image_bytes
                        )
                    ),
                    types.Part(text=prompt)
                ]
            )
        ]

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )

        # 응답 텍스트 추출
        return self._extract_response_text(response)

    def _extract_response_text(self, response) -> str:
        """응답에서 텍스트 추출"""
        if not response.candidates:
            return ""

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return ""

        text_parts = []
        for part in candidate.content.parts:
            if hasattr(part, 'text') and part.text:
                text_parts.append(part.text)
            elif hasattr(part, 'executable_code') and part.executable_code:
                # 실행된 코드 기록
                text_parts.append(f"[CODE]\n{part.executable_code.code}\n[/CODE]")
            elif hasattr(part, 'code_execution_result') and part.code_execution_result:
                # 코드 실행 결과 기록
                text_parts.append(f"[RESULT]\n{part.code_execution_result.output}\n[/RESULT]")

        return "\n".join(text_parts)

    def _extract_json(self, text: str) -> dict:
        """텍스트에서 JSON 추출

        API 응답이 배열([...]) 또는 객체({...}) 형태일 수 있음
        """
        text = text.strip()

        # 1. 직접 JSON 파싱 시도
        try:
            parsed = json.loads(text)
            # 배열인 경우 items로 래핑
            if isinstance(parsed, list):
                return {"items": parsed, "passages": []}
            return parsed
        except json.JSONDecodeError:
            pass

        # 2. JSON 블록 패턴 (객체)
        patterns = [
            r'```json\s*(\{[\s\S]*?\})\s*```',
            r'```\s*(\{[\s\S]*?\})\s*```',
            r'(\{[\s\S]*?"items"[\s\S]*?\})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        # 3. JSON 블록 패턴 (배열)
        array_patterns = [
            r'```json\s*(\[[\s\S]*?\])\s*```',
            r'```\s*(\[[\s\S]*?\])\s*```',
        ]

        for pattern in array_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    if isinstance(parsed, list):
                        return {"items": parsed, "passages": []}
                except json.JSONDecodeError:
                    continue

        # 4. 단순 JSON 찾기 (배열 우선)
        try:
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end > start:
                parsed = json.loads(text[start:end])
                if isinstance(parsed, list):
                    return {"items": parsed, "passages": []}
        except json.JSONDecodeError:
            pass

        # 5. 단순 JSON 객체 찾기
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

        return {"items": [], "passages": []}

    def _record_agentic_log(self, page_number: int, response_text: str):
        """Agentic 실행 로그 기록"""
        steps = []

        # Think 단계 추출
        think_patterns = [
            r'(?:생각|Think|분석|계획)[\s:]+(.+?)(?=\[CODE\]|$)',
        ]
        for pattern in think_patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                steps.append(AgenticStep(
                    step_type="think",
                    content=match.strip()[:500]
                ))

        # Act 단계 (코드 실행)
        code_matches = re.findall(r'\[CODE\]([\s\S]*?)\[/CODE\]', response_text)
        for code in code_matches:
            steps.append(AgenticStep(
                step_type="act",
                content=code.strip()[:1000]
            ))

        # Observe 단계 (결과)
        result_matches = re.findall(r'\[RESULT\]([\s\S]*?)\[/RESULT\]', response_text)
        for result in result_matches:
            steps.append(AgenticStep(
                step_type="observe",
                content=result.strip()[:500]
            ))

        log = AgenticLog(
            page_number=page_number,
            steps=steps,
            total_iterations=len(code_matches),
            success=True
        )
        self.agentic_logs.append(log)

    def get_logs(self) -> list[AgenticLog]:
        """실행 로그 반환"""
        return self.agentic_logs

    def clear_logs(self):
        """로그 초기화"""
        self.agentic_logs = []
