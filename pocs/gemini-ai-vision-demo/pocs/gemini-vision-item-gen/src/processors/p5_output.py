"""P5-OUTPUT 처리기

v3.0.0: 모델 기반 End-to-End 파이프라인
- 하드코딩된 정규식/키워드 로직 제거
- LLM이 생성한 visual_spec.image_prompt를 이미지 생성 모델에 직접 전달
- 문항 내용에 맞는 이미지 생성
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config import settings
from ..core.schemas import (
    ItemQuestion,
    ItemType,
    InputPack,
    ImagePosition,
    ImagePositionInfo,
    VisualSpec,
    GeneratedImage,
)
from ..agents.nano_banana_client import NanoBananaClient


class P5OutputProcessor:
    """P5-OUTPUT 처리기

    v3.0.0: 모델 기반 이미지 생성
    - LLM이 생성한 visual_spec.image_prompt를 직접 사용
    - 하드코딩된 정규식/키워드 로직 제거
    - 문항 내용에 맞는 이미지 생성
    """

    def __init__(self, nano_banana_client: Optional[NanoBananaClient] = None):
        """
        Args:
            nano_banana_client: Nano Banana Pro 클라이언트 (None이면 생성 비활성화)
        """
        self.nano_banana_client = nano_banana_client

    def process(
        self,
        item: ItemQuestion,
        input_pack: Optional[InputPack] = None,
        generate_image: bool = True,
        output_format: str = "json"
    ) -> dict:
        """
        P5-OUTPUT 처리

        Args:
            item: 처리할 문항
            input_pack: P1-INPUT 결과 (이미지 위치 정보 포함)
            generate_image: 이미지 생성 여부
            output_format: 출력 포맷 (json, qti, iml)

        Returns:
            처리 결과 딕셔너리
        """
        result = {
            "item_id": item.item_id,
            "success": False,
            "generated_images": [],
            "output_path": None,
            "image_positions": [],
        }

        # 1. 이미지 위치 정보 결정
        image_positions = self._determine_image_positions(item, input_pack)
        result["image_positions"] = [pos.model_dump() for pos in image_positions]

        # 2. 이미지 생성 (필요한 경우)
        if generate_image and self.nano_banana_client:
            generated_images = self._generate_images(item, image_positions)
            result["generated_images"] = generated_images

            # 문항에 생성된 이미지 추가
            if generated_images:
                item.generated_image = GeneratedImage(
                    image_id=generated_images[0]["image_id"],
                    path=generated_images[0]["path"],
                    format="PNG",
                    resolution=settings.image_resolution,
                    visual_spec=item.visual_spec,
                    generation_model=settings.nano_banana_model,
                )

        # 3. 출력 포맷 생성
        if output_format == "json":
            output_data = self._format_as_json(item, image_positions)
        elif output_format == "qti":
            output_data = self._format_as_qti(item, image_positions)
        elif output_format == "iml":
            output_data = self._format_as_iml(item, image_positions)
        else:
            output_data = item.model_dump(mode="json")

        result["output_data"] = output_data
        result["success"] = True

        return result

    def _determine_image_positions(
        self,
        item: ItemQuestion,
        input_pack: Optional[InputPack]
    ) -> list[ImagePositionInfo]:
        """이미지 위치 결정

        원본 InputPack의 위치 정보를 우선 사용하고,
        없으면 문항 유형과 내용을 분석하여 결정합니다.
        """
        # InputPack에서 위치 정보 가져오기
        if input_pack and input_pack.image_positions:
            return input_pack.image_positions

        # 기본 위치 결정 (문항 유형 기반)
        positions = []

        if item.source_image:
            # 기본: 문제 본문 후에 이미지 배치
            default_position = ImagePosition.AFTER_STEM

            # 문항 유형에 따른 위치 조정
            if item.item_type == ItemType.GRAPH:
                # 그래프는 문제 본문 후
                default_position = ImagePosition.AFTER_STEM
            elif item.item_type == ItemType.GEOMETRY:
                # 도형은 문제 본문 전 (시각 참조 우선)
                default_position = ImagePosition.BEFORE_STEM
            elif item.item_type == ItemType.MEASUREMENT:
                # 측정은 인라인
                default_position = ImagePosition.INLINE

            positions.append(ImagePositionInfo(
                image_path=item.source_image,
                position=default_position,
            ))

        return positions

    def _generate_images(
        self,
        item: ItemQuestion,
        positions: list[ImagePositionInfo]
    ) -> list[dict]:
        """v3.0.0: LLM의 image_prompt를 이미지 생성 모델에 전달

        Args:
            item: 문항
            positions: 이미지 위치 정보

        Returns:
            생성된 이미지 정보 목록
        """
        if not self.nano_banana_client:
            return []

        generated = []

        # v3.0.0: LLM이 생성한 visual_spec 사용
        visual_spec = self._get_visual_spec(item)

        if not visual_spec or not visual_spec.required:
            return []

        # visual_spec이 없거나 image_prompt가 비어있으면 생성 불필요
        if not visual_spec.image_prompt:
            return []

        try:
            # v3.0.0: LLM이 생성한 프롬프트 직접 사용
            prompt = visual_spec.image_prompt

            # 스타일 가이드 추가
            if visual_spec.style_guidance:
                prompt += f"\n\n스타일: {visual_spec.style_guidance}"

            # 과목/맥락 정보 추가
            if visual_spec.subject_context:
                prompt += f"\n과목/맥락: {visual_spec.subject_context}"

            # 공통 스타일 지시 추가
            prompt += """

[공통 스타일 지시]
- 교과서/시험지에 적합한 깔끔한 스타일
- 흰색 또는 밝은 배경
- 문제 텍스트나 질문 텍스트는 포함하지 마세요
- 시각 자료(그래프, 도형, 표지판, 다이어그램 등)만 생성하세요
- 한글과 수학 기호는 정확하게 렌더링하세요"""

            # Nano Banana Pro로 이미지 생성
            image_bytes = self.nano_banana_client.generate_from_prompt(
                prompt=prompt,
                size=settings.image_resolution
            )

            # 저장
            image_id = f"IMG-{uuid.uuid4().hex[:8].upper()}"
            output_path = settings.output_dir / "p5_output" / f"{image_id}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.nano_banana_client.save_image(image_bytes, output_path)

            # 위치 정보와 연결
            position = positions[0].position if positions else ImagePosition.AFTER_STEM

            generated.append({
                "image_id": image_id,
                "path": str(output_path),
                "position": position.value,
                "visual_spec": visual_spec.model_dump(),
                "prompt_used": prompt,  # 디버깅용
            })

        except Exception as e:
            # 이미지 생성 실패는 경고만 (문항은 유지)
            print(f"[P5-OUTPUT] 이미지 생성 실패: {e}")

        return generated

    def _get_visual_spec(self, item: ItemQuestion) -> Optional[VisualSpec]:
        """v3.0.0: LLM이 생성한 visual_spec 반환

        Args:
            item: 문항

        Returns:
            VisualSpec 또는 None
        """
        # LLM이 생성한 visual_spec이 있으면 그대로 사용
        if item.visual_spec and item.visual_spec.image_prompt:
            return item.visual_spec

        # visual_spec이 없으면 이미지 생성 불필요
        return None

    # =========================================================================
    # v3.0.0: 아래의 하드코딩된 메서드들은 제거됨
    # - _create_visual_spec() -> _get_visual_spec()로 대체
    # - _infer_subject_from_evidence() -> LLM이 subject_context 출력
    # - _extract_visual_info_from_evidence() -> LLM이 image_prompt 출력
    # - _create_graph_visual_spec() -> 삭제
    # - _create_geometry_visual_spec() -> 삭제
    # - _create_measurement_visual_spec() -> 삭제
    # - _create_default_visual_spec() -> 삭제
    # - _create_math_visual_spec() -> 삭제
    # - _create_science_visual_spec() -> 삭제
    # - _create_korean_visual_spec() -> 삭제
    # - _create_english_visual_spec() -> 삭제
    # - _create_history_visual_spec() -> 삭제
    # - _create_social_visual_spec() -> 삭제
    # =========================================================================

    def _format_as_json(
        self,
        item: ItemQuestion,
        positions: list[ImagePositionInfo]
    ) -> dict:
        """JSON 포맷 출력"""
        output = item.model_dump(mode="json")
        output["image_positions"] = [pos.model_dump() for pos in positions]
        return output

    def _format_as_qti(
        self,
        item: ItemQuestion,
        positions: list[ImagePositionInfo]
    ) -> str:
        """QTI 2.1 포맷 출력"""
        # 이미지 요소 생성
        image_elements = []
        for pos in positions:
            img_element = f'<img src="{pos.image_path}" alt="문항 이미지"/>'
            image_elements.append((pos.position, img_element))

        # 선지 생성
        choices_xml = ""
        for choice in item.choices:
            is_correct = "true" if choice.label == item.correct_answer else "false"
            choices_xml += f"""
            <simpleChoice identifier="{choice.label}" fixed="false">
                {choice.text}
            </simpleChoice>"""

        # 본문 구성 (이미지 위치 반영)
        stem_content = item.stem
        before_images = [img for pos, img in image_elements if pos == ImagePosition.BEFORE_STEM]
        after_images = [img for pos, img in image_elements if pos == ImagePosition.AFTER_STEM]

        before_content = "\n".join(before_images)
        after_content = "\n".join(after_images)

        qti_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"
    identifier="{item.item_id}"
    title="{item.item_id}"
    adaptive="false"
    timeDependent="false">

    <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="identifier">
        <correctResponse>
            <value>{item.correct_answer}</value>
        </correctResponse>
    </responseDeclaration>

    <itemBody>
        {before_content}
        <p>{stem_content}</p>
        {after_content}
        <choiceInteraction responseIdentifier="RESPONSE" shuffle="false" maxChoices="1">
            {choices_xml}
        </choiceInteraction>
    </itemBody>

    <modalFeedback outcomeIdentifier="FEEDBACK" identifier="correct" showHide="show">
        <p>{item.explanation}</p>
    </modalFeedback>
</assessmentItem>"""

        return qti_xml

    def _format_as_iml(
        self,
        item: ItemQuestion,
        positions: list[ImagePositionInfo]
    ) -> str:
        """IML 포맷 출력"""
        # 이미지 요소 생성
        image_elements = []
        for pos in positions:
            img_element = f'<IMG src="{pos.image_path}"/>'
            image_elements.append((pos.position, img_element))

        # 선지 생성
        choices_iml = ""
        for i, choice in enumerate(item.choices, 1):
            is_correct = choice.label == item.correct_answer
            correct_attr = f' 정오="{1 if is_correct else 0}"'
            choices_iml += f'<선지 순서="{i}"{correct_attr}>{choice.text}</선지>\n'

        # 본문 구성
        before_images = [img for pos, img in image_elements if pos == ImagePosition.BEFORE_STEM]
        after_images = [img for pos, img in image_elements if pos == ImagePosition.AFTER_STEM]

        before_content = "\n".join(before_images)
        after_content = "\n".join(after_images)

        iml_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<문항 id="{item.item_id}">
    <물음>
        {before_content}
        <P>{item.stem}</P>
        {after_content}
    </물음>
    <답지>
        {choices_iml}
    </답지>
    <정답>{item.correct_answer}</정답>
    <해설>{item.explanation}</해설>
</문항>"""

        return iml_xml

    def save_output(
        self,
        item: ItemQuestion,
        output_data: dict | str,
        output_format: str = "json"
    ) -> Path:
        """출력 파일 저장

        Args:
            item: 문항
            output_data: 출력 데이터
            output_format: 출력 포맷

        Returns:
            저장된 파일 경로
        """
        output_dir = settings.output_dir / "p5_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 결정
        ext_map = {"json": ".json", "qti": ".xml", "iml": ".xml"}
        ext = ext_map.get(output_format, ".json")
        filename = f"{item.item_id}{ext}"
        filepath = output_dir / filename

        # 저장
        if output_format == "json":
            import json
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(output_data)

        return filepath

    def process_batch(
        self,
        items: list[ItemQuestion],
        input_packs: Optional[list[InputPack]] = None,
        generate_images: bool = True,
        output_format: str = "json"
    ) -> list[dict]:
        """여러 문항 일괄 처리"""
        results = []

        for i, item in enumerate(items):
            input_pack = input_packs[i] if input_packs and i < len(input_packs) else None
            result = self.process(item, input_pack, generate_images, output_format)
            results.append(result)

        return results
