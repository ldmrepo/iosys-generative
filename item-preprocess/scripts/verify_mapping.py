"""
Verify curriculum mapping quality with 4 checks:
1. Coverage: every textbook classification has at least 1 mapping
2. Reverse coverage: list unmapped achievement standards
3. Domain consistency: same-domain standards map to same chapter area
4. Confidence distribution: per-subject stats

Output: item-preprocess/mapping_verification_report.md
"""

import json
import os
import sqlite3
from collections import defaultdict

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")


def load_db():
    db_path = os.path.join(BASE_DIR, "curriculum_mapping_2022.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def check_coverage(conn) -> tuple[list, int, int]:
    """Check that every textbook classification has at least 1 mapping."""
    cur = conn.cursor()

    # All textbooks
    cur.execute("SELECT id, subject, full_path, is_leaf FROM textbook_classifications")
    all_tb = cur.fetchall()

    # Textbooks with mappings
    cur.execute("SELECT DISTINCT textbook_id FROM mappings")
    mapped_ids = {row["textbook_id"] for row in cur.fetchall()}

    unmapped = []
    for tb in all_tb:
        if tb["id"] not in mapped_ids:
            unmapped.append(dict(tb))

    return unmapped, len(mapped_ids), len(all_tb)


def check_reverse_coverage(conn) -> tuple[list, int, int]:
    """Check which achievement standards have no mapping."""
    cur = conn.cursor()

    cur.execute("SELECT code, subject, description, domain FROM achievement_standards")
    all_std = cur.fetchall()

    cur.execute("SELECT DISTINCT standard_code FROM mappings")
    mapped_codes = {row["standard_code"] for row in cur.fetchall()}

    unmapped = []
    for std in all_std:
        if std["code"] not in mapped_codes:
            unmapped.append(dict(std))

    return unmapped, len(mapped_codes), len(all_std)


def check_domain_consistency(conn) -> list[dict]:
    """Check if standards from the same domain map to the same chapter area."""
    cur = conn.cursor()

    cur.execute("""
        SELECT m.standard_code, a.domain, a.subject, t.chapter, t.full_path, t.id
        FROM mappings m
        JOIN achievement_standards a ON m.standard_code = a.code
        JOIN textbook_classifications t ON m.textbook_id = t.id
    """)
    rows = cur.fetchall()

    # Group by (subject, domain) -> set of chapters
    domain_chapters: dict[tuple, set] = defaultdict(set)
    domain_details: dict[tuple, list] = defaultdict(list)

    for row in rows:
        key = (row["subject"], row["domain"])
        chapter = row["chapter"] or "(no chapter)"
        domain_chapters[key].add(chapter)
        domain_details[key].append({
            "standard_code": row["standard_code"],
            "chapter": chapter,
            "textbook_id": row["id"],
        })

    # Flag domains that map to multiple unrelated chapters
    issues = []
    for (subject, domain), chapters in domain_chapters.items():
        if len(chapters) > 1:
            issues.append({
                "subject": subject,
                "domain": domain,
                "chapters": sorted(chapters),
                "count": len(chapters),
            })

    return issues


def check_confidence_distribution(conn) -> dict:
    """Compute confidence distribution per subject."""
    cur = conn.cursor()

    cur.execute("""
        SELECT t.subject, m.confidence, m.textbook_id, m.standard_code, m.reasoning
        FROM mappings m
        JOIN textbook_classifications t ON m.textbook_id = t.id
    """)
    rows = cur.fetchall()

    by_subject: dict[str, list] = defaultdict(list)
    for row in rows:
        by_subject[row["subject"]].append(row)

    stats = {}
    for subject, entries in sorted(by_subject.items()):
        confidences = [e["confidence"] for e in entries]
        low_confidence = [
            {"textbook_id": e["textbook_id"], "standard_code": e["standard_code"],
             "confidence": e["confidence"], "reasoning": e["reasoning"]}
            for e in entries if e["confidence"] < 0.5
        ]
        stats[subject] = {
            "count": len(confidences),
            "mean": sum(confidences) / len(confidences) if confidences else 0,
            "min": min(confidences) if confidences else 0,
            "max": max(confidences) if confidences else 0,
            "low_confidence_count": len(low_confidence),
            "low_confidence_items": low_confidence[:10],  # First 10
        }

    return stats


def generate_report(
    coverage_unmapped, coverage_mapped, coverage_total,
    rev_unmapped, rev_mapped, rev_total,
    domain_issues, confidence_stats
) -> str:
    """Generate markdown verification report."""
    lines = ["# 교육과정 매핑 검증 보고서\n"]

    # 1. Coverage
    lines.append("## 1. 교과서 분류 커버리지\n")
    pct = coverage_mapped / coverage_total * 100 if coverage_total else 0
    lines.append(f"- 전체 교과서 분류: {coverage_total}개")
    lines.append(f"- 매핑된 분류: {coverage_mapped}개 ({pct:.1f}%)")
    lines.append(f"- 매핑되지 않은 분류: {len(coverage_unmapped)}개\n")

    if coverage_unmapped:
        lines.append("### 매핑되지 않은 교과서 분류\n")
        lines.append("| ID | 과목 | 경로 | Leaf |")
        lines.append("|---|---|---|---|")
        for item in coverage_unmapped:
            lines.append(f"| {item['id']} | {item['subject']} | {item['full_path']} | {'Y' if item['is_leaf'] else 'N'} |")
        lines.append("")

    # 2. Reverse coverage
    lines.append("## 2. 성취기준 역커버리지\n")
    rev_pct = rev_mapped / rev_total * 100 if rev_total else 0
    lines.append(f"- 전체 성취기준: {rev_total}개")
    lines.append(f"- 매핑된 성취기준: {rev_mapped}개 ({rev_pct:.1f}%)")
    lines.append(f"- 매핑되지 않은 성취기준: {len(rev_unmapped)}개\n")

    if rev_unmapped:
        # Group by subject
        by_subj: dict[str, list] = defaultdict(list)
        for item in rev_unmapped:
            by_subj[item["subject"]].append(item)

        for subj, items in sorted(by_subj.items()):
            lines.append(f"### {subj} ({len(items)}개 미매핑)\n")
            lines.append("| 코드 | 영역 | 설명 |")
            lines.append("|---|---|---|")
            for item in items:
                desc = item["description"][:60] + "..." if len(item["description"]) > 60 else item["description"]
                lines.append(f"| {item['code']} | {item['domain']} | {desc} |")
            lines.append("")

    # 3. Domain consistency
    lines.append("## 3. 도메인 일관성\n")
    if domain_issues:
        lines.append(f"⚠️ {len(domain_issues)}개 도메인에서 복수 단원 매핑 감지\n")
        lines.append("| 과목 | 도메인 | 매핑된 단원 수 | 단원 목록 |")
        lines.append("|---|---|---|---|")
        for issue in domain_issues:
            chapters = ", ".join(issue["chapters"][:5])
            lines.append(f"| {issue['subject']} | {issue['domain']} | {issue['count']} | {chapters} |")
        lines.append("")
        lines.append("> 참고: 복수 단원 매핑이 반드시 오류는 아닙니다. 하나의 도메인이 여러 단원에 걸칠 수 있습니다.\n")
    else:
        lines.append("✅ 모든 도메인이 일관된 단원에 매핑됨\n")

    # 4. Confidence distribution
    lines.append("## 4. 신뢰도 분포\n")
    lines.append("| 과목 | 매핑 수 | 평균 | 최소 | 최대 | 저신뢰(<0.5) |")
    lines.append("|---|---|---|---|---|---|")
    total_low = 0
    for subj, stat in sorted(confidence_stats.items()):
        lines.append(
            f"| {subj} | {stat['count']} | {stat['mean']:.3f} | "
            f"{stat['min']:.2f} | {stat['max']:.2f} | {stat['low_confidence_count']} |"
        )
        total_low += stat["low_confidence_count"]
    lines.append("")

    if total_low > 0:
        lines.append(f"### 저신뢰 매핑 ({total_low}개)\n")
        for subj, stat in sorted(confidence_stats.items()):
            if stat["low_confidence_items"]:
                lines.append(f"#### {subj}\n")
                lines.append("| 교과서 ID | 성취기준 | 신뢰도 | 사유 |")
                lines.append("|---|---|---|---|")
                for item in stat["low_confidence_items"]:
                    reasoning = (item["reasoning"] or "")[:50]
                    lines.append(
                        f"| {item['textbook_id']} | {item['standard_code']} | "
                        f"{item['confidence']:.2f} | {reasoning} |"
                    )
                lines.append("")

    # Summary
    lines.append("## 요약\n")
    lines.append(f"- 교과서 커버리지: {coverage_mapped}/{coverage_total} ({pct:.1f}%)")
    lines.append(f"- 성취기준 커버리지: {rev_mapped}/{rev_total} ({rev_pct:.1f}%)")
    lines.append(f"- 도메인 일관성 이슈: {len(domain_issues)}개")
    lines.append(f"- 저신뢰 매핑: {total_low}개")

    return "\n".join(lines)


def main():
    conn = load_db()

    print("1. Checking coverage...")
    coverage_unmapped, coverage_mapped, coverage_total = check_coverage(conn)
    print(f"   {coverage_mapped}/{coverage_total} mapped")

    print("2. Checking reverse coverage...")
    rev_unmapped, rev_mapped, rev_total = check_reverse_coverage(conn)
    print(f"   {rev_mapped}/{rev_total} standards mapped")

    print("3. Checking domain consistency...")
    domain_issues = check_domain_consistency(conn)
    print(f"   {len(domain_issues)} issues found")

    print("4. Checking confidence distribution...")
    confidence_stats = check_confidence_distribution(conn)
    for subj, stat in sorted(confidence_stats.items()):
        print(f"   {subj}: mean={stat['mean']:.3f}, low={stat['low_confidence_count']}")

    report = generate_report(
        coverage_unmapped, coverage_mapped, coverage_total,
        rev_unmapped, rev_mapped, rev_total,
        domain_issues, confidence_stats
    )

    report_path = os.path.join(BASE_DIR, "mapping_verification_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved: {report_path}")

    conn.close()


if __name__ == "__main__":
    main()
