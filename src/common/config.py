import os

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "225d7912-c0a3-46ae-88a3-2c4272f954f3")

LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "llama-3.1-8b-instant")
LLM_API_KEY = os.getenv("LLM_API_KEY", "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")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1/")

REDIS_HOST = os.getenv("REDIS_HOST", "redis-16993.c85.us-east-1-2.ec2.redns.redis-cloud.com")
REDIS_PORT = int(os.getenv("REDIS_PORT", 16993))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "2aIXbkXwXlE3LA3arGcRm8dhA5x4WBwO")

DB_SEARCH_API_URL = os.getenv("DB_SEARCH_API_URL", "http://0.0.0.0:8001/search/")