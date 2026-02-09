"""CLI 인터페이스"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.config import settings
from .core.schemas import ItemType, DifficultyLevel, ValidationStatus
from .agents.item_generator import ItemGeneratorAgent
from .validators.consistency_validator import ConsistencyValidator
from .validators.quality_checker import QualityChecker
from .utils.logger import AuditLogger
from .utils.image_utils import ImageProcessor

app = typer.Typer(
    name="agentic-vision",
    help="Gemini Agentic Vision 기반 AI 문항 생성 POC"
)
console = Console()


@app.command()
def generate(
    image: Path = typer.Argument(..., help="입력 이미지 경로", exists=True),
    item_type: str = typer.Option("graph", "--type", "-t", help="문항 유형: graph, geometry, measurement"),
    difficulty: str = typer.Option("medium", "--difficulty", "-d", help="난이도: easy, medium, hard"),
    validate: bool = typer.Option(True, "--validate/--no-validate", help="생성 후 검수 수행"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="출력 디렉토리")
):
    """이미지에서 문항을 생성합니다."""

    # 설정
    logger = AuditLogger()
    image_processor = ImageProcessor()

    # 이미지 유효성 검사
    is_valid, issues = image_processor.validate_image(image)
    if not is_valid:
        console.print(Panel(
            "\n".join(issues),
            title="[red]이미지 오류[/red]",
            border_style="red"
        ))
        raise typer.Exit(1)

    if issues:
        console.print(f"[yellow]경고:[/yellow] {', '.join(issues)}")

    # 유형 변환
    try:
        item_type_enum = ItemType(item_type)
    except ValueError:
        console.print(f"[red]잘못된 문항 유형: {item_type}[/red]")
        console.print(f"사용 가능: {[t.value for t in ItemType]}")
        raise typer.Exit(1)

    try:
        difficulty_enum = DifficultyLevel(difficulty)
    except ValueError:
        console.print(f"[red]잘못된 난이도: {difficulty}[/red]")
        console.print(f"사용 가능: {[d.value for d in DifficultyLevel]}")
        raise typer.Exit(1)

    console.print(Panel(
        f"이미지: {image}\n유형: {item_type_enum.value}\n난이도: {difficulty_enum.value}",
        title="[blue]문항 생성 시작[/blue]",
        border_style="blue"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # 문항 생성
        task = progress.add_task("[cyan]Agentic Vision으로 이미지 분석 중...", total=None)

        try:
            generator = ItemGeneratorAgent()
            item, gen_log = generator.generate_item(
                image_path=image,
                item_type=item_type_enum,
                difficulty=difficulty_enum
            )

            progress.update(task, description="[cyan]문항 생성 완료")
            logger.log_generation_complete(gen_log)

        except Exception as e:
            progress.stop()
            console.print(f"[red]문항 생성 실패: {e}[/red]")
            logger.log_error("generate", e)
            raise typer.Exit(1)

        if not item:
            progress.stop()
            console.print("[red]문항 파싱 실패. 응답 형식을 확인하세요.[/red]")
            raise typer.Exit(1)

        # 검수
        quality_report = None
        consistency_report = None
        if validate:
            progress.update(task, description="[cyan]문항 검수 중...")

            # 규칙 기반 검수
            quality_checker = QualityChecker()
            quality_report = quality_checker.check(item)

            # AI 기반 정합성 검수
            consistency_validator = ConsistencyValidator()
            consistency_report = consistency_validator.validate(item)

            logger.log_validation(quality_report)
            logger.log_validation(consistency_report)

            progress.update(task, description="[cyan]검수 완료")

    # 결과 출력
    console.print("\n")
    _display_item(item)

    if validate and quality_report and consistency_report:
        console.print("\n")
        _display_validation(quality_report, "규칙 기반 검수")
        console.print("\n")
        _display_validation(consistency_report, "AI 정합성 검수")

    # 파일 저장
    save_dir = output_dir or settings.output_dir / "items"
    item_path = generator.save_item(item, save_dir)
    log_path = generator.save_log(gen_log)

    console.print(f"\n[green]문항 저장됨:[/green] {item_path}")
    console.print(f"[green]로그 저장됨:[/green] {log_path}")


@app.command()
def validate_item(
    item_file: Path = typer.Argument(..., help="문항 JSON 파일 경로", exists=True),
    image: Optional[Path] = typer.Option(None, "--image", "-i", help="검수용 이미지 (미지정시 문항 내 경로 사용)")
):
    """기존 문항을 검수합니다."""
    import json
    from .core.schemas import ItemQuestion

    with open(item_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    item = ItemQuestion(**data)

    image_path = image or item.source_image

    console.print(Panel(
        f"문항 ID: {item.item_id}\n이미지: {image_path}",
        title="[blue]문항 검수[/blue]",
        border_style="blue"
    ))

    # 규칙 기반 검수
    quality_checker = QualityChecker()
    quality_report = quality_checker.check(item)

    # AI 정합성 검수
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]AI 검수 중...", total=None)

        consistency_validator = ConsistencyValidator()
        consistency_report = consistency_validator.validate(item, image_path)

        progress.update(task, description="[cyan]검수 완료")

    _display_validation(quality_report, "규칙 기반 검수")
    console.print("\n")
    _display_validation(consistency_report, "AI 정합성 검수")


@app.command()
def batch(
    input_dir: Path = typer.Argument(..., help="이미지 디렉토리", exists=True),
    item_type: str = typer.Option("graph", "--type", "-t", help="문항 유형"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="출력 디렉토리")
):
    """디렉토리 내 모든 이미지에서 문항을 일괄 생성합니다."""
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    images = [f for f in input_dir.iterdir() if f.suffix.lower() in image_extensions]

    if not images:
        console.print(f"[yellow]이미지를 찾을 수 없습니다: {input_dir}[/yellow]")
        raise typer.Exit(1)

    console.print(f"[blue]발견된 이미지: {len(images)}개[/blue]")

    results = {"success": 0, "fail": 0}

    for img in images:
        console.print(f"\n처리 중: {img.name}")
        try:
            # generate 명령 로직 재사용
            generator = ItemGeneratorAgent()
            item, gen_log = generator.generate_item(
                image_path=img,
                item_type=ItemType(item_type),
            )

            if item:
                save_dir = output_dir or settings.output_dir / "items"
                generator.save_item(item, save_dir)
                results["success"] += 1
                console.print(f"  [green]성공:[/green] {item.item_id}")
            else:
                results["fail"] += 1
                console.print(f"  [red]실패:[/red] 파싱 오류")

        except Exception as e:
            results["fail"] += 1
            console.print(f"  [red]실패:[/red] {e}")

    console.print(Panel(
        f"성공: {results['success']}개\n실패: {results['fail']}개",
        title="[blue]일괄 처리 결과[/blue]",
        border_style="blue"
    ))


@app.command()
def info():
    """현재 설정 정보를 표시합니다."""
    table = Table(title="Agentic Vision POC 설정")
    table.add_column("항목", style="cyan")
    table.add_column("값", style="green")

    table.add_row("Gemini 모델", settings.gemini_model)
    table.add_row("출력 디렉토리", str(settings.output_dir))
    table.add_row("로그 레벨", settings.log_level)
    table.add_row("최대 Vision 탐색", str(settings.max_vision_actions))
    table.add_row("최대 재생성", str(settings.max_regenerations))
    table.add_row("최소 신뢰도", str(settings.min_confidence))
    table.add_row("API 키 설정", "✓" if settings.google_api_key else "✗ (미설정)")

    console.print(table)


def _display_item(item):
    """문항 출력"""
    table = Table(title=f"생성된 문항 [{item.item_id}]", show_header=False)
    table.add_column("항목", style="cyan", width=12)
    table.add_column("내용", style="white")

    table.add_row("유형", item.item_type.value)
    table.add_row("난이도", item.difficulty.value)
    table.add_row("질문", item.stem)

    choices_text = "\n".join([f"{c.label}. {c.text}" for c in item.choices])
    table.add_row("선지", choices_text)
    table.add_row("정답", item.correct_answer)
    table.add_row("해설", item.explanation[:200] + "..." if len(item.explanation) > 200 else item.explanation)

    if item.evidence.extracted_facts:
        facts = "\n".join([f"• {f}" for f in item.evidence.extracted_facts[:5]])
        table.add_row("시각 근거", facts)

    console.print(table)


def _display_validation(report, title: str):
    """검수 결과 출력"""
    status_color = {
        ValidationStatus.PASS: "green",
        ValidationStatus.FAIL: "red",
        ValidationStatus.REVIEW: "yellow"
    }
    color = status_color.get(report.status, "white")

    table = Table(title=f"{title} [{report.status.value.upper()}]", border_style=color)
    table.add_column("구분", style="cyan", width=12)
    table.add_column("내용")

    if report.failure_codes:
        codes = ", ".join([f.value for f in report.failure_codes])
        table.add_row("실패 코드", f"[red]{codes}[/red]")

    if report.details:
        table.add_row("상세", "\n".join(report.details))

    if report.recommendations:
        table.add_row("권고사항", "\n".join(report.recommendations))

    console.print(table)


if __name__ == "__main__":
    app()
