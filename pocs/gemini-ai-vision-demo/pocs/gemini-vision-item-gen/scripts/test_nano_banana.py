#!/usr/bin/env python3
"""Nano Banana Pro 이미지 생성 테스트

생성된 문항의 visual_specification을 사용하여 실제 이미지를 생성합니다.
"""

import json
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel

console = Console()


def test_nano_banana_generation():
    """Nano Banana Pro로 이미지 생성 테스트"""
    from src.agents.nano_banana_client import NanoBananaClient

    console.print(Panel(
        "[bold]Nano Banana Pro (Gemini 3 Pro Image) 테스트[/bold]\n\n"
        "생성된 문항의 시각화 사양으로 실제 이미지를 생성합니다.",
        border_style="blue"
    ))

    # 클라이언트 초기화
    try:
        client = NanoBananaClient()
        console.print("[green]✓ Nano Banana Pro 클라이언트 초기화 완료[/green]")
    except Exception as e:
        console.print(f"[red]✗ 클라이언트 초기화 실패: {e}[/red]")
        return

    output_dir = Path("output/nano_banana")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 테스트 1: 기본 막대 그래프
    console.print("\n[bold cyan]== 테스트 1: 막대 그래프 생성 ==[/bold cyan]")
    try:
        data = {"1월": 83, "2월": 29, "3월": 86, "4월": 58, "5월": 67, "6월": 81}
        image_bytes = client.generate_chart(
            chart_type="막대 그래프",
            data=data,
            title="월별 판매량",
            style="educational"
        )
        path = client.save_image(image_bytes, output_dir / "bar_chart_nano.png")
        console.print(f"[green]✓ 생성 완료: {path}[/green]")
        console.print(f"  크기: {path.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        console.print(f"[red]✗ 실패: {e}[/red]")

    # 테스트 2: 삼각형 도형
    console.print("\n[bold cyan]== 테스트 2: 기하 도형 (삼각형) ==[/bold cyan]")
    try:
        image_bytes = client.generate_geometry(
            shape_type="삼각형 ABC",
            vertices={
                "A": "상단 중앙",
                "B": "좌측 하단",
                "C": "우측 하단"
            },
            measurements={
                "AB": "15cm",
                "BC": "19cm",
                "AC": "12cm"
            },
            angles={"B": "60°"}
        )
        path = client.save_image(image_bytes, output_dir / "triangle_nano.png")
        console.print(f"[green]✓ 생성 완료: {path}[/green]")
        console.print(f"  크기: {path.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        console.print(f"[red]✗ 실패: {e}[/red]")

    # 테스트 3: 생성된 문항의 visual_specification 사용
    console.print("\n[bold cyan]== 테스트 3: 문항 시각화 사양 기반 생성 ==[/bold cyan]")

    graph_item_path = Path("output/items/exam_graph_item.json")
    if graph_item_path.exists():
        with open(graph_item_path, "r", encoding="utf-8") as f:
            item_data = json.load(f)

        visual_spec = item_data.get("generated_item", {}).get("visual_specification", {})

        if visual_spec:
            console.print(f"[cyan]시각화 유형: {visual_spec.get('type', '-')}[/cyan]")
            console.print(f"[cyan]설명: {visual_spec.get('description', '-')[:100]}...[/cyan]")

            try:
                image_bytes = client.generate_from_specification(visual_spec)
                path = client.save_image(image_bytes, output_dir / "exam_visual_nano.png")
                console.print(f"[green]✓ 생성 완료: {path}[/green]")
                console.print(f"  크기: {path.stat().st_size / 1024:.1f} KB")
            except Exception as e:
                console.print(f"[red]✗ 실패: {e}[/red]")
        else:
            console.print("[yellow]⚠ 시각화 사양이 없습니다.[/yellow]")
    else:
        console.print("[yellow]⚠ exam_graph_item.json 파일이 없습니다.[/yellow]")

    # 테스트 4: 함수 그래프 (3차 함수)
    console.print("\n[bold cyan]== 테스트 4: 함수 그래프 ==[/bold cyan]")
    try:
        image_bytes = client.generate_function_graph(
            function_expr="x^3 - 3x^2 - 4x + 12",
            x_range=(-1, 5),
            y_range=(-5, 15),
            special_points=[
                ("O", 0, 0),
                ("P", 4, 12),
                ("Q", 1.3, 3.9)  # 근사값
            ],
            regions=[
                {"label": "A", "description": "곡선과 직선 OP 사이 (0~Q)", "color": "light gray"},
                {"label": "B", "description": "직선 OP와 곡선 사이 (Q~P)", "color": "dark gray"}
            ]
        )
        path = client.save_image(image_bytes, output_dir / "function_graph_nano.png")
        console.print(f"[green]✓ 생성 완료: {path}[/green]")
        console.print(f"  크기: {path.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        console.print(f"[red]✗ 실패: {e}[/red]")

    # 결과 요약
    console.print("\n[bold green]== 테스트 완료 ==[/bold green]")
    generated_files = list(output_dir.glob("*.png"))
    console.print(f"생성된 이미지: {len(generated_files)}개")
    for f in generated_files:
        console.print(f"  - {f.name} ({f.stat().st_size / 1024:.1f} KB)")

    if generated_files:
        console.print(f"\n[cyan]폴더 열기: open {output_dir}[/cyan]")


if __name__ == "__main__":
    test_nano_banana_generation()
