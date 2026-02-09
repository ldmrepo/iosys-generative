"""데이터 스키마 정의"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ItemType(str, Enum):
    """문항 유형"""
    GRAPH = "graph"           # 그래프 해석형
    GEOMETRY = "geometry"     # 도형/공간 인식형
    MEASUREMENT = "measurement"  # 측정값 판독형


class DifficultyLevel(str, Enum):
    """난이도"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class PhaseType(str, Enum):
    """에이전트 실행 단계"""
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"


class ValidationStatus(str, Enum):
    """검수 상태"""
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"


class FailureCode(str, Enum):
    """실패 사유 코드"""
    AMBIGUOUS_READ = "AMBIGUOUS_READ"
    NO_VISUAL_EVIDENCE = "NO_VISUAL_EVIDENCE"
    MULTI_CORRECT = "MULTI_CORRECT"
    OPTION_OVERLAP = "OPTION_OVERLAP"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    INVALID_FORMAT = "INVALID_FORMAT"
    CALCULATION_ERROR = "CALCULATION_ERROR"       # AG-CALC: 계산 오류
    FACTUAL_ERROR = "FACTUAL_ERROR"               # AG-FACT: 사실 오류
    SAFETY_VIOLATION = "SAFETY_VIOLATION"         # AG-SAFE: 안전 위반
    BIAS_DETECTED = "BIAS_DETECTED"               # AG-SAFE: 편향 감지


class ImagePosition(str, Enum):
    """이미지 위치"""
    BEFORE_STEM = "before_stem"     # 문제 본문 전
    AFTER_STEM = "after_stem"       # 문제 본문 후
    INLINE = "inline"               # 문제 본문 내 인라인
    IN_CHOICE = "in_choice"         # 선지 내


class Choice(BaseModel):
    """선지"""
    label: str = Field(..., description="선지 레이블 (A, B, C, D)")
    text: str = Field(..., description="선지 내용")


class Region(BaseModel):
    """이미지 영역"""
    region_id: str = Field(..., description="영역 ID")
    x: int = Field(..., description="X 좌표")
    y: int = Field(..., description="Y 좌표")
    width: int = Field(..., description="너비")
    height: int = Field(..., description="높이")
    transform: Optional[str] = Field(None, description="적용된 변환 (zoom, rotate 등)")
    extracted_text: Optional[str] = Field(None, description="추출된 텍스트")
    extracted_value: Optional[str] = Field(None, description="추출된 수치")
    confidence: float = Field(default=1.0, description="신뢰도")
    purpose: str = Field(default="evidence", description="용도 (정답 근거/오답 근거)")


class EvidencePack(BaseModel):
    """P2-ANALYZE 출력: Vision 모델의 이미지 분석 결과"""
    regions: list[Region] = Field(default_factory=list, description="분석된 영역들")
    extracted_facts: list[str] = Field(default_factory=list, description="추출된 사실들")
    analysis_summary: str = Field(default="", description="분석 요약")

    # v3.0.0: Vision 모델의 자연어 이미지 설명
    image_description: str = Field(default="", description="Vision 모델의 자연어 이미지 설명")
    visual_elements: list[str] = Field(default_factory=list, description="식별된 시각 요소 목록")
    content_type: str = Field(default="", description="이미지 내용 유형 (표지판, 그래프, 지도 등)")


class VisualSpec(BaseModel):
    """P3-GENERATE 출력: LLM이 생성한 시각 자료 사양

    v3.0.0: LLM이 자연어로 이미지 생성 프롬프트를 출력
    - image_prompt: 이미지 생성 모델에 직접 전달되는 프롬프트
    - subject_context: 과목/맥락 정보
    - style_guidance: 스타일 가이드
    """
    required: bool = Field(default=False, description="이미지 생성 필요 여부")
    visual_type: str = Field(default="", description="시각화 유형 (function_graph, geometry, bar_chart 등)")
    description: str = Field(default="", description="시각 자료 설명")

    # v3.0.0: LLM이 자연어로 출력하는 이미지 생성 프롬프트
    image_prompt: str = Field(default="", description="이미지 생성 프롬프트 (LLM 생성)")
    subject_context: str = Field(default="", description="과목/맥락 정보")
    style_guidance: str = Field(default="", description="스타일 가이드 (교과서풍, 사실적 등)")

    # 레거시 필드 (하위 호환성)
    data: dict = Field(default_factory=dict, description="[레거시] 시각화 데이터")
    rendering_instructions: str = Field(default="", description="[레거시] 렌더링 지침")


class GeneratedImage(BaseModel):
    """생성된 이미지 정보"""
    image_id: str = Field(..., description="이미지 ID")
    path: str = Field(..., description="저장 경로")
    format: str = Field(default="PNG", description="이미지 포맷")
    resolution: str = Field(default="2K", description="해상도")
    visual_spec: Optional[VisualSpec] = Field(None, description="생성 사양")
    generation_model: str = Field(default="", description="생성에 사용된 모델")
    generated_at: datetime = Field(default_factory=datetime.now, description="생성 시각")


class ItemQuestion(BaseModel):
    """생성된 문항"""
    item_id: str = Field(..., description="문항 ID")
    item_type: ItemType = Field(..., description="문항 유형")
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM, description="난이도")
    stem: str = Field(..., description="문항 질문")
    choices: list[Choice] = Field(..., description="선지 목록")
    correct_answer: str = Field(..., description="정답")
    explanation: str = Field(..., description="해설")
    evidence: EvidencePack = Field(default_factory=EvidencePack, description="시각 근거")
    source_image: str = Field(..., description="원본 이미지 경로")
    generated_at: datetime = Field(default_factory=datetime.now, description="생성 시각")
    model_version: str = Field(default="", description="사용된 모델 버전")

    # P5-OUTPUT 관련
    visual_spec: Optional[VisualSpec] = Field(default=None, description="시각 자료 생성 사양")
    generated_image: Optional[GeneratedImage] = Field(default=None, description="생성된 이미지")


class ValidationReport(BaseModel):
    """검수 보고서"""
    item_id: str = Field(..., description="문항 ID")
    status: ValidationStatus = Field(..., description="검수 상태")
    failure_codes: list[FailureCode] = Field(default_factory=list, description="실패 사유 코드")
    details: list[str] = Field(default_factory=list, description="상세 내용")
    recommendations: list[str] = Field(default_factory=list, description="개선 권고사항")
    validated_at: datetime = Field(default_factory=datetime.now, description="검수 시각")


class PhaseLog(BaseModel):
    """단계별 로그"""
    phase: PhaseType = Field(..., description="실행 단계")
    input_data: dict = Field(default_factory=dict, description="입력 데이터")
    output_data: dict = Field(default_factory=dict, description="출력 데이터")
    code_executed: Optional[str] = Field(None, description="실행된 코드")
    duration_ms: int = Field(default=0, description="소요 시간(ms)")
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")


class GenerationLog(BaseModel):
    """생성 전체 로그"""
    session_id: str = Field(..., description="세션 ID")
    source_image: str = Field(..., description="원본 이미지")
    item_type: ItemType = Field(..., description="문항 유형")
    phases: list[PhaseLog] = Field(default_factory=list, description="단계별 로그")
    total_duration_ms: int = Field(default=0, description="총 소요 시간")
    success: bool = Field(default=False, description="성공 여부")
    final_item_id: Optional[str] = Field(None, description="최종 문항 ID")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시각")


# ============================================================================
# P1-INPUT 스키마
# ============================================================================

class QuestionType(str, Enum):
    """문항 채점유형 (QTI/IML qt 속성)"""
    MULTIPLE_CHOICE = "11"      # 선다형
    TRUE_FALSE = "21"           # 진위형
    SHORT_ANSWER = "31"         # 단답형
    COMPLETION = "34"           # 완성형
    MATCHING = "37"             # 배합형
    ESSAY = "41"                # 서술형
    LONG_ESSAY = "51"           # 논술형


class ImageInfo(BaseModel):
    """검증된 이미지 정보"""
    path: str = Field(..., description="이미지 파일 경로")
    format: str = Field(..., description="이미지 포맷 (PNG, JPEG 등)")
    width: int = Field(..., description="너비 (px)")
    height: int = Field(..., description="높이 (px)")
    file_size: int = Field(..., description="파일 크기 (bytes)")
    is_valid: bool = Field(default=True, description="유효성 검증 통과 여부")
    validation_issues: list[str] = Field(default_factory=list, description="검증 이슈 목록")


class QTIItem(BaseModel):
    """파싱된 QTI/IML 문항

    IML 포맷 기반 문항 데이터 모델.
    문제(문), 선지, 정답, 해설 등 문항의 구성요소를 포함.
    """
    # 식별자
    item_id: str = Field(..., description="문항 ID (문항 태그의 id 속성)")
    source_path: Optional[Path] = Field(None, description="원본 XML 파일 경로")

    # 문항 내용
    title: str = Field(default="", description="문항 제목")
    stem: str = Field(default="", description="문제 본문 (물음)")
    choices: list[Choice] = Field(default_factory=list, description="선지 목록")
    correct_answer: str = Field(default="", description="정답")
    explanation: str = Field(default="", description="해설")
    hint: str = Field(default="", description="힌트")
    direction: str = Field(default="", description="지시문")

    # 문항 유형
    question_type: str = Field(default="", description="채점유형 (선다형, 단답형 등)")
    question_type_code: str = Field(default="", description="채점유형 코드 (qt)")

    # 미디어
    images: list[str] = Field(default_factory=list, description="이미지 경로 목록")
    math_expressions: list[str] = Field(default_factory=list, description="수식 목록 (EQN)")

    # 분류 정보
    subject: str = Field(default="", description="과목명")
    subject_code: str = Field(default="", description="과목 코드")
    grade: str = Field(default="", description="학년")
    grade_code: str = Field(default="", description="학년 코드")
    school_level: str = Field(default="", description="학교급 (초/중/고)")
    school_level_code: str = Field(default="", description="학교급 코드")
    difficulty: str = Field(default="", description="난이도")
    difficulty_code: str = Field(default="", description="난이도 코드")

    # 단원 분류
    curriculum_code: str = Field(default="", description="교육과정 코드 (cls1)")
    unit_large: str = Field(default="", description="대단원 (cls7)")
    unit_medium: str = Field(default="", description="중단원 (cls8)")

    # 기출 정보
    keywords: list[str] = Field(default_factory=list, description="키워드")

    # 원본 속성
    raw_attributes: dict = Field(default_factory=dict, description="원본 XML 속성")

    model_config = ConfigDict(
        json_encoders={Path: str}
    )


class VariationType(str, Enum):
    """문항 변형 유형"""
    SIMILAR = "similar"          # 유사 문항
    DIFFICULTY_UP = "diff_up"    # 난이도 상향
    DIFFICULTY_DOWN = "diff_down"  # 난이도 하향
    CONTEXT_CHANGE = "context"   # 맥락/소재 변경
    FORMAT_CHANGE = "format"     # 형식 변경 (선다형→서술형 등)


class ImagePositionInfo(BaseModel):
    """이미지 위치 정보"""
    image_path: str = Field(..., description="이미지 경로")
    position: ImagePosition = Field(..., description="이미지 위치")
    choice_label: Optional[str] = Field(None, description="선지 레이블 (IN_CHOICE인 경우)")
    inline_index: Optional[int] = Field(None, description="인라인 순서 (INLINE인 경우)")


class InputPack(BaseModel):
    """P1-INPUT 출력 객체

    P1-INPUT 단계에서 수집/검증된 모든 입력 데이터를 담는 컨테이너.
    후속 단계(P2-ANALYZE, P3-GENERATE)에서 사용.
    """
    # 요청 식별
    request_id: str = Field(..., description="요청 고유 ID")

    # 원본 문항 (있는 경우)
    qti_item: Optional[QTIItem] = Field(None, description="파싱된 원본 문항")

    # 이미지 정보
    images: list[ImageInfo] = Field(default_factory=list, description="검증된 이미지 목록")
    primary_image: Optional[str] = Field(None, description="주 이미지 경로")
    image_positions: list[ImagePositionInfo] = Field(default_factory=list, description="이미지 위치 정보 목록")

    # 메타데이터
    subject: str = Field(default="", description="과목 코드/명")
    grade: str = Field(default="", description="학년")
    difficulty: str = Field(default="medium", description="목표 난이도")
    item_type: Optional[ItemType] = Field(None, description="목표 문항 유형")

    # 변형 정보
    variation_type: Optional[VariationType] = Field(None, description="변형 유형")

    # 교육과정 메타
    curriculum_meta: dict = Field(default_factory=dict, description="교육과정 메타데이터")

    # 처리 상태
    is_valid: bool = Field(default=True, description="입력 유효성")
    validation_errors: list[str] = Field(default_factory=list, description="검증 오류 목록")

    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시각")
