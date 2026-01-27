"""
LLM Configuration for Ground Truth Generation
OpenAI API settings for LLM-as-a-Judge
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Model options
AVAILABLE_MODELS = {
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "input_cost_per_1m": 0.15,
        "output_cost_per_1m": 0.60,
        "max_tokens": 128000,
    },
    "gpt-4o": {
        "name": "GPT-4o",
        "input_cost_per_1m": 2.50,
        "output_cost_per_1m": 10.00,
        "max_tokens": 128000,
    },
    "gpt-4.1": {
        "name": "GPT-4.1",
        "input_cost_per_1m": 2.00,
        "output_cost_per_1m": 8.00,
        "max_tokens": 1000000,
    },
}

# Generation settings
LLM_GT_CONFIG = {
    "candidates_per_query": 20,  # Initial candidates from embedding
    "top_k_final": 5,            # Final GT items per query
    "min_relevance_score": 3,    # Minimum score to include (1-5)
    "batch_size": 5,             # Concurrent API calls
    "max_retries": 3,            # Retry on API errors
    "timeout": 30,               # API timeout in seconds
}

# Paths
POC_DIR = Path(__file__).parent.parent
DATA_DIR = POC_DIR / "data"
RESULTS_DIR = POC_DIR / "results"

# Output files
LLM_GT_OUTPUT = DATA_DIR / "ground_truth_llm.json"
LLM_EVAL_OUTPUT = RESULTS_DIR / "search_evaluation_llm_gt.json"
