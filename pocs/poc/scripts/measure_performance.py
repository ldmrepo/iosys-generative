#!/usr/bin/env python3
"""
Task #20-24: 성능 측정 스크립트
Latency, Throughput, VRAM 사용량, 안정성 테스트
"""
import json
import time
import torch
import gc
import numpy as np
from pathlib import Path
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/qwen3-vl-embedding-2b"
DATA_DIR = POC_DIR / "data"
RESULTS_DIR = POC_DIR / "results"

def get_gpu_memory():
    """GPU 메모리 사용량"""
    if torch.cuda.is_available():
        return {
            "allocated_gb": round(torch.cuda.memory_allocated() / 1e9, 3),
            "reserved_gb": round(torch.cuda.memory_reserved() / 1e9, 3),
            "max_allocated_gb": round(torch.cuda.max_memory_allocated() / 1e9, 3),
        }
    return None

def load_model():
    """모델 로드"""
    print("Loading model...")
    torch.cuda.reset_peak_memory_stats()

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    model.eval()

    return model, tokenizer

def load_test_texts():
    """테스트 텍스트 로드"""
    with open(DATA_DIR / "test_items.json", 'r') as f:
        data = json.load(f)

    texts = []
    for item in data['items']:
        content = item.get('content', {})
        question = content.get('question', '')
        texts.append(question)

    return texts

def generate_embedding(model, tokenizer, text):
    """단일 임베딩 생성"""
    device = next(model.parameters()).device

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

    attention_mask = inputs['attention_mask']
    token_embeddings = outputs.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    embedding = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)

    return embedding

def measure_latency(model, tokenizer, texts, n_runs=100):
    """Latency 측정"""
    print(f"\n[Latency Test] Running {n_runs} iterations...")

    latencies = []

    # Warmup
    for _ in range(5):
        generate_embedding(model, tokenizer, texts[0])

    torch.cuda.synchronize()

    for i in tqdm(range(n_runs), desc="Measuring latency"):
        text = texts[i % len(texts)]

        start = time.perf_counter()
        generate_embedding(model, tokenizer, text)
        torch.cuda.synchronize()
        end = time.perf_counter()

        latencies.append((end - start) * 1000)  # ms

    return {
        "mean_ms": round(np.mean(latencies), 2),
        "std_ms": round(np.std(latencies), 2),
        "p50_ms": round(np.percentile(latencies, 50), 2),
        "p95_ms": round(np.percentile(latencies, 95), 2),
        "p99_ms": round(np.percentile(latencies, 99), 2),
        "min_ms": round(np.min(latencies), 2),
        "max_ms": round(np.max(latencies), 2),
    }

def measure_throughput(model, tokenizer, texts, batch_size=1):
    """Throughput 측정"""
    print(f"\n[Throughput Test] Processing {len(texts)} items...")

    start = time.perf_counter()

    for text in tqdm(texts, desc="Processing"):
        generate_embedding(model, tokenizer, text)
        torch.cuda.synchronize()

    end = time.perf_counter()
    elapsed = end - start

    return {
        "total_items": len(texts),
        "elapsed_seconds": round(elapsed, 2),
        "items_per_second": round(len(texts) / elapsed, 2),
    }

def stability_test(model, tokenizer, texts, n_iterations=1000):
    """안정성 테스트"""
    print(f"\n[Stability Test] Running {n_iterations} iterations...")

    successes = 0
    failures = 0
    errors = []

    for i in tqdm(range(n_iterations), desc="Stability test"):
        try:
            text = texts[i % len(texts)]
            generate_embedding(model, tokenizer, text)
            successes += 1
        except Exception as e:
            failures += 1
            if len(errors) < 10:  # Keep first 10 errors
                errors.append(str(e))

    return {
        "total_iterations": n_iterations,
        "successes": successes,
        "failures": failures,
        "success_rate": round(successes / n_iterations * 100, 2),
        "errors": errors,
    }

def main():
    print("=" * 60)
    print("Qwen3-VL-Embedding-2B 성능 측정")
    print("=" * 60)

    # GPU info
    if torch.cuda.is_available():
        print(f"\nGPU: {torch.cuda.get_device_name(0)}")
        print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

    # Load model
    print("\n[1/5] 모델 로드...")
    model, tokenizer = load_model()
    vram_after_load = get_gpu_memory()
    print(f"      VRAM after load: {vram_after_load}")

    # Load test data
    print("\n[2/5] 테스트 데이터 로드...")
    texts = load_test_texts()
    print(f"      Loaded {len(texts)} texts")

    results = {
        "model": "Qwen3-VL-Embedding-2B",
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "vram_after_load": vram_after_load,
    }

    # Latency test
    print("\n[3/5] Latency 측정...")
    latency_results = measure_latency(model, tokenizer, texts, n_runs=100)
    results["latency"] = latency_results
    print(f"      Mean: {latency_results['mean_ms']:.2f}ms")
    print(f"      P95:  {latency_results['p95_ms']:.2f}ms {'✓' if latency_results['p95_ms'] <= 200 else '✗'} (target: ≤200ms)")

    # Throughput test
    print("\n[4/5] Throughput 측정...")
    throughput_results = measure_throughput(model, tokenizer, texts)
    results["throughput"] = throughput_results
    print(f"      Throughput: {throughput_results['items_per_second']:.2f} items/sec")

    # VRAM monitoring
    vram_peak = get_gpu_memory()
    results["vram_peak"] = vram_peak
    print(f"\n      Peak VRAM: {vram_peak['max_allocated_gb']:.2f} GB {'✓' if vram_peak['max_allocated_gb'] <= 8 else '✗'} (target: ≤8GB)")

    # Stability test
    print("\n[5/5] 안정성 테스트...")
    stability_results = stability_test(model, tokenizer, texts, n_iterations=1000)
    results["stability"] = stability_results
    print(f"      Success rate: {stability_results['success_rate']:.2f}% {'✓' if stability_results['success_rate'] == 100 else '✗'} (target: 100%)")

    # Save results
    output_file = RESULTS_DIR / "performance_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_file}")

    # Summary
    print("\n" + "=" * 60)
    print("성능 측정 요약")
    print("=" * 60)
    print(f"\n  Latency (P95):     {latency_results['p95_ms']:.2f}ms {'✓' if latency_results['p95_ms'] <= 200 else '✗'}")
    print(f"  Throughput:        {throughput_results['items_per_second']:.2f} items/sec")
    print(f"  Peak VRAM:         {vram_peak['max_allocated_gb']:.2f} GB {'✓' if vram_peak['max_allocated_gb'] <= 8 else '✗'}")
    print(f"  Stability:         {stability_results['success_rate']:.2f}% {'✓' if stability_results['success_rate'] == 100 else '✗'}")

    # Cleanup
    del model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()

    print("\n" + "=" * 60)
    print("성능 측정 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
