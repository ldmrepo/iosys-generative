#!/usr/bin/env python3
"""기출 PDF에서 이미지 추출 스크립트"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def extract_suneung_images(
    subject: str = "math",
    year: int = 2025,
    pages: list[int] | None = None,
    dpi: int = 200,
):
    """수능 시험지에서 이미지 추출

    Args:
        subject: 과목 코드 (math, kor, eng, sci, soc)
        year: 시험 년도
        pages: 추출할 페이지 (None이면 전체)
        dpi: 이미지 해상도
    """
    try:
        from src.integrations.pdf_extractor import ExamPDFExtractor
    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        console.print("Install integration dependencies: pip install -e '.[integration]'")
        return

    extractor = ExamPDFExtractor()

    try:
        pdf_path = extractor.get_exam_pdf_path(subject, year)
        console.print(f"[cyan]PDF: {pdf_path.name}[/cyan]")
        console.print(f"Size: {pdf_path.stat().st_size / 1024:.1f} KB")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    output_dir = Path("samples") / "exams" / str(year) / subject
    console.print(f"[cyan]Output: {output_dir}[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Extracting {subject} exam images...", total=None)

        try:
            image_paths = extractor.extract_pages_as_images(
                pdf_path,
                output_dir,
                dpi=dpi,
                pages=pages,
            )
            progress.update(task, completed=True)

            console.print(f"\n[green]✓ Extracted {len(image_paths)} images[/green]")
            for path in image_paths[:5]:
                console.print(f"  {path}")
            if len(image_paths) > 5:
                console.print(f"  ... and {len(image_paths) - 5} more")

        except ImportError as e:
            progress.update(task, completed=True)
            console.print(f"\n[yellow]⚠ {e}[/yellow]")
            console.print("Install pdf2image: pip install pdf2image")
            console.print("Also install poppler: brew install poppler (macOS)")
            return

    return image_paths


def list_available_subjects(year: int = 2025):
    """사용 가능한 과목 목록 출력"""
    from src.integrations.pdf_extractor import ExamPDFExtractor

    extractor = ExamPDFExtractor()
    exams = extractor.list_available_exams(exam_type="suneung", year=year)

    # 과목별 그룹화
    subjects = {}
    for exam in exams:
        subj = exam.get("subject", "unknown")
        if subj not in subjects:
            subjects[subj] = {"exam": 0, "ans": 0}
        doc_type = exam.get("doc_type", "")
        if doc_type in subjects[subj]:
            subjects[subj][doc_type] += 1

    console.print(f"\n[bold]Available Subjects for {year} Suneung:[/bold]")
    for subj, counts in sorted(subjects.items()):
        console.print(f"  {subj}: {counts['exam']} exam, {counts['ans']} answer sheets")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract images from exam PDFs")
    parser.add_argument("--subject", "-s", default="math", help="Subject code")
    parser.add_argument("--year", "-y", type=int, default=2025, help="Exam year")
    parser.add_argument("--pages", "-p", type=str, help="Pages to extract (e.g., '1,2,3' or '1-5')")
    parser.add_argument("--dpi", "-d", type=int, default=200, help="Image DPI")
    parser.add_argument("--list", "-l", action="store_true", help="List available subjects")

    args = parser.parse_args()

    if args.list:
        list_available_subjects(args.year)
        return

    # 페이지 파싱
    pages = None
    if args.pages:
        if "-" in args.pages:
            start, end = args.pages.split("-")
            pages = list(range(int(start), int(end) + 1))
        else:
            pages = [int(p) for p in args.pages.split(",")]

    extract_suneung_images(
        subject=args.subject,
        year=args.year,
        pages=pages,
        dpi=args.dpi,
    )


if __name__ == "__main__":
    main()
