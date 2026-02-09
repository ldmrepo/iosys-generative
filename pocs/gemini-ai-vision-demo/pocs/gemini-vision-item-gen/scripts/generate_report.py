#!/usr/bin/env python3
"""HTML 리포트 생성 스크립트"""

import json
from pathlib import Path
from datetime import datetime
import base64


def load_items(items_dir: Path) -> list[dict]:
    """문항 JSON 파일 로드"""
    items = []
    for item_file in sorted(items_dir.glob("*.json")):
        with open(item_file, "r", encoding="utf-8") as f:
            items.append(json.load(f))
    return items


def image_to_base64(image_path: str) -> str:
    """이미지를 base64로 인코딩"""
    path = Path(image_path)
    if not path.exists():
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_difficulty_badge(difficulty: str) -> str:
    """난이도별 배지 색상"""
    colors = {
        "easy": "#28a745",
        "medium": "#ffc107",
        "hard": "#dc3545"
    }
    labels = {
        "easy": "쉬움",
        "medium": "보통",
        "hard": "어려움"
    }
    color = colors.get(difficulty, "#6c757d")
    label = labels.get(difficulty, difficulty)
    return f'<span class="badge" style="background-color: {color};">{label}</span>'


def get_type_badge(item_type: str) -> str:
    """유형별 배지"""
    colors = {
        "graph": "#007bff",
        "geometry": "#6f42c1",
        "measurement": "#17a2b8"
    }
    labels = {
        "graph": "그래프",
        "geometry": "도형",
        "measurement": "측정"
    }
    color = colors.get(item_type, "#6c757d")
    label = labels.get(item_type, item_type)
    return f'<span class="badge" style="background-color: {color};">{label}</span>'


def generate_item_html(item: dict, index: int) -> str:
    """개별 문항 HTML 생성"""
    # 이미지 base64 인코딩
    img_base64 = image_to_base64(item.get("source_image", ""))
    img_html = f'<img src="data:image/png;base64,{img_base64}" alt="문항 이미지">' if img_base64 else '<div class="no-image">이미지 없음</div>'

    # 선지 HTML
    choices_html = ""
    for choice in item.get("choices", []):
        is_correct = choice["label"] == item.get("correct_answer", "")
        correct_class = "correct" if is_correct else ""
        correct_icon = " ✓" if is_correct else ""
        choices_html += f'''
        <div class="choice {correct_class}">
            <span class="choice-label">{choice["label"]}</span>
            <span class="choice-text">{choice["text"]}{correct_icon}</span>
        </div>
        '''

    # 시각 근거 HTML
    evidence = item.get("evidence", {})
    facts = evidence.get("extracted_facts", [])
    facts_html = ""
    if facts:
        facts_html = "<ul>" + "".join([f"<li>{fact}</li>" for fact in facts]) + "</ul>"
    else:
        facts_html = "<p class='no-data'>시각 근거 없음</p>"

    return f'''
    <div class="item-card">
        <div class="item-header">
            <h2>문항 #{index + 1}</h2>
            <div class="item-meta">
                <span class="item-id">{item.get("item_id", "N/A")}</span>
                {get_type_badge(item.get("item_type", ""))}
                {get_difficulty_badge(item.get("difficulty", ""))}
            </div>
        </div>

        <div class="item-content">
            <div class="image-section">
                {img_html}
                <div class="image-path">{item.get("source_image", "")}</div>
            </div>

            <div class="question-section">
                <div class="stem">
                    <h3>질문</h3>
                    <p>{item.get("stem", "")}</p>
                </div>

                <div class="choices">
                    <h3>선지</h3>
                    {choices_html}
                </div>

                <div class="answer">
                    <h3>정답</h3>
                    <div class="answer-box">{item.get("correct_answer", "")}</div>
                </div>

                <div class="explanation">
                    <h3>해설</h3>
                    <p>{item.get("explanation", "")}</p>
                </div>

                <div class="evidence">
                    <h3>시각 근거</h3>
                    {facts_html}
                </div>

                <div class="metadata">
                    <span>생성 시각: {item.get("generated_at", "")[:19]}</span>
                    <span>모델: {item.get("model_version", "")}</span>
                </div>
            </div>
        </div>
    </div>
    '''


def generate_report(items_dir: Path, output_path: Path):
    """HTML 리포트 생성"""
    items = load_items(items_dir)

    if not items:
        print("문항이 없습니다.")
        return

    # 통계
    total = len(items)
    by_type = {}
    by_difficulty = {}
    by_model = {}

    for item in items:
        t = item.get("item_type", "unknown")
        d = item.get("difficulty", "unknown")
        m = item.get("model_version", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_difficulty[d] = by_difficulty.get(d, 0) + 1
        by_model[m] = by_model.get(m, 0) + 1

    # 문항 HTML 생성
    items_html = ""
    for i, item in enumerate(items):
        items_html += generate_item_html(item, i)

    # 전체 HTML
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 문항 생성 리포트 - Gemini Agentic Vision POC</title>
    <style>
        :root {{
            --primary: #4285f4;
            --success: #28a745;
            --warning: #ffc107;
            --danger: #dc3545;
            --dark: #343a40;
            --light: #f8f9fa;
            --border: #dee2e6;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: var(--dark);
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: linear-gradient(135deg, #4285f4 0%, #34a853 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .stat-card h3 {{
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }}

        .stat-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary);
        }}

        .stat-card .detail {{
            font-size: 0.85rem;
            color: #888;
            margin-top: 5px;
        }}

        .item-card {{
            background: white;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .item-header {{
            background: var(--dark);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .item-header h2 {{
            font-size: 1.3rem;
        }}

        .item-meta {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}

        .item-id {{
            font-family: monospace;
            background: rgba(255,255,255,0.2);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
        }}

        .badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            color: white;
            font-weight: 500;
        }}

        .item-content {{
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 20px;
            padding: 20px;
        }}

        @media (max-width: 900px) {{
            .item-content {{
                grid-template-columns: 1fr;
            }}
        }}

        .image-section {{
            text-align: center;
        }}

        .image-section img {{
            max-width: 100%;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}

        .image-path {{
            font-size: 0.75rem;
            color: #888;
            margin-top: 8px;
            font-family: monospace;
        }}

        .no-image {{
            background: var(--light);
            padding: 60px 20px;
            border-radius: 8px;
            color: #888;
        }}

        .question-section h3 {{
            color: var(--primary);
            font-size: 1rem;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid var(--primary);
        }}

        .stem {{
            margin-bottom: 20px;
        }}

        .stem p {{
            font-size: 1.1rem;
            font-weight: 500;
        }}

        .choices {{
            margin-bottom: 20px;
        }}

        .choice {{
            display: flex;
            align-items: flex-start;
            padding: 12px;
            margin-bottom: 8px;
            background: var(--light);
            border-radius: 6px;
            border-left: 4px solid transparent;
        }}

        .choice.correct {{
            background: #d4edda;
            border-left-color: var(--success);
        }}

        .choice-label {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: var(--dark);
            color: white;
            border-radius: 50%;
            font-weight: bold;
            margin-right: 12px;
            flex-shrink: 0;
        }}

        .choice.correct .choice-label {{
            background: var(--success);
        }}

        .answer {{
            margin-bottom: 20px;
        }}

        .answer-box {{
            display: inline-block;
            background: var(--success);
            color: white;
            font-size: 1.5rem;
            font-weight: bold;
            width: 50px;
            height: 50px;
            line-height: 50px;
            text-align: center;
            border-radius: 8px;
        }}

        .explanation {{
            margin-bottom: 20px;
        }}

        .explanation p {{
            background: #fff3cd;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid var(--warning);
        }}

        .evidence {{
            margin-bottom: 20px;
        }}

        .evidence ul {{
            list-style: none;
            padding: 0;
        }}

        .evidence li {{
            padding: 8px 12px;
            background: #e7f3ff;
            margin-bottom: 5px;
            border-radius: 4px;
            border-left: 3px solid var(--primary);
        }}

        .evidence li::before {{
            content: "✓ ";
            color: var(--primary);
            font-weight: bold;
        }}

        .no-data {{
            color: #888;
            font-style: italic;
        }}

        .metadata {{
            display: flex;
            gap: 20px;
            font-size: 0.8rem;
            color: #888;
            padding-top: 15px;
            border-top: 1px solid var(--border);
            flex-wrap: wrap;
        }}

        footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.9rem;
        }}

        footer a {{
            color: var(--primary);
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI 문항 생성 리포트</h1>
            <p>Gemini Agentic Vision POC - {datetime.now().strftime("%Y년 %m월 %d일 %H:%M")}</p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <h3>총 문항 수</h3>
                <div class="value">{total}</div>
            </div>
            <div class="stat-card">
                <h3>문항 유형</h3>
                <div class="value">{len(by_type)}</div>
                <div class="detail">{", ".join([f"{k}: {v}개" for k, v in by_type.items()])}</div>
            </div>
            <div class="stat-card">
                <h3>난이도 분포</h3>
                <div class="value">{len(by_difficulty)}</div>
                <div class="detail">{", ".join([f"{k}: {v}개" for k, v in by_difficulty.items()])}</div>
            </div>
            <div class="stat-card">
                <h3>사용 모델</h3>
                <div class="value">{len(by_model)}</div>
                <div class="detail">{", ".join(by_model.keys())}</div>
            </div>
        </div>

        {items_html}

        <footer>
            <p>Generated by <a href="#">Gemini Agentic Vision POC</a></p>
            <p>Powered by Google Gemini 3 Flash</p>
        </footer>
    </div>
</body>
</html>
'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"리포트 생성 완료: {output_path}")
    print(f"총 {total}개 문항")


def main():
    project_root = Path(__file__).parent.parent
    items_dir = project_root / "output" / "items"
    output_path = project_root / "output" / "report.html"

    generate_report(items_dir, output_path)


if __name__ == "__main__":
    main()
