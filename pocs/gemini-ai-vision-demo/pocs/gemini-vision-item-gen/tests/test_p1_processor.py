"""P1InputProcessor 테스트"""

import pytest
import tempfile
from pathlib import Path
from PIL import Image

from src.processors.p1_input import P1InputProcessor
from src.core.schemas import InputPack, QTIItem, ImageInfo, VariationType


@pytest.fixture
def processor():
    return P1InputProcessor()


@pytest.fixture
def temp_image():
    """임시 테스트 이미지 생성"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (400, 300), color="white")
        img.save(f.name)
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def sample_iml_file():
    """샘플 IML 파일 생성"""
    content = '''<?xml version="1.0" encoding="utf-8"?>
<문항종류>
    <단위문항>
        <문항 id="TEST001" qt="11" cls2="02" cls3="08" cls4="03" df="02">
            <문제>
                <물음>
                    <단락 justh="0" justv="0" tidt="0" bidt="0">
                        <문자열>테스트 문항입니다.</문자열>
                    </단락>
                </물음>
                <답항>
                    <단락><문자열>선지1</문자열></단락>
                </답항>
                <답항>
                    <단락><문자열>선지2</문자열></단락>
                </답항>
            </문제>
            <정답><단락><문자열>①</문자열></단락></정답>
            <해설><단락><문자열>해설입니다.</문자열></단락></해설>
        </문항>
    </단위문항>
</문항종류>'''

    import os
    fd, temp_path = tempfile.mkstemp(suffix=".iml")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        yield Path(temp_path)
    finally:
        os.close(fd)
        Path(temp_path).unlink(missing_ok=True)


class TestProcessImage:
    """이미지 처리 테스트"""

    def test_process_valid_image(self, processor, temp_image):
        """유효한 이미지 처리"""
        result = processor.process(image_path=temp_image)

        assert isinstance(result, InputPack)
        assert result.is_valid
        assert len(result.images) == 1
        assert result.images[0].is_valid
        assert result.primary_image == str(temp_image)

    def test_process_nonexistent_image(self, processor):
        """존재하지 않는 이미지"""
        result = processor.process(image_path="/nonexistent/image.png")

        assert not result.is_valid
        assert len(result.validation_errors) > 0

    def test_image_info_populated(self, processor, temp_image):
        """이미지 정보 채워짐"""
        result = processor.process(image_path=temp_image)

        img_info = result.images[0]
        assert img_info.width == 400
        assert img_info.height == 300
        assert img_info.format == "PNG"
        assert img_info.file_size > 0


class TestProcessQTI:
    """QTI/IML 처리 테스트"""

    def test_process_valid_qti(self, processor, sample_iml_file):
        """유효한 QTI 파일 처리"""
        result = processor.process(qti_path=sample_iml_file)

        assert isinstance(result, InputPack)
        # QTI만 있고 이미지가 없으면 유효 (텍스트 기반 변형 가능)
        assert result.qti_item is not None
        assert result.qti_item.item_id == "TEST001"

    def test_process_nonexistent_qti(self, processor):
        """존재하지 않는 QTI 파일"""
        result = processor.process(qti_path="/nonexistent/file.iml")

        assert not result.is_valid
        assert "존재하지 않습니다" in str(result.validation_errors)

    def test_qti_metadata_extracted(self, processor, sample_iml_file):
        """QTI에서 메타데이터 추출"""
        result = processor.process(qti_path=sample_iml_file)

        # QTI에서 메타데이터가 InputPack으로 전달
        assert result.subject == "수학"
        assert result.grade == "중2"


class TestProcessCombined:
    """이미지 + QTI 결합 처리 테스트"""

    def test_process_image_with_qti(self, processor, temp_image, sample_iml_file):
        """이미지와 QTI 함께 처리"""
        result = processor.process(
            image_path=temp_image,
            qti_path=sample_iml_file,
        )

        assert result.is_valid
        assert len(result.images) == 1
        assert result.qti_item is not None

    def test_metadata_override(self, processor, temp_image, sample_iml_file):
        """메타데이터 오버라이드"""
        result = processor.process(
            image_path=temp_image,
            qti_path=sample_iml_file,
            metadata={"subject": "영어", "difficulty": "hard"},
        )

        # 명시적 메타데이터가 QTI보다 우선
        assert result.subject == "영어"
        assert result.difficulty == "hard"


class TestProcessMetadata:
    """메타데이터 처리 테스트"""

    def test_process_with_metadata(self, processor, temp_image):
        """메타데이터 포함 처리"""
        metadata = {
            "subject": "수학",
            "grade": "고1",
            "difficulty": "hard",
        }

        result = processor.process(
            image_path=temp_image,
            metadata=metadata,
        )

        assert result.subject == "수학"
        assert result.grade == "고1"
        assert result.difficulty == "hard"

    def test_metadata_normalization(self, processor, temp_image):
        """메타데이터 정규화"""
        metadata = {
            "subject": "03",  # 코드
            "difficulty": "상",  # 한글
        }

        result = processor.process(
            image_path=temp_image,
            metadata=metadata,
        )

        assert result.subject == "수학"  # 정규화됨
        assert result.difficulty == "hard"  # 정규화됨


class TestProcessVariationType:
    """변형 유형 처리 테스트"""

    def test_valid_variation_type(self, processor, temp_image):
        """유효한 변형 유형"""
        result = processor.process(
            image_path=temp_image,
            variation_type="similar",
        )

        assert result.variation_type == VariationType.SIMILAR

    def test_invalid_variation_type(self, processor, temp_image):
        """유효하지 않은 변형 유형"""
        result = processor.process(
            image_path=temp_image,
            variation_type="invalid_type",
        )

        # 오류는 기록되지만 처리는 계속됨
        assert "유효하지 않은 변형 유형" in str(result.validation_errors)


class TestValidation:
    """유효성 검증 테스트"""

    def test_no_input_invalid(self, processor):
        """입력 없음 - 유효하지 않음"""
        result = processor.process()

        assert not result.is_valid
        assert "필요합니다" in str(result.validation_errors)

    def test_request_id_generated(self, processor, temp_image):
        """요청 ID 생성"""
        result = processor.process(image_path=temp_image)

        assert result.request_id
        assert result.request_id.startswith("REQ-")

    def test_validate_input_pack(self, processor, temp_image):
        """InputPack 유효성 재검증"""
        input_pack = processor.process(image_path=temp_image)

        is_valid, errors = processor.validate_input_pack(input_pack)

        assert is_valid
        assert len(errors) == 0


class TestCurriculumMeta:
    """교육과정 메타데이터 테스트"""

    def test_curriculum_meta_populated(self, processor, sample_iml_file):
        """교육과정 메타데이터 채워짐"""
        result = processor.process(qti_path=sample_iml_file)

        assert "subject_code" in result.curriculum_meta
        assert "grade_code" in result.curriculum_meta
        assert "school_level" in result.curriculum_meta
        assert result.curriculum_meta["school_level"] == "중학교"


class TestSaveAndLoad:
    """저장 및 로드 테스트"""

    def test_save_input_pack(self, processor, temp_image):
        """InputPack 저장"""
        input_pack = processor.process(
            image_path=temp_image,
            metadata={"subject": "수학", "difficulty": "hard"},
        )

        # 임시 디렉토리에 저장
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            saved_path = processor.save_input_pack(input_pack, Path(tmpdir))

            assert saved_path.exists()
            assert saved_path.name == f"{input_pack.request_id}.json"

            # 파일 내용 확인
            import json
            with open(saved_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["request_id"] == input_pack.request_id
            assert data["subject"] == "수학"
            assert data["difficulty"] == "hard"

    def test_load_input_pack(self, processor, temp_image):
        """InputPack 로드"""
        original = processor.process(
            image_path=temp_image,
            metadata={"subject": "영어", "grade": "고1"},
        )

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            saved_path = processor.save_input_pack(original, Path(tmpdir))

            # 로드
            loaded = processor.load_input_pack(saved_path)

            assert loaded is not None
            assert loaded.request_id == original.request_id
            assert loaded.subject == original.subject
            assert loaded.grade == original.grade
            assert loaded.is_valid == original.is_valid

    def test_load_nonexistent_file(self, processor):
        """존재하지 않는 파일 로드"""
        result = processor.load_input_pack(Path("/nonexistent/file.json"))
        assert result is None
