#!/usr/bin/env python3
"""과목별 전체 파이프라인 테스트 (이미지 생성 포함)

v3.0.0 파이프라인 전체 흐름 테스트:
- P2-ANALYZE: 이미지 → 자연어 설명
- P3-GENERATE: 설명 → 문항 + visual_spec.image_prompt
- P5-OUTPUT: image_prompt → 이미지 생성
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.schemas import ItemType, DifficultyLevel
from src.agents.vision_client import GeminiVisionClient
from src.agents.item_generator import ItemGeneratorAgent
from src.agents.nano_banana_client import NanoBananaClient
from src.processors.p5_output import P5OutputProcessor
from src.core.config import settings


# 과목별 샘플 이미지 경로
SAMPLE_IMAGES = {
    "수학": "/root/work/mcp/iosys-generative/data/sample/수학/중1/F3DAC58DB0084A709FC4663D12B89CA4/images/P107A95A8.png",
    "과학": "/root/work/mcp/iosys-generative/data/sample/과학/중1/DC0AB613A6DF48129BD5751002F0104B/images/P0DEAEDD8.png",
    "영어": "/root/work/mcp/iosys-generative/data/sample/영어/중1/F94012572D9D4AAAADF70C972052C890/images/P042EC230.png",
    "국어": "/root/work/mcp/iosys-generative/data/sample/국어/중1/A9E010C88DD246429D2898549BED55EA/images/P11AD4C08.png",
    "사회": "/root/work/mcp/iosys-generative/data/sample/사회/초4/0E023EFCDFCE4B76BE7631E61B1A730C/images/P11BC6ED8.jpg",
    "역사": "/root/work/mcp/iosys-generative/data/sample/역사/초3/369E98BCD56745A6A884C9083D373D6A/images/P0E73D4B0.png",
}


def test_full_pipeline(subject: str, image_path: str) -> dict:
    """전체 파이프라인 테스트 (이미지 생성 포함)

    Args:
        subject: 과목명
        image_path: 이미지 경로

    Returns:
        테스트 결과 딕셔너리
    """
    result = {
        "subject": subject,
        "image_path": image_path,
        "success": False,
        "error": None,
        "p2_result": None,
        "item": None,
        "visual_spec": None,
        "generated_image": None,
    }

    # 이미지 파일 존재 확인
    if not Path(image_path).exists():
        result["error"] = f"이미지 파일 없음: {image_path}"
        return result

    try:
        print(f"\n{'='*60}")
        print(f"[{subject}] 전체 파이프라인 테스트")
        print(f"{'='*60}")
        print(f"원본 이미지: {image_path}")

        # Vision Client 초기화
        vision_client = GeminiVisionClient()

        # ========================================
        # P2-ANALYZE: 이미지 설명 생성
        # ========================================
        print(f"\n[P2-ANALYZE] 이미지 분석 중...")
        desc_result = vision_client.describe_image(image_path)

        image_description = desc_result.get("image_description", "")
        content_type = desc_result.get("content_type", "")
        visual_elements = desc_result.get("visual_elements", [])

        print(f"  - 이미지 유형: {content_type}")
        print(f"  - 시각 요소: {visual_elements[:3]}...")

        result["p2_result"] = {
            "content_type": content_type,
            "visual_elements": visual_elements,
            "description_length": len(image_description),
        }

        # ========================================
        # P3-GENERATE: 문항 생성
        # ========================================
        print(f"\n[P3-GENERATE] 문항 생성 중...")
        item_generator = ItemGeneratorAgent(vision_client=vision_client)

        item, gen_log = item_generator.generate_item_with_description(
            image_path=image_path,
            image_description=image_description,
            content_type=content_type,
            visual_elements=visual_elements,
            item_type=ItemType.GRAPH,
            difficulty=DifficultyLevel.MEDIUM,
        )

        if not item:
            result["error"] = "문항 생성 실패"
            return result

        print(f"  - 문항 ID: {item.item_id}")
        print(f"  - 문제: {item.stem[:50]}...")
        print(f"  - 정답: {item.correct_answer}")

        result["item"] = {
            "item_id": item.item_id,
            "stem": item.stem,
            "choices": [{"label": c.label, "text": c.text} for c in item.choices],
            "correct_answer": item.correct_answer,
            "explanation": item.explanation,
        }

        # visual_spec 확인
        if item.visual_spec:
            result["visual_spec"] = {
                "required": item.visual_spec.required,
                "image_prompt": item.visual_spec.image_prompt,
                "subject_context": item.visual_spec.subject_context,
                "style_guidance": item.visual_spec.style_guidance,
            }
            print(f"\n[Visual Spec]")
            print(f"  - required: {item.visual_spec.required}")
            print(f"  - image_prompt: {item.visual_spec.image_prompt[:80]}...")

        # ========================================
        # P5-OUTPUT: 이미지 생성
        # ========================================
        if item.visual_spec and item.visual_spec.required and item.visual_spec.image_prompt:
            print(f"\n[P5-OUTPUT] 이미지 생성 중...")

            try:
                nano_banana_client = NanoBananaClient()
                p5_processor = P5OutputProcessor(nano_banana_client=nano_banana_client)

                output_result = p5_processor.process(
                    item=item,
                    input_pack=None,
                    generate_image=True,
                    output_format="json"
                )

                if output_result.get("generated_images"):
                    gen_img = output_result["generated_images"][0]
                    print(f"  - 이미지 ID: {gen_img['image_id']}")
                    print(f"  - 저장 경로: {gen_img['path']}")

                    result["generated_image"] = {
                        "image_id": gen_img["image_id"],
                        "path": gen_img["path"],
                        "position": gen_img.get("position", "after_stem"),
                    }
                    result["success"] = True
                else:
                    print(f"  - 이미지 생성 실패 (응답 없음)")
                    result["error"] = "이미지 생성 실패"

            except Exception as e:
                print(f"  - 이미지 생성 오류: {e}")
                result["error"] = f"P5-OUTPUT 오류: {str(e)}"
        else:
            print(f"\n[P5-OUTPUT] visual_spec이 없어 이미지 생성 건너뜀")
            result["success"] = True  # visual_spec 없으면 이미지 생성 불필요

    except Exception as e:
        result["error"] = str(e)
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    return result


def main():
    """모든 과목 전체 파이프라인 테스트 실행"""
    print("\n" + "=" * 60)
    print("v3.0.0 전체 파이프라인 테스트 (이미지 생성 포함)")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    for subject, image_path in SAMPLE_IMAGES.items():
        result = test_full_pipeline(subject, image_path)
        results.append(result)

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    for r in results:
        status = "✅ 성공" if r["success"] else "❌ 실패"
        img_status = ""
        if r["generated_image"]:
            img_status = f" | 이미지: {r['generated_image']['image_id']}"
        print(f"  {status}: {r['subject']}{img_status}")
        if not r["success"] and r["error"]:
            print(f"         오류: {r['error'][:80]}...")

    print(f"\n총 {success_count}/{total_count} 과목 성공")

    # 생성된 이미지 목록
    print("\n" + "-" * 60)
    print("생성된 이미지 목록")
    print("-" * 60)
    for r in results:
        if r["generated_image"]:
            print(f"  [{r['subject']}] {r['generated_image']['path']}")

    # 결과 파일 저장
    output_dir = project_root / "output" / "test_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"full_pipeline_test_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n결과 저장: {output_file}")

    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
