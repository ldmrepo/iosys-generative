"""
POC Model Configuration
Memory-optimized settings for RTX 2070 8GB
"""
import torch

# Model paths
MODEL_DIR = "/mnt/sda/worker/dev_ldm/iosys-generative/poc/models"
QWEN_MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"  # Start with smaller model for testing
KURE_MODEL_ID = "nlpai-lab/KURE-v1"
SIGLIP_MODEL_ID = "google/siglip-base-patch16-256-i18n"

# Stage 1: FP16 configuration
FP16_CONFIG = {
    "torch_dtype": torch.float16,
    "device_map": "auto",
    "low_cpu_mem_usage": True,
}

# Stage 1-B: 4-bit quantization (if FP16 fails)
def get_bnb_4bit_config():
    from transformers import BitsAndBytesConfig
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

# Image processing limits (for 8GB GPU)
IMAGE_CONFIG = {
    "max_pixels": 512 * 512,  # Reduced from 1024*1024
    "min_pixels": 64 * 64,
}

# Batch size
BATCH_SIZE = 1  # Start conservative for 8GB GPU

# Data paths
DATA_DIR = "/mnt/sda/worker/dev_ldm/iosys-generative/data/processed"
POC_DATA_DIR = "/mnt/sda/worker/dev_ldm/iosys-generative/poc/data"
RAW_IMAGE_DIR = "/mnt/sda/worker/dev_ldm/iosys-generative/data/raw"

# Results
RESULTS_DIR = "/mnt/sda/worker/dev_ldm/iosys-generative/poc/results"

# Database configuration (Docker)
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "poc_itembank",
    "user": "poc_user",
    "password": "poc_password",
}

# Connection string
DB_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
