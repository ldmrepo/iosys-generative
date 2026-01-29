#!/usr/bin/env python3
"""
load_items.py
IML 파일을 파싱하여 PostgreSQL items 테이블에 로드

Usage:
    python scripts/load_items.py [--limit N] [--batch-size N]
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg
from tqdm import tqdm

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
ITEMBANK_API_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ITEMBANK_API_DIR))
from utils.iml_parser import IMLParser, ParsedItem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Database configuration from environment
DB_USER = os.environ.get("DB_USER", "poc_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "poc_password")
DB_NAME = os.environ.get("DB_NAME", "poc_itembank")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5433"))

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Data directory (relative to project root)
PROJECT_ROOT = ITEMBANK_API_DIR.parent  # iosys-generative
DATA_DIR = PROJECT_ROOT / "data" / "raw"

# SQL statements
INSERT_SQL = """
INSERT INTO items (
    id, source_file,
    question_type, question_type_code, difficulty, difficulty_code,
    curriculum, school_level, grade, subject, subject_detail,
    semester, unit_large, unit_medium, unit_small, unit_detail,
    question_text, choices, answer_text, explanation_text,
    question_images, explanation_images, has_image,
    keywords, year, source, exam_name, raw_attributes
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
    $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28
)
ON CONFLICT (id) DO UPDATE SET
    source_file = EXCLUDED.source_file,
    question_type = EXCLUDED.question_type,
    question_type_code = EXCLUDED.question_type_code,
    difficulty = EXCLUDED.difficulty,
    difficulty_code = EXCLUDED.difficulty_code,
    curriculum = EXCLUDED.curriculum,
    school_level = EXCLUDED.school_level,
    grade = EXCLUDED.grade,
    subject = EXCLUDED.subject,
    subject_detail = EXCLUDED.subject_detail,
    semester = EXCLUDED.semester,
    unit_large = EXCLUDED.unit_large,
    unit_medium = EXCLUDED.unit_medium,
    unit_small = EXCLUDED.unit_small,
    unit_detail = EXCLUDED.unit_detail,
    question_text = EXCLUDED.question_text,
    choices = EXCLUDED.choices,
    answer_text = EXCLUDED.answer_text,
    explanation_text = EXCLUDED.explanation_text,
    question_images = EXCLUDED.question_images,
    explanation_images = EXCLUDED.explanation_images,
    has_image = EXCLUDED.has_image,
    keywords = EXCLUDED.keywords,
    year = EXCLUDED.year,
    source = EXCLUDED.source,
    exam_name = EXCLUDED.exam_name,
    raw_attributes = EXCLUDED.raw_attributes,
    updated_at = CURRENT_TIMESTAMP
"""


def item_to_db_record(item: ParsedItem) -> tuple:
    """ParsedItem을 DB 레코드 튜플로 변환"""
    meta = item.metadata
    content = item.content

    # Relative source file path
    source_file = item.source_file
    if source_file.startswith(str(DATA_DIR)):
        source_file = str(Path(source_file).relative_to(PROJECT_ROOT))

    return (
        meta.id,
        source_file,
        meta.question_type,
        meta.question_type_code,
        meta.difficulty,
        meta.difficulty_code,
        meta.curriculum,
        meta.school_level,
        meta.grade,
        meta.subject,
        meta.subject_detail,
        meta.semester,
        meta.unit_large,
        meta.unit_medium,
        meta.unit_small,
        "",  # unit_detail (cls10 not in current parser, stored in raw_attributes)
        content.question_text,
        json.dumps(content.choices, ensure_ascii=False) if content.choices else None,
        content.answer_text,
        content.explanation_text,
        json.dumps(content.question_images, ensure_ascii=False) if content.question_images else None,
        json.dumps(content.explanation_images, ensure_ascii=False) if content.explanation_images else None,
        item.has_image,
        meta.keywords,
        meta.year,
        meta.source,
        meta.exam_name,
        json.dumps(meta.raw_attributes, ensure_ascii=False) if meta.raw_attributes else None,
    )


async def ensure_table_exists(pool: asyncpg.Pool) -> None:
    """items 테이블이 존재하는지 확인하고 없으면 생성"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS items (
        id VARCHAR(64) PRIMARY KEY,
        source_file TEXT NOT NULL,
        question_type VARCHAR(20),
        question_type_code VARCHAR(10),
        difficulty VARCHAR(10),
        difficulty_code VARCHAR(10),
        curriculum VARCHAR(100),
        school_level VARCHAR(20),
        grade VARCHAR(20),
        subject VARCHAR(50),
        subject_detail VARCHAR(50),
        semester VARCHAR(20),
        unit_large VARCHAR(100),
        unit_medium VARCHAR(100),
        unit_small VARCHAR(100),
        unit_detail VARCHAR(100),
        question_text TEXT,
        choices JSONB,
        answer_text VARCHAR(255),
        explanation_text TEXT,
        question_images JSONB,
        explanation_images JSONB,
        has_image BOOLEAN DEFAULT FALSE,
        keywords TEXT,
        year INTEGER,
        source VARCHAR(100),
        exam_name VARCHAR(200),
        raw_attributes JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    async with pool.acquire() as conn:
        await conn.execute(create_table_sql)
        logger.info("Ensured items table exists")


async def load_items(
    limit: Optional[int] = None,
    batch_size: int = 1000,
) -> Dict[str, Any]:
    """IML 파일을 파싱하여 DB에 로드"""

    # Statistics
    stats = {
        "total_files": 0,
        "parsed": 0,
        "failed": 0,
        "inserted": 0,
        "errors": [],
    }

    # Connect to database
    logger.info(f"Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    try:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
        )
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    # Ensure table exists
    await ensure_table_exists(pool)

    # Find IML files
    logger.info(f"Scanning for IML files in {DATA_DIR}...")
    iml_files = list(DATA_DIR.rglob("*.iml"))
    stats["total_files"] = len(iml_files)
    logger.info(f"Found {len(iml_files):,} IML files")

    if limit:
        iml_files = iml_files[:limit]
        logger.info(f"Limited to {limit:,} files")

    # Initialize parser
    parser = IMLParser()

    # Process in batches
    records = []
    failed_files = []

    for file_path in tqdm(iml_files, desc="Parsing IML files"):
        try:
            item = parser.parse_file(file_path)
            if item and item.metadata.id:
                records.append(item_to_db_record(item))
                stats["parsed"] += 1
            else:
                stats["failed"] += 1
                failed_files.append((str(file_path), "No ID or parse failed"))
        except Exception as e:
            stats["failed"] += 1
            failed_files.append((str(file_path), str(e)))

        # Insert batch
        if len(records) >= batch_size:
            try:
                async with pool.acquire() as conn:
                    await conn.executemany(INSERT_SQL, records)
                stats["inserted"] += len(records)
                records = []
            except Exception as e:
                logger.error(f"Batch insert failed: {e}")
                stats["errors"].append(str(e))
                records = []

    # Insert remaining records
    if records:
        try:
            async with pool.acquire() as conn:
                await conn.executemany(INSERT_SQL, records)
            stats["inserted"] += len(records)
        except Exception as e:
            logger.error(f"Final batch insert failed: {e}")
            stats["errors"].append(str(e))

    # Close pool
    await pool.close()

    # Log failed files (first 10)
    if failed_files:
        logger.warning(f"Failed to parse {len(failed_files)} files")
        for path, error in failed_files[:10]:
            logger.warning(f"  - {path}: {error}")
        if len(failed_files) > 10:
            logger.warning(f"  ... and {len(failed_files) - 10} more")

    return stats


async def verify_load(limit: int = 5) -> None:
    """로드된 데이터 확인"""
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)

    async with pool.acquire() as conn:
        # Count
        count = await conn.fetchval("SELECT COUNT(*) FROM items")
        logger.info(f"Total items in database: {count:,}")

        # Sample
        rows = await conn.fetch(
            """
            SELECT id, question_text, difficulty, subject, has_image
            FROM items
            LIMIT $1
            """,
            limit,
        )

        logger.info(f"\nSample items:")
        for row in rows:
            logger.info(f"  - {row['id']}: {row['question_text'][:50] if row['question_text'] else 'N/A'}...")
            logger.info(f"    difficulty={row['difficulty']}, subject={row['subject']}, has_image={row['has_image']}")

    await pool.close()


def main():
    parser = argparse.ArgumentParser(description="Load IML files to database")
    parser.add_argument("--limit", type=int, help="Limit number of files to process")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing data")
    args = parser.parse_args()

    if args.verify_only:
        asyncio.run(verify_load())
        return

    logger.info("=" * 60)
    logger.info("IML to Database Loader")
    logger.info("=" * 60)

    stats = asyncio.run(load_items(limit=args.limit, batch_size=args.batch_size))

    logger.info("\n" + "=" * 60)
    logger.info("Load Summary")
    logger.info("=" * 60)
    logger.info(f"  Total files: {stats['total_files']:,}")
    logger.info(f"  Parsed: {stats['parsed']:,}")
    logger.info(f"  Failed: {stats['failed']:,}")
    logger.info(f"  Inserted: {stats['inserted']:,}")

    if stats["errors"]:
        logger.error(f"  Errors: {len(stats['errors'])}")

    logger.info("=" * 60)

    # Verify
    logger.info("\nVerifying loaded data...")
    asyncio.run(verify_load())


if __name__ == "__main__":
    main()
