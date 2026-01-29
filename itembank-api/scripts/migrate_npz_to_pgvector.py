"""
Migrate NPZ embeddings to pgvector database.
"""
import asyncio
import numpy as np
import asyncpg
from pathlib import Path
import sys

# Configuration
NPZ_PATH = "/mnt/sda/worker/dev_ldm/iosys-generative/poc/results/qwen_embeddings_all_subjects_2b_multimodal_compat.npz"
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "poc_user",
    "password": "poc_password",
    "database": "poc_itembank"
}
BATCH_SIZE = 1000


async def migrate():
    print(f"Loading NPZ from: {NPZ_PATH}")

    # Load NPZ
    data = np.load(NPZ_PATH, allow_pickle=True)

    # Get embeddings and IDs
    if "embeddings" in data:
        embeddings = data["embeddings"]
    elif "embedding" in data:
        embeddings = data["embedding"]
    else:
        keys = list(data.keys())
        embeddings = data[keys[0]]

    if "ids" in data:
        ids = data["ids"]
    elif "id" in data:
        ids = data["id"]
    elif "item_ids" in data:
        ids = data["item_ids"]
    else:
        ids = None

    print(f"Loaded {len(embeddings)} embeddings with dimension {embeddings.shape[1]}")

    if ids is not None:
        print(f"Loaded {len(ids)} IDs")

    # Connect to database
    conn = await asyncpg.connect(**DB_CONFIG)

    # Check existing count
    existing = await conn.fetchval("SELECT COUNT(*) FROM qwen_embeddings")
    print(f"Existing embeddings in pgvector: {existing}")

    # Check if we should skip existing
    if existing > 1000:
        response = input(f"Already have {existing} embeddings. Continue? (y/n): ")
        if response.lower() != 'y':
            print("Aborted")
            await conn.close()
            return

    # Insert in batches
    total_inserted = 0
    total_skipped = 0

    for i in range(0, len(embeddings), BATCH_SIZE):
        batch_end = min(i + BATCH_SIZE, len(embeddings))
        batch_embeddings = embeddings[i:batch_end]
        batch_ids = ids[i:batch_end] if ids is not None else range(i, batch_end)

        for j, (item_id, embedding) in enumerate(zip(batch_ids, batch_embeddings)):
            item_id = str(item_id)

            # Convert embedding to pgvector format
            embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"

            try:
                # Insert or update
                await conn.execute("""
                    INSERT INTO qwen_embeddings (id, embedding)
                    VALUES ($1, $2::vector)
                    ON CONFLICT (id) DO NOTHING
                """, item_id, embedding_str)
                total_inserted += 1
            except Exception as e:
                print(f"Error inserting {item_id}: {e}")
                total_skipped += 1

        print(f"Progress: {batch_end}/{len(embeddings)} ({total_inserted} inserted, {total_skipped} skipped)")

    # Final count
    final_count = await conn.fetchval("SELECT COUNT(*) FROM qwen_embeddings")
    print(f"\nMigration complete!")
    print(f"Total in pgvector: {final_count}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
