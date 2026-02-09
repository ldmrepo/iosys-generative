"""파싱 결과 HTML 리포트 생성

이미지와 파싱 결과를 나란히 비교할 수 있는 HTML 문서를 생성합니다.
"""

import base64
from pathlib import Path
from typing import Optional

from ..core.schemas import ParsedItem, ContentType


class HTMLReportGenerator:
    """HTML 리포트 생성기"""

    def __init__(self):
        self.template = self._get_template()

    def generate(
        self,
        parsed_items: list[ParsedItem],
        output_path: Path,
        title: str = "문항 파싱 결과"
    ) -> Path:
        """HTML 리포트 생성

        Args:
            parsed_items: 파싱된 문항 목록
            output_path: 출력 파일 경로
            title: 리포트 제목

        Returns:
            생성된 파일 경로
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 문항별 HTML 생성
        items_html = []
        for item in parsed_items:
            item_html = self._render_item(item)
            items_html.append(item_html)

        # 전체 HTML 조합
        html = self.template.format(
            title=title,
            items="\n".join(items_html)
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def _render_item(self, item: ParsedItem) -> str:
        """단일 문항 HTML 렌더링"""
        # 이미지 base64 인코딩
        image_data = ""
        if item.source_image and Path(item.source_image).exists():
            with open(item.source_image, "rb") as f:
                image_bytes = f.read()
            image_data = base64.b64encode(image_bytes).decode("utf-8")

        # 질문 콘텐츠 렌더링
        question_html = self._render_content_blocks(item.question)

        # 선택지 렌더링
        choices_html = ""
        if item.choices:
            choices_html = "<div class='choices'>"
            for choice in item.choices:
                choice_content = self._render_content_blocks(choice.content)
                choices_html += f"<div class='choice'><span class='label'>{choice.label}</span> {choice_content}</div>"
            choices_html += "</div>"

        # 보기 박스 렌더링
        boxed_html = ""
        if item.has_boxed_text and item.boxed_content:
            boxed_content = self._render_content_blocks(item.boxed_content)
            boxed_html = f"<div class='boxed-content'><div class='boxed-title'>〈보기〉</div>{boxed_content}</div>"

        return f"""
        <div class="item-card">
            <div class="item-header">문항 {item.item_number}</div>
            <div class="item-content">
                <div class="image-panel">
                    <div class="panel-title">원본 이미지</div>
                    <img src="data:image/png;base64,{image_data}" alt="문항 {item.item_number}">
                </div>
                <div class="parsed-panel">
                    <div class="panel-title">파싱 결과</div>
                    <div class="question">{question_html}</div>
                    {boxed_html}
                    {choices_html}
                </div>
            </div>
        </div>
        """

    def _render_content_blocks(self, blocks: list) -> str:
        """콘텐츠 블록 목록 렌더링"""
        html_parts = []
        for block in blocks:
            if block.type == ContentType.TEXT:
                html_parts.append(f"<span class='text-block'>{block.value}</span>")
            elif block.type == ContentType.MATH:
                # LaTeX 수식 (MathJax로 렌더링)
                escaped = block.value.replace("\\", "\\\\")
                html_parts.append(f"<span class='math-block'>\\({escaped}\\)</span>")
            elif block.type == ContentType.IMAGE:
                desc = block.description or "이미지"
                html_parts.append(f"<span class='image-block'>[이미지: {desc}]</span>")
            elif block.type == ContentType.TABLE:
                html_parts.append(f"<div class='table-block'>{block.value}</div>")
            else:
                html_parts.append(f"<span>{block.value}</span>")

        return " ".join(html_parts)

    def _get_template(self) -> str:
        """HTML 템플릿"""
        return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }}
        .item-card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            overflow: hidden;
        }}
        .item-header {{
            background: #2196F3;
            color: white;
            padding: 12px 20px;
            font-size: 18px;
            font-weight: bold;
        }}
        .item-content {{
            display: flex;
            gap: 20px;
            padding: 20px;
        }}
        .image-panel, .parsed-panel {{
            flex: 1;
            min-width: 0;
        }}
        .panel-title {{
            font-weight: bold;
            color: #666;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid #eee;
        }}
        .image-panel img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .question {{
            font-size: 16px;
            margin-bottom: 15px;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 4px;
        }}
        .choices {{
            margin-top: 15px;
        }}
        .choice {{
            padding: 8px 12px;
            margin: 5px 0;
            background: #fafafa;
            border-left: 3px solid #2196F3;
            border-radius: 0 4px 4px 0;
        }}
        .choice .label {{
            font-weight: bold;
            color: #2196F3;
            margin-right: 8px;
        }}
        .boxed-content {{
            border: 2px solid #FF9800;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            background: #FFF8E1;
        }}
        .boxed-title {{
            font-weight: bold;
            color: #FF9800;
            margin-bottom: 10px;
        }}
        .text-block {{
            color: #333;
        }}
        .math-block {{
            color: #1565C0;
            font-family: 'Times New Roman', serif;
        }}
        .image-block {{
            display: inline-block;
            background: #E3F2FD;
            color: #1565C0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 14px;
        }}
        .table-block {{
            overflow-x: auto;
            margin: 10px 0;
        }}
        .table-block table {{
            border-collapse: collapse;
            width: 100%;
        }}
        .table-block td, .table-block th {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
        }}
        @media (max-width: 900px) {{
            .item-content {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {items}
</body>
</html>
"""
