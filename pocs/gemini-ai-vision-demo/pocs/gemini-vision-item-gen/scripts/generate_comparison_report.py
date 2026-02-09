#!/usr/bin/env python3
"""Nano Banana Pro vs Matplotlib 비교 리포트 생성"""

import json
from pathlib import Path
from datetime import datetime
import base64

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nano Banana Pro 이미지 생성 비교 리포트</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        :root {{
            --primary: #7c3aed;
            --secondary: #64748b;
            --success: #10b981;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}

        .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}

        header {{
            background: linear-gradient(135deg, var(--primary), #5b21b6);
            color: white;
            padding: 3rem 2rem;
            margin-bottom: 2rem;
            border-radius: 1rem;
            text-align: center;
        }}

        header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        header p {{ opacity: 0.9; font-size: 1.1rem; }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
        }}

        .stat-card .label {{
            color: var(--secondary);
            font-size: 0.85rem;
        }}

        .comparison-section {{
            margin-bottom: 3rem;
        }}

        .section-title {{
            font-size: 1.5rem;
            color: var(--text);
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 3px solid var(--primary);
        }}

        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
        }}

        .image-card {{
            background: var(--card-bg);
            border-radius: 1rem;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}

        .image-card-header {{
            background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .image-card-header h3 {{
            font-size: 1.1rem;
            color: var(--text);
        }}

        .badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .badge-nano {{ background: var(--primary); color: white; }}
        .badge-matplotlib {{ background: #f59e0b; color: white; }}

        .image-container {{
            padding: 1.5rem;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 400px;
            background: #fafafa;
        }}

        .image-container img {{
            max-width: 100%;
            max-height: 500px;
            border-radius: 0.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}

        .image-meta {{
            padding: 1rem 1.5rem;
            background: #f8fafc;
            font-size: 0.85rem;
            color: var(--secondary);
        }}

        .item-section {{
            background: var(--card-bg);
            border-radius: 1rem;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}

        .item-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e2e8f0;
        }}

        .stem {{
            font-size: 1.1rem;
            padding: 1.5rem;
            background: #f8fafc;
            border-left: 4px solid var(--primary);
            border-radius: 0 0.5rem 0.5rem 0;
            margin-bottom: 1.5rem;
            white-space: pre-wrap;
        }}

        .choices {{
            display: grid;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }}

        .choice {{
            display: flex;
            padding: 1rem;
            background: #f8fafc;
            border-radius: 0.5rem;
        }}

        .choice.correct {{
            background: #dcfce7;
            border: 2px solid var(--success);
        }}

        .choice-label {{
            font-weight: 700;
            margin-right: 1rem;
            color: var(--secondary);
        }}

        .answer-box {{
            padding: 1.5rem;
            background: linear-gradient(135deg, #dcfce7, #d1fae5);
            border-radius: 0.75rem;
        }}

        .answer-box h4 {{ color: var(--success); margin-bottom: 0.5rem; }}

        .explanation {{
            padding: 1.5rem;
            background: #fffbeb;
            border-radius: 0.75rem;
            margin-top: 1rem;
            border: 1px solid #fde68a;
        }}

        .explanation h4 {{ color: #f59e0b; margin-bottom: 0.75rem; }}
        .explanation-content {{ white-space: pre-wrap; line-height: 1.8; }}

        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--secondary);
        }}

        @media (max-width: 900px) {{
            .comparison-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🍌 Nano Banana Pro 이미지 생성 리포트</h1>
            <p>Gemini 3 Pro Image를 활용한 AI 기반 교육용 이미지 자동 생성</p>
            <p style="margin-top: 0.5rem; opacity: 0.8;">생성 일시: {generated_at}</p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <div class="number">{nano_count}</div>
                <div class="label">Nano Banana Pro 이미지</div>
            </div>
            <div class="stat-card">
                <div class="number">{total_size}</div>
                <div class="label">총 파일 크기</div>
            </div>
            <div class="stat-card">
                <div class="number">gemini-3-pro-image</div>
                <div class="label">사용 모델</div>
            </div>
            <div class="stat-card">
                <div class="number">2K</div>
                <div class="label">이미지 해상도</div>
            </div>
        </div>

        {sections_html}

        <footer>
            <p>Nano Banana Pro (Gemini 3 Pro Image) 기반 AI 이미지 생성 시스템</p>
            <p>Model: gemini-3-pro-image-preview</p>
        </footer>
    </div>
</body>
</html>
"""


def image_to_base64(path: Path) -> str:
    """이미지를 base64로 인코딩"""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def main():
    nano_dir = Path("output/nano_banana")
    matplotlib_dir = Path("samples/images_v2")
    items_dir = Path("output/items")

    sections_html = []

    # 1. 막대 그래프 비교
    nano_bar = nano_dir / "bar_chart_nano.png"
    mpl_bar = matplotlib_dir / "bar_chart_1.png"

    if nano_bar.exists():
        bar_section = f"""
        <div class="comparison-section">
            <h2 class="section-title">📊 막대 그래프 비교</h2>
            <div class="comparison-grid">
                <div class="image-card">
                    <div class="image-card-header">
                        <h3>Nano Banana Pro</h3>
                        <span class="badge badge-nano">AI Generated</span>
                    </div>
                    <div class="image-container">
                        <img src="data:image/png;base64,{image_to_base64(nano_bar)}" alt="Nano Banana Bar Chart">
                    </div>
                    <div class="image-meta">
                        크기: {nano_bar.stat().st_size / 1024:.1f} KB | 모델: gemini-3-pro-image-preview
                    </div>
                </div>
                {"" if not mpl_bar.exists() else f'''
                <div class="image-card">
                    <div class="image-card-header">
                        <h3>Matplotlib (기존)</h3>
                        <span class="badge badge-matplotlib">Code Generated</span>
                    </div>
                    <div class="image-container">
                        <img src="data:image/png;base64,{image_to_base64(mpl_bar)}" alt="Matplotlib Bar Chart">
                    </div>
                    <div class="image-meta">
                        크기: {mpl_bar.stat().st_size / 1024:.1f} KB | 라이브러리: Matplotlib
                    </div>
                </div>
                '''}
            </div>
        </div>
        """
        sections_html.append(bar_section)

    # 2. 삼각형 비교
    nano_tri = nano_dir / "triangle_nano.png"
    mpl_geo = matplotlib_dir / "geometry_1.png"

    if nano_tri.exists():
        tri_section = f"""
        <div class="comparison-section">
            <h2 class="section-title">📐 기하 도형 비교</h2>
            <div class="comparison-grid">
                <div class="image-card">
                    <div class="image-card-header">
                        <h3>Nano Banana Pro</h3>
                        <span class="badge badge-nano">AI Generated</span>
                    </div>
                    <div class="image-container">
                        <img src="data:image/png;base64,{image_to_base64(nano_tri)}" alt="Nano Banana Triangle">
                    </div>
                    <div class="image-meta">
                        크기: {nano_tri.stat().st_size / 1024:.1f} KB | 모델: gemini-3-pro-image-preview
                    </div>
                </div>
                {"" if not mpl_geo.exists() else f'''
                <div class="image-card">
                    <div class="image-card-header">
                        <h3>Matplotlib (기존)</h3>
                        <span class="badge badge-matplotlib">Code Generated</span>
                    </div>
                    <div class="image-container">
                        <img src="data:image/png;base64,{image_to_base64(mpl_geo)}" alt="Matplotlib Geometry">
                    </div>
                    <div class="image-meta">
                        크기: {mpl_geo.stat().st_size / 1024:.1f} KB | 라이브러리: Matplotlib
                    </div>
                </div>
                '''}
            </div>
        </div>
        """
        sections_html.append(tri_section)

    # 3. 함수 그래프 (문항 시각화)
    nano_func = nano_dir / "function_graph_nano.png"
    nano_exam = nano_dir / "exam_visual_nano.png"

    if nano_func.exists() or nano_exam.exists():
        func_section = f"""
        <div class="comparison-section">
            <h2 class="section-title">📈 함수 그래프 (문항 시각화)</h2>
            <div class="comparison-grid">
                {"" if not nano_func.exists() else f'''
                <div class="image-card">
                    <div class="image-card-header">
                        <h3>함수 그래프 (직접 생성)</h3>
                        <span class="badge badge-nano">AI Generated</span>
                    </div>
                    <div class="image-container">
                        <img src="data:image/png;base64,{image_to_base64(nano_func)}" alt="Function Graph">
                    </div>
                    <div class="image-meta">
                        함수: y = x³ - 3x² - 4x + 12 | 점 O, P, Q 표시 | 영역 A, B 색칠
                    </div>
                </div>
                '''}
                {"" if not nano_exam.exists() else f'''
                <div class="image-card">
                    <div class="image-card-header">
                        <h3>시각화 사양 기반 생성</h3>
                        <span class="badge badge-nano">AI Generated</span>
                    </div>
                    <div class="image-container">
                        <img src="data:image/png;base64,{image_to_base64(nano_exam)}" alt="Exam Visual">
                    </div>
                    <div class="image-meta">
                        기출 문항의 visual_specification에서 자동 생성
                    </div>
                </div>
                '''}
            </div>
        </div>
        """
        sections_html.append(func_section)

    # 4. 생성된 문항 + 이미지
    graph_item_path = items_dir / "exam_graph_item.json"
    if graph_item_path.exists() and nano_exam.exists():
        with open(graph_item_path, "r", encoding="utf-8") as f:
            item_data = json.load(f)

        gen_item = item_data.get("generated_item", {})

        choices_html = ""
        for choice in gen_item.get("choices", []):
            label = choice.get("label", "")
            text = choice.get("text", "")
            correct = gen_item.get("correct_answer", "")
            is_correct = label == correct
            choices_html += f'''
            <div class="choice {"correct" if is_correct else ""}">
                <span class="choice-label">{label}</span>
                <span>{text}</span>
            </div>
            '''

        item_section = f"""
        <div class="item-section">
            <div class="item-header">
                <h2>🎯 생성된 문항 + AI 이미지</h2>
                <span class="badge badge-nano">Complete Item</span>
            </div>

            <div class="comparison-grid" style="margin-bottom: 1.5rem;">
                <div>
                    <h3 style="margin-bottom: 1rem; color: var(--secondary);">AI 생성 이미지</h3>
                    <img src="data:image/png;base64,{image_to_base64(nano_exam)}"
                         style="max-width: 100%; border-radius: 0.5rem; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                </div>
                <div>
                    <h3 style="margin-bottom: 1rem; color: var(--secondary);">원본 기출 이미지</h3>
                    {"" if not Path("samples/exams/2025/math/kice-2025-exam-math-high_page_05.png").exists() else f'''
                    <img src="data:image/png;base64,{image_to_base64(Path("samples/exams/2025/math/kice-2025-exam-math-high_page_05.png"))}"
                         style="max-width: 100%; border-radius: 0.5rem; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                    '''}
                </div>
            </div>

            <div class="stem">{gen_item.get("stem", "")}</div>

            <div class="choices">
                {choices_html}
            </div>

            <div class="answer-box">
                <h4>✅ 정답</h4>
                <p><strong>{gen_item.get("correct_answer", "")}</strong></p>
            </div>

            <div class="explanation">
                <h4>📝 풀이</h4>
                <div class="explanation-content">{gen_item.get("explanation", "")}</div>
            </div>
        </div>
        """
        sections_html.append(item_section)

    # 통계 계산
    nano_files = list(nano_dir.glob("*.png")) if nano_dir.exists() else []
    nano_count = len(nano_files)
    total_size = sum(f.stat().st_size for f in nano_files) / 1024
    total_size_str = f"{total_size:.1f} KB" if total_size < 1024 else f"{total_size/1024:.1f} MB"

    # HTML 생성
    html_content = HTML_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nano_count=nano_count,
        total_size=total_size_str,
        sections_html="\n".join(sections_html)
    )

    # 저장
    report_path = Path("output/nano_banana_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✓ 리포트 생성 완료: {report_path}")
    print(f"  - Nano Banana Pro 이미지: {nano_count}개")
    print(f"  - 총 크기: {total_size_str}")

    return report_path


if __name__ == "__main__":
    path = main()
    import subprocess
    subprocess.run(["open", str(path)])
