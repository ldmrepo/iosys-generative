#!/usr/bin/env python3
"""Data-Collect 통합 테스트 스크립트"""

from pathlib import Path
import sys

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def test_pdf_extractor():
    """PDF 추출기 테스트"""
    console.print("\n[bold blue]1. PDF Extractor Test[/bold blue]")

    try:
        from src.integrations.pdf_extractor import ExamPDFExtractor

        extractor = ExamPDFExtractor()

        # 사용 가능한 시험 목록 조회
        exams = extractor.list_available_exams(exam_type="suneung", year=2025)

        table = Table(title="Available 2025 Suneung Exams")
        table.add_column("Subject", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Filename", style="yellow")

        for exam in exams[:10]:  # 최대 10개만 표시
            table.add_row(
                exam.get("subject", ""),
                exam.get("doc_type", ""),
                exam.get("filename", "")
            )

        console.print(table)
        console.print(f"[green]✓ Found {len(exams)} exam files[/green]")

    except ImportError as e:
        console.print(f"[yellow]⚠ Import warning: {e}[/yellow]")
    except FileNotFoundError as e:
        console.print(f"[red]✗ File not found: {e}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_curriculum_parser():
    """교육과정 파서 테스트"""
    console.print("\n[bold blue]2. Curriculum Parser Test[/bold blue]")

    try:
        from src.integrations.curriculum_parser import CurriculumParser

        parser = CurriculumParser()

        # 수학 교육과정 PDF 경로 확인
        pdf_path = parser.get_curriculum_pdf_path("math")
        console.print(f"[green]✓ Math curriculum PDF: {pdf_path}[/green]")
        console.print(f"  Size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")

        # 텍스트 추출 테스트 (PyMuPDF 필요)
        try:
            text = parser.extract_text_from_pdf(pdf_path)
            console.print(f"  Extracted text length: {len(text):,} chars")

            # 성취기준 파싱 테스트
            standards = parser.parse_achievement_standards(text, "math")
            console.print(f"  Found {len(standards)} achievement standards")

            # 샘플 출력
            if standards:
                console.print("\n[bold]Sample Achievement Standards:[/bold]")
                for std in standards[:5]:
                    console.print(f"  {std['full_code']} {std['content'][:50]}...")

        except ImportError as e:
            console.print(f"[yellow]⚠ PyMuPDF not installed: {e}[/yellow]")
            console.print("  Install with: pip install pymupdf")

    except FileNotFoundError as e:
        console.print(f"[red]✗ File not found: {e}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_textbook_mapper():
    """교과서 매퍼 테스트"""
    console.print("\n[bold blue]3. Textbook Mapper Test[/bold blue]")

    try:
        from src.integrations.textbook_mapper import TextbookMapper

        mapper = TextbookMapper()

        # CSV 로드 테스트
        try:
            df = mapper.df
            console.print(f"[green]✓ Loaded {len(df):,} textbook records[/green]")

            # 출판사 목록
            publishers = mapper.get_all_publishers()
            console.print(f"  Publishers: {len(publishers)}")

            # 수학 교과서 조회
            math_books = mapper.get_textbooks_by_subject("math", "high")
            console.print(f"  High school math textbooks: {len(math_books)}")

            # 과목 커버리지
            coverage = mapper.get_subject_coverage()
            console.print("\n[bold]Subject Coverage by School Level:[/bold]")
            for level, subjects in coverage.items():
                console.print(f"  {level}: {', '.join(subjects)}")

        except ImportError as e:
            console.print(f"[yellow]⚠ pandas not installed: {e}[/yellow]")
            console.print("  Install with: pip install pandas")

    except FileNotFoundError as e:
        console.print(f"[red]✗ File not found: {e}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_settings():
    """설정 테스트"""
    console.print("\n[bold blue]4. Settings Test[/bold blue]")

    try:
        from src.core.config import get_settings

        settings = get_settings()

        console.print(Panel(
            f"[bold]Data-Collect Integration Settings[/bold]\n\n"
            f"data_collect_path: {settings.data_collect_path}\n"
            f"curriculum_version: {settings.curriculum_version}\n"
            f"exam_years: {settings.exam_years_list}\n"
            f"curriculum_dir: {settings.curriculum_dir}\n"
            f"exam_dir: {settings.exam_dir}\n"
            f"textbook_csv: {settings.textbook_csv}",
            title="Settings",
            border_style="green"
        ))

        # 경로 존재 확인
        paths = [
            ("curriculum_dir", settings.curriculum_dir),
            ("exam_dir", settings.exam_dir),
            ("textbook_csv", settings.textbook_csv),
        ]

        for name, path in paths:
            exists = path.exists()
            status = "✓" if exists else "✗"
            color = "green" if exists else "red"
            console.print(f"[{color}]{status} {name}: {path}[/{color}]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def main():
    """메인 테스트 실행"""
    console.print(Panel(
        "[bold]Data-Collect Integration Test[/bold]\n\n"
        "Testing integration with /Users/ldm/work/data-collect project",
        title="Gemini AI Vision POC",
        border_style="blue"
    ))

    test_settings()
    test_pdf_extractor()
    test_curriculum_parser()
    test_textbook_mapper()

    console.print("\n[bold green]Integration test completed![/bold green]")


if __name__ == "__main__":
    main()
