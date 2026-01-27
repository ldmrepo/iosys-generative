#!/usr/bin/env python3
"""
Task #7 & #8: Qwen3-VL-Embedding-2B 임베딩 생성
텍스트 + 이미지 멀티모달 임베딩 생성
"""
import json
import torch
import gc
import numpy as np
from pathlib import Path
from tqdm import tqdm
from PIL import Image
from transformers import AutoModel, AutoTokenizer, AutoProcessor

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/qwen3-vl-embedding-2b"
DATA_DIR = POC_DIR / "data"
RAW_IMAGE_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/raw")
OUTPUT_DIR = POC_DIR / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

def get_gpu_memory():
    """GPU 메모리 사용량"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        return f"{allocated:.2f}GB"
    return "N/A"

def load_model():
    """모델 로드 (FP16)"""
    print(f"Loading model from {MODEL_PATH}...")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)

    model = AutoModel.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    model.eval()

    print(f"Model loaded. GPU memory: {get_gpu_memory()}")

    # Try to load processor for image handling
    try:
        processor = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
    except Exception as e:
        print(f"Processor not available: {e}")
        processor = None

    return model, tokenizer, processor

def load_test_items():
    """테스트 데이터 로드"""
    with open(DATA_DIR / "test_items.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['items']

def prepare_text_input(item):
    """문항에서 텍스트 입력 준비"""
    content = item.get('content', {})

    # 문제 텍스트
    question = content.get('question', '')

    # 선택지 (있으면)
    choices = content.get('choices', [])
    choices_text = ""
    if choices:
        for i, choice in enumerate(choices, 1):
            choices_text += f"\n{i}. {choice}"

    # 전체 텍스트
    text = f"문제: {question}"
    if choices_text:
        text += f"\n선택지:{choices_text}"

    return text

def find_image_path(item):
    """문항의 이미지 경로 찾기"""
    images = item.get('images', {})
    question_images = images.get('question', [])

    if not question_images:
        return None

    # 첫 번째 이미지 사용
    img_path = question_images[0]

    # 이미지 경로 구성
    item_id = item['id']

    # 여러 가능한 경로 시도
    possible_paths = [
        RAW_IMAGE_DIR / item_id / img_path,
        RAW_IMAGE_DIR / img_path,
    ]

    # 날짜 폴더 검색
    for date_folder in RAW_IMAGE_DIR.iterdir():
        if date_folder.is_dir():
            candidate = date_folder / item_id / img_path
            if candidate.exists():
                return candidate

    for path in possible_paths:
        if path.exists():
            return path

    return None

def generate_embedding(model, tokenizer, processor, text, image_path=None):
    """단일 문항 임베딩 생성"""
    device = next(model.parameters()).device

    # 텍스트만 사용 (이미지 처리는 모델 특성에 따라 조정 필요)
    inputs = tokenizer(
        text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    # Mean pooling
    attention_mask = inputs['attention_mask']
    token_embeddings = outputs.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    embedding = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    # Normalize
    embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)

    return embedding.cpu().numpy()[0]

def main():
    print("=" * 60)
    print("Qwen3-VL-Embedding-2B 임베딩 생성")
    print("=" * 60)

    # 모델 로드
    print("\n[1/4] 모델 로드...")
    model, tokenizer, processor = load_model()

    # 데이터 로드
    print("\n[2/4] 테스트 데이터 로드...")
    items = load_test_items()
    print(f"      문항 수: {len(items)}")

    # 임베딩 생성
    print("\n[3/4] 임베딩 생성...")
    embeddings = {}
    errors = []

    for item in tqdm(items, desc="Generating embeddings"):
        item_id = item['id']
        try:
            # 텍스트 준비
            text = prepare_text_input(item)

            # 이미지 경로 (있으면)
            image_path = find_image_path(item) if item.get('has_image') else None

            # 임베딩 생성
            embedding = generate_embedding(model, tokenizer, processor, text, image_path)
            embeddings[item_id] = embedding.tolist()

        except Exception as e:
            errors.append({"id": item_id, "error": str(e)})
            print(f"\nError for {item_id}: {e}")

    print(f"\n      성공: {len(embeddings)}/{len(items)}")
    if errors:
        print(f"      오류: {len(errors)}")

    # 저장
    print("\n[4/4] 저장...")
    output_data = {
        "metadata": {
            "model": "Qwen3-VL-Embedding-2B",
            "total_items": len(items),
            "successful": len(embeddings),
            "failed": len(errors),
            "embedding_dim": 2048,
            "dtype": "float16"
        },
        "embeddings": embeddings,
        "errors": errors
    }

    output_file = OUTPUT_DIR / "qwen_embeddings.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)

    print(f"      저장: {output_file}")

    # NumPy 형식으로도 저장 (빠른 로드용)
    np_file = OUTPUT_DIR / "qwen_embeddings.npz"
    ids = list(embeddings.keys())
    vectors = np.array([embeddings[id] for id in ids])
    np.savez(np_file, ids=ids, embeddings=vectors)
    print(f"      저장: {np_file}")

    # 메모리 정리
    del model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()

    print("\n" + "=" * 60)
    print("임베딩 생성 완료!")
    print(f"Embedding shape: ({len(embeddings)}, 2048)")
    print("=" * 60)

if __name__ == "__main__":
    main()
