import os

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "225d7912-c0a3-46ae-88a3-2c4272f954f3")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "llama-3.1-8b-instant")
LLM_API_KEY = os.getenv("LLM_API_KEY", "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")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1/")