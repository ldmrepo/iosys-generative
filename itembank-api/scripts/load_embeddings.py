#!/usr/bin/env python3
"""
Load embeddings from NPZ files into pgvector database.

Usage:
    python scripts/load_embeddings.py --npz-path ../poc/results/qwen_embeddings_all_subjects_2b_multimodal.npz
    python scripts/load_embeddings.py --npz-path ../poc/results/qwen_embeddings.npz --table qwen_embeddings
"""
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "database": os.getenv("DB_NAME", "poc_itembank"),
    "user": os.getenv("DB_USER", "poc_user"),
    "password": os.getenv("DB_PASSWORD", "poc_password"),
}

# Batch size for inserts
BATCH_SIZE = 1000


def load_npz(path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load embeddings and IDs from NPZ file."""
    logger.info(f"Loading NPZ file: {path}")
    data = np.load(path, allow_pickle=True)

    # Find embeddings
    embeddings = None
    ids = None

    for key in ["embeddings", "embedding"]:
        if key in data:
            embeddings = data[key]
            break

    if embeddings is None:
        keys = list(data.keys())
        if keys:
            embeddings = data[keys[0]]

    for key in ["ids", "id", "item_ids"]:
        if key in data:
            ids = data[key]
            break

    if embeddings is None:
        raise ValueError("No embeddings found in NPZ file")

    if ids is None:
        ids = np.array([str(i) for i in range(len(embeddings))])

    logger.info(f"Loaded {len(embeddings)} embeddings with dimension {embeddings.shape[1]}")
    return embeddings, ids


def get_table_for_dimension(dim: int) -> str:
    """Get appropriate table name based on embedding dimension."""
    dim_to_table = {
        2048: "qwen_embeddings",
        1024: "kure_embeddings",
        768: "siglip_embeddings",
        1792: "combined_embeddings",
    }
    return dim_to_table.get(dim, "qwen_embeddings")


def insert_embeddings(
    conn,
    embeddings: np.ndarray,
    ids: np.ndarray,
    table_name: str,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Insert embeddings into pgvector table."""
    total = len(embeddings)
    inserted = 0

    logger.info(f"Inserting {total} embeddings into {table_name}...")

    with conn.cursor() as cur:
        # Clear existing data
        cur.execute(f"TRUNCATE TABLE {table_name}")
        logger.info(f"Cleared existing data from {table_name}")

        # Insert in batches
        for i in tqdm(range(0, total, batch_size), desc="Inserting"):
            batch_ids = ids[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            # Prepare data for insert
            data = [
                (str(id_), embedding.tolist())
                for id_, embedding in zip(batch_ids, batch_embeddings)
            ]

            # Use execute_values for efficient bulk insert
            execute_values(
                cur,
                f"INSERT INTO {table_name} (id, embedding) VALUES %s ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding",
                data,
                template="(%s, %s::vector)",
                page_size=batch_size,
            )

            inserted += len(data)

        conn.commit()

    return inserted


def verify_insertion(conn, table_name: str) -> int:
    """Verify the number of inserted rows."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
    return count


def main():
    parser = argparse.ArgumentParser(description="Load embeddings into pgvector")
    parser.add_argument(
        "--npz-path",
        type=str,
        required=True,
        help="Path to NPZ file containing embeddings",
    )
    parser.add_argument(
        "--table",
        type=str,
        default=None,
        help="Target table name (auto-detected from dimension if not specified)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for inserts (default: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--db-host",
        type=str,
        default=DB_CONFIG["host"],
        help="Database host",
    )
    parser.add_argument(
        "--db-port",
        type=int,
        default=DB_CONFIG["port"],
        help="Database port",
    )

    args = parser.parse_args()

    # Load NPZ file
    npz_path = Path(args.npz_path)
    if not npz_path.exists():
        logger.error(f"NPZ file not found: {npz_path}")
        sys.exit(1)

    embeddings, ids = load_npz(str(npz_path))

    # Determine table name
    table_name = args.table or get_table_for_dimension(embeddings.shape[1])
    logger.info(f"Using table: {table_name}")

    # Connect to database
    db_config = {
        **DB_CONFIG,
        "host": args.db_host,
        "port": args.db_port,
    }

    logger.info(f"Connecting to database at {db_config['host']}:{db_config['port']}")

    try:
        conn = psycopg2.connect(**db_config)
        logger.info("Connected to database")

        # Insert embeddings
        inserted = insert_embeddings(
            conn, embeddings, ids, table_name, args.batch_size
        )
        logger.info(f"Inserted {inserted} embeddings")

        # Verify
        count = verify_insertion(conn, table_name)
        logger.info(f"Verified {count} rows in {table_name}")

        conn.close()
        logger.info("Done!")

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
