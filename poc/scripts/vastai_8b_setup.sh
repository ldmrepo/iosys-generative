#!/bin/bash
# Vast.ai Qwen3-VL-8B 실험 Setup 스크립트
#
# 사용법:
#   1. SSH 접속 후 이 스크립트 실행
#   2. source /opt/miniforge3/etc/profile.d/conda.sh && conda activate base
#   3. bash vastai_8b_setup.sh

echo "=================================================="
echo "Qwen3-VL-8B 실험 환경 설정"
echo "=================================================="

# 1. 패키지 설치
echo ""
echo "[1/4] 패키지 설치..."
pip install torch transformers accelerate tqdm qwen-vl-utils Pillow -q

# 2. GPU 확인
echo ""
echo "[2/4] GPU 확인..."
python3 -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}'); print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB' if torch.cuda.is_available() else '')"

# 3. 필요 파일 확인
echo ""
echo "[3/4] 필요 파일 확인..."
for file in test_items.json ground_truth_image.json ground_truth_hybrid.json; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (누락)"
    fi
done

# 4. 스크립트 확인
echo ""
echo "[4/4] 실행 스크립트 확인..."
for script in vastai_qwen3vl_8b_embedding.py vastai_qwen3vl_8b_reranker.py; do
    if [ -f "$script" ]; then
        echo "  ✓ $script"
    else
        echo "  ✗ $script (누락)"
    fi
done

echo ""
echo "=================================================="
echo "설정 완료!"
echo ""
echo "실행 순서:"
echo "  1. python3 vastai_qwen3vl_8b_embedding.py   # 임베딩 생성 (~10분)"
echo "  2. python3 vastai_qwen3vl_8b_reranker.py    # Reranker 평가 (~20분)"
echo ""
echo "결과 파일:"
echo "  - qwen_vl_embeddings_8b.json"
echo "  - qwen_vl_reranker_8b_evaluation.json"
echo "=================================================="
