#!/usr/bin/env python3
"""POC 실행 스크립트

파이프라인 단계:
- P1-INPUT: 입력 검증
- P2-ANALYZE: 시각 분석 (Gemini 3 Flash)
- P3-GENERATE: 문항 생성 (Gemini 3 Flash)
- P4-VALIDATE: 검증
- P5-OUTPUT: 이미지 생성 (Nano Banana Pro) + 출력
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.core.schemas import ItemType, DifficultyLevel
from src.pipeline import ItemGenerationPipeline, PipelineResult
from src.utils.image_utils import ImageProcessor


def print_result(result: PipelineResult, image_name: str, generate_image: bool = False):
    """결과 출력"""
    print(f"\n{'='*60}")
    print(f"이미지: {image_name}")
    print(f"상태: {result.final_status}")
    print(f"성공: {'O' if result.success else 'X'}")

    if result.item:
        print(f"\n[생성된 문항]")
        print(f"  ID: {result.item.item_id}")
        print(f"  질문: {result.item.stem[:100]}...")
        print(f"  정답: {result.item.correct_answer}")
        print(f"  선지 수: {len(result.item.choices)}개")
        print(f"  모델: {result.item.model_version}")

        # P5 이미지 생성 결과
        if generate_image and result.item.generated_image:
            print(f"\n[P5-OUTPUT 생성 이미지]")
            print(f"  이미지 ID: {result.item.generated_image.image_id}")
            print(f"  경로: {result.item.generated_image.path}")
            print(f"  모델: {result.item.generated_image.generation_model}")

    if result.quality_report:
        print(f"\n[규칙 검수] {result.quality_report.status.value}")
        if result.quality_report.failure_codes:
            print(f"  실패 코드: {[f.value for f in result.quality_report.failure_codes]}")

    if result.consistency_report:
        print(f"\n[정합성 검수] {result.consistency_report.status.value}")
        if result.consistency_report.failure_codes:
            print(f"  실패 코드: {[f.value for f in result.consistency_report.failure_codes]}")

    if result.error_message:
        print(f"\n[오류] {result.error_message}")


def main():
    # 인자 파싱
    parser = argparse.ArgumentParser(description="Gemini Agentic Vision POC 실행")
    parser.add_argument(
        "--generate-image", "-g",
        action="store_true",
        help="P5-OUTPUT에서 Nano Banana Pro로 새 이미지 생성"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=0,
        help="처리할 이미지 수 제한 (0=전체)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Gemini Agentic Vision POC 실행")
    print("=" * 60)

    # 모델 정보 출력
    print(f"\n[사용 모델]")
    print(f"  P2-ANALYZE/P3-GENERATE: {settings.gemini_model}")
    print(f"  P5-OUTPUT (이미지 생성): {settings.nano_banana_model}")
    print(f"  이미지 생성 활성화: {'O' if args.generate_image else 'X'}")

    # 샘플 이미지 디렉토리
    samples_dir = project_root / "samples" / "images"

    if not samples_dir.exists():
        print(f"\n샘플 이미지가 없습니다. 먼저 샘플을 생성하세요:")
        print(f"  python scripts/generate_samples.py")
        return

    # 이미지 목록
    image_processor = ImageProcessor()
    images = list(samples_dir.glob("*.png"))

    if not images:
        print(f"PNG 이미지를 찾을 수 없습니다: {samples_dir}")
        return

    # 이미지 수 제한
    if args.limit > 0:
        images = images[:args.limit]

    print(f"\n발견된 이미지: {len(images)}개")

    # 파이프라인 초기화
    pipeline = ItemGenerationPipeline(enable_image_generation=args.generate_image)

    results = []

    # 각 이미지 유형별 테스트
    for image_path in images:
        # 이미지 이름으로 유형 결정
        name = image_path.stem
        if "bar" in name or "line" in name or "chart" in name:
            item_type = ItemType.GRAPH
        elif "geometry" in name or "triangle" in name:
            item_type = ItemType.GEOMETRY
        elif "measurement" in name or "ruler" in name:
            item_type = ItemType.MEASUREMENT
        else:
            item_type = ItemType.GRAPH  # 기본값

        print(f"\n처리 중: {image_path.name} (유형: {item_type.value})")

        try:
            result = pipeline.run(
                image_path=image_path,
                item_type=item_type,
                difficulty=DifficultyLevel.MEDIUM,
                auto_retry=True,
                max_retries=2,
                generate_new_image=args.generate_image
            )
            results.append(result)
            print_result(result, image_path.name, args.generate_image)

        except Exception as e:
            print(f"  오류 발생: {e}")
            results.append(PipelineResult(
                success=False,
                item=None,
                generation_log=None,
                quality_report=None,
                consistency_report=None,
                final_status="ERROR",
                error_message=str(e)
            ))

    # 통계 출력
    stats = pipeline.get_statistics(results)

    print("\n" + "=" * 60)
    print("POC 실행 결과 요약")
    print("=" * 60)
    print(f"총 처리: {stats['total']}개")
    print(f"성공: {stats['success']}개")
    print(f"실패: {stats['fail']}개")
    print(f"성공률: {stats['success_rate']:.1f}%")
    print(f"\n상태 분포:")
    for status, count in stats['status_distribution'].items():
        print(f"  {status}: {count}개")

    # P5 이미지 생성 결과
    if args.generate_image:
        generated_images = [
            r.item.generated_image
            for r in results
            if r.item and r.item.generated_image
        ]
        print(f"\n[P5-OUTPUT 이미지 생성]")
        print(f"  생성된 이미지: {len(generated_images)}개")


if __name__ == "__main__":
    main()
