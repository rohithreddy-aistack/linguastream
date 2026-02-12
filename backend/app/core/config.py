import os
from dotenv import load_dotenv

# Load .env file from backend directory
# We assume this file is at backend/app/core/config.py
# So we go up two levels to find backend/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

class Settings:
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    BROWSER_RATE = 44100
    TARGET_RATE = 16000
    VAD_THRESHOLD = 0.5

settings = Settings()
