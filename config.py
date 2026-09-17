"""
config.py — sab settings ek jagah.
Groq API use kar rahe hain (OpenAI-compatible endpoint).
API key .env file se load hoti hai — kabhi bhi code mein hardcode mat karo.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # .env file ko load karta hai

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL_NAME = "openai/gpt-oss-120b"
MAX_TOKENS = 1500

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fitness.db")