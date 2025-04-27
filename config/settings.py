'''Configuration settings for the project.'''

import logging
import os
from pathlib import Path

# Import dotenv for loading .env files
try:
    from dotenv import load_dotenv
    # Try to load from .env file (if it exists)
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"Loaded environment variables from {env_path}")
except ImportError:
    print("python-dotenv not installed. Using environment variables directly.")

# Import our pump-and-dump keyword lists
try:
    from config.pump_keywords import get_default_keywords, HIGH_PRECISION_KEYWORDS
    # Use the default keywords (combination of high-precision + some combined keywords)
    DEFAULT_KEYWORDS = get_default_keywords()
except ImportError:
    # Fallback if the module isn't available
    DEFAULT_KEYWORDS = [
        "solana 100x", "solana gem", "SOL moonshot", 
        "solana presale", "SOL token moon", "$SOL easy gains"
    ]

# --- API Keys (Load from environment variables with fallbacks) ---
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "YOUR_TWITTER_API_IO_KEY")  # Get from https://twitterapi.io
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY", "YOUR_SOLSCAN_PRO_API_KEY") # Get from https://pro-api.solscan.io/
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")    # Get from https://platform.openai.com/api-keys

# --- Social Aggregator Settings ---
# Keywords to track on Twitter - Updated to target CAs more directly
TWITTER_KEYWORDS = [
    "SOL memecoin CA",
    "SOL hype CA",
    "SOL alpha CA"
    "SOL presale CA"
]
# Original generic keywords (uncomment to use these instead)
# TWITTER_KEYWORDS = ["solana", "$SOL", "specific_project_keyword"]
# Original pump-focused keywords (loaded from pump_keywords.py by default)
# from config.pump_keywords import get_default_keywords
# TWITTER_KEYWORDS = get_default_keywords()

TWITTER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]
# Add Telegram/Discord specific settings if needed
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
# TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
# DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_DISCORD_BOT_TOKEN")
# DISCORD_CHANNEL_IDS = os.getenv("DISCORD_CHANNEL_IDS", "").split(",")

# --- On-Chain Monitor Settings ---
SOLANA_WATCH_ADDRESSES = os.getenv("SOLANA_WATCH_ADDRESSES", "Address1...,Address2...").split(",")
SOLANA_WATCH_TOKENS = os.getenv("SOLANA_WATCH_TOKENS", "TokenMintAddress1...,TokenMintAddress2...").split(",")

# --- Correlation Engine Settings ---
CORRELATION_TIME_WINDOW_MINUTES = int(os.getenv("CORRELATION_TIME_WINDOW_MINUTES", "60"))
SENTIMENT_SPIKE_THRESHOLD = float(os.getenv("SENTIMENT_SPIKE_THRESHOLD", "0.7"))
VOLUME_SPIKE_THRESHOLD_PERCENT = int(os.getenv("VOLUME_SPIKE_THRESHOLD_PERCENT", "200"))

# --- AI Settings ---
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_PUMP_SCORE_THRESHOLD = float(os.getenv("AI_PUMP_SCORE_THRESHOLD", "0.6"))

# --- Alerting Settings ---
ALERT_EMAIL_RECIPIENTS = os.getenv("ALERT_EMAIL_RECIPIENTS", "your_email@example.com").split(",")
# Add other alert channel configs (e.g., Telegram chat ID, Discord channel ID)
# ALERT_TELEGRAM_CHAT_ID = os.getenv("ALERT_TELEGRAM_CHAT_ID", "your_alert_chat_id")
# ALERT_DISCORD_CHANNEL_ID = os.getenv("ALERT_DISCORD_CHANNEL_ID", "your_alert_channel_id")

# --- General Settings ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300")) 