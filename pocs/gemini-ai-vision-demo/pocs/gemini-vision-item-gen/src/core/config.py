"""설정 관리 모듈"""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# 과목별 설정 (SUBJECT_CONFIGS)
# ============================================================================

SUBJECT_CONFIGS = {
    "math": {
        "name": "수학",
        "code": "MA",
        "validators": ["quality", "consistency", "calc"],
        "cross_validation_level": 1,
        "prompt_template": """이 이미지는 수학 문제와 관련된 시각 자료입니다.

**분석 지시:**
1. 수식, 그래프, 도형 등 수학적 요소를 정확히 파악하세요.
2. 수치와 기호를 정확히 읽으세요.
3. 필요시 특정 영역을 확대하여 판독하세요.

**출력 요구사항:**
이미지에서 확인 가능한 수학적 정보만을 사용하여 객관식 문항을 생성하세요.
정확한 계산이 요구되는 경우, 계산 과정을 해설에 포함하세요.

{format_instructions}""",
        "item_types": ["graph", "geometry", "measurement"],
        "difficulty_weights": {"easy": 0.2, "medium": 0.5, "hard": 0.3},
    },
    "science": {
        "name": "과학",
        "code": "SC",
        "validators": ["quality", "consistency", "calc", "fact"],
        "cross_validation_level": 2,
        "prompt_template": """이 이미지는 과학 실험/관측 결과입니다.

**분석 지시:**
1. 실험 장치, 측정값, 그래프를 정확히 파악하세요.
2. 단위와 스케일을 확인하세요.
3. 과학적 원리와 연결하여 분석하세요.

**출력 요구사항:**
이미지에서 관찰 가능한 과학적 사실에 기반한 문항을 생성하세요.
과학적 원리 적용이 필요한 경우, 해설에 명확히 설명하세요.

{format_instructions}""",
        "item_types": ["graph", "measurement"],
        "difficulty_weights": {"easy": 0.25, "medium": 0.5, "hard": 0.25},
    },
    "social": {
        "name": "사회",
        "code": "SO",
        "validators": ["quality", "consistency", "fact", "safety"],
        "cross_validation_level": 2,
        "prompt_template": """이 이미지는 사회/역사 관련 자료입니다.

**분석 지시:**
1. 지도, 그래프, 사진, 역사 자료 등의 유형을 파악하세요.
2. 시대적 맥락과 지리적 위치를 확인하세요.
3. 객관적 사실만을 추출하세요.

**출력 요구사항:**
이미지에서 확인 가능한 사회적/역사적 사실에 기반한 문항을 생성하세요.
정치적 편향이나 가치 판단을 피하세요.

{format_instructions}""",
        "item_types": ["graph"],
        "difficulty_weights": {"easy": 0.3, "medium": 0.45, "hard": 0.25},
    },
    "history": {
        "name": "역사",
        "code": "HI",
        "validators": ["quality", "consistency", "fact", "safety"],
        "cross_validation_level": 3,  # 민감 주제 가능
        "prompt_template": """이 이미지는 역사적 자료입니다.

**분석 지시:**
1. 시대, 인물, 사건을 정확히 파악하세요.
2. 자료의 출처와 맥락을 고려하세요.
3. 역사적 사실과 해석을 구분하세요.

**출력 요구사항:**
검증 가능한 역사적 사실에 기반한 문항을 생성하세요.
논쟁적인 해석은 피하고 객관적 사실에 집중하세요.

{format_instructions}""",
        "item_types": ["graph"],
        "difficulty_weights": {"easy": 0.2, "medium": 0.5, "hard": 0.3},
    },
    "korean": {
        "name": "국어",
        "code": "KO",
        "validators": ["quality", "consistency", "safety"],
        "cross_validation_level": 1,
        "prompt_template": """이 이미지는 국어 관련 시각 자료입니다.

**분석 지시:**
1. 텍스트, 도표, 그래프 등의 내용을 정확히 파악하세요.
2. 맞춤법과 문법에 주의하세요.
3. 문맥과 의미를 파악하세요.

**출력 요구사항:**
이미지의 내용을 바탕으로 독해력, 어휘력, 문법 관련 문항을 생성하세요.

{format_instructions}""",
        "item_types": ["graph"],
        "difficulty_weights": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
    },
    "english": {
        "name": "영어",
        "code": "EN",
        "validators": ["quality", "consistency"],
        "cross_validation_level": 1,
        "prompt_template": """This image is related to an English language exercise.

**Analysis Instructions:**
1. Identify texts, charts, or visual elements.
2. Note vocabulary levels and grammar structures.
3. Consider the context and meaning.

**Output Requirements:**
Create a multiple-choice item based on the visual content.
Focus on reading comprehension, vocabulary, or grammar.

{format_instructions}""",
        "item_types": ["graph"],
        "difficulty_weights": {"easy": 0.35, "medium": 0.45, "hard": 0.2},
    },
}


def get_subject_config(subject_code: str) -> Optional[dict]:
    """과목 코드로 설정 조회

    Args:
        subject_code: 과목 코드 (math, science, social, history, korean, english)

    Returns:
        과목 설정 딕셔너리 또는 None
    """
    return SUBJECT_CONFIGS.get(subject_code.lower())


def get_validators_for_subject(subject_code: str) -> list[str]:
    """과목별 필요한 검증기 목록 반환"""
    config = get_subject_config(subject_code)
    if config:
        return config.get("validators", ["quality", "consistency"])
    return ["quality", "consistency"]


def get_cross_validation_level(subject_code: str) -> int:
    """과목별 교차검증 레벨 반환"""
    config = get_subject_config(subject_code)
    if config:
        return config.get("cross_validation_level", 1)
    return 1


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API 설정
    google_api_key: str = Field(default="", description="Google AI API Key")

    # 모델 설정 (스펙 기준)
    # - Gemini 3 Flash: gemini-3-flash-preview (Vision 분석, 문항 생성)
    # - Nano Banana Pro: gemini-3-pro-image-preview (이미지 생성)
    gemini_model: str = Field(default="gemini-3-flash-preview", description="Gemini 3 Flash - Vision 분석/문항 생성")
    nano_banana_model: str = Field(default="gemini-3-pro-image-preview", description="Nano Banana Pro - 이미지 생성")

    # 경로 설정
    output_dir: Path = Field(default=Path("./output"), description="출력 디렉토리")
    log_level: str = Field(default="INFO", description="로그 레벨")

    # 생성 설정
    max_vision_actions: int = Field(default=5, description="최대 Vision 탐색 횟수")
    max_regenerations: int = Field(default=3, description="최대 재생성 횟수")

    # 검수 설정
    min_confidence: float = Field(default=0.7, description="최소 신뢰도")

    # P5 이미지 생성 설정
    image_resolution: str = Field(default="1K", description="생성 이미지 해상도 (1K, 2K, 4K)")
    image_aspect_ratio: str = Field(default="1:1", description="생성 이미지 비율 (16:9, 4:3, 1:1)")

    # P4 교차검증 설정 (Cross-Validation)
    # Level 2: OpenAI GPT-4o
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI 모델")

    # Level 3: Gemini Pro (민감 주제 검증)
    gemini_pro_model: str = Field(default="gemini-2.5-pro-preview", description="Gemini Pro 모델")

    # 교차검증 활성화
    cross_validation_enabled: bool = Field(default=False, description="교차검증 활성화")
    cross_validation_level: int = Field(default=1, description="검증 레벨 (1-4)")

    # Data-Collect 통합 설정
    data_collect_path: str = Field(
        default="/Users/ldm/work/data-collect",
        description="Data-Collect 프로젝트 경로"
    )
    curriculum_version: str = Field(default="2022", description="교육과정 버전")
    exam_years: str = Field(
        default="2020,2021,2022,2023,2024,2025",
        description="수집 대상 시험 년도 (콤마 구분)"
    )

    @property
    def curriculum_dir(self) -> Path:
        """교육과정 PDF 디렉토리"""
        return Path(self.data_collect_path) / "data" / "raw" / "curriculum" / "ncic" / self.curriculum_version

    @property
    def exam_dir(self) -> Path:
        """시험지 PDF 디렉토리"""
        return Path(self.data_collect_path) / "data" / "raw" / "examinations"

    @property
    def textbook_csv(self) -> Path:
        """교과서 메타데이터 CSV"""
        return Path(self.data_collect_path) / "data" / "raw" / "textbook" / "data-2015-meta-textbook-all.csv"

    @property
    def exam_years_list(self) -> list[int]:
        """시험 년도 리스트"""
        return [int(y.strip()) for y in self.exam_years.split(",")]

    @property
    def cross_validation_models(self) -> list[dict]:
        """교차검증 레벨에 따른 모델 목록"""
        models = [{"provider": "google", "model": self.gemini_model}]

        if self.cross_validation_level >= 2 and self.openai_api_key:
            models.append({"provider": "openai", "model": self.openai_model})

        if self.cross_validation_level >= 3:
            models.append({"provider": "google", "model": self.gemini_pro_model})

        return models

    @property
    def is_cross_validation_ready(self) -> bool:
        """교차검증 가능 여부"""
        if not self.cross_validation_enabled:
            return False

        if self.cross_validation_level >= 2 and not self.openai_api_key:
            return False

        # Level 3는 Gemini Pro 사용 (동일 API 키)
        return True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "items").mkdir(exist_ok=True)
        (self.output_dir / "logs").mkdir(exist_ok=True)
        (self.output_dir / "p1_input").mkdir(exist_ok=True)


# 전역 설정 인스턴스
settings = Settings()


@lru_cache()
def get_settings() -> Settings:
    """캐시된 설정 인스턴스 반환"""
    return Settings()
