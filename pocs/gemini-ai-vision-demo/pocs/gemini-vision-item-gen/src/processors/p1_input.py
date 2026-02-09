"""P1-INPUT 단계 처리기

입력 검증 및 정규화를 수행하는 P1-INPUT 단계 통합 처리기.
이미지, QTI/IML 문항, 메타데이터를 처리하여 InputPack 생성.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config import settings
from ..core.schemas import (
    InputPack,
    QTIItem,
    ImageInfo,
    ItemType,
    VariationType,
)
from ..parsers.qti_parser import QTIParser
from ..utils.image_utils import ImageProcessor
from ..utils.metadata_normalizer import MetadataNormalizer


class P1InputProcessor:
    """P1-INPUT 단계 통합 처리기

    입력 소스:
    1. 이미지 경로 + 메타데이터
    2. QTI/IML XML 파일
    3. 이미지 + QTI/IML (원본 문항 기반 변형)

    출력:
    - InputPack: 검증된 입력 데이터 패키지
    """

    def __init__(self):
        self.image_processor = ImageProcessor()
        self.qti_parser = QTIParser()
        self.metadata_normalizer = MetadataNormalizer()

    def process(
        self,
        image_path: Optional[str | Path] = None,
        qti_path: Optional[str | Path] = None,
        metadata: Optional[dict] = None,
        variation_type: Optional[str] = None,
    ) -> InputPack:
        """P1-INPUT 처리

        여러 입력 방식 지원:
        1. 이미지 + 메타데이터: 이미지 기반 문항 생성
        2. QTI/IML: 원본 문항 기반 변형 생성
        3. 이미지 + QTI/IML: 원본 문항 참조하여 이미지 기반 생성

        Args:
            image_path: 입력 이미지 경로
            qti_path: QTI/IML XML 파일 경로
            metadata: 메타데이터 딕셔너리 (subject, grade, difficulty 등)
            variation_type: 변형 유형 (similar, diff_up 등)

        Returns:
            InputPack 객체
        """
        request_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        validation_errors: list[str] = []

        # 입력 검증
        if not image_path and not qti_path:
            validation_errors.append("이미지 경로 또는 QTI 파일 경로가 필요합니다")
            return self._create_invalid_pack(request_id, validation_errors)

        # QTI/IML 파싱 (있는 경우)
        qti_item: Optional[QTIItem] = None
        if qti_path:
            qti_path = Path(qti_path)
            qti_item = self._process_qti(qti_path, validation_errors)

        # 이미지 처리 (있는 경우)
        images: list[ImageInfo] = []
        primary_image: Optional[str] = None
        if image_path:
            image_path = Path(image_path)
            image_info = self._process_image(image_path, validation_errors)
            if image_info:
                images.append(image_info)
                if image_info.is_valid:
                    primary_image = str(image_path)

        # QTI에서 이미지 추출 (이미지 경로가 없고 QTI에 이미지가 있는 경우)
        if not images and qti_item and qti_item.images:
            images = self._process_qti_images(qti_item, qti_path, validation_errors)
            if images:
                # 첫 번째 유효한 이미지를 primary로
                for img in images:
                    if img.is_valid:
                        primary_image = img.path
                        break

        # 메타데이터 정규화
        normalized_meta = self._normalize_metadata(metadata, qti_item)

        # 변형 유형 처리
        var_type: Optional[VariationType] = None
        if variation_type:
            try:
                var_type = VariationType(variation_type)
            except ValueError:
                validation_errors.append(f"유효하지 않은 변형 유형: {variation_type}")

        # 문항 유형 처리
        item_type: Optional[ItemType] = None
        if metadata and "item_type" in metadata:
            try:
                item_type = ItemType(metadata["item_type"])
            except ValueError:
                pass  # 무시

        # 유효성 판단
        is_valid = len(validation_errors) == 0

        # 이미지 없음 경고 (필수는 아님)
        if not images:
            # QTI만 있는 경우 텍스트 기반 변형 가능
            if not qti_item:
                validation_errors.append("처리할 이미지가 없습니다")
                is_valid = False

        return InputPack(
            request_id=request_id,
            qti_item=qti_item,
            images=images,
            primary_image=primary_image,
            subject=normalized_meta.get("subject", ""),
            grade=normalized_meta.get("grade", ""),
            difficulty=normalized_meta.get("difficulty", "medium"),
            item_type=item_type,
            variation_type=var_type,
            curriculum_meta={
                "subject_code": normalized_meta.get("subject_code", ""),
                "grade_code": normalized_meta.get("grade_code", ""),
                "school_level": normalized_meta.get("school_level", ""),
                "school_level_code": normalized_meta.get("school_level_code", ""),
                "question_type": normalized_meta.get("question_type", ""),
            },
            is_valid=is_valid,
            validation_errors=validation_errors,
            created_at=datetime.now(),
        )

    def _process_image(
        self, image_path: Path, errors: list[str]
    ) -> Optional[ImageInfo]:
        """단일 이미지 처리

        Args:
            image_path: 이미지 경로
            errors: 오류 메시지 누적 리스트

        Returns:
            ImageInfo 또는 None
        """
        if not image_path.exists():
            errors.append(f"이미지 파일이 존재하지 않습니다: {image_path}")
            return ImageInfo(
                path=str(image_path),
                format="",
                width=0,
                height=0,
                file_size=0,
                is_valid=False,
                validation_issues=["파일이 존재하지 않음"],
            )

        # 이미지 검증
        is_valid, issues = self.image_processor.validate_image(image_path)

        # 이미지 정보 조회
        try:
            info = self.image_processor.get_image_info(image_path)
            return ImageInfo(
                path=str(image_path),
                format=info.get("format", ""),
                width=info.get("width", 0),
                height=info.get("height", 0),
                file_size=info.get("file_size_bytes", 0),
                is_valid=is_valid,
                validation_issues=issues,
            )
        except Exception as e:
            errors.append(f"이미지 정보 조회 실패: {e}")
            return ImageInfo(
                path=str(image_path),
                format="",
                width=0,
                height=0,
                file_size=0,
                is_valid=False,
                validation_issues=[str(e)],
            )

    def _process_qti(
        self, qti_path: Path, errors: list[str]
    ) -> Optional[QTIItem]:
        """QTI/IML 파일 처리

        Args:
            qti_path: QTI/IML 파일 경로
            errors: 오류 메시지 누적 리스트

        Returns:
            QTIItem 또는 None
        """
        if not qti_path.exists():
            errors.append(f"QTI 파일이 존재하지 않습니다: {qti_path}")
            return None

        qti_item = self.qti_parser.parse(qti_path)
        if qti_item is None:
            errors.append(f"QTI 파일 파싱 실패: {qti_path}")

        return qti_item

    def _process_qti_images(
        self,
        qti_item: QTIItem,
        qti_path: Optional[Path],
        errors: list[str],
    ) -> list[ImageInfo]:
        """QTI 문항의 이미지 처리

        Args:
            qti_item: 파싱된 QTI 문항
            qti_path: QTI 파일 경로 (이미지 상대경로 해석용)
            errors: 오류 메시지 누적 리스트

        Returns:
            ImageInfo 리스트
        """
        images: list[ImageInfo] = []
        base_dir = qti_path.parent if qti_path else Path(".")

        for img_rel_path in qti_item.images:
            # 절대 경로 구성
            img_path = base_dir / img_rel_path
            if not img_path.exists():
                # item_id 하위에 있을 수 있음
                img_path = base_dir / qti_item.item_id / img_rel_path

            image_info = self._process_image(img_path, errors)
            if image_info:
                images.append(image_info)

        return images

    def _normalize_metadata(
        self,
        metadata: Optional[dict],
        qti_item: Optional[QTIItem],
    ) -> dict:
        """메타데이터 정규화

        입력 메타데이터와 QTI 문항 정보를 병합하여 정규화.
        명시적 메타데이터가 QTI 정보보다 우선.

        Args:
            metadata: 입력 메타데이터
            qti_item: 파싱된 QTI 문항 (옵션)

        Returns:
            정규화된 메타데이터
        """
        # QTI에서 기본값 추출
        base_meta = {}
        if qti_item:
            base_meta = {
                "subject": qti_item.subject,
                "subject_code": qti_item.subject_code,
                "grade": qti_item.grade,
                "grade_code": qti_item.grade_code,
                "school_level": qti_item.school_level,
                "school_level_code": qti_item.school_level_code,
                "difficulty": qti_item.difficulty,
                "question_type": qti_item.question_type,
            }

        # 입력 메타데이터로 덮어쓰기
        if metadata:
            for key, value in metadata.items():
                if value:  # 빈 값이 아닌 경우만
                    base_meta[key] = value

        # 정규화
        return self.metadata_normalizer.normalize(base_meta)

    def _create_invalid_pack(
        self, request_id: str, errors: list[str]
    ) -> InputPack:
        """유효하지 않은 InputPack 생성

        Args:
            request_id: 요청 ID
            errors: 오류 메시지 목록

        Returns:
            is_valid=False인 InputPack
        """
        return InputPack(
            request_id=request_id,
            qti_item=None,
            images=[],
            primary_image=None,
            subject="",
            grade="",
            difficulty="medium",
            item_type=None,
            variation_type=None,
            curriculum_meta={},
            is_valid=False,
            validation_errors=errors,
            created_at=datetime.now(),
        )

    def validate_input_pack(self, input_pack: InputPack) -> tuple[bool, list[str]]:
        """InputPack 유효성 재검증

        Args:
            input_pack: 검증할 InputPack

        Returns:
            (유효 여부, 오류 메시지 목록)
        """
        errors: list[str] = list(input_pack.validation_errors)

        # 이미지 또는 QTI 필수
        if not input_pack.images and not input_pack.qti_item:
            errors.append("이미지 또는 원본 문항이 필요합니다")

        # 이미지 유효성
        for img in input_pack.images:
            if not img.is_valid:
                errors.append(f"유효하지 않은 이미지: {img.path}")

        # 과목 권장
        if not input_pack.subject:
            # 경고만 (필수는 아님)
            pass

        return len(errors) == 0, errors

    def save_input_pack(
        self,
        input_pack: InputPack,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """InputPack을 JSON 파일로 저장

        Args:
            input_pack: 저장할 InputPack
            output_dir: 출력 디렉토리 (기본: output/p1_input)

        Returns:
            저장된 파일 경로
        """
        output_dir = output_dir or settings.output_dir / "p1_input"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{input_pack.request_id}.json"
        filepath = output_dir / filename

        # Pydantic 모델을 JSON으로 직렬화
        data = input_pack.model_dump(mode="json")

        # Path 객체를 문자열로 변환
        if input_pack.qti_item and input_pack.qti_item.source_path:
            data["qti_item"]["source_path"] = str(input_pack.qti_item.source_path)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return filepath

    def load_input_pack(self, filepath: Path) -> Optional[InputPack]:
        """JSON 파일에서 InputPack 로드

        Args:
            filepath: JSON 파일 경로

        Returns:
            로드된 InputPack 또는 None
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            return InputPack.model_validate(data)
        except Exception as e:
            print(f"InputPack 로드 실패: {e}")
            return None
