#!/usr/bin/env python3
"""
Task #2: Qwen3-VL-Embedding-2B 모델 로드 테스트
8GB GPU에서 FP16/4-bit로 로드 테스트
"""
import torch
import gc
import sys

def get_gpu_memory():
    """GPU 메모리 사용량 확인"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        total = torch.cuda.get_device_properties(0).total_memory / 1e9
        return {
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "total_gb": round(total, 2),
            "free_gb": round(total - reserved, 2)
        }
    return None

def test_fp16_load():
    """FP16으로 모델 로드 테스트"""
    print("\n" + "="*60)
    print("Test 1: FP16 Load")
    print("="*60)

    from transformers import AutoModel, AutoTokenizer

    model_path = "./models/qwen3-vl-embedding-2b"

    print(f"\nLoading model from: {model_path}")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    try:
        # Load tokenizer
        print("\n[1/3] Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        print(f"      Tokenizer loaded")

        # Load model with FP16
        print("\n[2/3] Loading model (FP16)...")
        model = AutoModel.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        print(f"      Model loaded")
        print(f"      GPU memory after load: {get_gpu_memory()}")

        # Test inference
        print("\n[3/3] Testing inference...")
        test_text = "이차함수 y = x² - 4x + 3의 그래프를 그리시오."
        inputs = tokenizer(test_text, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)

        # Get embedding (use last hidden state mean pooling)
        embedding = outputs.last_hidden_state.mean(dim=1)
        print(f"      Embedding shape: {embedding.shape}")
        print(f"      GPU memory after inference: {get_gpu_memory()}")

        # Cleanup
        del model, tokenizer, inputs, outputs, embedding
        gc.collect()
        torch.cuda.empty_cache()

        print("\n✅ FP16 Load: SUCCESS")
        return True

    except Exception as e:
        print(f"\n❌ FP16 Load: FAILED")
        print(f"   Error: {e}")
        gc.collect()
        torch.cuda.empty_cache()
        return False

def test_4bit_load():
    """4-bit 양자화로 모델 로드 테스트"""
    print("\n" + "="*60)
    print("Test 2: 4-bit Quantization Load")
    print("="*60)

    from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig

    model_path = "./models/qwen3-vl-embedding-2b"

    print(f"\nLoading model from: {model_path}")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    try:
        # 4-bit config
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        # Load tokenizer
        print("\n[1/3] Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        print(f"      Tokenizer loaded")

        # Load model with 4-bit
        print("\n[2/3] Loading model (4-bit)...")
        model = AutoModel.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        print(f"      Model loaded")
        print(f"      GPU memory after load: {get_gpu_memory()}")

        # Test inference
        print("\n[3/3] Testing inference...")
        test_text = "이차함수 y = x² - 4x + 3의 그래프를 그리시오."
        inputs = tokenizer(test_text, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)

        embedding = outputs.last_hidden_state.mean(dim=1)
        print(f"      Embedding shape: {embedding.shape}")
        print(f"      GPU memory after inference: {get_gpu_memory()}")

        # Cleanup
        del model, tokenizer, inputs, outputs, embedding
        gc.collect()
        torch.cuda.empty_cache()

        print("\n✅ 4-bit Load: SUCCESS")
        return True

    except Exception as e:
        print(f"\n❌ 4-bit Load: FAILED")
        print(f"   Error: {e}")
        gc.collect()
        torch.cuda.empty_cache()
        return False

def main():
    print("="*60)
    print("Qwen3-VL-Embedding-2B Model Load Test")
    print("="*60)

    print(f"\nPyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {get_gpu_memory()}")

    # Test FP16 first
    fp16_success = test_fp16_load()

    # If FP16 fails, try 4-bit
    if not fp16_success:
        print("\nFP16 failed, trying 4-bit quantization...")
        bit4_success = test_4bit_load()

        if not bit4_success:
            print("\n" + "="*60)
            print("⚠️  Both FP16 and 4-bit failed!")
            print("   Consider using cloud GPU (RunPod/Vast.ai)")
            print("="*60)
            sys.exit(1)

    print("\n" + "="*60)
    print("Model Load Test Complete!")
    print("="*60)

if __name__ == "__main__":
    main()
