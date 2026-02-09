"""QTI/IML XML 파서

한국 교육용 IML 포맷 및 표준 QTI 포맷의 XML 파일을 파싱하여
구조화된 QTIItem 객체로 변환.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from ..core.schemas import QTIItem, Choice
from ..utils.metadata_normalizer import MetadataNormalizer


class QTIParser:
    """QTI/IML XML 파서

    IML (한국 교육 문항 포맷)과 QTI 2.1/3.0을 지원.
    주로 IML 포맷에 최적화되어 있음.
    """

    # 지원하는 인코딩 목록
    ENCODINGS = ["euc-kr", "cp949", "utf-8", "utf-8-sig"]

    # 채점유형 코드 매핑
    QUESTION_TYPE_CODES = {
        "11": "선택형",
        "21": "진위형",
        "31": "단답형",
        "34": "완성형",
        "37": "배합형",
        "41": "서술형",
        "51": "논술형",
    }

    # 과목 코드 매핑
    SUBJECT_CODES = {
        "01": "국어", "02": "영어", "03": "수학",
        "04": "사회", "05": "과학", "06": "역사",
    }

    # 난이도 코드 매핑
    DIFFICULTY_CODES = {
        "01": "easy", "02": "medium", "03": "hard",
    }

    # 학교급 코드 매핑
    SCHOOL_LEVEL_CODES = {
        "01": "초등학교", "02": "중학교", "03": "고등학교",
    }

    def __init__(self):
        self.normalizer = MetadataNormalizer()

    def parse(self, xml_path: Path) -> Optional[QTIItem]:
        """XML 파일 파싱

        Args:
            xml_path: IML/QTI XML 파일 경로

        Returns:
            파싱된 QTIItem 또는 실패 시 None
        """
        try:
            content = self._read_file(xml_path)
            return self._parse_content(content, xml_path)
        except Exception as e:
            print(f"Error parsing {xml_path}: {e}")
            return None

    def parse_string(self, xml_string: str, source_path: Optional[Path] = None) -> Optional[QTIItem]:
        """XML 문자열 파싱

        Args:
            xml_string: IML/QTI XML 문자열
            source_path: 원본 파일 경로 (옵션)

        Returns:
            파싱된 QTIItem 또는 실패 시 None
        """
        try:
            return self._parse_content(xml_string, source_path)
        except Exception as e:
            print(f"Error parsing XML string: {e}")
            return None

    def validate_schema(self, xml_string: str) -> tuple[bool, list[str]]:
        """스키마 유효성 검증

        Args:
            xml_string: XML 문자열

        Returns:
            (유효 여부, 오류 메시지 목록)
        """
        errors = []

        try:
            # XML 파싱 시도
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            return False, [f"XML 파싱 오류: {e}"]

        # 문항 요소 확인
        quiz_elem = self._find_quiz_element(root)
        if quiz_elem is None:
            errors.append("문항 요소(문항, 단위문항)를 찾을 수 없습니다")

        # 필수 속성 확인
        if quiz_elem is not None:
            if not quiz_elem.get("id"):
                errors.append("문항 ID(id 속성)가 없습니다")
            if not quiz_elem.get("qt"):
                errors.append("채점유형(qt 속성)이 없습니다")

        # 문제 요소 확인
        if quiz_elem is not None:
            question = quiz_elem.find(".//문제")
            if question is None:
                errors.append("문제 요소를 찾을 수 없습니다")

        return len(errors) == 0, errors

    def _read_file(self, file_path: Path) -> str:
        """파일 읽기 (인코딩 자동 감지)

        Args:
            file_path: 파일 경로

        Returns:
            파일 내용 문자열
        """
        with open(file_path, "rb") as f:
            raw_data = f.read()

        # 여러 인코딩 시도
        for encoding in self.ENCODINGS:
            try:
                return raw_data.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue

        # 실패 시 대체 문자로 디코딩
        return raw_data.decode("euc-kr", errors="replace")

    def _parse_content(self, content: str, source_path: Optional[Path]) -> Optional[QTIItem]:
        """XML 내용 파싱

        Args:
            content: XML 문자열
            source_path: 원본 파일 경로

        Returns:
            파싱된 QTIItem
        """
        # XML 선언의 인코딩 수정 (파싱을 위해)
        content = self._fix_encoding_declaration(content)

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            print(f"XML 파싱 오류: {e}")
            return None

        # 문항 요소 찾기
        quiz_elem = self._find_quiz_element(root)
        if quiz_elem is None:
            return None

        # 속성 추출
        attrs = dict(quiz_elem.attrib)
        item_id = attrs.get("id", "")

        if not item_id:
            return None

        # 분류 코드 추출
        subject_code = self._extract_code(attrs.get("cls4", ""))
        grade_code = self._extract_code(attrs.get("cls3", ""))
        school_level_code = self._extract_code(attrs.get("cls2", ""))
        question_type_code = self._extract_code(attrs.get("qt", ""))
        difficulty_code = self._extract_code(attrs.get("df", ""))

        # 코드를 이름으로 매핑
        subject = self.SUBJECT_CODES.get(subject_code, "")
        school_level = self.SCHOOL_LEVEL_CODES.get(school_level_code, "")
        grade = self._get_grade_name(grade_code, school_level_code)
        question_type = self.QUESTION_TYPE_CODES.get(question_type_code, "")
        difficulty = self.DIFFICULTY_CODES.get(difficulty_code, "medium")

        # 내용 추출
        stem = self._extract_stem(quiz_elem)
        choices = self._extract_choices(quiz_elem)
        answer = self._extract_answer(quiz_elem)
        explanation = self._extract_explanation(quiz_elem)
        hint = self._extract_hint(quiz_elem)
        direction = self._extract_direction(quiz_elem)

        # 이미지 추출
        images = self._extract_images(quiz_elem, source_path)

        # 수식 추출
        math_expressions = self._extract_math(quiz_elem)

        # 키워드 추출
        keywords = self._extract_keywords(attrs)

        # 제목 추출
        title = attrs.get("title", "")

        return QTIItem(
            item_id=item_id,
            source_path=source_path,
            title=title,
            stem=stem,
            choices=choices,
            correct_answer=answer,
            explanation=explanation,
            hint=hint,
            direction=direction,
            question_type=question_type,
            question_type_code=question_type_code,
            images=images,
            math_expressions=math_expressions,
            subject=subject,
            subject_code=subject_code,
            grade=grade,
            grade_code=grade_code,
            school_level=school_level,
            school_level_code=school_level_code,
            difficulty=difficulty,
            difficulty_code=difficulty_code,
            curriculum_code=attrs.get("cls1", ""),
            unit_large=attrs.get("cls7", ""),
            unit_medium=attrs.get("cls8", ""),
            keywords=keywords,
            raw_attributes=attrs,
        )

    def _fix_encoding_declaration(self, content: str) -> str:
        """XML 인코딩 선언 수정"""
        # ksc5601, euc-kr 인코딩 선언을 제거 (이미 UTF-8 문자열임)
        content = re.sub(
            r'<\?xml[^>]*encoding=["\'](?:ksc5601|euc-kr)["\'][^>]*\?>',
            '<?xml version="1.0" encoding="utf-8"?>',
            content,
            flags=re.IGNORECASE
        )
        return content

    def _find_quiz_element(self, root: ET.Element) -> Optional[ET.Element]:
        """문항 요소 찾기"""
        # 단위문항 > 문항
        unit_quiz = root.find(".//단위문항/문항")
        if unit_quiz is not None:
            return unit_quiz

        # 단위문항 > 지문
        passage = root.find(".//단위문항/지문")
        if passage is not None:
            return passage

        # 그룹문항 > 문항
        group_quiz = root.find(".//그룹문항/문항")
        if group_quiz is not None:
            return group_quiz

        # 직접 문항
        direct_quiz = root.find(".//문항")
        if direct_quiz is not None:
            return direct_quiz

        return None

    def _extract_code(self, value: str) -> str:
        """분류값에서 코드 추출

        "03 수학" -> "03"
        """
        if not value:
            return ""

        parts = value.strip().split(maxsplit=1)
        if parts:
            return parts[0]
        return ""

    def _get_grade_name(self, grade_code: str, school_level_code: str) -> str:
        """학년 코드에서 학년명 추출"""
        if not grade_code:
            return ""

        # 학교급에 따른 학년 매핑
        if school_level_code == "01":  # 초등학교
            mapping = {"01": "초1", "02": "초2", "03": "초3",
                      "04": "초4", "05": "초5", "06": "초6"}
            return mapping.get(grade_code, "")

        elif school_level_code == "02":  # 중학교
            mapping = {"01": "중1", "02": "중2", "03": "중3",
                      "07": "중1", "08": "중2", "09": "중3"}
            return mapping.get(grade_code, "")

        elif school_level_code == "03":  # 고등학교
            mapping = {"01": "고1", "02": "고2", "03": "고3",
                      "10": "고1", "11": "고2", "12": "고3"}
            return mapping.get(grade_code, "")

        # 코드에서 직접 추론
        try:
            code_int = int(grade_code)
            if 1 <= code_int <= 6:
                return f"초{code_int}"
            elif 7 <= code_int <= 9:
                return f"중{code_int - 6}"
            elif 10 <= code_int <= 12:
                return f"고{code_int - 9}"
        except ValueError:
            pass

        return ""

    def _extract_text_from_element(self, elem: Optional[ET.Element]) -> str:
        """요소에서 모든 텍스트 추출"""
        if elem is None:
            return ""

        texts: list[str] = []

        if elem.text:
            texts.append(elem.text.strip())

        for child in elem:
            child_text = self._extract_text_from_element(child)
            if child_text:
                texts.append(child_text)

            if child.tail:
                texts.append(child.tail.strip())

        return " ".join(filter(None, texts))

    def _extract_stem(self, quiz_elem: ET.Element) -> str:
        """문제 본문(물음) 추출"""
        # 문제/물음
        quest = quiz_elem.find(".//문제/물음")
        if quest is not None:
            return self._extract_text_from_element(quest)

        # 물음 직접
        quest = quiz_elem.find(".//물음")
        if quest is not None:
            return self._extract_text_from_element(quest)

        return ""

    def _extract_choices(self, quiz_elem: ET.Element) -> list[Choice]:
        """선지(답항) 추출"""
        choices: list[Choice] = []
        labels = ["①", "②", "③", "④", "⑤", "A", "B", "C", "D", "E"]

        for idx, choice_elem in enumerate(quiz_elem.findall(".//문제/답항")):
            text = self._extract_text_from_element(choice_elem)
            if text:
                label = labels[idx] if idx < len(labels) else str(idx + 1)
                choices.append(Choice(label=label, text=text))

        return choices

    def _extract_answer(self, quiz_elem: ET.Element) -> str:
        """정답 추출"""
        answer_elem = quiz_elem.find(".//정답")
        if answer_elem is not None:
            return self._extract_text_from_element(answer_elem)
        return ""

    def _extract_explanation(self, quiz_elem: ET.Element) -> str:
        """해설 추출"""
        explanation = quiz_elem.find(".//해설")
        if explanation is not None:
            return self._extract_text_from_element(explanation)
        return ""

    def _extract_hint(self, quiz_elem: ET.Element) -> str:
        """힌트 추출"""
        hint = quiz_elem.find(".//힌트")
        if hint is not None:
            return self._extract_text_from_element(hint)
        return ""

    def _extract_direction(self, quiz_elem: ET.Element) -> str:
        """지시문 추출"""
        direction = quiz_elem.find(".//지시")
        if direction is not None:
            return self._extract_text_from_element(direction)
        return ""

    def _extract_images(
        self, quiz_elem: ET.Element, file_path: Optional[Path]
    ) -> list[str]:
        """이미지 경로 추출"""
        images: list[str] = []

        # 그림 요소
        for pic in quiz_elem.findall(".//그림"):
            path = pic.text
            if path:
                path = path.strip()
                if path:
                    images.append(path)

        # 문자그림 요소
        for cpic in quiz_elem.findall(".//문자그림"):
            path = cpic.get("path") or cpic.text
            if path:
                path = path.strip()
                if path:
                    images.append(path)

        # DrawObjPic 디렉토리 확인
        if file_path:
            item_id = quiz_elem.get("id", "")
            if item_id:
                item_dir = file_path.parent
                draw_dir = item_dir / item_id / "DrawObjPic"
                if draw_dir.exists():
                    for img_file in draw_dir.iterdir():
                        if img_file.suffix.lower() in {
                            ".png", ".jpg", ".jpeg", ".gif", ".bmp"
                        }:
                            rel_path = f"{item_id}/DrawObjPic/{img_file.name}"
                            if rel_path not in images:
                                images.append(rel_path)

        return images

    def _extract_math(self, quiz_elem: ET.Element) -> list[str]:
        """수식 추출"""
        expressions: list[str] = []

        for math_elem in quiz_elem.findall(".//수식"):
            text = math_elem.text
            if text:
                expressions.append(text.strip())

        return expressions

    def _extract_keywords(self, attrs: dict[str, str]) -> list[str]:
        """키워드 추출"""
        keywords: list[str] = []

        for key in ["kw", "kw2", "kw3", "kw4", "kw5"]:
            value = attrs.get(key, "")
            if value:
                for kw in value.split(","):
                    kw = kw.strip()
                    if kw:
                        keywords.append(kw)

        return keywords
