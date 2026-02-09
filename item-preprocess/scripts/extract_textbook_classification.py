"""
2022개정교육과정 문항(IML)에서 교과서 분류 체계를 중복 없이 추출한다.

입력: data/raw/**/*.iml (KSC-5601 인코딩)
출력: item-preprocess/textbook_classification_2022.json
      item-preprocess/textbook_classification_2022.csv

분류 필드: cls1~cls12 (교육과정 > 학교급 > 학년 > 과목코드 > 과목상세 > 학기 > 대단원 > 중단원 > 소단원 > 세단원 ...)
"""

import os
import re
import json
import csv
import sys
from collections import defaultdict

RAW_DIR = os.path.join(os.path.dirname(__file__), "../../data/raw")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..")

CLS_KEYS = [f"cls{i}" for i in range(1, 13)]
CLS_LABELS = {
    "cls1": "교육과정",
    "cls2": "학교급",
    "cls3": "학년",
    "cls4": "과목코드",
    "cls5": "과목상세",
    "cls6": "학기",
    "cls7": "대단원",
    "cls8": "중단원",
    "cls9": "소단원",
    "cls10": "세단원",
    "cls11": "세세단원",
    "cls12": "세세세단원",
}

ATTR_RE = {key: re.compile(rf'{key}="([^"]*?)"') for key in CLS_KEYS}
QUIZ_TAG_RE = re.compile(r"<문항\s+([^>]+)>")


def parse_cls(attrs_str: str) -> dict | None:
    """문항 태그 속성에서 cls1~cls12 추출. A13(2022개정) 아니면 None."""
    fields = {}
    for key, pat in ATTR_RE.items():
        m = pat.search(attrs_str)
        if m:
            val = m.group(1).strip()
            if val and val != "0":
                fields[key] = val
    if not fields.get("cls1", "").startswith("A13"):
        return None
    return fields


def cls_to_tuple(fields: dict) -> tuple:
    """분류 필드를 비교 가능한 튜플로 변환 (빈 값은 빈 문자열)."""
    return tuple(fields.get(k, "") for k in CLS_KEYS)


def build_tree(rows: list[dict]) -> dict:
    """분류 행들을 계층 트리로 구성."""
    tree = {}
    for row in rows:
        node = tree
        for key in CLS_KEYS:
            val = row.get(key, "")
            if not val:
                break
            if val not in node:
                node[val] = {}
            node = node[val]
    return tree


def main():
    raw_dir = os.path.abspath(RAW_DIR)
    out_dir = os.path.abspath(OUT_DIR)

    if not os.path.isdir(raw_dir):
        print(f"ERROR: raw directory not found: {raw_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning: {raw_dir}")

    seen = set()
    rows = []
    total_files = 0
    matched_files = 0

    folders = sorted(os.listdir(raw_dir))
    for fi, folder in enumerate(folders):
        folder_path = os.path.join(raw_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        imls = [f for f in os.listdir(folder_path) if f.endswith(".iml")]
        for iml in imls:
            total_files += 1
            fpath = os.path.join(folder_path, iml)
            try:
                with open(fpath, "rb") as f:
                    header = f.read(3000)
                text = header.decode("euc-kr", errors="replace")
                m = QUIZ_TAG_RE.search(text)
                if not m:
                    continue
                fields = parse_cls(m.group(1))
                if fields is None:
                    continue
                matched_files += 1
                key = cls_to_tuple(fields)
                if key not in seen:
                    seen.add(key)
                    rows.append(fields)
            except Exception as e:
                print(f"  WARN: {fpath}: {e}", file=sys.stderr)

        if (fi + 1) % 50 == 0:
            print(f"  [{fi+1}/{len(folders)}] scanned {total_files} files, "
                  f"matched {matched_files}, unique {len(rows)}")

    print(f"\nDone: {total_files} files scanned, "
          f"{matched_files} matched (A13 2022), "
          f"{len(rows)} unique classifications")

    # Sort rows by cls hierarchy
    rows.sort(key=lambda r: cls_to_tuple(r))

    # --- Save JSON ---
    out_json = os.path.join(out_dir, "textbook_classification_2022.json")
    output = {
        "meta": {
            "curriculum": "2022개정교육과정",
            "total_items_scanned": total_files,
            "matched_items": matched_files,
            "unique_classifications": len(rows),
        },
        "fields": {k: CLS_LABELS[k] for k in CLS_KEYS},
        "classifications": rows,
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out_json}")

    # --- Save CSV ---
    out_csv = os.path.join(out_dir, "textbook_classification_2022.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(CLS_KEYS)
        for row in rows:
            writer.writerow([row.get(k, "") for k in CLS_KEYS])
    print(f"Saved: {out_csv}")

    # --- Print summary ---
    print("\n=== 과목별 분류 수 ===")
    by_subject = defaultdict(int)
    for row in rows:
        subj = row.get("cls4", "(없음)")
        by_subject[subj] += 1
    for subj, cnt in sorted(by_subject.items()):
        print(f"  {subj}: {cnt}개")

    print(f"\n=== 분류 깊이 분포 ===")
    depth_counts = defaultdict(int)
    for row in rows:
        depth = sum(1 for k in CLS_KEYS if row.get(k, ""))
        depth_counts[depth] += 1
    for d in sorted(depth_counts):
        print(f"  depth {d}: {depth_counts[d]}개")


if __name__ == "__main__":
    main()
