import os
from dotenv import load_dotenv

load_dotenv()

# Crusoe Managed Inference (OpenAI-compatible)
CRUSOE_API_KEY = os.getenv("CRUSOE_API_KEY", "")
CRUSOE_BASE_URL = os.getenv("CRUSOE_BASE_URL", "https://api.inference.crusoecloud.com/v1/")
MODEL_NAME = os.getenv("MODEL_NAME", "nvidia/nemotron-3-nano-30b-a3b")  # Replace with exact model string

# You.com web search for the Researcher (optional: without a key it answers from the model alone)
YDC_API_KEY = os.getenv("YDC_API_KEY", "")
YDC_SEARCH_URL = os.getenv("YDC_SEARCH_URL", "https://ydc-index.io/v1/search")

# Shared memory path
MEMORY_PATH = os.getenv("MEMORY_PATH", "shared_memory.json")

# Safety limits
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "15"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
