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
DAILY_TACO_LIMIT = int(os.environ.get("DAILY_TACO_LIMIT", 5))
DEFAULT_HISTORY_LINES = 10
LEADERBOARD_LIMIT = 10
TACO_ANNOUNCE_CHANNEL = os.environ.get("TACO_ANNOUNCE_CHANNEL") # Optional announcement channel
# TACO_REACTION_EMOJI = os.environ.get("TACO_REACTION_EMOJI", "taco").lower() # REMOVED

# Basic Logging Configuration (can be expanded)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Ensure required environment variables are set
if not SLACK_BOT_TOKEN:
    raise ValueError("Missing required environment variable: SLACK_BOT_TOKEN")
if not SLACK_APP_TOKEN:
    raise ValueError("Missing required environment variable: SLACK_APP_TOKEN") 