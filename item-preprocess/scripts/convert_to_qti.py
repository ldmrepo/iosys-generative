"""
convert_to_qti.py
IML → QTI 2.1 변환 스크립트

2022 개정교육과정 IML 문항을 QTI 2.1 표준 XML로 변환한다.
- 입력: data/raw/{date}/{item_id}.iml
- 출력: data/qti/2022/{item_id}/item.xml + images/

Usage:
    # 전체 변환
    python convert_to_qti.py --input-dir data/raw --output-dir data/qti/2022

    # 과목 필터
    python convert_to_qti.py --input-dir data/raw --output-dir data/qti/2022 --subject 수학

    # 단일 파일
    python convert_to_qti.py --input-file data/raw/2024/06/17/ITEM.iml --output-dir data/qti/2022

    # 테스트 (최대 N건)
    python convert_to_qti.py --input-dir data/raw --output-dir data/qti/2022 --limit 100
"""

import argparse
import json
import logging
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent / "../../preprocessing/scripts/utils"))
sys.path.insert(0, str(Path(__file__).parent / "../../preprocessing/scripts"))

from iml_parser import IMLParser, ParsedItem, ContentBlock, ItemMetadata
from latex_cleaner import clean_latex

logger = logging.getLogger(__name__)

# QTI 2.1 namespace constants
QTI_NS = "http://www.imsglobal.org/xsd/imsqti_v2p1"
QTI_XSI = "http://www.w3.org/2001/XMLSchema-instance"
QTI_SCHEMA_LOC = (
    "http://www.imsglobal.org/xsd/imsqti_v2p1 "
    "http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"
)
IOSYS_NS = "http://iosys.co.kr/xsd/iml-metadata"

# 2022 curriculum filter
CURRICULUM_2022_PREFIX = "A13"


def _extract_code(raw_value: str) -> str:
    """Extract the code part from 'CODE LABEL' format. e.g. '03 수학' -> '03'"""
    if not raw_value:
        return ""
    return raw_value.split()[0] if raw_value else ""


def _extract_label(raw_value: str) -> str:
    """Extract the label part from 'CODE LABEL' format. e.g. '03 수학' -> '수학'"""
    if not raw_value:
        return ""
    parts = raw_value.split(" ", 1)
    return parts[1] if len(parts) > 1 else raw_value


# ---------------------------------------------------------------------------
# ImageResolver
# ---------------------------------------------------------------------------

class ImageResolver:
    """Resolves and copies IML image references to QTI output directories."""

    def __init__(self, raw_dirs: List[str]):
        self.raw_dirs = [Path(d) for d in raw_dirs]

    def resolve_and_copy(
        self, image_ref: str, source_iml_path: Path, output_item_dir: Path
    ) -> Optional[str]:
        """
        Resolve an IML image path and copy it to the output directory.

        Args:
            image_ref: Image path from IML (e.g. "ITEMID\\DrawObjPic\\file.png")
            source_iml_path: Path to the source IML file
            output_item_dir: Target item directory under data/qti/2022/{item_id}/

        Returns:
            Relative path for QTI XML (e.g. "images/file.png") or None if not found
        """
        # Normalize path separators
        image_ref_normalized = image_ref.replace("\\", "/")
        filename = Path(image_ref_normalized).name

        images_dir = output_item_dir / "images"

        # Strategy 1: Look relative to the source IML file's parent directory
        source_parent = source_iml_path.parent
        candidates = [
            source_parent / image_ref_normalized,
            source_parent / Path(image_ref_normalized).relative_to(
                Path(image_ref_normalized).parts[0]
            ) if len(Path(image_ref_normalized).parts) > 1 else None,
        ]

        # Strategy 2: Look in item-named subdirectory next to IML
        item_id_from_ref = Path(image_ref_normalized).parts[0] if Path(image_ref_normalized).parts else ""
        if item_id_from_ref:
            candidates.append(source_parent / item_id_from_ref / "DrawObjPic" / filename)

        # Strategy 3: For sample data structure (images/ subdir)
        candidates.append(source_parent / "images" / filename)

        for candidate in candidates:
            if candidate and candidate.is_file():
                images_dir.mkdir(parents=True, exist_ok=True)
                dest = images_dir / filename
                if not dest.exists():
                    shutil.copy2(candidate, dest)
                return f"images/{filename}"

        return None


# ---------------------------------------------------------------------------
# QTIConverter
# ---------------------------------------------------------------------------

class QTIConverter:
    """Converts ParsedItem to QTI 2.1 XML."""

    # Question type -> QTI interaction mapping
    INTERACTION_MAP = {
        "11": "choiceInteraction",     # 선택형
        "21": "choiceInteraction",     # 진위형
        "31": "textEntryInteraction",  # 단답형
        "34": "textEntryInteraction",  # 완성형
        "41": "extendedTextInteraction",  # 서술형
        "51": "extendedTextInteraction",  # 논술형
    }

    def __init__(self, image_resolver: Optional[ImageResolver] = None):
        self.image_resolver = image_resolver

    def convert_item(
        self,
        item: ParsedItem,
        source_path: Optional[Path] = None,
        output_item_dir: Optional[Path] = None,
    ) -> str:
        """Convert a ParsedItem to QTI 2.1 XML string."""
        meta = item.metadata
        content = item.content
        raw = meta.raw_attributes
        qt_code = meta.question_type_code
        daps_str = raw.get("daps", "1") or "1"
        try:
            daps = int(daps_str)
        except ValueError:
            daps = 1

        # Build title
        title = self._build_title(meta)

        lines = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append(
            f'<assessmentItem xmlns="{QTI_NS}"'
            f'\n                xmlns:xsi="{QTI_XSI}"'
            f'\n                xmlns:iosys="{IOSYS_NS}"'
            f'\n                xsi:schemaLocation="{QTI_SCHEMA_LOC}"'
            f'\n                identifier="{xml_escape(meta.id)}"'
            f'\n                title="{xml_escape(title)}"'
            f'\n                adaptive="false"'
            f'\n                timeDependent="false">'
        )

        # responseDeclaration
        lines.append(self._build_response_declaration(item, qt_code, daps))

        # outcomeDeclaration
        lines.append(
            '  <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float"/>'
        )

        # itemBody
        lines.append(
            self._build_item_body(item, qt_code, daps, source_path, output_item_dir)
        )

        # responseProcessing
        rp = self._build_response_processing(item, qt_code)
        if rp:
            lines.append(rp)

        # modalFeedback (explanation)
        fb = self._build_feedback(item, source_path, output_item_dir)
        if fb:
            lines.append(fb)

        # iosys:metadata
        lines.append(self._build_metadata(item))

        lines.append("</assessmentItem>")

        return "\n".join(lines)

    # ---- title ----

    def _build_title(self, meta: ItemMetadata) -> str:
        parts = []
        if meta.subject:
            parts.append(meta.subject)
        if meta.grade:
            parts.append(meta.grade)
        if meta.unit_large:
            parts.append(meta.unit_large)
        return " - ".join(parts) if parts else meta.id

    # ---- responseDeclaration ----

    def _build_response_declaration(
        self, item: ParsedItem, qt_code: str, daps: int
    ) -> str:
        content = item.content

        if qt_code in ("11", "21"):
            # Choice-based
            cardinality = "multiple" if daps > 1 else "single"
            base_type = "identifier"
            lines = [
                f'  <responseDeclaration identifier="RESPONSE" cardinality="{cardinality}" baseType="{base_type}">',
            ]
            if content.answers:
                lines.append("    <correctResponse>")
                for ans in content.answers:
                    lines.append(f"      <value>choice_{ans}</value>")
                lines.append("    </correctResponse>")
            lines.append("  </responseDeclaration>")
            return "\n".join(lines)

        elif qt_code in ("31", "34"):
            # Text entry
            lines = [
                '  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="string">',
            ]
            answer_text = content.answer_text.strip()
            if answer_text and answer_text not in ("해설참조", "풀이참조"):
                lines.append("    <correctResponse>")
                lines.append(f"      <value>{xml_escape(answer_text)}</value>")
                lines.append("    </correctResponse>")
            lines.append("  </responseDeclaration>")
            return "\n".join(lines)

        elif qt_code in ("41", "51"):
            # Extended text (essay) - no correct response typically
            return (
                '  <responseDeclaration identifier="RESPONSE" '
                'cardinality="single" baseType="string"/>'
            )

        else:
            # Fallback: treat as text entry
            return (
                '  <responseDeclaration identifier="RESPONSE" '
                'cardinality="single" baseType="string"/>'
            )

    # ---- itemBody ----

    def _build_item_body(
        self,
        item: ParsedItem,
        qt_code: str,
        daps: int,
        source_path: Optional[Path],
        output_item_dir: Optional[Path],
    ) -> str:
        content = item.content
        lines = ["  <itemBody>"]

        # Stem (question)
        lines.append('    <div class="stem">')
        stem_html = self._render_blocks(
            content.question_blocks, source_path, output_item_dir, indent=6
        )
        lines.append(stem_html)
        lines.append("    </div>")

        # Interaction
        interaction = self._build_interaction(
            item, qt_code, daps, source_path, output_item_dir
        )
        lines.append(interaction)

        lines.append("  </itemBody>")
        return "\n".join(lines)

    # ---- interaction ----

    def _build_interaction(
        self,
        item: ParsedItem,
        qt_code: str,
        daps: int,
        source_path: Optional[Path],
        output_item_dir: Optional[Path],
    ) -> str:
        content = item.content

        if qt_code in ("11", "21"):
            return self._build_choice_interaction(
                content, daps, source_path, output_item_dir
            )
        elif qt_code in ("31", "34"):
            return self._build_text_entry_interaction(content)
        elif qt_code in ("41", "51"):
            return self._build_extended_text_interaction()
        else:
            # Fallback to text entry
            return self._build_text_entry_interaction(content)

    def _build_choice_interaction(
        self,
        content,
        daps: int,
        source_path: Optional[Path],
        output_item_dir: Optional[Path],
    ) -> str:
        max_choices = daps if daps > 1 else 1
        lines = [
            f'    <choiceInteraction responseIdentifier="RESPONSE" shuffle="false" maxChoices="{max_choices}">',
        ]

        for i, choice_blocks in enumerate(content.choices_blocks, 1):
            choice_html = self._render_blocks_inline(
                choice_blocks, source_path, output_item_dir
            )
            lines.append(
                f'      <simpleChoice identifier="choice_{i}">{choice_html}</simpleChoice>'
            )

        lines.append("    </choiceInteraction>")
        return "\n".join(lines)

    def _build_text_entry_interaction(self, content) -> str:
        return '    <textEntryInteraction responseIdentifier="RESPONSE" expectedLength="20"/>'

    def _build_extended_text_interaction(self) -> str:
        return (
            '    <extendedTextInteraction responseIdentifier="RESPONSE" '
            'expectedLines="5"/>'
        )

    # ---- responseProcessing ----

    def _build_response_processing(self, item: ParsedItem, qt_code: str) -> Optional[str]:
        content = item.content
        answer_text = content.answer_text.strip()

        # Skip response processing for essay types or when answer is "해설참조"
        if qt_code in ("41", "51"):
            return None
        if answer_text in ("해설참조", "풀이참조", ""):
            return None

        if qt_code in ("11", "21") and content.answers:
            return (
                '  <responseProcessing\n'
                '    template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"/>'
            )
        elif qt_code in ("31", "34") and answer_text:
            return (
                '  <responseProcessing\n'
                '    template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"/>'
            )
        return None

    # ---- feedback (explanation) ----

    def _build_feedback(
        self,
        item: ParsedItem,
        source_path: Optional[Path],
        output_item_dir: Optional[Path],
    ) -> Optional[str]:
        content = item.content
        if not content.explanation_blocks:
            return None

        lines = [
            '  <modalFeedback outcomeIdentifier="SCORE" showHide="show" identifier="SOLUTION">',
            '    <div class="explanation">',
        ]
        explanation_html = self._render_blocks(
            content.explanation_blocks, source_path, output_item_dir, indent=6
        )
        lines.append(explanation_html)
        lines.append("    </div>")
        lines.append("  </modalFeedback>")
        return "\n".join(lines)

    # ---- metadata ----

    def _build_metadata(self, item: ParsedItem) -> str:
        meta = item.metadata
        raw = meta.raw_attributes

        lines = ["  <iosys:metadata>"]

        def add_field(tag: str, raw_key: str, label: Optional[str] = None):
            raw_val = raw.get(raw_key, "")
            if not raw_val or raw_val == "0":
                return
            code = _extract_code(raw_val)
            text = label if label else _extract_label(raw_val)
            lines.append(
                f'    <iosys:{tag} code="{xml_escape(code)}">'
                f"{xml_escape(text)}</iosys:{tag}>"
            )

        add_field("curriculum", "cls1")
        add_field("schoolLevel", "cls2")
        add_field("grade", "cls3")
        add_field("subject", "cls4")
        add_field("subjectDetail", "cls5")
        add_field("semester", "cls6")

        # Units don't always have clean code/label split
        for tag, key in [
            ("unitLarge", "cls7"),
            ("unitMedium", "cls8"),
            ("unitSmall", "cls9"),
        ]:
            val = raw.get(key, "")
            if val and val != "0":
                label = _extract_label(val)
                lines.append(f"    <iosys:{tag}>{xml_escape(label)}</iosys:{tag}>")

        add_field("difficulty", "df")
        add_field("questionType", "qt")

        if meta.keywords:
            lines.append(
                f"    <iosys:keywords>{xml_escape(meta.keywords)}</iosys:keywords>"
            )

        lines.append("  </iosys:metadata>")
        return "\n".join(lines)

    # ---- block rendering ----

    def _render_blocks(
        self,
        blocks: List[ContentBlock],
        source_path: Optional[Path],
        output_item_dir: Optional[Path],
        indent: int = 0,
    ) -> str:
        """Render ContentBlock list to HTML for QTI itemBody."""
        prefix = " " * indent
        parts = []

        # Group consecutive inline blocks into paragraphs
        inline_buf: List[str] = []

        def flush_inline():
            if inline_buf:
                parts.append(f"{prefix}<p>{''.join(inline_buf)}</p>")
                inline_buf.clear()

        for block in blocks:
            if block.type == "text":
                text = block.content.strip()
                if text:
                    inline_buf.append(xml_escape(text))

            elif block.type == "latex":
                cleaned = clean_latex(block.content)
                if cleaned:
                    inline_buf.append(
                        f'<span class="math-tex">{xml_escape(cleaned)}</span>'
                    )

            elif block.type == "image":
                flush_inline()
                rel_path = self._resolve_image(
                    block.content, source_path, output_item_dir
                )
                if rel_path:
                    parts.append(f'{prefix}<img src="{xml_escape(rel_path)}" alt=""/>')
                else:
                    parts.append(
                        f'{prefix}<!-- image not found: {xml_escape(block.content)} -->'
                    )

        flush_inline()
        return "\n".join(parts)

    def _render_blocks_inline(
        self,
        blocks: List[ContentBlock],
        source_path: Optional[Path],
        output_item_dir: Optional[Path],
    ) -> str:
        """Render ContentBlock list as inline HTML (for simpleChoice etc.)."""
        parts = []

        for block in blocks:
            if block.type == "text":
                text = block.content.strip()
                if text:
                    parts.append(xml_escape(text))
            elif block.type == "latex":
                cleaned = clean_latex(block.content)
                if cleaned:
                    parts.append(
                        f'<span class="math-tex">{xml_escape(cleaned)}</span>'
                    )
            elif block.type == "image":
                rel_path = self._resolve_image(
                    block.content, source_path, output_item_dir
                )
                if rel_path:
                    parts.append(f'<img src="{xml_escape(rel_path)}" alt=""/>')

        return "".join(parts)

    def _resolve_image(
        self,
        image_ref: str,
        source_path: Optional[Path],
        output_item_dir: Optional[Path],
    ) -> Optional[str]:
        """Resolve and copy an image, returning the relative QTI path."""
        if not self.image_resolver or not source_path or not output_item_dir:
            # Return a placeholder path without copying
            filename = Path(image_ref.replace("\\", "/")).name
            return f"images/{filename}"
        return self.image_resolver.resolve_and_copy(
            image_ref, source_path, output_item_dir
        )


# ---------------------------------------------------------------------------
# ConversionReport
# ---------------------------------------------------------------------------

@dataclass
class ConversionReport:
    """Collects conversion statistics."""

    total_scanned: int = 0
    total_matched_2022: int = 0
    total_converted: int = 0
    total_errors: int = 0
    total_skipped: int = 0
    total_images_copied: int = 0
    total_images_missing: int = 0

    by_subject: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_question_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_difficulty: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: List[Dict] = field(default_factory=list)
    duration_seconds: float = 0.0

    def add_converted(self, item: ParsedItem):
        self.total_converted += 1
        self.by_subject[item.metadata.subject or "(unknown)"] += 1
        self.by_question_type[item.metadata.question_type or "(unknown)"] += 1
        self.by_difficulty[item.metadata.difficulty or "(unknown)"] += 1

    def add_error(self, file_path: str, errors: List[str]):
        self.total_errors += 1
        self.errors.append({"file": file_path, "errors": errors})

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_scanned": self.total_scanned,
                "total_matched_2022": self.total_matched_2022,
                "total_converted": self.total_converted,
                "total_errors": self.total_errors,
                "total_skipped": self.total_skipped,
                "total_images_copied": self.total_images_copied,
                "total_images_missing": self.total_images_missing,
                "duration_seconds": round(self.duration_seconds, 1),
            },
            "by_subject": dict(sorted(self.by_subject.items())),
            "by_question_type": dict(sorted(self.by_question_type.items())),
            "by_difficulty": dict(sorted(self.by_difficulty.items())),
            "errors": self.errors[:100],  # Limit stored errors
            "error_count": len(self.errors),
        }

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def print_summary(self):
        print(f"\n{'='*60}")
        print("QTI Conversion Report")
        print(f"{'='*60}")
        print(f"  Scanned:     {self.total_scanned:>8}")
        print(f"  Matched(A13):{self.total_matched_2022:>8}")
        print(f"  Converted:   {self.total_converted:>8}")
        print(f"  Errors:      {self.total_errors:>8}")
        print(f"  Skipped:     {self.total_skipped:>8}")
        print(f"  Images OK:   {self.total_images_copied:>8}")
        print(f"  Images miss: {self.total_images_missing:>8}")
        print(f"  Duration:    {self.duration_seconds:>7.1f}s")

        if self.by_subject:
            print(f"\n--- By Subject ---")
            for subj, cnt in sorted(self.by_subject.items()):
                print(f"  {subj}: {cnt}")

        if self.by_question_type:
            print(f"\n--- By Question Type ---")
            for qt, cnt in sorted(self.by_question_type.items()):
                print(f"  {qt}: {cnt}")

        if self.by_difficulty:
            print(f"\n--- By Difficulty ---")
            for df, cnt in sorted(self.by_difficulty.items()):
                print(f"  {df}: {cnt}")


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def find_2022_iml_files(
    input_dir: str,
    subject_filter: Optional[str] = None,
    limit: Optional[int] = None,
) -> Tuple[List[Tuple[Path, str]], int]:
    """
    Scan input_dir for IML files belonging to the 2022 curriculum.

    Returns:
        (list of (file_path, raw_cls1), total_scanned_count)
    """
    import codecs

    input_path = Path(input_dir)
    quiz_tag_re = re.compile(r'<문항\s+([^>]+)>')
    cls1_re = re.compile(r'cls1="([^"]*)"')
    cls4_re = re.compile(r'cls4="([^"]*)"')

    matched = []
    total_scanned = 0

    for root, dirs, files in os.walk(input_path):
        for fname in files:
            if not fname.endswith(".iml"):
                continue
            total_scanned += 1
            fpath = Path(root) / fname

            # Quick header scan (don't full-parse yet)
            try:
                with open(fpath, "rb") as f:
                    header = f.read(4000)
                # Try EUC-KR first (most common), then UTF-8
                try:
                    text = header.decode("euc-kr", errors="replace")
                except Exception:
                    text = header.decode("utf-8", errors="replace")

                m = quiz_tag_re.search(text)
                if not m:
                    continue

                attrs_str = m.group(1)

                # Check curriculum
                cls1_m = cls1_re.search(attrs_str)
                if not cls1_m:
                    continue
                cls1_val = cls1_m.group(1)
                if not cls1_val.startswith(CURRICULUM_2022_PREFIX):
                    continue

                # Subject filter
                if subject_filter:
                    cls4_m = cls4_re.search(attrs_str)
                    if cls4_m:
                        cls4_label = _extract_label(cls4_m.group(1))
                        if subject_filter not in cls4_label:
                            continue
                    else:
                        continue

                matched.append((fpath, cls1_val))

                if limit and len(matched) >= limit:
                    return matched, total_scanned

            except Exception as e:
                logger.debug(f"Error scanning {fpath}: {e}")
                continue

            if total_scanned % 10000 == 0:
                logger.info(f"  Scanned {total_scanned} files, matched {len(matched)}...")

    return matched, total_scanned


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def convert_single_file(
    iml_path: Path,
    output_dir: Path,
    parser: IMLParser,
    converter: QTIConverter,
    report: ConversionReport,
) -> bool:
    """Convert a single IML file to QTI. Returns True on success."""
    item = parser.parse_file(iml_path)

    if not item:
        report.add_error(str(iml_path), ["Failed to parse file"])
        return False

    if item.parse_errors:
        report.add_error(str(iml_path), item.parse_errors)
        return False

    item_id = item.metadata.id
    if not item_id:
        report.add_error(str(iml_path), ["No item ID found"])
        return False

    # Skip group passage items (지문)
    raw = item.metadata.raw_attributes
    qk = raw.get("qk", "")
    if qk.startswith("1"):
        report.total_skipped += 1
        return False

    item_output_dir = output_dir / item_id
    item_output_dir.mkdir(parents=True, exist_ok=True)

    # Generate QTI XML
    qti_xml = converter.convert_item(item, iml_path, item_output_dir)

    # Count image results
    for img_ref in item.content.question_images + item.content.explanation_images:
        img_path = item_output_dir / "images" / Path(img_ref.replace("\\", "/")).name
        if img_path.exists():
            report.total_images_copied += 1
        else:
            report.total_images_missing += 1

    # Write QTI XML
    xml_path = item_output_dir / "item.xml"
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(qti_xml)

    report.add_converted(item)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert 2022 curriculum IML items to QTI 2.1"
    )
    parser.add_argument(
        "--input-dir",
        help="Root directory containing IML files (data/raw/)",
    )
    parser.add_argument(
        "--input-file",
        help="Single IML file to convert",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for QTI files (e.g. data/qti/2022)",
    )
    parser.add_argument(
        "--subject",
        help="Filter by subject name (e.g. 수학, 국어, 과학, 사회, 역사)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of items to convert",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    if not args.input_dir and not args.input_file:
        parser.error("Either --input-dir or --input-file is required")

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = ConversionReport()
    start_time = time.time()

    # Determine raw dirs for image resolution
    raw_dirs = []
    if args.input_dir:
        raw_dirs.append(args.input_dir)
    if args.input_file:
        raw_dirs.append(str(Path(args.input_file).parent))

    image_resolver = ImageResolver(raw_dirs)
    iml_parser = IMLParser()
    converter = QTIConverter(image_resolver=image_resolver)

    if args.input_file:
        # Single file mode
        iml_path = Path(args.input_file)
        if not iml_path.exists():
            logger.error(f"File not found: {iml_path}")
            sys.exit(1)

        report.total_scanned = 1
        report.total_matched_2022 = 1
        success = convert_single_file(
            iml_path, output_dir, iml_parser, converter, report
        )
        if success:
            logger.info(f"Converted: {iml_path} -> {output_dir}")
        else:
            logger.error(f"Failed to convert: {iml_path}")

    else:
        # Batch mode
        logger.info(f"Scanning {args.input_dir} for 2022 curriculum IML files...")
        if args.subject:
            logger.info(f"Subject filter: {args.subject}")
        if args.limit:
            logger.info(f"Limit: {args.limit}")

        matched_files, total_scanned = find_2022_iml_files(
            args.input_dir,
            subject_filter=args.subject,
            limit=args.limit,
        )

        report.total_scanned = total_scanned
        report.total_matched_2022 = len(matched_files)

        logger.info(
            f"Found {len(matched_files)} files "
            f"(scanned {total_scanned} total)"
        )

        for i, (iml_path, _) in enumerate(matched_files):
            try:
                convert_single_file(
                    iml_path, output_dir, iml_parser, converter, report
                )
            except Exception as e:
                report.add_error(str(iml_path), [str(e)])
                logger.debug(f"Error converting {iml_path}: {e}")

            if (i + 1) % 1000 == 0:
                logger.info(
                    f"  Progress: {i+1}/{len(matched_files)} "
                    f"(converted: {report.total_converted}, "
                    f"errors: {report.total_errors})"
                )

    report.duration_seconds = time.time() - start_time

    # Save report
    report_path = str(output_dir / "conversion_report.json")
    report.save(report_path)
    logger.info(f"Report saved: {report_path}")

    report.print_summary()


if __name__ == "__main__":
    main()
