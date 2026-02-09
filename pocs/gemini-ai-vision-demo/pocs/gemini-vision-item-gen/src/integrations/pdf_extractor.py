"""PDF to Image extraction for exam papers."""

from pathlib import Path
from typing import Optional

from ..core.config import get_settings


class ExamPDFExtractor:
    """Extract images from exam PDF files.

    Integrates with data-collect project to extract exam paper images
    for analysis and similar item generation.
    """

    SUBJECT_MAP = {
        "math": "수학",
        "kor": "국어",
        "eng": "영어",
        "sci": "과학",
        "soc": "사회",
        "kor_hist": "한국사",
    }

    def __init__(self, data_collect_path: Optional[Path] = None):
        """Initialize extractor with data-collect path.

        Args:
            data_collect_path: Path to data-collect project root.
                             Uses settings default if not provided.
        """
        settings = get_settings()
        self.base_path = Path(data_collect_path or settings.data_collect_path)
        self.exam_path = self.base_path / "data" / "raw" / "examinations"

    def get_exam_pdf_path(
        self,
        subject: str,
        year: int,
        exam_type: str = "suneung",
        doc_type: str = "exam",
    ) -> Path:
        """Get path to exam PDF file.

        Args:
            subject: Subject code (math, kor, eng, sci, soc)
            year: Exam year (e.g., 2025)
            exam_type: Type of exam (suneung, mocktest, hakpyeong)
            doc_type: Document type (exam, ans)

        Returns:
            Path to PDF file

        Raises:
            FileNotFoundError: If PDF file doesn't exist
        """
        # suneung uses curriculum version subdirectory
        if exam_type == "suneung":
            pdf_path = self.exam_path / exam_type / "2022" / str(year) / f"kice-{year}-{doc_type}-{subject}-high.pdf"
        else:
            pdf_path = self.exam_path / exam_type / str(year) / f"kice-{year}-{doc_type}-{subject}-high.pdf"

        if not pdf_path.exists():
            raise FileNotFoundError(f"Exam PDF not found: {pdf_path}")

        return pdf_path

    def list_available_exams(
        self,
        exam_type: str = "suneung",
        year: Optional[int] = None,
    ) -> list[dict]:
        """List available exam PDFs.

        Args:
            exam_type: Type of exam (suneung, mocktest, hakpyeong)
            year: Filter by year (optional)

        Returns:
            List of available exam metadata dicts
        """
        exams = []

        if exam_type == "suneung":
            search_path = self.exam_path / exam_type / "2022"
        else:
            search_path = self.exam_path / exam_type

        if not search_path.exists():
            return exams

        for pdf_file in search_path.rglob("*.pdf"):
            # Parse filename: kice-{year}-{type}-{subject}-{level}.pdf
            parts = pdf_file.stem.split("-")
            if len(parts) >= 4:
                exam_year = int(parts[1]) if parts[1].isdigit() else None
                if year and exam_year != year:
                    continue

                exams.append({
                    "path": pdf_file,
                    "year": exam_year,
                    "doc_type": parts[2],
                    "subject": parts[3],
                    "filename": pdf_file.name,
                })

        return sorted(exams, key=lambda x: (x.get("year", 0), x.get("subject", "")))

    def extract_pages_as_images(
        self,
        pdf_path: Path,
        output_dir: Path,
        dpi: int = 200,
        pages: Optional[list[int]] = None,
    ) -> list[Path]:
        """Extract PDF pages as images.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save extracted images
            dpi: Image resolution (default 200 for balance of quality/size)
            pages: Specific pages to extract (1-indexed), None for all

        Returns:
            List of paths to extracted images

        Note:
            Requires pdf2image and poppler-utils to be installed.
        """
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError(
                "pdf2image is required for PDF extraction. "
                "Install with: pip install pdf2image\n"
                "Also requires poppler-utils: brew install poppler (macOS)"
            )

        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert PDF to images
        if pages:
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=min(pages),
                last_page=max(pages),
            )
            page_nums = pages
        else:
            images = convert_from_path(pdf_path, dpi=dpi)
            page_nums = list(range(1, len(images) + 1))

        # Save images
        paths = []
        for img, page_num in zip(images, page_nums):
            img_path = output_dir / f"{pdf_path.stem}_page_{page_num:02d}.png"
            img.save(img_path, "PNG")
            paths.append(img_path)

        return paths

    def extract_exam_images(
        self,
        subject: str,
        year: int,
        output_dir: Optional[Path] = None,
        dpi: int = 200,
    ) -> list[Path]:
        """Extract all pages from an exam PDF as images.

        Args:
            subject: Subject code (math, kor, eng, etc.)
            year: Exam year
            output_dir: Output directory (default: samples/exams/{year}/{subject})
            dpi: Image resolution

        Returns:
            List of paths to extracted images
        """
        pdf_path = self.get_exam_pdf_path(subject, year)

        if output_dir is None:
            output_dir = Path("samples") / "exams" / str(year) / subject

        return self.extract_pages_as_images(pdf_path, output_dir, dpi)


def extract_suneung_images(
    subject: str,
    year: int = 2025,
    data_collect_path: Optional[str] = None,
) -> list[Path]:
    """Convenience function to extract KICE exam images.

    Args:
        subject: Subject code (math, kor, eng, sci, soc)
        year: Exam year
        data_collect_path: Path to data-collect project

    Returns:
        List of extracted image paths
    """
    extractor = ExamPDFExtractor(Path(data_collect_path) if data_collect_path else None)
    return extractor.extract_exam_images(subject, year)
