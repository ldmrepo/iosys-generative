"""문항 콘텐츠 파서

크롭된 문항 이미지에서 구조화된 콘텐츠를 추출합니다.
"""

import json
import re
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from ..core.config import settings
from ..core.schemas import (
    ContentBlock, ContentType, Choice, ParsedItem, ExtractedItem
)


class ItemParser:
    """문항 콘텐츠 파서

    Gemini Vision을 사용하여 문항 이미지에서
    텍스트, 수식, 이미지, 표 등을 구조화된 형태로 추출합니다.
    """

    def __init__(self, api_key: Optional[str] = None):
        """파서 초기화

        Args:
            api_key: Google API 키 (없으면 설정에서 로드)
        """
        self.api_key = api_key or settings.google_api_key
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = settings.gemini_model
        self._prompt_cache: dict[str, str] = {}

    def _load_prompt(self, prompt_name: str) -> str:
        """프롬프트 파일 로드"""
        if prompt_name in self._prompt_cache:
            return self._prompt_cache[prompt_name]

        prompt_path = settings.prompts_dir / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        self._prompt_cache[prompt_name] = prompt
        return prompt

    def parse_item(self, image_path: Path) -> ParsedItem:
        """문항 이미지 파싱

        Args:
            image_path: 크롭된 문항 이미지 경로

        Returns:
            파싱된 문항 구조
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

        # 이미지 로드
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # 프롬프트 로드
        prompt = self._load_prompt("item_parsing")

        # Gemini Vision 호출
        response = self._call_vision(prompt, image_bytes)

        # JSON 파싱
        parsed_data = self._extract_json(response)

        # ParsedItem 생성
        return self._build_parsed_item(parsed_data, str(image_path))

    def parse_items(self, items: list[ExtractedItem]) -> list[ParsedItem]:
        """여러 문항 이미지 파싱

        Args:
            items: 추출된 문항 목록 (image_path 포함)

        Returns:
            파싱된 문항 목록
        """
        parsed_items = []

        for item in items:
            if not item.image_path:
                print(f"  문항 {item.item_number}: 이미지 경로 없음, 스킵")
                continue

            try:
                parsed = self.parse_item(Path(item.image_path))
                parsed_items.append(parsed)

                # 콘텐츠 요약 출력
                text_count = sum(1 for b in parsed.question if b.type == ContentType.TEXT)
                math_count = sum(1 for b in parsed.question if b.type == ContentType.MATH)
                image_count = sum(1 for b in parsed.question if b.type == ContentType.IMAGE)

                print(f"  문항 {item.item_number}: "
                      f"텍스트 {text_count}, 수식 {math_count}, 이미지 {image_count}, "
                      f"선택지 {len(parsed.choices)}개")

            except Exception as e:
                print(f"  문항 {item.item_number}: 파싱 실패 - {e}")

        return parsed_items

    def _call_vision(self, prompt: str, image_bytes: bytes) -> str:
        """Gemini Vision API 호출"""
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    types.Part.from_text(text=prompt),
                ],
            )
        ]

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config,
        )

        return response.text

    def _extract_json(self, response_text: str) -> dict:
        """응답에서 JSON 추출"""
        # JSON 블록 추출 시도
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response_text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"응답: {response_text[:500]}")
            return {}

    def _build_parsed_item(self, data: dict, source_image: str) -> ParsedItem:
        """딕셔너리에서 ParsedItem 생성"""
        # 질문 콘텐츠 블록
        question_blocks = []
        for block in data.get("question", []):
            question_blocks.append(ContentBlock(
                type=ContentType(block.get("type", "text")),
                value=block.get("value", ""),
                description=block.get("description"),
                box_2d=block.get("box_2d")
            ))

        # 선택지
        choices = []
        for choice_data in data.get("choices", []):
            choice_content = []
            for block in choice_data.get("content", []):
                choice_content.append(ContentBlock(
                    type=ContentType(block.get("type", "text")),
                    value=block.get("value", ""),
                    description=block.get("description"),
                    box_2d=block.get("box_2d")
                ))
            choices.append(Choice(
                label=choice_data.get("label", ""),
                content=choice_content,
                box_2d=choice_data.get("box_2d")
            ))

        # 보기 박스 콘텐츠
        boxed_content = []
        for block in data.get("boxed_content", []):
            boxed_content.append(ContentBlock(
                type=ContentType(block.get("type", "text")),
                value=block.get("value", ""),
                description=block.get("description"),
                box_2d=block.get("box_2d")
            ))

        return ParsedItem(
            item_number=data.get("item_number", ""),
            question=question_blocks,
            choices=choices,
            has_boxed_text=data.get("has_boxed_text", False),
            boxed_content=boxed_content,
            boxed_area=data.get("boxed_area"),
            source_image=source_image
        )

    def save_parsed_items(
        self,
        parsed_items: list[ParsedItem],
        output_path: Path
    ) -> Path:
        """파싱 결과 저장

        Args:
            parsed_items: 파싱된 문항 목록
            output_path: 출력 파일 경로

        Returns:
            저장된 파일 경로
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # JSON 직렬화
        data = [item.model_dump() for item in parsed_items]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path
