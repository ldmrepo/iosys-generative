"""통합 파이프라인 - 출제-검수 자동화

v3.0.0: 모델 기반 End-to-End 파이프라인
- P2-ANALYZE: 이미지 → 자연어 설명
- P3-GENERATE: 이미지 설명 → 새 문항 + visual_spec.image_prompt
- P5-OUTPUT: image_prompt → 이미지 생성
- P4-VALIDATE: 문항 ↔ 이미지 정합성 검증

파이프라인 단계:
- P1-INPUT: 입력 검증
- P2-ANALYZE: 시각 분석 → 자연어 이미지 설명 (Gemini 3 Flash)
- P3-GENERATE: 문항 생성 + visual_spec 출력 (Gemini 3 Flash)
- P4-VALIDATE: 검증 (QualityChecker, ConsistencyValidator, ImageConsistencyValidator, ...)
- P5-OUTPUT: 이미지 생성 (Nano Banana Pro) + 출력
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .core.config import settings, get_subject_config, get_validators_for_subject, get_cross_validation_level
from .core.schemas import (
    ItemType,
    DifficultyLevel,
    ItemQuestion,
    ValidationReport,
    ValidationStatus,
    GenerationLog,
    VisualSpec,
    GeneratedImage,
    InputPack,
    VariationType,
)
from .agents.item_generator import ItemGeneratorAgent
from .agents.nano_banana_client import NanoBananaClient
from .validators.consistency_validator import ConsistencyValidator, ImageConsistencyValidator
from .validators.quality_checker import QualityChecker
from .validators.calc_validator import CalcValidator
from .validators.fact_validator import FactValidator
from .validators.safety_validator import SafetyValidator
from .validators.cross_validator import CrossValidator
from .utils.logger import AuditLogger
from .utils.image_utils import ImageProcessor
from .processors.p1_input import P1InputProcessor
from .processors.p5_output import P5OutputProcessor


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    success: bool
    item: Optional[ItemQuestion]
    generation_log: Optional[GenerationLog]
    quality_report: Optional[ValidationReport]
    consistency_report: Optional[ValidationReport]
    final_status: str
    error_message: Optional[str] = None
    input_pack: Optional[InputPack] = None  # P1-INPUT 결과
    # 추가 검증 보고서
    calc_report: Optional[ValidationReport] = None        # AG-CALC
    fact_report: Optional[ValidationReport] = None        # AG-FACT
    safety_report: Optional[ValidationReport] = None      # AG-SAFE
    cross_validation_report: Optional[ValidationReport] = None  # 교차 검증
    # v3.0.0: 이미지 정합성 검증
    image_consistency_report: Optional[ValidationReport] = None  # 생성 이미지 ↔ 문항 정합성
    # P5-OUTPUT 결과
    output_result: Optional[dict] = None


class ItemGenerationPipeline:
    """
    출제-검수 통합 파이프라인

    단계:
    1. 입력 검증 - 이미지 유효성 확인
    2. 시각 분석 - Agentic Vision으로 이미지 탐색
    3. 문항 생성 - 질문/선지/정답/해설 생성
    4. 자동 검수 - 규칙 기반 + AI 기반 검증
    5. 품질 판정 - 통과/재생성/폐기 결정
    """

    def __init__(self, enable_image_generation: bool = True, cross_validation_level: int = 1):
        """파이프라인 초기화

        Args:
            enable_image_generation: P5에서 Nano Banana Pro 이미지 생성 활성화
            cross_validation_level: 교차 검증 레벨 (1-3)
        """
        # P1-INPUT: 입력 처리
        self.p1_processor = P1InputProcessor()
        self.image_processor = ImageProcessor()

        # P2-ANALYZE & P3-GENERATE
        self.item_generator = ItemGeneratorAgent()

        # P4-VALIDATE: 기본 검증기
        self.quality_checker = QualityChecker()
        self.consistency_validator = ConsistencyValidator()

        # P4-VALIDATE: 추가 검증기 (AG-CALC, AG-FACT, AG-SAFE)
        self.calc_validator = CalcValidator()
        self.fact_validator = FactValidator()
        self.safety_validator = SafetyValidator()

        # P4-VALIDATE: 교차 검증
        self.cross_validation_level = cross_validation_level
        self.cross_validator = CrossValidator(level=cross_validation_level) if settings.cross_validation_enabled else None

        # v3.0.0: 이미지 정합성 검증
        self.image_consistency_validator = ImageConsistencyValidator()

        # 로깅
        self.logger = AuditLogger()

        # P5-OUTPUT: Nano Banana Pro 이미지 생성
        self.enable_image_generation = enable_image_generation
        self.nano_banana_client = NanoBananaClient() if enable_image_generation else None
        self.p5_processor = P5OutputProcessor(self.nano_banana_client) if enable_image_generation else None

    def run(
        self,
        image_path: Optional[str | Path] = None,
        item_type: Optional[ItemType] = None,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
        auto_retry: bool = True,
        max_retries: int = 3,
        save_results: bool = True,
        generate_new_image: bool = True,
        qti_path: Optional[str | Path] = None,
        metadata: Optional[dict] = None,
        variation_type: Optional[str] = None,
    ) -> PipelineResult:
        """
        파이프라인 실행

        Args:
            image_path: 입력 이미지 경로
            item_type: 문항 유형 (None이면 자동 감지 시도)
            difficulty: 난이도
            auto_retry: 검수 실패 시 자동 재생성
            max_retries: 최대 재시도 횟수
            save_results: 결과 파일 저장 여부
            generate_new_image: P5에서 새 이미지 생성 여부
            qti_path: QTI/IML XML 파일 경로 (원본 문항 기반 변형 시)
            metadata: 추가 메타데이터 (subject, grade 등)
            variation_type: 변형 유형 (similar, diff_up 등)

        Returns:
            PipelineResult
        """
        # P1-INPUT: 통합 입력 처리
        input_pack = self.p1_processor.process(
            image_path=image_path,
            qti_path=qti_path,
            metadata=metadata,
            variation_type=variation_type,
        )

        # P1 결과 저장
        if save_results:
            input_pack_path = self.p1_processor.save_input_pack(input_pack)
            self.logger.log_info(f"[P1-INPUT] 저장 완료: {input_pack_path}")

        # 입력 유효성 검사
        if not input_pack.is_valid:
            return PipelineResult(
                success=False,
                item=None,
                generation_log=None,
                quality_report=None,
                consistency_report=None,
                final_status="INPUT_INVALID",
                error_message="; ".join(input_pack.validation_errors),
                input_pack=input_pack,
            )

        # 이미지 경로 결정 (InputPack에서)
        effective_image_path: Optional[Path] = None
        if input_pack.primary_image:
            effective_image_path = Path(input_pack.primary_image)
        elif image_path:
            effective_image_path = Path(image_path)

        if not effective_image_path:
            return PipelineResult(
                success=False,
                item=None,
                generation_log=None,
                quality_report=None,
                consistency_report=None,
                final_status="INPUT_INVALID",
                error_message="처리할 이미지가 없습니다",
                input_pack=input_pack,
            )

        # item_type 결정 (명시 > InputPack > 기본값)
        effective_item_type = item_type or input_pack.item_type or ItemType.GRAPH

        # difficulty 결정
        if metadata and "difficulty" in metadata:
            difficulty_str = metadata["difficulty"]
            try:
                difficulty = DifficultyLevel(difficulty_str)
            except ValueError:
                # 한글 등 변환 시도
                diff_map = {"easy": DifficultyLevel.EASY, "medium": DifficultyLevel.MEDIUM, "hard": DifficultyLevel.HARD}
                difficulty = diff_map.get(input_pack.difficulty, DifficultyLevel.MEDIUM)

        # 재시도 루프
        attempts = 0
        last_error = None

        while attempts < max_retries:
            attempts += 1
            self.logger.log_generation_start(
                session_id=f"{input_pack.request_id}-{attempts}",
                image_path=str(effective_image_path),
                item_type=effective_item_type.value
            )

            try:
                # v3.0.0: P2-ANALYZE: 이미지 → 자연어 설명
                self.logger.log_info(f"[P2-ANALYZE] 이미지 설명 생성 시작: {effective_image_path}")
                image_desc_result = self.item_generator.vision_client.describe_image(effective_image_path)

                image_description = image_desc_result.get("image_description", "")
                content_type = image_desc_result.get("content_type", "")
                visual_elements = image_desc_result.get("visual_elements", [])

                self.logger.log_info(f"[P2-ANALYZE] 이미지 유형: {content_type}")
                self.logger.log_info(f"[P2-ANALYZE] 시각 요소: {visual_elements}")

                # v3.0.0: P3-GENERATE: 이미지 설명 → 문항 + visual_spec
                item, gen_log = self.item_generator.generate_item_with_description(
                    image_path=effective_image_path,
                    image_description=image_description,
                    content_type=content_type,
                    visual_elements=visual_elements,
                    item_type=effective_item_type,
                    difficulty=difficulty
                )

                # P2/P3 결과 즉시 저장 (성공/실패 무관)
                if save_results:
                    log_path = self.item_generator.save_log(gen_log)
                    self.logger.log_info(f"[P2-ANALYZE/P3-GENERATE] 로그 저장: {log_path}")

                if not item:
                    last_error = "문항 파싱 실패"
                    if not auto_retry:
                        break
                    continue

                self.logger.log_generation_complete(gen_log)

                # P4-VALIDATE: 과목 기반 검증 설정
                subject_code = input_pack.subject or (metadata or {}).get("subject", "")
                required_validators = get_validators_for_subject(subject_code) if subject_code else ["quality", "consistency"]
                cv_level = get_cross_validation_level(subject_code) if subject_code else self.cross_validation_level

                # P4-VALIDATE: 기본 검증
                quality_report = self.quality_checker.check(item)
                consistency_report = self.consistency_validator.validate(item)

                self.logger.log_validation(quality_report)
                self.logger.log_validation(consistency_report)

                # P4-VALIDATE: 추가 검증기 (과목별 분기)
                calc_report = None
                fact_report = None
                safety_report = None
                cross_report = None

                if "calc" in required_validators:
                    calc_report = self.calc_validator.validate(item)
                    self.logger.log_validation(calc_report)

                if "fact" in required_validators:
                    fact_report = self.fact_validator.validate(item, subject_code)
                    self.logger.log_validation(fact_report)

                if "safety" in required_validators:
                    safety_report = self.safety_validator.validate(item)
                    self.logger.log_validation(safety_report)

                # P4-VALIDATE: 교차 검증 (설정에 따라)
                if self.cross_validator and cv_level > 1:
                    cross_report = self.cross_validator.validate(
                        item,
                        image_path=str(effective_image_path) if effective_image_path else None
                    )
                    self.logger.log_validation(cross_report)

                # 품질 판정 (모든 검증 결과 종합)
                all_reports = [quality_report, consistency_report]
                if calc_report:
                    all_reports.append(calc_report)
                if fact_report:
                    all_reports.append(fact_report)
                if safety_report:
                    all_reports.append(safety_report)
                if cross_report:
                    all_reports.append(cross_report)

                final_status = self._determine_final_status_multi(all_reports)

                # P5-OUTPUT: 출력 처리
                output_result = None
                image_consistency_report = None

                if final_status == "PASS":
                    # P5-OUTPUT: 이미지 생성 및 출력 처리
                    if generate_new_image and self.p5_processor:
                        output_result = self.p5_processor.process(
                            item,
                            input_pack=input_pack,
                            generate_image=True,
                            output_format="json"
                        )
                        if output_result.get("generated_images"):
                            generated_image_info = output_result["generated_images"][0]
                            item.generated_image = GeneratedImage(
                                image_id=generated_image_info["image_id"],
                                path=generated_image_info["path"],
                                format="PNG",
                                resolution=settings.image_resolution,
                                generation_model=settings.nano_banana_model,
                            )

                            # v3.0.0: P4-VALIDATE (추가): 생성된 이미지 ↔ 문항 정합성 검증
                            self.logger.log_info(f"[P4-VALIDATE] 생성 이미지 정합성 검증 시작")
                            image_consistency_report = self.image_consistency_validator.validate(
                                item=item,
                                generated_image_path=generated_image_info["path"]
                            )
                            self.logger.log_validation(image_consistency_report)

                            # 이미지 정합성 실패 시 최종 상태 조정
                            if image_consistency_report.status == ValidationStatus.FAIL:
                                self.logger.log_info("[P4-VALIDATE] 생성 이미지 정합성 검증 실패")
                                # 이미지 정합성 실패는 REVIEW로 처리 (문항은 유효하지만 이미지 재생성 필요)
                                final_status = "REVIEW"

                    elif generate_new_image and self.enable_image_generation:
                        item = self._generate_item_image(item, effective_item_type)

                    # P3 결과 저장 (문항)
                    if save_results:
                        self.item_generator.save_item(item)

                    return PipelineResult(
                        success=True if final_status == "PASS" else False,
                        item=item,
                        generation_log=gen_log,
                        quality_report=quality_report,
                        consistency_report=consistency_report,
                        final_status=final_status,
                        input_pack=input_pack,
                        calc_report=calc_report,
                        fact_report=fact_report,
                        safety_report=safety_report,
                        cross_validation_report=cross_report,
                        image_consistency_report=image_consistency_report,
                        output_result=output_result,
                    )

                elif final_status == "REJECT":
                    # 폐기
                    return PipelineResult(
                        success=False,
                        item=item,
                        generation_log=gen_log,
                        quality_report=quality_report,
                        consistency_report=consistency_report,
                        final_status=final_status,
                        error_message="검수 기준 미달",
                        input_pack=input_pack,
                        calc_report=calc_report,
                        fact_report=fact_report,
                        safety_report=safety_report,
                        cross_validation_report=cross_report,
                        image_consistency_report=None,
                    )

                else:  # RETRY
                    last_error = "검수 미통과, 재생성 필요"
                    if not auto_retry:
                        # 재시도 비활성화 시 REVIEW로 반환
                        if save_results:
                            self.item_generator.save_item(item)

                        return PipelineResult(
                            success=False,
                            item=item,
                            generation_log=gen_log,
                            quality_report=quality_report,
                            consistency_report=consistency_report,
                            final_status="REVIEW",
                            input_pack=input_pack,
                            calc_report=calc_report,
                            fact_report=fact_report,
                            safety_report=safety_report,
                            cross_validation_report=cross_report,
                            image_consistency_report=None,
                        )

            except Exception as e:
                last_error = str(e)
                self.logger.log_error("pipeline", e)
                if not auto_retry:
                    break

        # 모든 재시도 실패
        return PipelineResult(
            success=False,
            item=None,
            generation_log=None,
            quality_report=None,
            consistency_report=None,
            final_status="MAX_RETRIES_EXCEEDED",
            error_message=last_error,
            input_pack=input_pack,
            image_consistency_report=None,
        )


    def _generate_item_image(self, item: ItemQuestion, item_type: ItemType) -> ItemQuestion:
        """P5-OUTPUT: Nano Banana Pro로 이미지 생성

        Args:
            item: 문항 객체
            item_type: 문항 유형

        Returns:
            이미지가 추가된 문항 객체
        """
        if not self.nano_banana_client:
            return item

        try:
            # 시각 사양 생성
            visual_spec = self._create_visual_spec(item, item_type)
            item.visual_spec = visual_spec

            if not visual_spec.required:
                return item

            # 이미지 생성
            self.logger.log_info(f"[P5-OUTPUT] Nano Banana Pro 이미지 생성 시작: {item.item_id}")

            image_bytes = self.nano_banana_client.generate_from_specification(
                visual_spec=visual_spec.model_dump(),
                size=settings.image_resolution
            )

            # 이미지 저장
            image_id = f"IMG-{uuid.uuid4().hex[:8].upper()}"
            output_path = settings.output_dir / "nano_banana" / f"{image_id}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.nano_banana_client.save_image(image_bytes, output_path)

            # GeneratedImage 객체 생성
            generated_image = GeneratedImage(
                image_id=image_id,
                path=str(output_path),
                format="PNG",
                resolution=settings.image_resolution,
                visual_spec=visual_spec,
                generation_model=settings.nano_banana_model,
            )
            item.generated_image = generated_image

            self.logger.log_info(f"[P5-OUTPUT] 이미지 생성 완료: {output_path}")

        except Exception as e:
            self.logger.log_error("P5-OUTPUT", e)
            # 이미지 생성 실패해도 문항은 유지

        return item

    def _create_visual_spec(self, item: ItemQuestion, item_type: ItemType) -> VisualSpec:
        """문항 유형에 맞는 시각 사양 생성"""
        visual_type_map = {
            ItemType.GRAPH: "bar_chart",
            ItemType.GEOMETRY: "geometry",
            ItemType.MEASUREMENT: "diagram",
        }

        # 기본 시각 사양
        visual_spec = VisualSpec(
            required=True,
            visual_type=visual_type_map.get(item_type, "diagram"),
            description=f"문항 '{item.stem[:50]}...'에 대한 시각 자료",
            data={
                "item_type": item_type.value,
                "stem": item.stem,
                "choices": [c.model_dump() for c in item.choices],
                "correct_answer": item.correct_answer,
            },
            rendering_instructions=f"""
- 교과서/시험지에 적합한 깔끔한 스타일
- 흰색 배경
- 모든 레이블과 텍스트 선명하게
- 한글 및 수학 기호 정확하게 렌더링
- 문항 유형: {item_type.value}
"""
        )

        return visual_spec

    def _determine_final_status(
        self,
        quality_report: ValidationReport,
        consistency_report: ValidationReport
    ) -> str:
        """
        최종 상태 결정 (기본 2개 검증기)

        Returns:
            "PASS" - 통과
            "RETRY" - 재생성 필요
            "REJECT" - 폐기
        """
        return self._determine_final_status_multi([quality_report, consistency_report])

    def _determine_final_status_multi(
        self,
        reports: list[ValidationReport]
    ) -> str:
        """
        최종 상태 결정 (다중 검증기)

        Args:
            reports: 검증 보고서 목록

        Returns:
            "PASS" - 통과
            "RETRY" - 재생성 필요
            "REJECT" - 폐기
        """
        if not reports:
            return "RETRY"

        # 모든 보고서의 상태와 실패 코드 수집
        statuses = [r.status for r in reports if r is not None]
        all_failure_codes = set()
        for r in reports:
            if r is not None:
                all_failure_codes.update(f.value for f in r.failure_codes)

        # 심각한 실패 코드
        critical_codes = {
            "NO_VISUAL_EVIDENCE",
            "OUT_OF_SCOPE",
            "SAFETY_VIOLATION",  # AG-SAFE 위반
        }

        # 중간 수준 실패 코드 (재시도 가능)
        retry_codes = {
            "AMBIGUOUS_READ",
            "INVALID_FORMAT",
            "CALCULATION_ERROR",
            "FACTUAL_ERROR",
            "BIAS_DETECTED",
        }

        # 1. 심각한 실패 → 폐기
        if all_failure_codes & critical_codes:
            return "REJECT"

        # 2. FAIL 상태가 있으면
        if ValidationStatus.FAIL in statuses:
            # 재시도 가능한 코드만 있으면 RETRY
            if all_failure_codes and all_failure_codes <= retry_codes:
                return "RETRY"
            # 그 외 FAIL은 폐기
            return "REJECT"

        # 3. 모두 PASS면 통과
        if all(s == ValidationStatus.PASS for s in statuses):
            return "PASS"

        # 4. REVIEW가 있으면 재시도
        return "RETRY"

    def run_batch(
        self,
        image_dir: str | Path,
        item_type: ItemType,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    ) -> list[PipelineResult]:
        """
        디렉토리 내 이미지 일괄 처리
        """
        image_dir = Path(image_dir)
        extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        images = [f for f in image_dir.iterdir() if f.suffix.lower() in extensions]

        results = []
        for image_path in images:
            result = self.run(
                image_path=image_path,
                item_type=item_type,
                difficulty=difficulty
            )
            results.append(result)

        return results

    def get_statistics(self, results: list[PipelineResult]) -> dict:
        """결과 통계"""
        total = len(results)
        success = sum(1 for r in results if r.success)
        fail = total - success

        status_counts = {}
        for r in results:
            status_counts[r.final_status] = status_counts.get(r.final_status, 0) + 1

        return {
            "total": total,
            "success": success,
            "fail": fail,
            "success_rate": success / total * 100 if total > 0 else 0,
            "status_distribution": status_counts
        }
