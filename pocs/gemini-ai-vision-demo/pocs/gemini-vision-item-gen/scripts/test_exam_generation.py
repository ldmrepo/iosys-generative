#!/usr/bin/env python3
"""기출 이미지 기반 문항 생성 테스트"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
import json

console = Console()


def analyze_exam_page(image_path: Path):
    """기출 페이지 분석"""
    from src.agents.vision_client import GeminiVisionClient

    client = GeminiVisionClient()

    prompt = """이 이미지는 2025학년도 대학수학능력시험 수학 문제지입니다.

이미지에 포함된 모든 문항을 분석하세요:

1. 각 문항 번호와 유형 (객관식/주관식)
2. 문항에 포함된 시각적 요소 (그래프, 도형, 표 등)
3. 각 문항의 수학적 개념/영역
4. 예상 난이도 (상/중/하)

JSON 형식으로 출력:
{
    "page_info": "페이지 설명",
    "items": [
        {
            "number": 문항번호,
            "type": "객관식/주관식",
            "visual_elements": ["그래프", "도형" 등],
            "math_concepts": ["개념1", "개념2"],
            "difficulty": "상/중/하"
        }
    ]
}
"""

    console.print(f"\n[cyan]Analyzing: {image_path.name}[/cyan]")

    result = client.analyze_image_with_agentic_vision(image_path, prompt)
    return result.get("text", "")


def generate_similar_item(image_path: Path, item_number: int):
    """특정 문항과 유사한 새 문항 생성"""
    from src.agents.vision_client import GeminiVisionClient

    client = GeminiVisionClient()

    prompt = f"""이 이미지는 2025학년도 수능 수학 문제지입니다.
이미지에서 {item_number}번 문항을 찾아 분석한 후, 유사한 새로운 문항을 생성하세요.

**요구사항:**
1. 원본 문항의 유형과 난이도 유지
2. 수치나 조건을 변경하여 새 문항 생성
3. 문항이 그래프/도형을 포함한다면, 새 문항에도 유사한 시각 자료 설명 포함

**출력 형식 (JSON):**
{{
    "original_analysis": {{
        "number": {item_number},
        "content_summary": "원본 문항 요약",
        "math_concept": "수학적 개념",
        "difficulty": "난이도"
    }},
    "generated_item": {{
        "stem": "새 문항의 발문",
        "choices": [
            {{"label": "①", "text": "선택지1"}},
            {{"label": "②", "text": "선택지2"}},
            {{"label": "③", "text": "선택지3"}},
            {{"label": "④", "text": "선택지4"}},
            {{"label": "⑤", "text": "선택지5"}}
        ],
        "correct_answer": "정답 번호",
        "explanation": "풀이 설명",
        "visual_description": "필요한 시각 자료 설명 (있을 경우)"
    }}
}}
"""

    console.print(f"\n[cyan]Generating similar item for #{item_number}...[/cyan]")

    result = client.analyze_image_with_agentic_vision(image_path, prompt)
    return result.get("text", "")


def main():
    """메인 테스트 실행"""
    exam_dir = Path("samples/exams/2025/math")

    if not exam_dir.exists():
        console.print("[red]Exam images not found. Run extract_with_fitz.py first.[/red]")
        return

    # 페이지 2 분석 (보통 객관식 문제 시작)
    page2 = exam_dir / "kice-2025-exam-math-high_page_02.png"

    console.print(Panel(
        "[bold]2025 수능 수학 기출 기반 문항 생성 테스트[/bold]\n\n"
        "1. 기출 페이지 분석\n"
        "2. 유사 문항 생성",
        title="Exam-Based Item Generation",
        border_style="blue"
    ))

    # Step 1: 페이지 분석
    console.print("\n[bold blue]== Step 1: 기출 페이지 분석 ==[/bold blue]")

    try:
        analysis = analyze_exam_page(page2)
        console.print("\n[bold]Page 2 Analysis:[/bold]")
        console.print(Panel(analysis[:2000] if len(analysis) > 2000 else analysis))

    except Exception as e:
        console.print(f"[red]Error analyzing page: {e}[/red]")
        import traceback
        traceback.print_exc()
        return

    # Step 2: 유사 문항 생성 (5번 문항 기준)
    console.print("\n[bold blue]== Step 2: 유사 문항 생성 ==[/bold blue]")

    try:
        generated = generate_similar_item(page2, item_number=5)
        console.print("\n[bold]Generated Similar Item:[/bold]")
        console.print(Panel(generated[:3000] if len(generated) > 3000 else generated))

        # JSON 파싱 시도
        try:
            # JSON 블록 추출
            if "```json" in generated:
                json_str = generated.split("```json")[1].split("```")[0]
            elif "```" in generated:
                json_str = generated.split("```")[1].split("```")[0]
            else:
                json_str = generated

            data = json.loads(json_str)

            # 생성된 문항 저장
            output_path = Path("output/items/exam_based_item.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            console.print(f"\n[green]✓ Saved to {output_path}[/green]")

        except json.JSONDecodeError:
            console.print("[yellow]⚠ Could not parse JSON, raw response saved[/yellow]")

    except Exception as e:
        console.print(f"[red]Error generating item: {e}[/red]")

    console.print("\n[bold green]Test completed![/bold green]")


if __name__ == "__main__":
    main()
