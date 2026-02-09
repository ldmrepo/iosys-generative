"""Map textbook metadata to subjects and grades."""

from pathlib import Path
from typing import Optional

from ..core.config import get_settings


class TextbookMapper:
    """Map and query textbook metadata from data-collect CSV.

    The CSV contains textbook information including:
    - 검인정구분: Approval type (검정/인정/국정)
    - 교지명: Material type (교과서/지도서)
    - 학교급명: School level (초등학교/중학교/고등학교)
    - 출판사: Publisher
    - 도서명: Book title
    - 저자: Author
    - 개정구분: Curriculum version (2015개정)
    - 시작년도: Start year
    """

    SCHOOL_LEVEL_MAP = {
        "elem": "초등학교",
        "mid": "중학교",
        "high": "고등학교",
    }

    SUBJECT_KEYWORDS = {
        "math": ["수학", "Mathematics"],
        "kor": ["국어", "Korean"],
        "eng": ["영어", "English"],
        "sci": ["과학", "Science", "물리", "화학", "생명과학", "지구과학"],
        "soc": ["사회", "역사", "지리", "윤리", "도덕"],
        "art": ["음악", "미술"],
        "pe": ["체육"],
        "tech": ["기술", "가정", "정보"],
    }

    def __init__(self, data_collect_path: Optional[Path] = None):
        """Initialize mapper with textbook CSV path.

        Args:
            data_collect_path: Path to data-collect project root
        """
        settings = get_settings()
        self.base_path = Path(data_collect_path or settings.data_collect_path)
        self.csv_path = (
            self.base_path / "data" / "raw" / "textbook" / "data-2015-meta-textbook-all.csv"
        )
        self._df = None

    def _load_dataframe(self):
        """Lazy load the CSV dataframe."""
        if self._df is None:
            try:
                import pandas as pd
            except ImportError:
                raise ImportError(
                    "pandas is required for textbook mapping. "
                    "Install with: pip install pandas"
                )

            if not self.csv_path.exists():
                raise FileNotFoundError(f"Textbook CSV not found: {self.csv_path}")

            self._df = pd.read_csv(self.csv_path, encoding='utf-8')

        return self._df

    @property
    def df(self):
        """Get the textbook dataframe."""
        return self._load_dataframe()

    def get_all_publishers(self) -> list[str]:
        """Get list of all publishers.

        Returns:
            Sorted list of unique publisher names
        """
        return sorted(self.df['출판사'].unique().tolist())

    def get_textbooks_by_school_level(
        self,
        school_level: str,
        material_type: str = "교과서",
    ) -> list[dict]:
        """Get textbooks filtered by school level.

        Args:
            school_level: Level code (elem, mid, high) or Korean name
            material_type: Material type (교과서, 지도서)

        Returns:
            List of textbook metadata dicts
        """
        # Convert level code to Korean if needed
        if school_level in self.SCHOOL_LEVEL_MAP:
            school_level = self.SCHOOL_LEVEL_MAP[school_level]

        filtered = self.df[
            (self.df['학교급명'] == school_level) &
            (self.df['교지명'] == material_type)
        ]

        return filtered.to_dict('records')

    def get_textbooks_by_subject(
        self,
        subject: str,
        school_level: Optional[str] = None,
    ) -> list[dict]:
        """Get textbooks filtered by subject.

        Args:
            subject: Subject code (math, kor, etc.) or Korean keyword
            school_level: Optional school level filter

        Returns:
            List of textbook metadata dicts
        """
        # Get subject keywords
        if subject in self.SUBJECT_KEYWORDS:
            keywords = self.SUBJECT_KEYWORDS[subject]
        else:
            keywords = [subject]

        # Build filter condition
        mask = self.df['도서명'].str.contains(
            '|'.join(keywords),
            case=False,
            na=False
        )

        if school_level:
            if school_level in self.SCHOOL_LEVEL_MAP:
                school_level = self.SCHOOL_LEVEL_MAP[school_level]
            mask &= (self.df['학교급명'] == school_level)

        filtered = self.df[mask]
        return filtered.to_dict('records')

    def get_textbooks_by_publisher(
        self,
        publisher: str,
        school_level: Optional[str] = None,
    ) -> list[dict]:
        """Get textbooks filtered by publisher.

        Args:
            publisher: Publisher name (partial match)
            school_level: Optional school level filter

        Returns:
            List of textbook metadata dicts
        """
        mask = self.df['출판사'].str.contains(publisher, case=False, na=False)

        if school_level:
            if school_level in self.SCHOOL_LEVEL_MAP:
                school_level = self.SCHOOL_LEVEL_MAP[school_level]
            mask &= (self.df['학교급명'] == school_level)

        filtered = self.df[mask]
        return filtered.to_dict('records')

    def get_subject_coverage(self) -> dict:
        """Get summary of subjects covered at each school level.

        Returns:
            Dict mapping school level to list of subjects
        """
        coverage = {}

        for level_code, level_name in self.SCHOOL_LEVEL_MAP.items():
            textbooks = self.get_textbooks_by_school_level(level_name)

            subjects = set()
            for tb in textbooks:
                title = tb.get('도서명', '')
                for subj_code, keywords in self.SUBJECT_KEYWORDS.items():
                    if any(kw in title for kw in keywords):
                        subjects.add(subj_code)

            coverage[level_code] = sorted(subjects)

        return coverage

    def search_textbooks(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict]:
        """Search textbooks by title, publisher, or author.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching textbook dicts
        """
        mask = (
            self.df['도서명'].str.contains(query, case=False, na=False) |
            self.df['출판사'].str.contains(query, case=False, na=False) |
            self.df['저자'].str.contains(query, case=False, na=False)
        )

        filtered = self.df[mask].head(limit)
        return filtered.to_dict('records')

    def get_grade_mapping(self, school_level: str) -> dict:
        """Get grade range for a school level.

        Args:
            school_level: Level code or Korean name

        Returns:
            Dict with grade range info
        """
        grade_ranges = {
            "elem": {"start": 1, "end": 6, "name": "초등학교"},
            "mid": {"start": 7, "end": 9, "name": "중학교"},
            "high": {"start": 10, "end": 12, "name": "고등학교"},
            "초등학교": {"start": 1, "end": 6, "name": "초등학교"},
            "중학교": {"start": 7, "end": 9, "name": "중학교"},
            "고등학교": {"start": 10, "end": 12, "name": "고등학교"},
        }

        return grade_ranges.get(school_level, {})


def get_textbook_info(
    subject: str,
    school_level: Optional[str] = None,
    data_collect_path: Optional[str] = None,
) -> list[dict]:
    """Convenience function to get textbook information.

    Args:
        subject: Subject code (math, kor, eng, etc.)
        school_level: School level filter (elem, mid, high)
        data_collect_path: Path to data-collect project

    Returns:
        List of textbook metadata dicts
    """
    mapper = TextbookMapper(Path(data_collect_path) if data_collect_path else None)
    return mapper.get_textbooks_by_subject(subject, school_level)
