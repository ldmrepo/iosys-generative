# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IOSYS ItemBank AI - AI 기반 차세대 문항은행 시스템 구축 프로젝트

### Goals
- 자연어 문항 검색 (semantic search)
- 유사 문항 검색 및 추천
- 교육과정/성취기준/난이도 자동 분류
- 이미지 참조형 문항 자동 생성 (with hallucination prevention)

### Project Phases
1. **Phase 1**: 문항 벡터화 및 검색 인프라 (embedding + vector DB)
2. **Phase 2**: 자동 분류 시스템
3. **Phase 3**: 이미지 참조형 문항 생성 (Fact Graph 기반)
4. **Phase 4**: 통합 플랫폼 및 API

## Document Structure

| File | Purpose |
|------|---------|
| `00 IMG-ITEM-PIPELINE-001.md` | 이미지 참조 문항 생성 파이프라인 기술 명세 |
| `01 IOSYS-ITEMBANK-AI-001.md` | 프로젝트 마스터 플랜 |
| `02 ...-T01.md` | Phase 1 태스크 목록 |
| `04 ...-R01.md` | 기술 리서치 결과 (Qwen3-VL 반영) |
| `05 ...-R02.md` | Qwen3-VL-Embedding 종합 리서치 보고서 |
| `06 ...-POC.md` | POC 계획서 |

## Planned Technology Stack

### Embedding Models
- **Primary**: Qwen3-VL-Embedding-2B (multimodal: text + image unified)
- **Reranker**: Qwen3-VL-Reranker-2B
- **Fallback**: KURE-v1 (Korean text), SigLIP (image)

### Vector Database
- **Initial**: pgvector (PostgreSQL extension)
- **Scale-up**: Qdrant or Milvus

### Key Dependencies (planned)
```
torch>=2.2.0
transformers>=4.45.0
vllm>=0.11.0
sentence-transformers
pgvector
psycopg2-binary
```

## Key Concepts

### Fact Graph
문항 생성의 단일 근거 모델(Single Source of Truth). 이미지에서 추출된 검증 가능한 사실(Entities, Relations, Numerics)을 구조화하여 환각(hallucination) 방지.

### Integrity Gate
생성된 문항의 논리적 무결성 자동 검증 (참조 무결성, 수치 재현성, 관계 무결성, 정보 충분성, 도메인 위반 여부).

### Two-Stage Retrieval
1. Qwen3-VL-Embedding으로 초기 검색 (Top-K)
2. Qwen3-VL-Reranker로 재순위화 (정밀도 향상)

## Language Notes

- 문서 및 문항 콘텐츠: 한국어
- 코드 주석/변수명: 영어 권장
- Embedding instruction prompts: 영어 권장 (모델 특성)
