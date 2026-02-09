"""
Prepare per-subject mapping input data for curriculum mapping.

Loads textbook_classification_2022.json and 5 subject CSV files,
normalizes data, and generates per-subject input JSON files.

Output: item-preprocess/mapping_input/{subject}_input.json
"""

import csv
import json
import os
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")

# Subject code mapping: cls4 prefix -> (subject_key, subject_name_ko, csv_name)
SUBJECT_MAP = {
    "01": ("korean", "국어", "국어"),
    "03": ("math", "수학", "수학"),
    "04": ("social", "사회", "사회"),
    "045": ("history", "역사", "역사"),
    "05": ("science", "과학", "과학"),
}

CLS_KEYS = [f"cls{i}" for i in range(1, 13)]


def strip_prefix(val: str) -> str:
    """Remove leading number prefix: '01 1. 수와 연산' -> '1. 수와 연산'."""
    return re.sub(r"^\d+\s+", "", val).strip()


def normalize_section_name(name: str) -> str:
    """Normalize section names: remove extra spaces around dots, etc.
    e.g. '03. 소설' and '03.소설' -> '03.소설'
    """
    return re.sub(r"(\d+)\.\s*", r"\1.", name).strip()


def build_textbook_id(subject_key: str, idx: int) -> str:
    """Generate a textbook ID like tb_math_001."""
    return f"tb_{subject_key}_{idx:03d}"


def build_full_path(entry: dict, subject_name: str) -> str:
    """Build a human-readable path from cls fields."""
    parts = [subject_name]
    # grade
    cls3 = entry.get("cls3", "")
    if cls3:
        parts.append(strip_prefix(cls3))
    # semester/volume
    cls6 = entry.get("cls6", "")
    if cls6:
        parts.append(strip_prefix(cls6))
    # chapter levels
    for key in ["cls7", "cls8", "cls9", "cls10", "cls11", "cls12"]:
        val = entry.get(key, "")
        if val:
            parts.append(strip_prefix(val))
    return " > ".join(parts)


def determine_leaf(entry: dict, all_entries: list[dict]) -> bool:
    """A classification is a leaf if no other entry extends it with deeper cls fields."""
    depth = 0
    for key in CLS_KEYS:
        if entry.get(key, ""):
            depth += 1
        else:
            break

    entry_tuple = tuple(entry.get(k, "") for k in CLS_KEYS[:depth])

    for other in all_entries:
        if other is entry:
            continue
        other_depth = 0
        for key in CLS_KEYS:
            if other.get(key, ""):
                other_depth += 1
            else:
                break
        if other_depth <= depth:
            continue
        other_tuple = tuple(other.get(k, "") for k in CLS_KEYS[:depth])
        if other_tuple == entry_tuple:
            return False
    return True


def extract_subject_code(cls4: str) -> str:
    """Extract the numeric code from cls4: '045 역사' -> '045'."""
    return cls4.split()[0]


def load_achievement_standards(subject_csv_name: str) -> list[dict]:
    """Load achievement standards from CSV."""
    csv_path = os.path.join(
        BASE_DIR, "2022",
        f"(중등)2022 개정 교육과정에 따른 성취수준({subject_csv_name}).csv"
    )
    standards = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            standards.append({
                "code": row["code"].strip(),
                "description": row["description"].strip(),
                "domain": row["domain"].strip(),
            })
    return standards


def main():
    # Load textbook classifications
    cls_path = os.path.join(BASE_DIR, "textbook_classification_2022.json")
    with open(cls_path, encoding="utf-8") as f:
        data = json.load(f)
    classifications = data["classifications"]

    # Group by subject
    subject_entries: dict[str, list[dict]] = {}
    for entry in classifications:
        cls4 = entry.get("cls4", "")
        code = extract_subject_code(cls4)
        if code in SUBJECT_MAP:
            key = SUBJECT_MAP[code][0]
            if key not in subject_entries:
                subject_entries[key] = []
            subject_entries[key].append(entry)

    # Process each subject
    output_dir = os.path.join(BASE_DIR, "mapping_input")
    os.makedirs(output_dir, exist_ok=True)

    for code, (subject_key, subject_name, csv_name) in SUBJECT_MAP.items():
        entries = subject_entries.get(subject_key, [])
        if not entries:
            print(f"WARNING: No entries for {subject_name}")
            continue

        # Build textbook items with dedup by normalized path
        seen_paths = {}
        textbook_items = []
        idx = 1

        for entry in entries:
            full_path = build_full_path(entry, subject_name)
            normalized = normalize_section_name(full_path)

            if normalized in seen_paths:
                # Record original variant but skip
                seen_paths[normalized]["original_variants"].append(full_path)
                continue

            is_leaf = determine_leaf(entry, entries)
            item = {
                "textbook_id": build_textbook_id(subject_key, idx),
                "textbook_path": full_path,
                "normalized_path": normalized,
                "is_leaf": is_leaf,
                "cls4": extract_subject_code(entry.get("cls4", "")),
                "cls5": entry.get("cls5", ""),
                "cls6": entry.get("cls6", ""),
                "cls7": entry.get("cls7", ""),
                "cls8": entry.get("cls8", ""),
                "cls9": entry.get("cls9", ""),
                "grade": strip_prefix(entry.get("cls3", "")),
                "chapter": strip_prefix(entry.get("cls7", "")),
                "section": strip_prefix(entry.get("cls8", "")),
                "subsection": strip_prefix(entry.get("cls9", "")),
                "original_variants": [full_path],
            }
            seen_paths[normalized] = item
            textbook_items.append(item)
            idx += 1

        # Load achievement standards
        standards = load_achievement_standards(csv_name)

        # Build domain list for quick reference
        domains = sorted(set(s["domain"] for s in standards))

        output = {
            "subject": subject_name,
            "subject_key": subject_key,
            "subject_code": code,
            "textbook_count": len(textbook_items),
            "leaf_count": sum(1 for t in textbook_items if t["is_leaf"]),
            "intermediate_count": sum(1 for t in textbook_items if not t["is_leaf"]),
            "standards_count": len(standards),
            "domains": domains,
            "textbook_classifications": textbook_items,
            "achievement_standards": standards,
        }

        out_path = os.path.join(output_dir, f"{subject_key}_input.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Saved: {out_path}")
        print(f"  {subject_name}: {len(textbook_items)} classifications "
              f"({output['leaf_count']} leaf, {output['intermediate_count']} intermediate), "
              f"{len(standards)} standards, {len(domains)} domains")


if __name__ == "__main__":
    main()
