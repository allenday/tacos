import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Slack Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN") # Needed for Socket Mode

# Database Configuration
DATABASE_FILE = os.environ.get("DATABASE_FILE", "tacos.db")

# Bot Configuration
DAILY_UNIT_LIMIT = int(os.environ.get("DAILY_UNIT_LIMIT", 5))
DEFAULT_HISTORY_LINES = 10
LEADERBOARD_LIMIT = 10
UNIT_ANNOUNCE_CHANNEL = os.environ.get("UNIT_ANNOUNCE_CHANNEL") # Optional announcement channel

# Unit Configuration
UNIT_NAME = os.environ.get("UNIT_NAME", "kudos").lower()
UNIT_NAME_PLURAL = os.environ.get("UNIT_NAME_PLURAL", UNIT_NAME + "s").lower()

# Emoji Configuration
PRIMARY_EMOJI = os.environ.get("PRIMARY_EMOJI", "star-struck").lower()
UNIT_REACTION_EMOJI = os.environ.get("UNIT_REACTION_EMOJI", PRIMARY_EMOJI).lower()
ALTERNATE_EMOJIS = [
    "open_mouth", "astonished", "exploding_head", "sparkles", "fire", "100",
    "face_holding_back_tears", "heart_eyes", "raised_hands", "sunglasses",
    "nerd_face", "telescope", "eyes", "disguised_face"
]
ALL_EMOJIS = [PRIMARY_EMOJI, UNIT_REACTION_EMOJI] + ALTERNATE_EMOJIS

# Basic Logging Configuration (can be expanded)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Ensure required environment variables are set
if not SLACK_BOT_TOKEN:
    raise ValueError("Missing required environment variable: SLACK_BOT_TOKEN")
if not SLACK_APP_TOKEN:
    raise ValueError("Missing required environment variable: SLACK_APP_TOKEN")        