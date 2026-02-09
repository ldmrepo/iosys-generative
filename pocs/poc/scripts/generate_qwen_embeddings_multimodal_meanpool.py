#!/usr/bin/env python3
"""
멀티모달 Qwen3-VL-Embedding-2B 임베딩 생성 (mean pooling 방식)
Qwen3VLEmbedder의 전처리를 사용하되, pooling은 mean pooling으로 변경
"""
import json
import sys
import torch
import torch.nn.functional as F
import gc
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/qwen3-vl-embedding-2b"
DATA_DIR = POC_DIR / "data"
RAW_IMAGE_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/raw")
OUTPUT_DIR = POC_DIR / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Add model scripts to path
sys.path.insert(0, str(MODEL_PATH / "scripts"))


def get_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        return f"{allocated:.2f}GB"
    return "N/A"


class Qwen3VLEmbedderMeanPool:
    """Qwen3VLEmbedder with mean pooling instead of last token pooling"""

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
        """Format input for model"""
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
    def process(self, inputs, normalize=True):
        """Process inputs with mean pooling"""
        from qwen_vl_utils.vision_process import process_vision_info

        # Format conversations
        conversations = [
            self.format_input(text=inp.get('text'), image=inp.get('image'))
            for inp in inputs
        ]

        # Apply chat template
        text = self.processor.apply_chat_template(
            conversations, add_generation_prompt=True, tokenize=False
        )

        # Process vision info
        try:
            images, video_inputs, video_kwargs = process_vision_info(
                conversations, image_patch_size=16,
                return_video_metadata=True, return_video_kwargs=True
            )
        except Exception as e:
            images = None
            video_inputs = None
            video_kwargs = {'do_sample_frames': False}

        if video_inputs is not None:
            videos, video_metadata = zip(*video_inputs)
            videos = list(videos)
            video_metadata = list(video_metadata)
        else:
            videos, video_metadata = None, None

        # Process with processor
        processed = self.processor(
            text=text, images=images, videos=videos, video_metadata=video_metadata,
            truncation=True, max_length=8192, padding=True, do_resize=False,
            return_tensors='pt', **video_kwargs
        )
        processed = {k: v.to(self.model.device) for k, v in processed.items()}

        # Forward pass
        outputs = self.model(**processed)

        # Mean pooling (instead of last token pooling)
        attention_mask = processed['attention_mask']
        token_embeddings = outputs.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

        if normalize:
            embeddings = F.normalize(embeddings, p=2, dim=-1)

        return embeddings


def load_model():
    print(f"Loading model from {MODEL_PATH}...")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    model = Qwen3VLEmbedderMeanPool(
        model_name_or_path=str(MODEL_PATH),
        torch_dtype=torch.float16
    )

    print(f"Model loaded. GPU memory: {get_gpu_memory()}")
    return model


def load_test_items():
    with open(DATA_DIR / "test_items.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['items']


def prepare_text_input(item):
    content = item.get('content', {})
    question = content.get('question', '')
    choices = content.get('choices', [])
    choices_text = ""
    if choices:
        for i, choice in enumerate(choices, 1):
            choices_text += f"\n{i}. {choice}"
    text = f"문제: {question}"
    if choices_text:
        text += f"\n선택지:{choices_text}"
    return text


def find_image_path(item):
    """문항의 이미지 경로 찾기 (question + explanation)"""
    images = item.get('images', {})
    image_candidates = images.get('question', []) or images.get('explanation', [])

    if not image_candidates:
        return None

    img_path = image_candidates[0]

    direct_path = RAW_IMAGE_DIR / img_path
    if direct_path.exists():
        return direct_path

    for folder in RAW_IMAGE_DIR.iterdir():
        if not folder.is_dir() or not folder.name.isdigit():
            continue

        if len(folder.name) == 8:
            candidate = folder / img_path
            if candidate.exists():
                return candidate
        elif len(folder.name) == 4:
            for month_folder in folder.iterdir():
                if not month_folder.is_dir():
                    continue
                for day_folder in month_folder.iterdir():
                    if not day_folder.is_dir():
                        continue
                    candidate = day_folder / img_path
                    if candidate.exists():
                        return candidate

    return None


def generate_embeddings_batch(model, items, batch_size=4):
    all_embeddings = {}
    errors = []

    for i in tqdm(range(0, len(items), batch_size), desc="Generating embeddings"):
        batch_items = items[i:i + batch_size]
        batch_inputs = []

        for item in batch_items:
            try:
                text = prepare_text_input(item)
                inp = {"text": text}

                if item.get('has_image'):
                    image_path = find_image_path(item)
                    if image_path and image_path.exists():
                        inp["image"] = str(image_path)

                batch_inputs.append((item['id'], inp))
            except Exception as e:
                errors.append({"id": item['id'], "error": str(e)})

        if not batch_inputs:
            continue

        try:
            inputs_for_model = [inp for _, inp in batch_inputs]
            embeddings = model.process(inputs_for_model, normalize=True)

            for idx, (item_id, _) in enumerate(batch_inputs):
                all_embeddings[item_id] = embeddings[idx].cpu().numpy().tolist()

        except Exception as e:
            print(f"\nBatch failed, processing individually: {e}")
            for item_id, inp in batch_inputs:
                try:
                    embedding = model.process([inp], normalize=True)
                    all_embeddings[item_id] = embedding[0].cpu().numpy().tolist()
                except Exception as e2:
                    errors.append({"id": item_id, "error": str(e2)})

    return all_embeddings, errors


def main():
    print("=" * 60)
    print("Qwen3-VL-Embedding-2B 멀티모달 임베딩 (Mean Pooling)")
    print("=" * 60)

    print("\n[1/4] 모델 로드...")
    model = load_model()

    print("\n[2/4] 테스트 데이터 로드...")
    items = load_test_items()
    print(f"      문항 수: {len(items)}")

    image_items = [item for item in items if item.get('has_image')]
    print(f"      이미지 문항: {len(image_items)}")
    print(f"      텍스트 문항: {len(items) - len(image_items)}")

    found_images = sum(1 for item in image_items if find_image_path(item))
    print(f"      이미지 파일 발견: {found_images}/{len(image_items)}")

    print("\n[3/4] 멀티모달 임베딩 생성 (mean pooling)...")
    embeddings, errors = generate_embeddings_batch(model, items, batch_size=4)

    print(f"\n      성공: {len(embeddings)}/{len(items)}")
    if errors:
        print(f"      오류: {len(errors)}")

    print("\n[4/4] 저장...")
    output_data = {
        "metadata": {
            "model": "Qwen3-VL-Embedding-2B",
            "mode": "multimodal_meanpool",
            "method": "Qwen3VLEmbedder + mean pooling",
            "total_items": len(items),
            "successful": len(embeddings),
            "failed": len(errors),
            "image_items": len(image_items),
            "images_found": found_images,
            "embedding_dim": 2048,
            "dtype": "float16"
        },
        "embeddings": embeddings,
        "errors": errors
    }

    output_file = OUTPUT_DIR / "qwen_embeddings_multimodal_meanpool.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)
    print(f"      저장: {output_file}")

    np_file = OUTPUT_DIR / "qwen_embeddings_multimodal_meanpool.npz"
    ids = list(embeddings.keys())
    vectors = np.array([embeddings[id] for id in ids])
    np.savez(np_file, ids=ids, embeddings=vectors)
    print(f"      저장: {np_file}")

    del model
    gc.collect()
    torch.cuda.empty_cache()

    print("\n" + "=" * 60)
    print("멀티모달 임베딩 (Mean Pooling) 생성 완료!")
    print(f"Embedding shape: ({len(embeddings)}, 2048)")
    print("=" * 60)


if __name__ == "__main__":
    main()
