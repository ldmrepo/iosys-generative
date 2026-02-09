#!/usr/bin/env python3
"""테스트용 샘플 이미지 생성 스크립트"""

from pathlib import Path
from PIL import Image, ImageDraw
import random


def create_bar_chart(output_path: Path):
    """막대 그래프 이미지 생성"""
    width, height = 800, 600
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # 제목
    draw.text((width // 2 - 100, 20), "월별 판매량", fill="black")

    # 축
    margin = 80
    chart_left = margin
    chart_right = width - margin
    chart_top = 80
    chart_bottom = height - margin

    # Y축
    draw.line([(chart_left, chart_top), (chart_left, chart_bottom)], fill="black", width=2)
    # X축
    draw.line([(chart_left, chart_bottom), (chart_right, chart_bottom)], fill="black", width=2)

    # 데이터
    months = ["1월", "2월", "3월", "4월", "5월", "6월"]
    values = [random.randint(20, 100) for _ in range(6)]

    # Y축 눈금
    max_val = max(values)
    for i in range(5):
        y = chart_bottom - (i + 1) * (chart_bottom - chart_top) // 5
        val = (i + 1) * (max_val // 5 + 10)
        draw.line([(chart_left - 5, y), (chart_left, y)], fill="black")
        draw.text((chart_left - 40, y - 10), str(val), fill="black")

    # 막대 그리기
    bar_width = (chart_right - chart_left) // (len(months) + 1)
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]

    for i, (month, value) in enumerate(zip(months, values)):
        x = chart_left + (i + 1) * bar_width - bar_width // 2
        bar_height = int((value / (max_val + 20)) * (chart_bottom - chart_top))
        y = chart_bottom - bar_height

        draw.rectangle([x, y, x + bar_width - 10, chart_bottom], fill=colors[i], outline="black")
        draw.text((x + 10, chart_bottom + 10), month, fill="black")
        draw.text((x + 10, y - 20), str(value), fill="black")

    img.save(output_path)
    print(f"막대 그래프 생성: {output_path}")
    return values


def create_line_chart(output_path: Path):
    """선 그래프 이미지 생성"""
    width, height = 800, 600
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # 제목
    draw.text((width // 2 - 80, 20), "온도 변화", fill="black")

    margin = 80
    chart_left = margin
    chart_right = width - margin
    chart_top = 80
    chart_bottom = height - margin

    # 축
    draw.line([(chart_left, chart_top), (chart_left, chart_bottom)], fill="black", width=2)
    draw.line([(chart_left, chart_bottom), (chart_right, chart_bottom)], fill="black", width=2)

    # 데이터
    hours = list(range(0, 24, 4))
    temps = [random.randint(15, 35) for _ in hours]

    # Y축 눈금 (온도)
    for i in range(5):
        y = chart_bottom - (i + 1) * (chart_bottom - chart_top) // 5
        temp = 10 + (i + 1) * 6
        draw.line([(chart_left - 5, y), (chart_left, y)], fill="gray")
        draw.text((chart_left - 35, y - 10), f"{temp}°C", fill="black")

    # 데이터 포인트 계산
    points = []
    x_step = (chart_right - chart_left) // (len(hours) - 1)
    y_range = chart_bottom - chart_top

    for i, (hour, temp) in enumerate(zip(hours, temps)):
        x = chart_left + i * x_step
        y = chart_bottom - int((temp - 10) / 30 * y_range)
        points.append((x, y))
        draw.text((x - 10, chart_bottom + 10), f"{hour}시", fill="black")

    # 선 그리기
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill="blue", width=2)

    # 점 그리기
    for i, (x, y) in enumerate(points):
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill="red", outline="black")
        draw.text((x - 15, y - 25), f"{temps[i]}°", fill="black")

    img.save(output_path)
    print(f"선 그래프 생성: {output_path}")
    return dict(zip(hours, temps))


def create_geometry_image(output_path: Path):
    """기하 도형 이미지 생성"""
    width, height = 800, 600
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # 삼각형 그리기
    triangle_points = [(400, 100), (200, 400), (600, 400)]
    draw.polygon(triangle_points, outline="black", width=2)

    # 꼭짓점 레이블
    draw.text((395, 70), "A", fill="black")
    draw.text((170, 400), "B", fill="black")
    draw.text((610, 400), "C", fill="black")

    # 변의 길이 (랜덤)
    ab = random.randint(8, 15)
    bc = random.randint(10, 20)
    ac = random.randint(8, 15)

    draw.text((280, 220), f"{ab}cm", fill="blue")
    draw.text((380, 420), f"{bc}cm", fill="blue")
    draw.text((500, 220), f"{ac}cm", fill="blue")

    # 각도 표시
    draw.arc([180, 380, 220, 420], start=-30, end=0, fill="red", width=2)
    draw.text((230, 360), "60°", fill="red")

    img.save(output_path)
    print(f"기하 도형 생성: {output_path}")
    return {"AB": ab, "BC": bc, "AC": ac, "angle_B": 60}


def create_measurement_image(output_path: Path):
    """측정 기기 이미지 생성 (자/눈금)"""
    width, height = 800, 400
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # 제목
    draw.text((width // 2 - 60, 20), "길이 측정", fill="black")

    # 자 그리기
    ruler_y = 200
    ruler_start = 100
    ruler_end = 700
    ruler_height = 40

    draw.rectangle([ruler_start, ruler_y, ruler_end, ruler_y + ruler_height],
                   outline="black", fill="#FFFACD", width=2)

    # 눈금 (cm 단위)
    for i in range(16):
        x = ruler_start + i * 40
        if i % 5 == 0:
            # 큰 눈금
            draw.line([(x, ruler_y), (x, ruler_y + 30)], fill="black", width=2)
            draw.text((x - 5, ruler_y + ruler_height + 5), str(i), fill="black")
        else:
            # 작은 눈금
            draw.line([(x, ruler_y), (x, ruler_y + 15)], fill="black", width=1)

    # 측정 대상 (막대)
    object_start = random.randint(3, 5)  # 시작 위치 (cm)
    object_length = random.randint(5, 10)  # 길이 (cm)

    obj_x1 = ruler_start + object_start * 40
    obj_x2 = ruler_start + (object_start + object_length) * 40

    draw.rectangle([obj_x1, ruler_y - 60, obj_x2, ruler_y - 20],
                   fill="#87CEEB", outline="black", width=2)
    draw.text((obj_x1 + 10, ruler_y - 50), "물체", fill="black")

    # 화살표
    draw.line([(obj_x1, ruler_y - 10), (obj_x1, ruler_y + 5)], fill="red", width=2)
    draw.line([(obj_x2, ruler_y - 10), (obj_x2, ruler_y + 5)], fill="red", width=2)

    img.save(output_path)
    print(f"측정 이미지 생성: {output_path}")
    return {"start": object_start, "end": object_start + object_length, "length": object_length}


def main():
    # 출력 디렉토리
    output_dir = Path(__file__).parent.parent / "samples" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 메타데이터 저장용
    metadata = {}

    # 그래프 유형 (2개씩)
    print("\n=== 그래프 이미지 생성 ===")
    for i in range(2):
        data = create_bar_chart(output_dir / f"bar_chart_{i+1}.png")
        metadata[f"bar_chart_{i+1}"] = {"type": "graph", "data": data}

    for i in range(2):
        data = create_line_chart(output_dir / f"line_chart_{i+1}.png")
        metadata[f"line_chart_{i+1}"] = {"type": "graph", "data": data}

    # 도형 유형
    print("\n=== 도형 이미지 생성 ===")
    for i in range(2):
        data = create_geometry_image(output_dir / f"geometry_{i+1}.png")
        metadata[f"geometry_{i+1}"] = {"type": "geometry", "data": data}

    # 측정 유형
    print("\n=== 측정 이미지 생성 ===")
    for i in range(2):
        data = create_measurement_image(output_dir / f"measurement_{i+1}.png")
        metadata[f"measurement_{i+1}"] = {"type": "measurement", "data": data}

    # 메타데이터 저장
    import json
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n=== 완료 ===")
    print(f"생성된 이미지: {len(metadata)}개")
    print(f"메타데이터: {metadata_path}")


if __name__ == "__main__":
    main()
