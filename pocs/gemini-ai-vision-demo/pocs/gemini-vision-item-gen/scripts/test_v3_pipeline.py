#!/usr/bin/env python3
"""v3.0.0 파이프라인 테스트 스크립트

테스트 항목:
1. 스키마 변경 테스트 (EvidencePack, VisualSpec)
2. P2-ANALYZE 테스트 (자연어 이미지 설명)
3. P3-GENERATE 테스트 (visual_spec.image_prompt 포함)
4. P5-OUTPUT 테스트 (LLM 프롬프트 기반 이미지 생성)
5. 정합성 검증 테스트 (ImageConsistencyValidator)
"""

import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_schemas():
    """1. 스키마 변경 테스트"""
    print("\n" + "=" * 60)
    print("1. 스키마 변경 테스트")
    print("=" * 60)

    from src.core.schemas import EvidencePack, VisualSpec

    # EvidencePack 테스트
    evidence = EvidencePack(
        image_description="빨간색 원 안에 담배 그림이 있고, 대각선으로 금지 표시가 그려진 금연 표지판입니다.",
        visual_elements=["빨간 원", "담배 그림", "금지 대각선", "텍스트"],
        content_type="표지판",
        extracted_facts=["금연 표지판", "No Smoking 텍스트"],
        analysis_summary="금연 구역을 나타내는 표지판"
    )

    print(f"✓ EvidencePack.image_description: {evidence.image_description[:50]}...")
    print(f"✓ EvidencePack.visual_elements: {evidence.visual_elements}")
    print(f"✓ EvidencePack.content_type: {evidence.content_type}")

    # VisualSpec 테스트
    visual_spec = VisualSpec(
        required=True,
        image_prompt="주차 금지 표지판. 빨간색 원 안에 P 글자가 있고 대각선 금지 표시. 흰색 배경, 교과서 스타일.",
        subject_context="영어/표지판 읽기",
        style_guidance="실제 표지판처럼 사실적으로",
        visual_type="sign",
        description="주차 금지 표지판 이미지"
    )

    print(f"✓ VisualSpec.image_prompt: {visual_spec.image_prompt[:50]}...")
    print(f"✓ VisualSpec.subject_context: {visual_spec.subject_context}")
    print(f"✓ VisualSpec.style_guidance: {visual_spec.style_guidance}")

    print("\n✅ 스키마 테스트 통과")
    return True


def test_vision_client():
    """2. P2-ANALYZE 테스트 (모의 테스트)"""
    print("\n" + "=" * 60)
    print("2. P2-ANALYZE 테스트 (VisionClient)")
    print("=" * 60)

    from src.agents.vision_client import GeminiVisionClient

    # 클래스 메서드 확인
    assert hasattr(GeminiVisionClient, 'describe_image'), "describe_image 메서드 없음"
    assert hasattr(GeminiVisionClient, 'DESCRIBE_IMAGE_PROMPT'), "DESCRIBE_IMAGE_PROMPT 상수 없음"

    print(f"✓ describe_image() 메서드 존재")
    print(f"✓ DESCRIBE_IMAGE_PROMPT 프롬프트 길이: {len(GeminiVisionClient.DESCRIBE_IMAGE_PROMPT)}자")

    # 프롬프트 내용 확인
    prompt = GeminiVisionClient.DESCRIBE_IMAGE_PROMPT
    assert "이미지에 무엇이 보이나요" in prompt, "프롬프트에 이미지 설명 요청 없음"
    assert "content_type" in prompt, "프롬프트에 content_type 없음"
    assert "visual_elements" in prompt, "프롬프트에 visual_elements 없음"

    print(f"✓ 프롬프트에 자연어 설명 요청 포함")
    print(f"✓ 프롬프트에 JSON 요약 형식 포함")

    print("\n✅ VisionClient 테스트 통과")
    return True


def test_item_generator():
    """3. P3-GENERATE 테스트 (모의 테스트)"""
    print("\n" + "=" * 60)
    print("3. P3-GENERATE 테스트 (ItemGenerator)")
    print("=" * 60)

    from src.agents.item_generator import ItemGeneratorAgent
    from src.core.schemas import DifficultyLevel

    # 클래스 메서드 확인
    assert hasattr(ItemGeneratorAgent, 'generate_item_with_description'), "generate_item_with_description 메서드 없음"
    assert hasattr(ItemGeneratorAgent, '_build_generation_prompt'), "_build_generation_prompt 메서드 없음"
    assert hasattr(ItemGeneratorAgent, 'GENERATION_PROMPT_TEMPLATE'), "GENERATION_PROMPT_TEMPLATE 상수 없음"

    print(f"✓ generate_item_with_description() 메서드 존재")
    print(f"✓ _build_generation_prompt() 메서드 존재")
    print(f"✓ GENERATION_PROMPT_TEMPLATE 프롬프트 길이: {len(ItemGeneratorAgent.GENERATION_PROMPT_TEMPLATE)}자")

    # 프롬프트 내용 확인
    prompt = ItemGeneratorAgent.GENERATION_PROMPT_TEMPLATE
    assert "image_description" in prompt, "프롬프트에 image_description 없음"
    assert "visual_spec" in prompt, "프롬프트에 visual_spec 없음"
    assert "image_prompt" in prompt, "프롬프트에 image_prompt 없음"
    assert "subject_context" in prompt, "프롬프트에 subject_context 없음"
    assert "style_guidance" in prompt, "프롬프트에 style_guidance 없음"

    print(f"✓ 프롬프트에 이미지 설명 입력 포함")
    print(f"✓ 프롬프트에 visual_spec 출력 형식 포함")

    print("\n✅ ItemGenerator 테스트 통과")
    return True


def test_p5_output():
    """4. P5-OUTPUT 테스트 (하드코딩 제거 확인)"""
    print("\n" + "=" * 60)
    print("4. P5-OUTPUT 테스트 (하드코딩 제거 확인)")
    print("=" * 60)

    from src.processors.p5_output import P5OutputProcessor

    # 제거된 메서드 확인
    removed_methods = [
        '_create_visual_spec',
        '_infer_subject_from_evidence',
        '_extract_visual_info_from_evidence',
        '_create_graph_visual_spec',
        '_create_geometry_visual_spec',
        '_create_measurement_visual_spec',
        '_create_default_visual_spec',
        '_create_math_visual_spec',
        '_create_science_visual_spec',
        '_create_korean_visual_spec',
        '_create_english_visual_spec',
        '_create_history_visual_spec',
        '_create_social_visual_spec',
    ]

    for method in removed_methods:
        assert not hasattr(P5OutputProcessor, method), f"❌ {method} 메서드가 아직 존재함"
        print(f"✓ {method}() 제거됨")

    # 새로운 메서드 확인
    assert hasattr(P5OutputProcessor, '_get_visual_spec'), "_get_visual_spec 메서드 없음"
    print(f"✓ _get_visual_spec() 메서드 존재 (v3.0.0)")

    print("\n✅ P5-OUTPUT 테스트 통과 (하드코딩 로직 제거됨)")
    return True


def test_nano_banana_client():
    """Nano Banana Client 테스트"""
    print("\n" + "=" * 60)
    print("4-1. NanoBananaClient 테스트")
    print("=" * 60)

    from src.agents.nano_banana_client import NanoBananaClient

    # 새로운 메서드 확인
    assert hasattr(NanoBananaClient, 'generate_from_prompt'), "generate_from_prompt 메서드 없음"
    print(f"✓ generate_from_prompt() 메서드 존재 (v3.0.0)")

    print("\n✅ NanoBananaClient 테스트 통과")
    return True


def test_image_consistency_validator():
    """5. 정합성 검증 테스트"""
    print("\n" + "=" * 60)
    print("5. ImageConsistencyValidator 테스트")
    print("=" * 60)

    from src.validators.consistency_validator import ImageConsistencyValidator

    # 클래스 확인
    assert hasattr(ImageConsistencyValidator, 'validate'), "validate 메서드 없음"
    assert hasattr(ImageConsistencyValidator, 'VALIDATION_PROMPT'), "VALIDATION_PROMPT 상수 없음"

    print(f"✓ ImageConsistencyValidator 클래스 존재")
    print(f"✓ validate() 메서드 존재")
    print(f"✓ VALIDATION_PROMPT 프롬프트 길이: {len(ImageConsistencyValidator.VALIDATION_PROMPT)}자")

    # 프롬프트 내용 확인
    prompt = ImageConsistencyValidator.VALIDATION_PROMPT
    assert "is_consistent" in prompt, "프롬프트에 is_consistent 없음"
    assert "consistency_score" in prompt, "프롬프트에 consistency_score 없음"
    assert "missing_elements" in prompt, "프롬프트에 missing_elements 없음"

    print(f"✓ 프롬프트에 정합성 검증 응답 형식 포함")

    print("\n✅ ImageConsistencyValidator 테스트 통과")
    return True


def test_pipeline():
    """6. 파이프라인 통합 테스트"""
    print("\n" + "=" * 60)
    print("6. 파이프라인 통합 테스트")
    print("=" * 60)

    from src.pipeline import ItemGenerationPipeline, PipelineResult

    # PipelineResult 필드 확인
    import dataclasses
    fields = {f.name for f in dataclasses.fields(PipelineResult)}
    assert 'image_consistency_report' in fields, "image_consistency_report 필드 없음"
    print(f"✓ PipelineResult.image_consistency_report 필드 존재")

    # Pipeline 속성 확인
    # (실제 초기화는 API 키 필요하므로 속성만 확인)
    import inspect
    init_params = inspect.signature(ItemGenerationPipeline.__init__).parameters
    print(f"✓ ItemGenerationPipeline 초기화 파라미터: {list(init_params.keys())}")

    print("\n✅ 파이프라인 테스트 통과")
    return True


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("v3.0.0 파이프라인 고도화 테스트")
    print("=" * 60)

    tests = [
        ("스키마 변경", test_schemas),
        ("VisionClient (P2-ANALYZE)", test_vision_client),
        ("ItemGenerator (P3-GENERATE)", test_item_generator),
        ("P5OutputProcessor", test_p5_output),
        ("NanoBananaClient", test_nano_banana_client),
        ("ImageConsistencyValidator (P4-VALIDATE)", test_image_consistency_validator),
        ("Pipeline 통합", test_pipeline),
    ]

    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 테스트 실패: {e}")
            results.append((name, False))

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\n총 {passed}/{total} 테스트 통과")

    if passed == total:
        print("\n🎉 모든 테스트 통과! v3.0.0 파이프라인 고도화 완료")
        return 0
    else:
        print("\n⚠️ 일부 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
