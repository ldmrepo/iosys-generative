"""
Merge 5 subject mapping outputs into unified JSON, CSV, and SQLite formats.

Input:  item-preprocess/mapping_output/{subject}_mapping.json
Output: item-preprocess/curriculum_mapping_2022.json
        item-preprocess/curriculum_mapping_2022.csv
        item-preprocess/curriculum_mapping_2022.db
"""

import csv
import json
import os
import re
import sqlite3

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")

SUBJECTS = [
    ("math", "수학", "03"),
    ("korean", "국어", "01"),
    ("science", "과학", "05"),
    ("social", "사회", "04"),
    ("history", "역사", "045"),
]

INPUT_DIR = os.path.join(BASE_DIR, "mapping_input")
OUTPUT_DIR = os.path.join(BASE_DIR, "mapping_output")


def load_input(subject_key: str) -> dict:
    """Load the original input file for a subject."""
    path = os.path.join(INPUT_DIR, f"{subject_key}_input.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_mapping(subject_key: str) -> dict:
    """Load the mapping output for a subject."""
    path = os.path.join(OUTPUT_DIR, f"{subject_key}_mapping.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_path_components(textbook_item: dict) -> dict:
    """Extract structured components from a textbook item."""
    return {
        "grade": textbook_item.get("grade", ""),
        "semester": re.sub(r"^\d+\s+", "", textbook_item.get("cls6", "")).strip() if textbook_item.get("cls6") else "",
        "chapter": textbook_item.get("chapter", ""),
        "section": textbook_item.get("section", ""),
        "subsection": textbook_item.get("subsection", ""),
    }


def create_sqlite_db(db_path: str, all_textbooks: list, all_standards: list, all_mappings: list):
    """Create SQLite database with the mapping data."""
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE textbook_classifications (
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            subject_code TEXT NOT NULL,
            grade TEXT,
            semester TEXT,
            chapter TEXT,
            section TEXT,
            subsection TEXT,
            full_path TEXT NOT NULL,
            is_leaf INTEGER NOT NULL DEFAULT 1,
            cls4 TEXT, cls5 TEXT, cls6 TEXT, cls7 TEXT, cls8 TEXT, cls9 TEXT
        );

        CREATE TABLE achievement_standards (
            code TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            domain TEXT NOT NULL
        );

        CREATE TABLE mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            textbook_id TEXT NOT NULL REFERENCES textbook_classifications(id),
            standard_code TEXT NOT NULL REFERENCES achievement_standards(code),
            confidence REAL NOT NULL DEFAULT 0.0,
            reasoning TEXT,
            UNIQUE(textbook_id, standard_code)
        );

        CREATE INDEX idx_mappings_textbook ON mappings(textbook_id);
        CREATE INDEX idx_mappings_standard ON mappings(standard_code);
    """)

    # Insert textbook classifications
    for tb in all_textbooks:
        cur.execute(
            """INSERT OR IGNORE INTO textbook_classifications
               (id, subject, subject_code, grade, semester, chapter, section, subsection,
                full_path, is_leaf, cls4, cls5, cls6, cls7, cls8, cls9)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tb["id"], tb["subject"], tb["subject_code"],
             tb["grade"], tb["semester"], tb["chapter"], tb["section"], tb["subsection"],
             tb["full_path"], 1 if tb["is_leaf"] else 0,
             tb.get("cls4", ""), tb.get("cls5", ""), tb.get("cls6", ""),
             tb.get("cls7", ""), tb.get("cls8", ""), tb.get("cls9", ""))
        )

    # Insert achievement standards
    for std in all_standards:
        cur.execute(
            """INSERT OR IGNORE INTO achievement_standards (code, subject, description, domain)
               VALUES (?, ?, ?, ?)""",
            (std["code"], std["subject"], std["description"], std["domain"])
        )

    # Insert mappings
    for m in all_mappings:
        cur.execute(
            """INSERT OR IGNORE INTO mappings (textbook_id, standard_code, confidence, reasoning)
               VALUES (?, ?, ?, ?)""",
            (m["textbook_id"], m["standard_code"], m["confidence"], m["reasoning"])
        )

    conn.commit()
    conn.close()


def main():
    all_textbooks = []
    all_standards = []
    all_mappings = []
    all_mapping_entries = []
    unmapped_standards = []

    for subject_key, subject_name, subject_code in SUBJECTS:
        print(f"\nProcessing {subject_name}...")

        # Load input data
        input_data = load_input(subject_key)

        # Load mapping results
        try:
            mapping_data = load_mapping(subject_key)
        except FileNotFoundError:
            print(f"  WARNING: No mapping output for {subject_name}, skipping")
            continue

        # Build textbook lookup from input
        tb_lookup = {}
        for tb_item in input_data["textbook_classifications"]:
            tb_lookup[tb_item["textbook_id"]] = tb_item

        # Process textbook items
        for tb_item in input_data["textbook_classifications"]:
            components = parse_path_components(tb_item)
            all_textbooks.append({
                "id": tb_item["textbook_id"],
                "subject": subject_name,
                "subject_code": subject_code,
                "grade": components["grade"],
                "semester": components["semester"],
                "chapter": components["chapter"],
                "section": components["section"],
                "subsection": components["subsection"],
                "full_path": tb_item["textbook_path"],
                "is_leaf": tb_item["is_leaf"],
                "cls4": tb_item.get("cls4", ""),
                "cls5": tb_item.get("cls5", ""),
                "cls6": tb_item.get("cls6", ""),
                "cls7": tb_item.get("cls7", ""),
                "cls8": tb_item.get("cls8", ""),
                "cls9": tb_item.get("cls9", ""),
            })

        # Process achievement standards
        for std in input_data["achievement_standards"]:
            all_standards.append({
                "code": std["code"],
                "subject": subject_name,
                "description": std["description"],
                "domain": std["domain"],
            })

        # Process mappings
        mappings_list = mapping_data.get("mappings", [])
        mapped_count = 0
        for entry in mappings_list:
            tb_id = entry["textbook_id"]
            tb_path = entry.get("textbook_path", "")
            is_leaf = entry.get("is_leaf", True)

            for std in entry.get("mapped_standards", []):
                all_mappings.append({
                    "textbook_id": tb_id,
                    "standard_code": std["code"],
                    "confidence": std.get("confidence", 0.0),
                    "reasoning": std.get("reasoning", ""),
                })
                mapped_count += 1

            all_mapping_entries.append(entry)

        # Collect unmapped standards if present
        for u in mapping_data.get("unmapped_standards", []):
            unmapped_standards.append({
                "code": u["code"],
                "subject": subject_name,
                "domain": u.get("domain", ""),
                "reason": u.get("reason", ""),
            })

        print(f"  {len(mappings_list)} textbook items mapped, {mapped_count} total mappings")

    # === Save JSON ===
    json_output = {
        "meta": {
            "total_textbooks": len(all_textbooks),
            "total_standards": len(all_standards),
            "total_mappings": len(all_mappings),
            "unmapped_standards_count": len(unmapped_standards),
        },
        "mappings": all_mapping_entries,
        "unmapped_standards": unmapped_standards,
    }
    json_path = os.path.join(BASE_DIR, "curriculum_mapping_2022.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved JSON: {json_path}")

    # === Save CSV ===
    csv_path = os.path.join(BASE_DIR, "curriculum_mapping_2022.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "textbook_id", "subject", "textbook_path", "is_leaf",
            "standard_code", "standard_description", "standard_domain",
            "confidence", "reasoning"
        ])
        # Build standard lookup
        std_lookup = {s["code"]: s for s in all_standards}
        for m in all_mappings:
            std = std_lookup.get(m["standard_code"], {})
            # Find textbook
            tb = next((t for t in all_textbooks if t["id"] == m["textbook_id"]), {})
            writer.writerow([
                m["textbook_id"],
                tb.get("subject", ""),
                tb.get("full_path", ""),
                tb.get("is_leaf", True),
                m["standard_code"],
                std.get("description", ""),
                std.get("domain", ""),
                m["confidence"],
                m["reasoning"],
            ])
    print(f"Saved CSV: {csv_path}")

    # === Save SQLite ===
    db_path = os.path.join(BASE_DIR, "curriculum_mapping_2022.db")
    create_sqlite_db(db_path, all_textbooks, all_standards, all_mappings)
    print(f"Saved SQLite: {db_path}")

    # === Summary ===
    print(f"\n=== Summary ===")
    print(f"Textbook classifications: {len(all_textbooks)}")
    print(f"Achievement standards: {len(all_standards)}")
    print(f"Mappings: {len(all_mappings)}")
    print(f"Unmapped standards: {len(unmapped_standards)}")

    # Per-subject breakdown
    from collections import Counter
    subject_counts = Counter(m["textbook_id"].split("_")[1] for m in all_mappings)
    for subj, count in sorted(subject_counts.items()):
        print(f"  {subj}: {count} mappings")


if __name__ == "__main__":
    main()
