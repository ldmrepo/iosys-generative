"""Parse curriculum PDFs to extract achievement standards."""

import re
from pathlib import Path
from typing import Optional

from ..core.config import get_settings


class CurriculumParser:
    """Parse 2022 revised curriculum PDFs to extract achievement standards.

    Achievement standards follow the format:
    [학년코드과목코드-성취기준번호] 성취기준 내용

    Examples:
        [9수01-01] 소인수분해의 뜻을 알고, 자연수를 소인수분해할 수 있다.
        [4과01-02] 물체의 무게를 측정하는 방법을 알고, 무게를 측정할 수 있다.
    """

    SUBJECT_PDF_MAP = {
        "math": "moe-2022-cur-math-all.pdf",
        "kor": "moe-2022-cur-kor-all.pdf",
        "eng": "moe-2022-cur-eng-all.pdf",
        "sci": "moe-2022-cur-sci-all.pdf",
        "soc": "moe-2022-cur-soc-all.pdf",
        "art": "moe-2022-cur-art-all.pdf",
        "pe": "moe-2022-cur-pe-all.pdf",
        "tech": "moe-2022-cur-tech-all.pdf",
    }

    # Achievement standard code pattern
    # Format: [학년(1-12)과목코드(가-힣)단원(01-99)-번호(01-99)]
    STANDARD_PATTERN = re.compile(
        r'\[(\d{1,2})([가-힣]+)(\d{2})-(\d{2})\]\s*(.+?)(?=\[|\n\n|\Z)',
        re.DOTALL
    )

    def __init__(self, data_collect_path: Optional[Path] = None):
        """Initialize parser with curriculum PDF directory.

        Args:
            data_collect_path: Path to data-collect project root
        """
        settings = get_settings()
        self.base_path = Path(data_collect_path or settings.data_collect_path)
        self.curriculum_path = (
            self.base_path / "data" / "raw" / "curriculum" / "ncic" / "2022"
        )

    def get_curriculum_pdf_path(self, subject: str) -> Path:
        """Get path to curriculum PDF for a subject.

        Args:
            subject: Subject code (math, kor, eng, sci, soc, etc.)

        Returns:
            Path to curriculum PDF

        Raises:
            ValueError: If subject is not supported
            FileNotFoundError: If PDF doesn't exist
        """
        if subject not in self.SUBJECT_PDF_MAP:
            raise ValueError(
                f"Unsupported subject: {subject}. "
                f"Available: {list(self.SUBJECT_PDF_MAP.keys())}"
            )

        pdf_path = self.curriculum_path / self.SUBJECT_PDF_MAP[subject]

        if not pdf_path.exists():
            raise FileNotFoundError(f"Curriculum PDF not found: {pdf_path}")

        return pdf_path

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text content from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text content
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PyMuPDF is required for PDF parsing. "
                "Install with: pip install pymupdf"
            )

        doc = fitz.open(pdf_path)
        text_parts = []

        for page in doc:
            text_parts.append(page.get_text())

        doc.close()
        return "\n".join(text_parts)

    def parse_achievement_standards(
        self,
        text: str,
        subject: Optional[str] = None,
    ) -> list[dict]:
        """Parse achievement standards from curriculum text.

        Args:
            text: Curriculum text content
            subject: Subject code for metadata

        Returns:
            List of achievement standard dicts with:
            - code: Full standard code (e.g., "9수01-01")
            - grade: Grade level (1-12)
            - subject_code: Subject code in Korean (e.g., "수")
            - unit: Unit number
            - number: Standard number within unit
            - content: Standard description
            - subject: Subject code in English (if provided)
        """
        standards = []
        matches = self.STANDARD_PATTERN.findall(text)

        for match in matches:
            grade, subj_code, unit, number, content = match
            standards.append({
                "code": f"{grade}{subj_code}{unit}-{number}",
                "full_code": f"[{grade}{subj_code}{unit}-{number}]",
                "grade": int(grade),
                "subject_code": subj_code,
                "unit": unit,
                "number": number,
                "content": content.strip(),
                "subject": subject,
            })

        return standards

    def extract_standards_for_subject(self, subject: str) -> list[dict]:
        """Extract all achievement standards for a subject.

        Args:
            subject: Subject code (math, kor, eng, etc.)

        Returns:
            List of achievement standard dicts
        """
        pdf_path = self.get_curriculum_pdf_path(subject)
        text = self.extract_text_from_pdf(pdf_path)
        return self.parse_achievement_standards(text, subject)

    def get_standards_by_grade(
        self,
        subject: str,
        grade: int,
    ) -> list[dict]:
        """Get achievement standards filtered by grade.

        Args:
            subject: Subject code
            grade: Grade level (1-12)

        Returns:
            Filtered list of standards
        """
        standards = self.extract_standards_for_subject(subject)
        return [s for s in standards if s["grade"] == grade]

    def get_standards_by_unit(
        self,
        subject: str,
        grade: int,
        unit: str,
    ) -> list[dict]:
        """Get achievement standards filtered by grade and unit.

        Args:
            subject: Subject code
            grade: Grade level
            unit: Unit number (e.g., "01", "02")

        Returns:
            Filtered list of standards
        """
        standards = self.get_standards_by_grade(subject, grade)
        return [s for s in standards if s["unit"] == unit]

    def build_standards_index(
        self,
        subjects: Optional[list[str]] = None,
    ) -> dict:
        """Build searchable index of all achievement standards.

        Args:
            subjects: List of subject codes (default: all supported)

        Returns:
            Dict with standards indexed by code
        """
        if subjects is None:
            subjects = list(self.SUBJECT_PDF_MAP.keys())

        index = {}
        for subject in subjects:
            try:
                standards = self.extract_standards_for_subject(subject)
                for std in standards:
                    index[std["full_code"]] = std
            except (FileNotFoundError, ImportError) as e:
                print(f"Warning: Could not process {subject}: {e}")

        return index


def get_achievement_standards(
    subject: str,
    grade: Optional[int] = None,
    data_collect_path: Optional[str] = None,
) -> list[dict]:
    """Convenience function to get achievement standards.

    Args:
        subject: Subject code (math, kor, eng, sci, soc)
        grade: Filter by grade (optional)
        data_collect_path: Path to data-collect project

    Returns:
        List of achievement standard dicts
    """
    parser = CurriculumParser(Path(data_collect_path) if data_collect_path else None)

    if grade is not None:
        return parser.get_standards_by_grade(subject, grade)

    return parser.extract_standards_for_subject(subject)
