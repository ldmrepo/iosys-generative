#!/usr/bin/env python3
"""과목별 샘플 문항 생성 테스트

v3.0.0 파이프라인을 사용하여 과목별 1개씩 문항을 생성하고 결과를 확인합니다.
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


# 과목별 샘플 이미지 경로
SAMPLE_IMAGES = {
    "수학": "/root/work/mcp/iosys-generative/data/sample/수학/중1/F3DAC58DB0084A709FC4663D12B89CA4/images/P107A95A8.png",
    "과학": "/root/work/mcp/iosys-generative/data/sample/과학/중1/DC0AB613A6DF48129BD5751002F0104B/images/P0DEAEDD8.png",
    "영어": "/root/work/mcp/iosys-generative/data/sample/영어/중1/F94012572D9D4AAAADF70C972052C890/images/P042EC230.png",
    "국어": "/root/work/mcp/iosys-generative/data/sample/국어/중1/A9E010C88DD246429D2898549BED55EA/images/P11AD4C08.png",
    "사회": "/root/work/mcp/iosys-generative/data/sample/사회/초4/0E023EFCDFCE4B76BE7631E61B1A730C/images/P11BC6ED8.jpg",
    "역사": "/root/work/mcp/iosys-generative/data/sample/역사/초3/369E98BCD56745A6A884C9083D373D6A/images/P0E73D4B0.png",
}


def test_subject(subject: str, image_path: str) -> dict:
    """과목별 문항 생성 테스트

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
    }

    # 이미지 파일 존재 확인
    if not Path(image_path).exists():
        result["error"] = f"이미지 파일 없음: {image_path}"
        return result

    try:
        print(f"\n{'='*60}")
        print(f"[{subject}] 문항 생성 테스트")
        print(f"{'='*60}")
        print(f"이미지: {image_path}")

        # Vision Client 초기화
        vision_client = GeminiVisionClient()

        # P2-ANALYZE: 이미지 설명 생성
        print(f"\n[P2-ANALYZE] 이미지 분석 중...")
        desc_result = vision_client.describe_image(image_path)

        image_description = desc_result.get("image_description", "")
        content_type = desc_result.get("content_type", "")
        visual_elements = desc_result.get("visual_elements", [])

        print(f"  - 이미지 유형: {content_type}")
        print(f"  - 시각 요소: {visual_elements}")
        print(f"  - 설명 길이: {len(image_description)}자")

        result["p2_result"] = {
            "content_type": content_type,
            "visual_elements": visual_elements,
            "description_length": len(image_description),
            "description_preview": image_description[:200] + "..." if len(image_description) > 200 else image_description,
        }

        # P3-GENERATE: 문항 생성
        print(f"\n[P3-GENERATE] 문항 생성 중...")
        item_generator = ItemGeneratorAgent(vision_client=vision_client)

        item, gen_log = item_generator.generate_item_with_description(
            image_path=image_path,
            image_description=image_description,
            content_type=content_type,
            visual_elements=visual_elements,
            item_type=ItemType.GRAPH,  # 기본값
            difficulty=DifficultyLevel.MEDIUM,
        )

        if item:
            print(f"  - 문항 ID: {item.item_id}")
            print(f"  - 문제: {item.stem[:100]}..." if len(item.stem) > 100 else f"  - 문제: {item.stem}")
            print(f"  - 선지 수: {len(item.choices)}")
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
                print(f"\n[Visual Spec]")
                print(f"  - required: {item.visual_spec.required}")
                print(f"  - image_prompt: {item.visual_spec.image_prompt[:100]}..." if item.visual_spec.image_prompt and len(item.visual_spec.image_prompt) > 100 else f"  - image_prompt: {item.visual_spec.image_prompt}")
                print(f"  - subject_context: {item.visual_spec.subject_context}")
                print(f"  - style_guidance: {item.visual_spec.style_guidance}")

                result["visual_spec"] = {
                    "required": item.visual_spec.required,
                    "image_prompt": item.visual_spec.image_prompt,
                    "subject_context": item.visual_spec.subject_context,
                    "style_guidance": item.visual_spec.style_guidance,
                }
            else:
                print(f"\n[Visual Spec] 없음")

            result["success"] = True
        else:
            result["error"] = "문항 생성 실패 (파싱 오류)"

    except Exception as e:
        result["error"] = str(e)
        print(f"\n❌ 오류 발생: {e}")

    return result


def main():
    """모든 과목 테스트 실행"""
    print("\n" + "=" * 60)
    print("v3.0.0 과목별 문항 생성 테스트")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    for subject, image_path in SAMPLE_IMAGES.items():
        result = test_subject(subject, image_path)
        results.append(result)

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    for r in results:
        status = "✅ 성공" if r["success"] else "❌ 실패"
        print(f"  {status}: {r['subject']}")
        if not r["success"] and r["error"]:
            print(f"         오류: {r['error'][:50]}...")

    print(f"\n총 {success_count}/{total_count} 과목 성공")

    # 결과 파일 저장
    output_dir = project_root / "output" / "test_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"subject_test_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n결과 저장: {output_file}")

    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
