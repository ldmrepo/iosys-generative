-- POC ItemBank Database Initialization
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Embedding dimension (Qwen3-VL-Embedding-2B uses 2048 dimensions)
-- KURE-v1 uses 1024 dimensions
-- SigLIP uses 768 dimensions

-- Qwen3-VL embeddings table
CREATE TABLE IF NOT EXISTS qwen_embeddings (
    id VARCHAR(64) PRIMARY KEY,
    embedding vector(2048),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- KURE-v1 embeddings table (text only)
CREATE TABLE IF NOT EXISTS kure_embeddings (
    id VARCHAR(64) PRIMARY KEY,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SigLIP embeddings table (image only)
CREATE TABLE IF NOT EXISTS siglip_embeddings (
    id VARCHAR(64) PRIMARY KEY,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Combined KURE+SigLIP embeddings table
CREATE TABLE IF NOT EXISTS combined_embeddings (
    id VARCHAR(64) PRIMARY KEY,
    embedding vector(1792),  -- 1024 + 768
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create HNSW indexes for fast similarity search
CREATE INDEX IF NOT EXISTS qwen_embedding_idx ON qwen_embeddings
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS kure_embedding_idx ON kure_embeddings
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS siglip_embedding_idx ON siglip_embeddings
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS combined_embedding_idx ON combined_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- Test items metadata table
CREATE TABLE IF NOT EXISTS test_items (
    id VARCHAR(64) PRIMARY KEY,
    category VARCHAR(20),  -- image, text_only, latex
    difficulty VARCHAR(10),
    question_type VARCHAR(20),
    question_text TEXT,
    has_image BOOLEAN,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ground truth table for evaluation
CREATE TABLE IF NOT EXISTS ground_truth (
    query_id VARCHAR(64),
    relevant_id VARCHAR(64),
    relevance_score INTEGER,  -- 3: very similar, 2: similar, 1: related
    PRIMARY KEY (query_id, relevant_id)
);

COMMENT ON TABLE qwen_embeddings IS 'Qwen3-VL-Embedding-2B multimodal embeddings';
COMMENT ON TABLE kure_embeddings IS 'KURE-v1 Korean text embeddings';
COMMENT ON TABLE siglip_embeddings IS 'SigLIP image embeddings';
COMMENT ON TABLE combined_embeddings IS 'KURE + SigLIP concatenated embeddings';
