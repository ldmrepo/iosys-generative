#!/usr/bin/env python3
"""기출 기반 생성 문항 HTML 리포트 생성"""

import json
from pathlib import Path
from datetime import datetime
import base64

# 리포트 HTML 템플릿
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>기출 기반 AI 문항 생성 리포트</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        :root {{
            --primary: #2563eb;
            --secondary: #64748b;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --border: #e2e8f0;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        header {{
            background: linear-gradient(135deg, var(--primary), #1d4ed8);
            color: white;
            padding: 3rem 2rem;
            margin-bottom: 2rem;
            border-radius: 1rem;
            box-shadow: 0 10px 40px rgba(37, 99, 235, 0.2);
        }}

        header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        header p {{
            opacity: 0.9;
            font-size: 1.1rem;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            text-align: center;
        }}

        .stat-card .number {{
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary);
        }}

        .stat-card .label {{
            color: var(--secondary);
            font-size: 0.9rem;
        }}

        .section {{
            margin-bottom: 2rem;
        }}

        .section-title {{
            font-size: 1.5rem;
            color: var(--text);
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--primary);
        }}

        .item-card {{
            background: var(--card-bg);
            border-radius: 1rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            margin-bottom: 2rem;
            overflow: hidden;
        }}

        .item-header {{
            background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
            padding: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .item-id {{
            font-weight: 700;
            font-size: 1.2rem;
            color: var(--primary);
        }}

        .item-meta {{
            display: flex;
            gap: 0.5rem;
        }}

        .badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .badge-primary {{
            background: var(--primary);
            color: white;
        }}

        .badge-success {{
            background: var(--success);
            color: white;
        }}

        .badge-warning {{
            background: var(--warning);
            color: white;
        }}

        .item-content {{
            padding: 2rem;
        }}

        .stem {{
            font-size: 1.1rem;
            margin-bottom: 1.5rem;
            padding: 1.5rem;
            background: #f8fafc;
            border-left: 4px solid var(--primary);
            border-radius: 0 0.5rem 0.5rem 0;
            white-space: pre-wrap;
        }}

        .choices {{
            display: grid;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }}

        .choice {{
            display: flex;
            align-items: flex-start;
            padding: 1rem;
            background: #f8fafc;
            border-radius: 0.5rem;
            transition: all 0.2s;
        }}

        .choice:hover {{
            background: #e2e8f0;
        }}

        .choice.correct {{
            background: #dcfce7;
            border: 2px solid var(--success);
        }}

        .choice-label {{
            font-weight: 700;
            margin-right: 1rem;
            color: var(--secondary);
            min-width: 2rem;
        }}

        .answer-section {{
            margin-top: 1.5rem;
            padding: 1.5rem;
            background: linear-gradient(135deg, #dcfce7, #d1fae5);
            border-radius: 0.75rem;
        }}

        .answer-section h4 {{
            color: var(--success);
            margin-bottom: 0.5rem;
        }}

        .explanation {{
            margin-top: 1.5rem;
            padding: 1.5rem;
            background: #fffbeb;
            border-radius: 0.75rem;
            border: 1px solid #fde68a;
        }}

        .explanation h4 {{
            color: var(--warning);
            margin-bottom: 0.75rem;
        }}

        .explanation-content {{
            white-space: pre-wrap;
            line-height: 1.8;
        }}

        .visual-spec {{
            margin-top: 1.5rem;
            padding: 1.5rem;
            background: #ede9fe;
            border-radius: 0.75rem;
            border: 1px solid #c4b5fd;
        }}

        .visual-spec h4 {{
            color: #7c3aed;
            margin-bottom: 0.75rem;
        }}

        .visual-spec-content {{
            white-space: pre-wrap;
            font-family: 'Consolas', monospace;
            font-size: 0.9rem;
        }}

        .source-image {{
            margin-top: 1.5rem;
            padding: 1.5rem;
            background: #f1f5f9;
            border-radius: 0.75rem;
        }}

        .source-image h4 {{
            color: var(--secondary);
            margin-bottom: 1rem;
        }}

        .source-image img {{
            max-width: 100%;
            border-radius: 0.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}

        .original-analysis {{
            margin-bottom: 1.5rem;
            padding: 1rem;
            background: #dbeafe;
            border-radius: 0.75rem;
        }}

        .original-analysis h4 {{
            color: var(--primary);
            margin-bottom: 0.5rem;
        }}

        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--secondary);
            font-size: 0.9rem;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}

            header {{
                padding: 2rem 1rem;
            }}

            header h1 {{
                font-size: 1.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 기출 기반 AI 문항 생성 리포트</h1>
            <p>2025학년도 수능 수학 기출 분석 기반 유사 문항 자동 생성 결과</p>
            <p style="margin-top: 0.5rem; opacity: 0.8;">생성 일시: {generated_at}</p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <div class="number">{total_items}</div>
                <div class="label">생성 문항 수</div>
            </div>
            <div class="stat-card">
                <div class="number">{source_pages}</div>
                <div class="label">분석 페이지</div>
            </div>
            <div class="stat-card">
                <div class="number">수학</div>
                <div class="label">과목</div>
            </div>
            <div class="stat-card">
                <div class="number">2025</div>
                <div class="label">기출 년도</div>
            </div>
        </div>

        {items_html}

        <footer>
            <p>Gemini Agentic Vision 기반 AI 문항 생성 시스템</p>
            <p>Model: gemini-3-flash-preview | Data Source: KICE 2025 수능</p>
        </footer>
    </div>
</body>
</html>
"""

ITEM_TEMPLATE = """
<div class="section">
    <h2 class="section-title">{section_title}</h2>
    <div class="item-card">
        <div class="item-header">
            <span class="item-id">{item_id}</span>
            <div class="item-meta">
                <span class="badge badge-primary">{math_concept}</span>
                <span class="badge badge-{difficulty_class}">{difficulty}</span>
            </div>
        </div>
        <div class="item-content">
            {original_analysis_html}

            <div class="stem">{stem}</div>

            <div class="choices">
                {choices_html}
            </div>

            <div class="answer-section">
                <h4>✅ 정답</h4>
                <p><strong>{correct_answer}</strong></p>
            </div>

            <div class="explanation">
                <h4>📝 풀이</h4>
                <div class="explanation-content">{explanation}</div>
            </div>

            {visual_spec_html}

            {source_image_html}
        </div>
    </div>
</div>
"""


def load_json_file(path: Path) -> dict:
    """JSON 파일 로드"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def image_to_base64(image_path: Path) -> str:
    """이미지를 base64로 인코딩"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def render_choices(choices: list, correct_answer: str) -> str:
    """선택지 HTML 렌더링"""
    html_parts = []
    for choice in choices:
        label = choice.get("label", "")
        text = choice.get("text", "")
        is_correct = label == correct_answer or text == correct_answer
        correct_class = "correct" if is_correct else ""
        html_parts.append(f'''
            <div class="choice {correct_class}">
                <span class="choice-label">{label}</span>
                <span>{text}</span>
            </div>
        ''')
    return "\n".join(html_parts)


def render_item(data: dict, section_title: str, source_image: Path = None) -> str:
    """개별 문항 HTML 렌더링"""

    # 기출 분석 기반 문항인 경우
    if "generated_item" in data:
        item = data["generated_item"]
        original = data.get("original_analysis") or data.get("selected_item", {})

        original_html = ""
        if original:
            original_html = f'''
            <div class="original-analysis">
                <h4>📌 원본 기출 분석</h4>
                <p><strong>문항 번호:</strong> {original.get("number", "-")}</p>
                <p><strong>원본 요약:</strong> {original.get("content_summary", original.get("visual_type", "-"))}</p>
                <p><strong>수학 개념:</strong> {original.get("math_concept", "-")}</p>
            </div>
            '''

        item_id = item.get("item_id", "EXAM-GEN")
        stem = item.get("stem", "")
        choices = item.get("choices", [])
        correct = item.get("correct_answer", "")
        explanation = item.get("explanation", "")
        math_concept = original.get("math_concept", "미분법")
        difficulty = original.get("difficulty", "중")

        # 시각화 사양
        visual_spec_html = ""
        if "visual_specification" in item:
            spec = item["visual_specification"]
            visual_spec_html = f'''
            <div class="visual-spec">
                <h4>🎨 시각화 사양</h4>
                <p><strong>유형:</strong> {spec.get("type", "-")}</p>
                <p><strong>설명:</strong> {spec.get("description", "-")}</p>
                <div class="visual-spec-content"><strong>렌더링 지침:</strong>
{spec.get("rendering_instructions", "-")}</div>
            </div>
            '''
    else:
        # 일반 문항
        item = data
        original_html = ""
        item_id = item.get("item_id", "ITEM")
        stem = item.get("stem", "")
        choices = item.get("choices", [])
        correct = item.get("correct_answer", "")
        explanation = item.get("explanation", "")
        math_concept = item.get("math_concept", "수학")
        difficulty = item.get("difficulty", "중")
        visual_spec_html = ""

    # 난이도 배지 색상
    difficulty_class = "warning"
    if "상" in difficulty:
        difficulty_class = "danger"
    elif "하" in difficulty:
        difficulty_class = "success"

    # 소스 이미지
    source_image_html = ""
    if source_image and source_image.exists():
        img_b64 = image_to_base64(source_image)
        source_image_html = f'''
        <div class="source-image">
            <h4>📷 원본 기출 이미지</h4>
            <img src="data:image/png;base64,{img_b64}" alt="Source exam page">
        </div>
        '''

    return ITEM_TEMPLATE.format(
        section_title=section_title,
        item_id=item_id,
        math_concept=math_concept,
        difficulty=difficulty,
        difficulty_class=difficulty_class,
        original_analysis_html=original_html,
        stem=stem,
        choices_html=render_choices(choices, correct),
        correct_answer=correct,
        explanation=explanation,
        visual_spec_html=visual_spec_html,
        source_image_html=source_image_html,
    )


def main():
    """메인 리포트 생성"""
    output_dir = Path("output")
    items_dir = output_dir / "items"
    exam_images_dir = Path("samples/exams/2025/math")

    items_html_parts = []
    total_items = 0

    # 1. 기본 미분법 문항 (exam_based_item.json)
    basic_item_path = items_dir / "exam_based_item.json"
    if basic_item_path.exists():
        data = load_json_file(basic_item_path)
        source_img = exam_images_dir / "kice-2025-exam-math-high_page_02.png"
        html = render_item(data, "문항 1: 미분법 (곱의 미분법)", source_img)
        items_html_parts.append(html)
        total_items += 1

    # 2. 그래프 문항 (exam_graph_item.json)
    graph_item_path = items_dir / "exam_graph_item.json"
    if graph_item_path.exists():
        data = load_json_file(graph_item_path)
        source_img = exam_images_dir / "kice-2025-exam-math-high_page_05.png"
        html = render_item(data, "문항 2: 그래프 (정적분과 넓이)", source_img)
        items_html_parts.append(html)
        total_items += 1

    # 3. 기존 생성 문항들 (ITEM-*.json)
    existing_items = sorted(items_dir.glob("ITEM-*.json"))
    for i, item_path in enumerate(existing_items[:3]):  # 최대 3개
        data = load_json_file(item_path)
        html = render_item(
            {
                "generated_item": {
                    "item_id": data.get("item_id", item_path.stem),
                    "stem": data.get("stem", ""),
                    "choices": data.get("choices", []),
                    "correct_answer": data.get("correct_answer", ""),
                    "explanation": data.get("explanation", ""),
                }
            },
            f"문항 {total_items + 1}: 샘플 이미지 기반",
            None
        )
        items_html_parts.append(html)
        total_items += 1

    # HTML 생성
    source_pages = len(list(exam_images_dir.glob("*.png"))) if exam_images_dir.exists() else 0

    html_content = HTML_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_items=total_items,
        source_pages=source_pages,
        items_html="\n".join(items_html_parts),
    )

    # 저장
    report_path = output_dir / "exam_based_report.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✓ 리포트 생성 완료: {report_path}")
    print(f"  - 총 문항 수: {total_items}")
    print(f"  - 분석 페이지: {source_pages}")

    return report_path


if __name__ == "__main__":
    main()
