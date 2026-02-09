#!/usr/bin/env python3
"""
전체 10,952건 문항 임베딩 생성 (2B 멀티모달, mean pooling)
- 중단 시 재개 가능 (체크포인트)
- 배치 처리로 메모리 효율화
"""
import json
import sys
import torch
import torch.nn.functional as F
import gc
import time
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/qwen3-vl-embedding-2b"
DATA_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/processed")
RAW_IMAGE_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/raw")
OUTPUT_DIR = POC_DIR / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Output files
OUTPUT_FILE = OUTPUT_DIR / "qwen_embeddings_full_2b_multimodal.json"
CHECKPOINT_FILE = OUTPUT_DIR / "embedding_checkpoint.json"
LOG_FILE = OUTPUT_DIR / "embedding_log.txt"

# Add model scripts to path
sys.path.insert(0, str(MODEL_PATH / "scripts"))


def log(msg):
    """Log message to file and stdout"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    with open(LOG_FILE, "a") as f:
        f.write(log_msg + "\n")


def get_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        return f"{allocated:.2f}GB"
    return "N/A"


def find_image_path(item_id):
    """문항 ID에 해당하는 이미지 경로 찾기"""
    # YYYYMMDD 형식 검색
    for date_dir in RAW_IMAGE_DIR.iterdir():
        if not date_dir.is_dir():
            continue
        item_dir = date_dir / item_id
        if item_dir.exists():
            for img_file in item_dir.rglob("*.png"):
                return str(img_file)
            for img_file in item_dir.rglob("*.jpg"):
                return str(img_file)

    # YYYY/MM/DD 형식 검색
    for year_dir in RAW_IMAGE_DIR.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        if len(year_dir.name) == 4:  # YYYY
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for day_dir in month_dir.iterdir():
                    if not day_dir.is_dir():
                        continue
                    item_dir = day_dir / item_id
                    if item_dir.exists():
                        for img_file in item_dir.rglob("*.png"):
                            return str(img_file)
                        for img_file in item_dir.rglob("*.jpg"):
                            return str(img_file)
    return None


class Qwen3VLEmbedderMeanPool:
    """Qwen3VLEmbedder with mean pooling"""

    def __init__(self, model_name_or_path, **kwargs):
        from qwen3_vl_embedding import Qwen3VLForEmbedding
        from transformers.models.qwen3_vl.processing_qwen3_vl import Qwen3VLProcessor

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = Qwen3VLForEmbedding.from_pretrained(
            model_name_or_path, trust_remote_code=True, **kwargs
        ).to(device)
        self.processor = Qwen3VLProcessor.from_pretrained(
            model_name_or_path, padding_side='right'
        )
        self.model.eval()
        self.default_instruction = "Represent this educational question item for retrieval."

    def format_input(self, text=None, image=None):
        content = []
        conversation = [
            {"role": "system", "content": [{"type": "text", "text": self.default_instruction}]},
            {"role": "user", "content": content}
        ]

        if image:
            image_content = image if image.startswith(('http', 'oss')) else 'file://' + image
            content.append({
                'type': 'image', 'image': image_content,
                "min_pixels": 4 * 32 * 32,
                "max_pixels": 1800 * 32 * 32
            })

        if text:
            content.append({'type': 'text', 'text': text})

        if not content:
            content.append({'type': 'text', 'text': "NULL"})

        return conversation

    @torch.no_grad()
    def process_single(self, text=None, image=None, normalize=True):
        """Process single input with mean pooling"""
        from qwen_vl_utils.vision_process import process_vision_info

        conversation = self.format_input(text=text, image=image)

        # Apply chat template
        text_input = self.processor.apply_chat_template(
            [conversation], add_generation_prompt=True, tokenize=False
        )

        # Process vision info
        try:
            images, video_inputs, video_kwargs = process_vision_info(
                [conversation], image_patch_size=16,
                return_video_metadata=True, return_video_kwargs=True
            )
        except Exception:
            images = None
            video_inputs = None
            video_kwargs = {}

        # Prepare inputs
        inputs = self.processor(
            text=text_input,
            images=images if images else None,
            videos=video_inputs if video_inputs else None,
            padding=True,
            return_tensors="pt",
            **video_kwargs
        ).to(self.model.device)

        # Forward pass
        outputs = self.model(**inputs)
        last_hidden_state = outputs.last_hidden_state

        # Mean pooling
        attention_mask = inputs["attention_mask"]
        mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        sum_embeddings = torch.sum(last_hidden_state * mask_expanded, dim=1)
        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
        embedding = sum_embeddings / sum_mask

        if normalize:
            embedding = F.normalize(embedding, p=2, dim=-1)

        return embedding.squeeze().cpu().numpy().tolist()


def load_all_items():
    """모든 전처리된 문항 로드"""
    items = []
    for part_file in sorted(DATA_DIR.glob("items_part*.json")):
        with open(part_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and "items" in data:
                items.extend(data["items"])
            elif isinstance(data, list):
                items.extend(data)
    return items


def load_checkpoint():
    """체크포인트 로드"""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"completed_ids": [], "embeddings": {}}


def save_checkpoint(checkpoint):
    """체크포인트 저장"""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f)


def save_final_result(embeddings, metadata):
    """최종 결과 저장"""
    result = {
        "model": "Qwen/Qwen3-VL-Embedding-2B",
        "mode": "multimodal_meanpool",
        "num_items": len(embeddings),
        "embedding_dim": 2048,
        "metadata": metadata,
        "embeddings": embeddings
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f)
    log(f"최종 결과 저장: {OUTPUT_FILE}")


def main():
    log("=" * 60)
    log("전체 문항 임베딩 생성 시작")
    log("=" * 60)

    # 모델 로드
    log(f"[1/4] 모델 로드 중... (VRAM: {get_gpu_memory()})")
    embedder = Qwen3VLEmbedderMeanPool(
        str(MODEL_PATH),
        torch_dtype=torch.float16
    )
    log(f"모델 로드 완료 (VRAM: {get_gpu_memory()})")

    # 데이터 로드
    log("[2/4] 데이터 로드 중...")
    items = load_all_items()
    log(f"총 문항: {len(items):,}개")

    # 체크포인트 로드
    checkpoint = load_checkpoint()
    completed_ids = set(checkpoint.get("completed_ids", []))
    embeddings = checkpoint.get("embeddings", {})
    log(f"기존 진행: {len(completed_ids):,}개 완료")

    # 미완료 문항 필터링
    remaining_items = [item for item in items if item["id"] not in completed_ids]
    log(f"남은 문항: {len(remaining_items):,}개")

    if not remaining_items:
        log("모든 문항 임베딩 완료!")
        save_final_result(embeddings, {"total": len(items), "with_image": 0})
        return

    # 임베딩 생성
    log("[3/4] 임베딩 생성 중...")
    start_time = time.time()
    image_count = 0
    error_count = 0
    save_interval = 500  # 500개마다 체크포인트 저장

    for i, item in enumerate(tqdm(remaining_items, desc="Embedding")):
        item_id = item["id"]

        try:
            # 텍스트 추출
            content = item.get("content", {})
            question = content.get("question", "")
            choices = content.get("choices", [])

            text_parts = [f"문제: {question}"]
            if choices:
                for j, choice in enumerate(choices, 1):
                    text_parts.append(f"{j}. {choice}")
            text = "\n".join(text_parts)

            # 이미지 경로 찾기
            image_path = None
            if item.get("has_image", False):
                image_path = find_image_path(item_id)
                if image_path:
                    image_count += 1

            # 임베딩 생성
            embedding = embedder.process_single(text=text, image=image_path)
            embeddings[item_id] = embedding
            completed_ids.add(item_id)

        except Exception as e:
            error_count += 1
            log(f"Error [{item_id}]: {str(e)[:100]}")
            continue

        # 주기적 체크포인트 저장
        if (i + 1) % save_interval == 0:
            checkpoint = {
                "completed_ids": list(completed_ids),
                "embeddings": embeddings
            }
            save_checkpoint(checkpoint)
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = len(remaining_items) - (i + 1)
            eta = remaining / rate if rate > 0 else 0
            log(f"진행: {len(completed_ids):,}/{len(items):,} ({rate:.1f}/sec, ETA: {eta/60:.1f}min)")

        # 메모리 정리
        if (i + 1) % 100 == 0:
            gc.collect()
            torch.cuda.empty_cache()

    # 최종 저장
    log("[4/4] 결과 저장 중...")
    elapsed = time.time() - start_time
    metadata = {
        "total": len(items),
        "completed": len(embeddings),
        "with_image": image_count,
        "errors": error_count,
        "elapsed_seconds": elapsed,
        "items_per_second": len(remaining_items) / elapsed if elapsed > 0 else 0
    }
    save_final_result(embeddings, metadata)

    # 체크포인트 삭제
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    log("=" * 60)
    log(f"완료! {len(embeddings):,}개 임베딩 생성")
    log(f"이미지 포함: {image_count:,}개")
    log(f"에러: {error_count}개")
    log(f"소요 시간: {elapsed/60:.1f}분")
    log(f"처리 속도: {len(remaining_items)/elapsed:.2f} items/sec")
    log("=" * 60)


if __name__ == "__main__":
    main()
