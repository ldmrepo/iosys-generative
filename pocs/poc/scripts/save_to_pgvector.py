#!/usr/bin/env python3
"""
Task #12: 임베딩 pgvector 저장
모든 임베딩을 PostgreSQL pgvector에 저장
"""
import json
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
RESULTS_DIR = POC_DIR / "results"
DATA_DIR = POC_DIR / "data"

# Database config
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "poc_itembank",
    "user": "poc_user",
    "password": "poc_password",
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def save_embeddings(conn, table_name, embeddings_file):
    """임베딩을 테이블에 저장"""
    print(f"  Loading {embeddings_file.name}...")
    with open(embeddings_file, 'r') as f:
        data = json.load(f)

    embeddings = data['embeddings']
    dim = len(list(embeddings.values())[0])

    print(f"  Dimension: {dim}, Count: {len(embeddings)}")

    # Clear existing data
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {table_name}")

    # Insert embeddings
    rows = [(id, emb) for id, emb in embeddings.items()]

    with conn.cursor() as cur:
        execute_values(
            cur,
            f"INSERT INTO {table_name} (id, embedding) VALUES %s",
            rows,
            template="(%s, %s::vector)"
        )

    conn.commit()
    print(f"  Saved {len(rows)} embeddings to {table_name}")

def save_test_items(conn):
    """테스트 문항 메타데이터 저장"""
    print("  Loading test_items.json...")
    with open(DATA_DIR / "test_items.json", 'r') as f:
        data = json.load(f)

    items = data['items']

    # Clear existing data
    with conn.cursor() as cur:
        cur.execute("DELETE FROM test_items")

    # Insert items
    rows = []
    for item in items:
        has_image = item.get('has_image', False)
        has_latex = len(item.get('content', {}).get('question_latex', [])) > 0

        if has_image:
            category = "image"
        elif has_latex:
            category = "latex"
        else:
            category = "text_only"

        rows.append((
            item['id'],
            category,
            item.get('metadata', {}).get('difficulty', ''),
            item.get('metadata', {}).get('question_type', ''),
            item.get('content', {}).get('question', ''),
            has_image,
            json.dumps(item.get('metadata', {}), ensure_ascii=False)
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """INSERT INTO test_items
               (id, category, difficulty, question_type, question_text, has_image, metadata)
               VALUES %s""",
            rows
        )

    conn.commit()
    print(f"  Saved {len(rows)} items to test_items")

def save_ground_truth(conn):
    """Ground truth 저장"""
    print("  Loading ground_truth.json...")
    with open(DATA_DIR / "ground_truth.json", 'r') as f:
        data = json.load(f)

    ground_truth = data['ground_truth']

    # Clear existing data
    with conn.cursor() as cur:
        cur.execute("DELETE FROM ground_truth")

    # Insert ground truth
    rows = []
    for gt in ground_truth:
        query_id = gt['query_id']
        for rel in gt['relevant_items']:
            rows.append((query_id, rel['id'], rel['relevance']))

    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO ground_truth (query_id, relevant_id, relevance_score) VALUES %s",
            rows
        )

    conn.commit()
    print(f"  Saved {len(rows)} ground truth pairs")

def main():
    print("=" * 60)
    print("임베딩 pgvector 저장")
    print("=" * 60)

    conn = get_connection()
    print(f"\nConnected to {DB_CONFIG['database']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")

    try:
        # Qwen embeddings
        print("\n[1/6] Qwen3-VL 임베딩 저장...")
        save_embeddings(conn, "qwen_embeddings", RESULTS_DIR / "qwen_embeddings.json")

        # KURE embeddings
        print("\n[2/6] KURE-v1 임베딩 저장...")
        save_embeddings(conn, "kure_embeddings", RESULTS_DIR / "kure_embeddings.json")

        # SigLIP embeddings
        print("\n[3/6] SigLIP 임베딩 저장...")
        save_embeddings(conn, "siglip_embeddings", RESULTS_DIR / "siglip_embeddings.json")

        # Combined embeddings
        print("\n[4/6] Combined 임베딩 저장...")
        save_embeddings(conn, "combined_embeddings", RESULTS_DIR / "combined_embeddings.json")

        # Test items
        print("\n[5/6] 테스트 문항 저장...")
        save_test_items(conn)

        # Ground truth
        print("\n[6/6] Ground truth 저장...")
        save_ground_truth(conn)

        # Verify
        print("\n" + "=" * 60)
        print("저장 검증")
        print("=" * 60)

        with conn.cursor() as cur:
            tables = ['qwen_embeddings', 'kure_embeddings', 'siglip_embeddings',
                      'combined_embeddings', 'test_items', 'ground_truth']
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  {table}: {count} rows")

    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("pgvector 저장 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
