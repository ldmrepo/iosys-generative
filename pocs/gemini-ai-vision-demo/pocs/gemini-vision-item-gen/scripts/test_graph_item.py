#!/usr/bin/env python3
"""그래프/도형 문항 생성 테스트 - 페이지 5"""

from pathlib import Path
import sys
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel

console = Console()


def test_graph_page():
    """그래프가 포함된 페이지 분석 및 문항 생성"""
    from src.agents.vision_client import GeminiVisionClient

    client = GeminiVisionClient()

    # 페이지 5 (가장 큰 파일 - 그래프 포함 가능성 높음)
    image_path = Path("samples/exams/2025/math/kice-2025-exam-math-high_page_05.png")

    if not image_path.exists():
        console.print("[red]Image not found. Run extract_with_fitz.py first.[/red]")
        return

    console.print(Panel(
        "[bold]2025 수능 수학 그래프/도형 문항 생성 테스트[/bold]",
        border_style="blue"
    ))

    # Step 1: 페이지 분석
    console.print("\n[bold cyan]== 페이지 5 분석 ==[/bold cyan]")

    prompt1 = """이 이미지는 2025학년도 대학수학능력시험 수학 문제지입니다.

이미지에 포함된 모든 문항을 분석하세요. 특히 그래프, 도형, 표 등 시각적 요소에 주목하세요.

JSON 형식으로 출력:
{
    "page_info": "페이지 설명",
    "items": [
        {
            "number": 문항번호,
            "type": "객관식/주관식",
            "visual_elements": ["그래프 유형", "도형 유형" 등 상세히],
            "visual_description": "시각 요소의 상세 설명",
            "math_concepts": ["개념1", "개념2"],
            "difficulty": "상/중/하"
        }
    ]
}
"""

    console.print(f"Analyzing: {image_path.name}")
    result1 = client.analyze_image_with_agentic_vision(image_path, prompt1)
    analysis = result1.get("text", "")

    console.print("\n[bold]Analysis Result:[/bold]")
    console.print(Panel(analysis[:2500] if len(analysis) > 2500 else analysis))

    # Step 2: 그래프가 있는 문항에서 유사 문항 생성
    console.print("\n[bold cyan]== 그래프 기반 유사 문항 생성 ==[/bold cyan]")

    prompt2 = """이 이미지는 2025학년도 수능 수학 문제지입니다.

이미지에서 **그래프 또는 도형이 포함된 문항**을 하나 선택하여 분석한 후,
유사하지만 새로운 문항을 생성하세요.

**요구사항:**
1. 원본의 그래프/도형 유형과 수학적 개념 유지
2. 함수식, 수치, 조건 등을 변경
3. 새 문항에 필요한 그래프/도형을 상세히 설명

**출력 형식 (JSON):**
{
    "selected_item": {
        "number": "원본 문항 번호",
        "visual_type": "그래프/도형 유형",
        "math_concept": "수학적 개념"
    },
    "generated_item": {
        "item_id": "EXAM-GEN-001",
        "stem": "새 문항의 발문 (LaTeX 수식 포함)",
        "choices": [
            {"label": "①", "text": "선택지1"},
            {"label": "②", "text": "선택지2"},
            {"label": "③", "text": "선택지3"},
            {"label": "④", "text": "선택지4"},
            {"label": "⑤", "text": "선택지5"}
        ],
        "correct_answer": "정답",
        "explanation": "상세 풀이",
        "visual_specification": {
            "type": "그래프/도형 유형",
            "description": "그래프/도형의 상세 사양 (좌표, 함수식, 점 등)",
            "rendering_instructions": "시각화 구현을 위한 상세 지침"
        }
    }
}
"""

    result2 = client.analyze_image_with_agentic_vision(image_path, prompt2)
    generated = result2.get("text", "")

    console.print("\n[bold]Generated Item:[/bold]")
    console.print(Panel(generated[:3500] if len(generated) > 3500 else generated))

    # JSON 저장
    try:
        if "```json" in generated:
            json_str = generated.split("```json")[1].split("```")[0]
        elif "```" in generated:
            json_str = generated.split("```")[1].split("```")[0]
        else:
            json_str = generated

        data = json.loads(json_str)

        output_path = Path("output/items/exam_graph_item.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        console.print(f"\n[green]✓ Saved to {output_path}[/green]")

    except json.JSONDecodeError as e:
        console.print(f"[yellow]⚠ JSON parsing failed: {e}[/yellow]")

    console.print("\n[bold green]Test completed![/bold green]")


if __name__ == "__main__":
    test_graph_page()
