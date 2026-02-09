#!/usr/bin/env python3
"""PyMuPDF(fitz)를 사용한 PDF 이미지 추출 스크립트"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import fitz  # PyMuPDF
from rich.console import Console
from rich.progress import track

console = Console()


def extract_pdf_pages(
    pdf_path: Path,
    output_dir: Path,
    pages: list[int] | None = None,
    dpi: int = 200,
) -> list[Path]:
    """PDF 페이지를 이미지로 추출 (PyMuPDF 사용)

    Args:
        pdf_path: PDF 파일 경로
        output_dir: 출력 디렉토리
        pages: 추출할 페이지 (1-indexed), None이면 전체
        dpi: 이미지 해상도

    Returns:
        추출된 이미지 경로 리스트
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if pages is None:
        pages = list(range(1, total_pages + 1))

    # DPI를 zoom factor로 변환 (72 DPI 기준)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    image_paths = []
    for page_num in track(pages, description="Extracting pages..."):
        if page_num < 1 or page_num > total_pages:
            console.print(f"[yellow]⚠ Page {page_num} out of range (1-{total_pages})[/yellow]")
            continue

        page = doc[page_num - 1]  # 0-indexed
        pix = page.get_pixmap(matrix=mat)

        img_path = output_dir / f"{pdf_path.stem}_page_{page_num:02d}.png"
        pix.save(img_path)
        image_paths.append(img_path)

    doc.close()
    return image_paths


def main():
    from src.core.config import get_settings

    settings = get_settings()

    # 수학 수능 PDF 경로
    pdf_path = (
        Path(settings.data_collect_path) /
        "data/raw/examinations/suneung/2022/2025/kice-2025-exam-math-high.pdf"
    )

    if not pdf_path.exists():
        console.print(f"[red]PDF not found: {pdf_path}[/red]")
        return

    console.print(f"[cyan]PDF: {pdf_path.name}[/cyan]")
    console.print(f"Size: {pdf_path.stat().st_size / 1024:.1f} KB")

    # 출력 디렉토리
    output_dir = Path("samples/exams/2025/math")

    # 처음 5페이지만 추출
    pages = [1, 2, 3, 4, 5]

    console.print(f"[cyan]Extracting pages {pages}...[/cyan]")

    image_paths = extract_pdf_pages(
        pdf_path=pdf_path,
        output_dir=output_dir,
        pages=pages,
        dpi=200,
    )

    console.print(f"\n[green]✓ Extracted {len(image_paths)} images:[/green]")
    for path in image_paths:
        size_kb = path.stat().st_size / 1024
        console.print(f"  {path.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
