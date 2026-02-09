#!/usr/bin/env python3
"""고품질 샘플 이미지 생성 스크립트 v2 - Matplotlib 기반"""

from pathlib import Path
import random
import json
import platform

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Arc
import matplotlib.font_manager as fm
import numpy as np


def setup_korean_font():
    """한글 폰트 설정"""
    system = platform.system()

    if system == "Darwin":  # macOS
        font_candidates = [
            "AppleGothic",
            "Apple SD Gothic Neo",
            "NanumGothic"
        ]
    elif system == "Windows":
        font_candidates = [
            "Malgun Gothic",
            "NanumGothic",
            "Gulim"
        ]
    else:  # Linux
        font_candidates = [
            "NanumGothic",
            "UnDotum",
            "DejaVu Sans"
        ]

    # 사용 가능한 폰트 찾기
    available_fonts = [f.name for f in fm.fontManager.ttflist]

    for font in font_candidates:
        if font in available_fonts:
            plt.rcParams['font.family'] = font
            print(f"폰트 설정: {font}")
            break
    else:
        print("경고: 한글 폰트를 찾을 수 없습니다. 기본 폰트 사용")

    plt.rcParams['axes.unicode_minus'] = False


def create_bar_chart(output_path: Path) -> list:
    """고품질 막대 그래프 생성"""
    fig, ax = plt.subplots(figsize=(10, 7), dpi=150)

    months = ["1월", "2월", "3월", "4월", "5월", "6월"]
    values = [random.randint(20, 100) for _ in range(6)]

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']

    bars = ax.bar(months, values, color=colors, edgecolor='black', linewidth=1.2)

    # 데이터 레이블
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                str(val), ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax.set_xlabel('월', fontsize=14)
    ax.set_ylabel('판매량 (개)', fontsize=14)
    ax.set_title('월별 판매량', fontsize=20, fontweight='bold', pad=20)

    ax.set_ylim(0, max(values) + 15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # 테두리 스타일
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"막대 그래프 생성: {output_path}")
    return values


def create_line_chart(output_path: Path) -> dict:
    """고품질 선 그래프 생성"""
    fig, ax = plt.subplots(figsize=(10, 7), dpi=150)

    hours = list(range(0, 24, 4))
    temps = [random.randint(15, 35) for _ in hours]

    ax.plot(hours, temps, 'b-', linewidth=2.5, marker='o', markersize=10,
            markerfacecolor='red', markeredgecolor='black', markeredgewidth=1.5)

    # 데이터 레이블
    for h, t in zip(hours, temps):
        ax.annotate(f'{t}°C', (h, t), textcoords="offset points",
                   xytext=(0, 12), ha='center', fontsize=11, fontweight='bold')

    ax.set_xlabel('시간', fontsize=14)
    ax.set_ylabel('온도 (°C)', fontsize=14)
    ax.set_title('시간대별 온도 변화', fontsize=20, fontweight='bold', pad=20)

    ax.set_xticks(hours)
    ax.set_xticklabels([f'{h}시' for h in hours])
    ax.set_ylim(min(temps) - 5, max(temps) + 10)
    ax.set_xlim(-1, 24)

    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"선 그래프 생성: {output_path}")
    return dict(zip(hours, temps))


def create_geometry_image(output_path: Path) -> dict:
    """고품질 기하 도형 생성"""
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)

    # 삼각형 꼭짓점
    A = (5, 8)
    B = (2, 2)
    C = (8, 2)

    # 삼각형 그리기
    triangle = plt.Polygon([A, B, C], fill=False, edgecolor='black', linewidth=2.5)
    ax.add_patch(triangle)

    # 꼭짓점 레이블
    ax.annotate('A', A, textcoords="offset points", xytext=(0, 15),
               ha='center', fontsize=18, fontweight='bold')
    ax.annotate('B', B, textcoords="offset points", xytext=(-15, -10),
               ha='center', fontsize=18, fontweight='bold')
    ax.annotate('C', C, textcoords="offset points", xytext=(15, -10),
               ha='center', fontsize=18, fontweight='bold')

    # 변의 길이 (랜덤)
    ab = random.randint(8, 15)
    bc = random.randint(10, 20)
    ac = random.randint(8, 15)

    # 변 레이블 (중점에 배치)
    mid_ab = ((A[0] + B[0])/2 - 0.8, (A[1] + B[1])/2)
    mid_bc = ((B[0] + C[0])/2, (B[1] + C[1])/2 - 0.8)
    mid_ac = ((A[0] + C[0])/2 + 0.8, (A[1] + C[1])/2)

    ax.annotate(f'{ab}cm', mid_ab, fontsize=14, color='blue', fontweight='bold')
    ax.annotate(f'{bc}cm', mid_bc, fontsize=14, color='blue', fontweight='bold')
    ax.annotate(f'{ac}cm', mid_ac, fontsize=14, color='blue', fontweight='bold')

    # 각도 B 표시 (60°)
    angle = 60
    arc = Arc(B, 1.2, 1.2, angle=0, theta1=0, theta2=angle,
             color='red', linewidth=2)
    ax.add_patch(arc)
    ax.annotate(f'{angle}°', (B[0] + 0.9, B[1] + 0.5),
               fontsize=14, color='red', fontweight='bold')

    # 꼭짓점 점 표시
    for point in [A, B, C]:
        ax.plot(*point, 'ko', markersize=8)

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')

    # 제목
    ax.set_title('삼각형 ABC', fontsize=20, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"기하 도형 생성: {output_path}")
    return {"AB": ab, "BC": bc, "AC": ac, "angle_B": angle}


def create_measurement_image(output_path: Path) -> dict:
    """고품질 측정 이미지 생성"""
    fig, ax = plt.subplots(figsize=(12, 5), dpi=150)

    # 자 그리기
    ruler_y = 0.4
    ruler_height = 0.15

    # 자 배경
    ruler = FancyBboxPatch((0, ruler_y), 15, ruler_height,
                           boxstyle="round,pad=0.02",
                           facecolor='#FFFACD', edgecolor='black', linewidth=2)
    ax.add_patch(ruler)

    # 눈금 그리기
    for i in range(16):
        x = i
        if i % 5 == 0:
            # 큰 눈금
            ax.plot([x, x], [ruler_y, ruler_y + ruler_height * 0.8], 'k-', linewidth=2)
            ax.text(x, ruler_y - 0.08, str(i), ha='center', fontsize=12, fontweight='bold')
        elif i % 1 == 0:
            # 작은 눈금
            ax.plot([x, x], [ruler_y, ruler_y + ruler_height * 0.5], 'k-', linewidth=1)

    # cm 단위 표시
    ax.text(15.5, ruler_y + ruler_height/2, 'cm', fontsize=12, va='center')

    # 측정 대상 (막대)
    object_start = random.randint(2, 4)
    object_length = random.randint(5, 9)
    object_end = object_start + object_length

    obj = FancyBboxPatch((object_start, ruler_y + ruler_height + 0.15),
                         object_length, 0.2,
                         boxstyle="round,pad=0.02",
                         facecolor='#87CEEB', edgecolor='black', linewidth=2)
    ax.add_patch(obj)
    ax.text(object_start + object_length/2, ruler_y + ruler_height + 0.25,
           '물체', ha='center', va='center', fontsize=14, fontweight='bold')

    # 측정 화살표
    arrow_y = ruler_y + ruler_height + 0.05
    ax.annotate('', xy=(object_start, arrow_y), xytext=(object_start, ruler_y + ruler_height),
               arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax.annotate('', xy=(object_end, arrow_y), xytext=(object_end, ruler_y + ruler_height),
               arrowprops=dict(arrowstyle='->', color='red', lw=2))

    # 양방향 화살표와 길이 표시
    ax.annotate('', xy=(object_end, ruler_y - 0.25), xytext=(object_start, ruler_y - 0.25),
               arrowprops=dict(arrowstyle='<->', color='green', lw=2))
    ax.text((object_start + object_end)/2, ruler_y - 0.35,
           f'길이 = ? cm', ha='center', fontsize=14, fontweight='bold', color='green')

    ax.set_xlim(-0.5, 16)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.axis('off')

    ax.set_title('길이 측정', fontsize=20, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"측정 이미지 생성: {output_path}")
    return {"start": object_start, "end": object_end, "length": object_length}


def create_pie_chart(output_path: Path) -> dict:
    """고품질 원 그래프 생성 (추가 유형)"""
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)

    categories = ['A반', 'B반', 'C반', 'D반']
    values = [random.randint(15, 35) for _ in range(4)]
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']

    wedges, texts, autotexts = ax.pie(
        values,
        labels=categories,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        explode=(0.02, 0.02, 0.02, 0.02),
        shadow=True,
        textprops={'fontsize': 14}
    )

    for autotext in autotexts:
        autotext.set_fontsize(12)
        autotext.set_fontweight('bold')

    ax.set_title('반별 학생 수 비율', fontsize=20, fontweight='bold', pad=20)

    # 범례
    ax.legend(wedges, [f'{cat}: {val}명' for cat, val in zip(categories, values)],
             title="반", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"원 그래프 생성: {output_path}")
    return dict(zip(categories, values))


def main():
    # 한글 폰트 설정
    setup_korean_font()

    # 출력 디렉토리
    output_dir = Path(__file__).parent.parent / "samples" / "images_v2"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {}

    print("\n=== 고품질 그래프 이미지 생성 (v2) ===\n")

    # 막대 그래프
    for i in range(2):
        data = create_bar_chart(output_dir / f"bar_chart_{i+1}.png")
        metadata[f"bar_chart_{i+1}"] = {"type": "graph", "subtype": "bar", "data": data}

    # 선 그래프
    for i in range(2):
        data = create_line_chart(output_dir / f"line_chart_{i+1}.png")
        metadata[f"line_chart_{i+1}"] = {"type": "graph", "subtype": "line", "data": data}

    # 원 그래프 (추가)
    for i in range(2):
        data = create_pie_chart(output_dir / f"pie_chart_{i+1}.png")
        metadata[f"pie_chart_{i+1}"] = {"type": "graph", "subtype": "pie", "data": data}

    # 도형
    print()
    for i in range(2):
        data = create_geometry_image(output_dir / f"geometry_{i+1}.png")
        metadata[f"geometry_{i+1}"] = {"type": "geometry", "data": data}

    # 측정
    print()
    for i in range(2):
        data = create_measurement_image(output_dir / f"measurement_{i+1}.png")
        metadata[f"measurement_{i+1}"] = {"type": "measurement", "data": data}

    # 메타데이터 저장
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n=== 완료 ===")
    print(f"생성된 이미지: {len(metadata)}개")
    print(f"출력 디렉토리: {output_dir}")
    print(f"메타데이터: {metadata_path}")


if __name__ == "__main__":
    main()
