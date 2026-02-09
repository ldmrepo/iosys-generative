"""IML XML parser for extracting question data."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from ..core.config import Settings, get_settings
from ..core.schemas import IMLItem
from ..utils.encoding import read_file_with_encoding


class IMLParser:
    """Parser for IML XML files."""

    def __init__(self, settings: Settings | None = None):
        """
        Initialize the parser.

        Args:
            settings: Application settings (uses default if not provided)
        """
        self.settings = settings or get_settings()

    def parse_file(self, file_path: Path) -> IMLItem | None:
        """
        Parse an IML file and extract item data.

        Args:
            file_path: Path to the IML file

        Returns:
            Parsed IMLItem or None if parsing fails
        """
        try:
            content = read_file_with_encoding(file_path)
            return self._parse_content(content, file_path)
        except Exception as e:
            # Log error but don't raise - return None for failed parses
            print(f"Error parsing {file_path}: {e}")
            return None

    def _parse_content(self, content: str, file_path: Path) -> IMLItem | None:
        """
        Parse IML content string.

        Args:
            content: IML XML content
            file_path: Original file path (for reference)

        Returns:
            Parsed IMLItem or None
        """
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return None

        # Find the 문항 element (can be under 단위문항, 그룹문항, or 지문)
        quiz_elem = self._find_quiz_element(root)
        if quiz_elem is None:
            return None

        # Extract attributes
        attrs = dict(quiz_elem.attrib)
        item_id = attrs.get("id", "")

        if not item_id:
            return None

        # Parse classification codes
        subject_code = self._extract_code(attrs.get("cls4", ""))
        grade_code = self._extract_code(attrs.get("cls3", ""))
        school_level_code = self._extract_code(attrs.get("cls2", ""))
        question_type_code = self._extract_code(attrs.get("qt", ""))
        difficulty_code = self._extract_code(attrs.get("df", ""))

        # Map codes to names
        subject = self.settings.SUBJECT_CODES.get(subject_code, "")
        school_level = self.settings.SCHOOL_LEVEL_CODES.get(school_level_code, "")
        grade = self._get_grade_name(grade_code, school_level_code)
        question_type = self.settings.QUESTION_TYPE_CODES.get(question_type_code, "")
        difficulty = self.settings.DIFFICULTY_CODES.get(difficulty_code, "")

        # Parse content
        stem = self._extract_stem(quiz_elem)
        choices = self._extract_choices(quiz_elem)
        answer = self._extract_answer(quiz_elem)
        explanation = self._extract_explanation(quiz_elem)
        hint = self._extract_hint(quiz_elem)
        direction = self._extract_direction(quiz_elem)

        # Parse images
        images = self._extract_images(quiz_elem, file_path)

        # Parse math expressions
        math_expressions = self._extract_math(quiz_elem)

        # Parse keywords
        keywords = self._extract_keywords(attrs)

        return IMLItem(
            id=item_id,
            raw_path=file_path,
            subject=subject,
            subject_code=subject_code,
            grade=grade,
            grade_code=grade_code,
            school_level=school_level,
            school_level_code=school_level_code,
            question_type=question_type,
            question_type_code=question_type_code,
            difficulty=difficulty,
            difficulty_code=difficulty_code,
            stem=stem,
            choices=choices,
            answer=answer,
            explanation=explanation,
            hint=hint,
            direction=direction,
            images=images,
            has_images=len(images) > 0,
            math_expressions=math_expressions,
            has_math=len(math_expressions) > 0,
            keywords=keywords,
            cls1=attrs.get("cls1", ""),
            cls5=attrs.get("cls5", ""),
            cls6=attrs.get("cls6", ""),
            cls7=attrs.get("cls7", ""),
            cls8=attrs.get("cls8", ""),
            raw_attributes=attrs,
        )

    def _find_quiz_element(self, root: ET.Element) -> ET.Element | None:
        """Find the main quiz element in the XML tree."""
        # Check for 단위문항 > 문항
        unit_quiz = root.find(".//단위문항/문항")
        if unit_quiz is not None:
            return unit_quiz

        # Check for 단위문항 > 지문 (passage-based question)
        passage = root.find(".//단위문항/지문")
        if passage is not None:
            return passage

        # Check for 그룹문항 > 문항
        group_quiz = root.find(".//그룹문항/문항")
        if group_quiz is not None:
            return group_quiz

        # Check direct 문항
        direct_quiz = root.find(".//문항")
        if direct_quiz is not None:
            return direct_quiz

        return None

    def _extract_code(self, value: str) -> str:
        """
        Extract the numeric code from a classification value.

        Example: "03 수학" -> "03"
        """
        if not value:
            return ""

        # Split by space and take the first part
        parts = value.strip().split(maxsplit=1)
        if parts:
            return parts[0]
        return ""

    def _get_grade_name(self, grade_code: str, school_level_code: str) -> str:
        """
        Get the grade name based on code and school level.

        Args:
            grade_code: Grade code (e.g., "08")
            school_level_code: School level code (e.g., "02" for middle school)

        Returns:
            Grade name (e.g., "중2")
        """
        if not grade_code:
            return ""

        # Check based on school level
        if school_level_code == "01":  # Elementary
            return self.settings.GRADE_CODES_ELEMENTARY.get(grade_code, "")
        elif school_level_code == "02":  # Middle school
            grade = self.settings.GRADE_CODES_MIDDLE.get(grade_code, "")
            if grade:
                return grade
            # Try alternative coding for middle school (01-03)
            alt_mapping = {"01": "중1", "02": "중2", "03": "중3"}
            return alt_mapping.get(grade_code, "")
        elif school_level_code == "03":  # High school
            grade = self.settings.GRADE_CODES_HIGH.get(grade_code, "")
            if grade:
                return grade
            alt_mapping = {"01": "고1", "02": "고2", "03": "고3"}
            return alt_mapping.get(grade_code, "")

        # Fallback: try to infer from code
        code_int = int(grade_code) if grade_code.isdigit() else 0
        if 1 <= code_int <= 6:
            return f"초{code_int}"
        elif 7 <= code_int <= 9:
            return f"중{code_int - 6}"
        elif 10 <= code_int <= 12:
            return f"고{code_int - 9}"

        return ""

    def _extract_text_from_element(self, elem: ET.Element | None) -> str:
        """
        Recursively extract all text content from an element.

        Args:
            elem: XML element

        Returns:
            Combined text content
        """
        if elem is None:
            return ""

        texts: list[str] = []

        # Get element's own text
        if elem.text:
            texts.append(elem.text.strip())

        # Recursively get text from children
        for child in elem:
            child_text = self._extract_text_from_element(child)
            if child_text:
                texts.append(child_text)

            # Also get tail text
            if child.tail:
                texts.append(child.tail.strip())

        return " ".join(filter(None, texts))

    def _extract_stem(self, quiz_elem: ET.Element) -> str:
        """Extract the question stem (물음) from the quiz element."""
        # Try 문제/물음 first
        quest = quiz_elem.find(".//문제/물음")
        if quest is not None:
            return self._extract_text_from_element(quest)

        # Try 물음 directly
        quest = quiz_elem.find(".//물음")
        if quest is not None:
            return self._extract_text_from_element(quest)

        return ""

    def _extract_choices(self, quiz_elem: ET.Element) -> list[str]:
        """Extract answer choices (답항) from the quiz element."""
        choices: list[str] = []

        # Find all 답항 elements
        for choice in quiz_elem.findall(".//문제/답항"):
            text = self._extract_text_from_element(choice)
            if text:
                choices.append(text)

        return choices

    def _extract_answer(self, quiz_elem: ET.Element) -> str:
        """Extract the correct answer (정답) from the quiz element."""
        answer_elem = quiz_elem.find(".//정답")
        if answer_elem is not None:
            return self._extract_text_from_element(answer_elem)
        return ""

    def _extract_explanation(self, quiz_elem: ET.Element) -> str:
        """Extract the explanation (해설) from the quiz element."""
        explanation = quiz_elem.find(".//해설")
        if explanation is not None:
            return self._extract_text_from_element(explanation)
        return ""

    def _extract_hint(self, quiz_elem: ET.Element) -> str:
        """Extract the hint (힌트) from the quiz element."""
        hint = quiz_elem.find(".//힌트")
        if hint is not None:
            return self._extract_text_from_element(hint)
        return ""

    def _extract_direction(self, quiz_elem: ET.Element) -> str:
        """Extract the direction (지시) from the quiz element."""
        direction = quiz_elem.find(".//지시")
        if direction is not None:
            return self._extract_text_from_element(direction)
        return ""

    def _extract_images(self, quiz_elem: ET.Element, file_path: Path) -> list[str]:
        """
        Extract image paths from the quiz element.

        Images are stored in:
        - 그림 elements (content is the path)
        - 문자그림 elements (path attribute)

        Args:
            quiz_elem: Quiz XML element
            file_path: Path to the IML file

        Returns:
            List of image paths relative to the IML file
        """
        images: list[str] = []
        item_dir = file_path.parent

        # Find 그림 elements
        for pic in quiz_elem.findall(".//그림"):
            path = pic.text
            if path:
                path = path.strip()
                if path:
                    images.append(path)

        # Find 문자그림 elements
        for cpic in quiz_elem.findall(".//문자그림"):
            path = cpic.get("path") or cpic.text
            if path:
                path = path.strip()
                if path:
                    images.append(path)

        # Check for DrawObjPic directory
        item_id = quiz_elem.get("id", "")
        if item_id:
            draw_dir = item_dir / item_id / "DrawObjPic"
            if draw_dir.exists():
                for img_file in draw_dir.iterdir():
                    if img_file.suffix.lower() in {
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".bmp",
                    }:
                        rel_path = f"{item_id}/DrawObjPic/{img_file.name}"
                        if rel_path not in images:
                            images.append(rel_path)

        return images

    def _extract_math(self, quiz_elem: ET.Element) -> list[str]:
        """Extract math expressions (수식) from the quiz element."""
        expressions: list[str] = []

        for math_elem in quiz_elem.findall(".//수식"):
            text = math_elem.text
            if text:
                expressions.append(text.strip())

        return expressions

    def _extract_keywords(self, attrs: dict[str, str]) -> list[str]:
        """Extract keywords from attributes."""
        keywords: list[str] = []

        # Keywords are in kw, kw2, kw3, kw4, kw5 attributes
        for key in ["kw", "kw2", "kw3", "kw4", "kw5"]:
            value = attrs.get(key, "")
            if value:
                # Keywords may be comma-separated
                for kw in value.split(","):
                    kw = kw.strip()
                    if kw:
                        keywords.append(kw)

        return keywords


def parse_iml_file(file_path: Path) -> IMLItem | None:
    """
    Convenience function to parse a single IML file.

    Args:
        file_path: Path to the IML file

    Returns:
        Parsed IMLItem or None
    """
    parser = IMLParser()
    return parser.parse_file(file_path)
