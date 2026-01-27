#!/usr/bin/env python3
"""
02_parse_iml.py
전체 IML 파일 파싱 및 구조화된 데이터 생성

Usage:
    python scripts/02_parse_iml.py
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.iml_parser import IMLParser, item_to_dict, ParsedItem

# Constants
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data" / "raw"
OUTPUT_DIR = SCRIPT_DIR.parent / "output"


def find_iml_files(data_dir: Path) -> List[Path]:
    """Find all IML files in the data directory."""
    iml_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.lower().endswith('.iml'):
                iml_files.append(Path(root) / file)
    return sorted(iml_files)


def main():
    print("=" * 60)
    print("IML File Parsing")
    print("=" * 60)

    # Find all IML files
    print(f"\n[1/4] Scanning for IML files in {DATA_DIR}...")
    iml_files = find_iml_files(DATA_DIR)
    print(f"      Found {len(iml_files):,} IML files")

    if not iml_files:
        print("ERROR: No IML files found!")
        return

    # Parse files
    print(f"\n[2/4] Parsing IML files...")
    parser = IMLParser()

    parsed_items: List[Dict[str, Any]] = []
    error_files: List[str] = []
    stats = defaultdict(int)

    total = len(iml_files)
    for i, file_path in enumerate(iml_files):
        if (i + 1) % 500 == 0 or i == 0 or i == total - 1:
            print(f"      Processing: {i + 1:,}/{total:,} ({(i+1)/total*100:.1f}%)")

        try:
            item = parser.parse_file(file_path)

            if item and not item.parse_errors:
                item_dict = item_to_dict(item)
                parsed_items.append(item_dict)

                # Collect stats
                stats['total'] += 1
                if item.has_image:
                    stats['with_image'] += 1
                else:
                    stats['text_only'] += 1

                # By question type
                qt = item.metadata.question_type or 'unknown'
                stats[f'type_{qt}'] += 1

                # By difficulty
                df = item.metadata.difficulty or 'unknown'
                stats[f'difficulty_{df}'] += 1

                # By subject
                subj = item.metadata.subject or 'unknown'
                stats[f'subject_{subj}'] += 1

                # By grade
                grade = item.metadata.grade or 'unknown'
                stats[f'grade_{grade}'] += 1

            else:
                error_files.append(str(file_path))
                if item:
                    for err in item.parse_errors:
                        stats[f'error_{err[:50]}'] += 1

        except Exception as e:
            error_files.append(str(file_path))
            stats[f'exception_{str(e)[:50]}'] += 1

    print(f"      Successfully parsed: {len(parsed_items):,}")
    print(f"      Errors: {len(error_files):,}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save parsed items
    print(f"\n[3/4] Saving parsed data to {OUTPUT_DIR}...")

    # Save as JSON (with intermediate format)
    items_file = OUTPUT_DIR / "items_parsed.json"
    with open(items_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_items": len(parsed_items),
            "items": parsed_items
        }, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {items_file}")

    # Save statistics
    stats_file = OUTPUT_DIR / "parse_statistics.json"
    stats_dict = dict(stats)
    stats_dict['error_files'] = error_files[:100]  # First 100 errors
    stats_dict['error_count'] = len(error_files)

    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_dict, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {stats_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("Parsing Summary")
    print("=" * 60)
    print(f"  Total files processed: {total:,}")
    print(f"  Successfully parsed: {len(parsed_items):,}")
    print(f"  Parse errors: {len(error_files):,}")

    print(f"\n  By Image Presence:")
    print(f"    - With image: {stats.get('with_image', 0):,}")
    print(f"    - Text only: {stats.get('text_only', 0):,}")

    print(f"\n  By Question Type:")
    for key, val in sorted(stats.items()):
        if key.startswith('type_'):
            print(f"    - {key[5:]}: {val:,}")

    print(f"\n  By Difficulty:")
    for key, val in sorted(stats.items()):
        if key.startswith('difficulty_'):
            print(f"    - {key[11:]}: {val:,}")

    print(f"\n  By Subject:")
    for key, val in sorted(stats.items()):
        if key.startswith('subject_'):
            print(f"    - {key[8:]}: {val:,}")

    print(f"\n  By Grade:")
    for key, val in sorted(stats.items()):
        if key.startswith('grade_'):
            print(f"    - {key[6:]}: {val:,}")

    print("\n" + "=" * 60)
    print("Parsing completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
