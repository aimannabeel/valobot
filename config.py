import os
import ssl
import certifi
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HENRIK_API_KEY = os.getenv("HENRIK_API_KEY")
ssl_context = ssl.create_default_context(cafile=certifi.where())

if DISCORD_TOKEN is None:
    raise ValueError("DISCORD_TOKEN is missing from .env")

if not HENRIK_API_KEY:
    raise ValueError("HENRIK_API_KEY is missing from .env")
