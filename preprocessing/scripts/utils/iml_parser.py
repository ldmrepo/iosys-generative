"""
iml_parser.py
IML 파일 파싱 유틸리티

IML(XML) 파일을 구조화된 Python 객체로 변환
"""

import re
import codecs
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from xml.etree import ElementTree as ET

# Import latex cleaner for formula normalization
try:
    from latex_cleaner import clean_latex as normalize_latex
except ImportError:
    # Add utils directory to path if running from parent
    sys.path.insert(0, str(Path(__file__).parent))
    from latex_cleaner import clean_latex as normalize_latex


@dataclass
class ItemMetadata:
    """문항 메타데이터"""
    id: str = ""
    difficulty: str = ""          # df: 난이도
    difficulty_code: str = ""
    question_type: str = ""       # qt: 문항유형
    question_type_code: str = ""
    curriculum: str = ""          # cls1: 교육과정
    school_level: str = ""        # cls2: 학교급
    grade: str = ""               # cls3: 학년
    subject: str = ""             # cls4: 과목
    subject_detail: str = ""      # cls5: 세부과목
    semester: str = ""            # cls6: 학기
    unit_large: str = ""          # cls7: 대단원
    unit_medium: str = ""         # cls8: 중단원
    unit_small: str = ""          # cls9: 소단원
    keywords: str = ""            # kw: 키워드
    year: Optional[int] = None    # dyear: 출제년도
    source: str = ""              # qs: 출처
    exam_name: str = ""           # qns: 시험명
    raw_attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class ContentBlock:
    """콘텐츠 블록 (텍스트, 수식, 이미지 등)"""
    type: str  # 'text', 'latex', 'image'
    content: str
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class ItemContent:
    """문항 콘텐츠"""
    question_blocks: List[ContentBlock] = field(default_factory=list)
    question_text: str = ""       # 순수 텍스트
    question_latex: List[str] = field(default_factory=list)  # LaTeX 수식들
    question_images: List[str] = field(default_factory=list)  # 이미지 경로들

    choices: List[str] = field(default_factory=list)  # 선택지 (텍스트)
    choices_blocks: List[List[ContentBlock]] = field(default_factory=list)

    answer: Optional[int] = None  # 정답 번호 (단일)
    answers: List[int] = field(default_factory=list)  # 정답 번호들 (복수정답 포함)
    answer_text: str = ""         # 정답 텍스트 (주관식)

    explanation_blocks: List[ContentBlock] = field(default_factory=list)
    explanation_text: str = ""
    explanation_latex: List[str] = field(default_factory=list)
    explanation_images: List[str] = field(default_factory=list)


@dataclass
class ParsedItem:
    """파싱된 문항"""
    metadata: ItemMetadata
    content: ItemContent
    has_image: bool = False
    parse_errors: List[str] = field(default_factory=list)
    source_file: str = ""


class IMLParser:
    """IML 파일 파서"""

    # 난이도 코드 매핑
    DIFFICULTY_MAP = {
        "01": "상",
        "02": "상중",
        "03": "중",
        "04": "중하",
        "05": "하",
    }

    # 문항유형 코드 매핑
    QUESTION_TYPE_MAP = {
        "11": "선택형",
        "31": "단답형",
        "34": "완결형",
    }

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir

    def read_file(self, file_path: Path) -> Optional[str]:
        """IML 파일을 읽고 UTF-8로 변환"""
        try:
            with open(file_path, 'rb') as f:
                raw = f.read()
        except Exception:
            return None

        # Detect declared encoding from XML prolog
        header = raw[:200]
        if b'encoding="utf-8"' in header or b"encoding='utf-8'" in header:
            encodings = ['utf-8', 'euc-kr', 'cp949']
        else:
            encodings = ['euc-kr', 'cp949', 'utf-8']

        for encoding in encodings:
            try:
                return raw.decode(encoding, errors='replace')
            except Exception:
                continue
        return None

    def parse_file(self, file_path: Path) -> Optional[ParsedItem]:
        """IML 파일 파싱"""
        content = self.read_file(file_path)
        if content is None:
            return None

        try:
            root = ET.fromstring(content)
            return self._parse_root(root, str(file_path))
        except ET.ParseError as e:
            item = ParsedItem(
                metadata=ItemMetadata(),
                content=ItemContent(),
                source_file=str(file_path)
            )
            item.parse_errors.append(f"XML Parse Error: {e}")
            return item

    def _parse_root(self, root: ET.Element, source_file: str) -> ParsedItem:
        """루트 엘리먼트 파싱"""
        item = ParsedItem(
            metadata=ItemMetadata(),
            content=ItemContent(),
            source_file=source_file
        )

        # 문항 엘리먼트 찾기
        quiz_elem = root.find(".//문항")
        if quiz_elem is None:
            item.parse_errors.append("문항 element not found")
            return item

        # 메타데이터 파싱
        item.metadata = self._parse_metadata(quiz_elem)

        # 콘텐츠 파싱
        item.content = self._parse_content(quiz_elem)

        # 이미지 여부 확인
        item.has_image = bool(
            item.content.question_images or
            item.content.explanation_images
        )

        return item

    def _parse_metadata(self, quiz_elem: ET.Element) -> ItemMetadata:
        """문항 메타데이터 파싱"""
        attrs = quiz_elem.attrib
        meta = ItemMetadata(raw_attributes=dict(attrs))

        # ID
        meta.id = attrs.get('id', '')

        # 난이도
        df = attrs.get('df', '')
        meta.difficulty_code = df.split()[0] if df else ''
        meta.difficulty = self._parse_labeled_value(df)

        # 문항유형
        qt = attrs.get('qt', '')
        meta.question_type_code = qt.split()[0] if qt else ''
        meta.question_type = self._parse_labeled_value(qt)

        # 분류체계
        meta.curriculum = self._parse_labeled_value(attrs.get('cls1', ''))
        meta.school_level = self._parse_labeled_value(attrs.get('cls2', ''))
        meta.grade = self._parse_labeled_value(attrs.get('cls3', ''))
        meta.subject = self._parse_labeled_value(attrs.get('cls4', ''))
        meta.subject_detail = self._parse_labeled_value(attrs.get('cls5', ''))
        meta.semester = self._parse_labeled_value(attrs.get('cls6', ''))
        meta.unit_large = self._parse_labeled_value(attrs.get('cls7', ''))
        meta.unit_medium = self._parse_labeled_value(attrs.get('cls8', ''))
        meta.unit_small = self._parse_labeled_value(attrs.get('cls9', ''))

        # 기타
        meta.keywords = attrs.get('kw', '')
        meta.source = attrs.get('qs', '')
        meta.exam_name = attrs.get('qns', '')

        # 출제년도
        dyear = attrs.get('dyear', '')
        if dyear and dyear.isdigit():
            meta.year = int(dyear)

        return meta

    def _parse_labeled_value(self, value: str) -> str:
        """'01 라벨' 형태에서 라벨 추출"""
        if not value:
            return ""
        parts = value.split(' ', 1)
        return parts[1] if len(parts) > 1 else value

    def _parse_content(self, quiz_elem: ET.Element) -> ItemContent:
        """문항 콘텐츠 파싱"""
        content = ItemContent()

        # 문제 파싱
        problem_elem = quiz_elem.find("문제")
        if problem_elem is not None:
            # 물음 (문제 본문)
            question_elem = problem_elem.find("물음")
            if question_elem is not None:
                blocks = self._parse_content_blocks(question_elem)
                content.question_blocks = blocks
                content.question_text = self._blocks_to_text(blocks)
                content.question_latex = self._extract_latex(blocks)
                content.question_images = self._extract_images(blocks)

            # 답항 (선택지)
            for choice_elem in problem_elem.findall("답항"):
                blocks = self._parse_content_blocks(choice_elem)
                content.choices_blocks.append(blocks)
                content.choices.append(self._blocks_to_text(blocks))

        # 정답 파싱
        answer_elem = quiz_elem.find("정답")
        if answer_elem is not None:
            answer_text = self._get_element_text(answer_elem).strip()
            content.answer_text = answer_text

            # 정답 파싱 (단일 또는 복수)
            # 선택형 문항의 경우만 숫자를 정답 번호로 처리 (1-5 범위)
            if answer_text:
                # 쉼표로 구분된 복수 정답 처리 (예: "1,3" 또는 "1, 3")
                if ',' in answer_text:
                    parts = [p.strip() for p in answer_text.split(',')]
                    valid_answers = []
                    for p in parts:
                        # 1-5 범위의 단일 ASCII 숫자만 선택지 정답으로 인식
                        if p.isascii() and p.isdigit() and 1 <= int(p) <= 5:
                            valid_answers.append(int(p))
                    # 모든 파트가 유효한 선택지 번호인 경우만 복수정답으로 처리
                    if valid_answers and len(valid_answers) == len([p for p in parts if p.strip().isascii() and p.strip().isdigit()]):
                        content.answers = valid_answers
                        content.answer = valid_answers[0]
                # 단일 정답
                elif answer_text.isascii() and answer_text.isdigit() and 1 <= int(answer_text) <= 5:
                    content.answer = int(answer_text)
                    content.answers = [int(answer_text)]

        # 해설 파싱
        explanation_elem = quiz_elem.find("해설")
        if explanation_elem is not None:
            blocks = self._parse_content_blocks(explanation_elem)
            content.explanation_blocks = blocks
            content.explanation_text = self._blocks_to_text(blocks)
            content.explanation_latex = self._extract_latex(blocks)
            content.explanation_images = self._extract_images(blocks)

        return content

    def _parse_content_blocks(self, elem: ET.Element) -> List[ContentBlock]:
        """콘텐츠 엘리먼트를 블록 리스트로 파싱"""
        blocks = []

        def traverse(element):
            # 문자열 태그
            if element.tag == '문자열':
                text = self._get_direct_text(element)
                if text.strip():
                    blocks.append(ContentBlock(
                        type='text',
                        content=text
                    ))

            # 수식 태그
            elif element.tag == '수식':
                latex = element.text or ''
                if latex.strip():
                    blocks.append(ContentBlock(
                        type='latex',
                        content=latex.strip(),
                        attributes={'w': element.get('w', ''), 'h': element.get('h', '')}
                    ))

            # 그림 태그
            elif element.tag == '그림':
                img_path = element.text or ''
                if img_path.strip():
                    # Windows 경로를 Unix로 변환
                    img_path = img_path.strip().replace('\\', '/')
                    blocks.append(ContentBlock(
                        type='image',
                        content=img_path,
                        attributes={
                            'w': element.get('w', ''),
                            'h': element.get('h', ''),
                            'ow': element.get('ow', ''),
                            'oh': element.get('oh', ''),
                            'name': element.get('name', '')
                        }
                    ))

            # 자식 순회
            for child in element:
                traverse(child)

        traverse(elem)
        return blocks

    def _get_direct_text(self, element: ET.Element) -> str:
        """엘리먼트의 직접 텍스트만 추출 (자식 제외)"""
        text = element.text or ''
        # 자식의 tail 텍스트도 포함
        for child in element:
            if child.tail:
                text += child.tail
        return text

    def _get_element_text(self, element: ET.Element) -> str:
        """엘리먼트의 모든 텍스트 추출"""
        texts = []

        def traverse(elem):
            if elem.text:
                texts.append(elem.text)
            for child in elem:
                traverse(child)
                if child.tail:
                    texts.append(child.tail)

        traverse(element)
        return ''.join(texts)

    def _blocks_to_text(self, blocks: List[ContentBlock]) -> str:
        """블록 리스트를 텍스트로 변환 (수식은 $..$ 형태로)"""
        parts = []
        for block in blocks:
            if block.type == 'text':
                parts.append(block.content)
            elif block.type == 'latex':
                # LaTeX 수식을 $..$ 형태로 포함
                latex = self._clean_latex(block.content)
                parts.append(f"${latex}$")
            elif block.type == 'image':
                parts.append("[이미지]")
        return ''.join(parts)

    def _clean_latex(self, latex: str) -> str:
        """LaTeX 수식 정리 - latex_cleaner 모듈 사용"""
        return normalize_latex(latex)

    def _extract_latex(self, blocks: List[ContentBlock]) -> List[str]:
        """블록에서 LaTeX 수식 추출"""
        return [
            self._clean_latex(b.content)
            for b in blocks
            if b.type == 'latex'
        ]

    def _extract_images(self, blocks: List[ContentBlock]) -> List[str]:
        """블록에서 이미지 경로 추출"""
        return [b.content for b in blocks if b.type == 'image']


def parse_iml_file(file_path: Path) -> Optional[ParsedItem]:
    """IML 파일 파싱 헬퍼 함수"""
    parser = IMLParser()
    return parser.parse_file(file_path)


def item_to_dict(item: ParsedItem) -> Dict[str, Any]:
    """ParsedItem을 딕셔너리로 변환"""
    return {
        "id": item.metadata.id,
        "metadata": {
            "difficulty": item.metadata.difficulty,
            "difficulty_code": item.metadata.difficulty_code,
            "question_type": item.metadata.question_type,
            "question_type_code": item.metadata.question_type_code,
            "curriculum": item.metadata.curriculum,
            "school_level": item.metadata.school_level,
            "grade": item.metadata.grade,
            "subject": item.metadata.subject,
            "subject_detail": item.metadata.subject_detail,
            "semester": item.metadata.semester,
            "unit_large": item.metadata.unit_large,
            "unit_medium": item.metadata.unit_medium,
            "unit_small": item.metadata.unit_small,
            "keywords": item.metadata.keywords,
            "year": item.metadata.year,
            "source": item.metadata.source,
            "exam_name": item.metadata.exam_name,
        },
        "content": {
            "question": item.content.question_text,
            "question_latex": item.content.question_latex,
            "question_images": item.content.question_images,
            "choices": item.content.choices,
            "answer": item.content.answer,
            "answers": item.content.answers,
            "answer_text": item.content.answer_text,
            "explanation": item.content.explanation_text,
            "explanation_latex": item.content.explanation_latex,
            "explanation_images": item.content.explanation_images,
        },
        "has_image": item.has_image,
        "source_file": item.source_file,
        "parse_errors": item.parse_errors,
    }
