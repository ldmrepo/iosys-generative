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

-- Test items metadata table (legacy, for backward compatibility)
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

-- Items table (full metadata from IML files)
CREATE TABLE IF NOT EXISTS items (
    -- 기본 식별자
    id VARCHAR(64) PRIMARY KEY,
    source_file TEXT NOT NULL,

    -- 문항 유형 정보
    question_type VARCHAR(20),      -- qt: 선택형/단답형/완결형
    question_type_code VARCHAR(10), -- 11/31/34
    difficulty VARCHAR(10),         -- df: 상/상중/중/중하/하
    difficulty_code VARCHAR(10),    -- 01-05

    -- 분류 체계 (cls1-cls12)
    curriculum VARCHAR(100),        -- cls1: 교육과정
    school_level VARCHAR(20),       -- cls2: 학교급
    grade VARCHAR(20),              -- cls3: 학년
    subject VARCHAR(50),            -- cls4: 과목
    subject_detail VARCHAR(50),     -- cls5: 세부과목
    semester VARCHAR(20),           -- cls6: 학기
    unit_large VARCHAR(100),        -- cls7: 대단원
    unit_medium VARCHAR(100),       -- cls8: 중단원
    unit_small VARCHAR(100),        -- cls9: 소단원
    unit_detail VARCHAR(100),       -- cls10: 세세단원

    -- 콘텐츠
    question_text TEXT,             -- 문제 텍스트 (수식 포함)
    choices JSONB,                  -- 선택지 배열
    answer_text TEXT,               -- 정답
    explanation_text TEXT,          -- 해설

    -- 미디어 (경로만 저장)
    question_images JSONB,          -- 문제 이미지 경로 배열
    explanation_images JSONB,       -- 해설 이미지 경로 배열
    has_image BOOLEAN DEFAULT FALSE,

    -- 메타
    keywords TEXT,                  -- kw: 키워드
    year INTEGER,                   -- dyear: 출제년도
    source VARCHAR(100),            -- qs: 출처
    exam_name VARCHAR(200),         -- qns: 시험명

    -- 원본 속성 (확장용)
    raw_attributes JSONB,

    -- 타임스탬프
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_items_difficulty ON items(difficulty_code);
CREATE INDEX IF NOT EXISTS idx_items_subject ON items(subject);
CREATE INDEX IF NOT EXISTS idx_items_grade ON items(grade);
CREATE INDEX IF NOT EXISTS idx_items_year ON items(year);
CREATE INDEX IF NOT EXISTS idx_items_has_image ON items(has_image);
CREATE INDEX IF NOT EXISTS idx_items_question_type ON items(question_type_code);

-- Full-text search (simple tokenizer for Korean)
CREATE INDEX IF NOT EXISTS idx_items_question_text ON items
    USING gin(to_tsvector('simple', COALESCE(question_text, '')));

COMMENT ON TABLE items IS 'Full item metadata parsed from IML files';

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
