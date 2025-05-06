import os
import yaml # Added for YAML parsing
import logging # Added for logging config loading errors
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Basic Logging Setup (before config loading) ---
# Configure logging early to catch potential config errors
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level_str)
config_logger = logging.getLogger(__name__) # Use a dedicated logger for config

# --- Slack Configuration --- #
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN") # Needed for Socket Mode

# --- Database Configuration --- #
DATABASE_FILE = os.environ.get("DATABASE_FILE", "kudos.db")

# --- Bot Behavior Configuration --- #
DAILY_UNIT_LIMIT = int(os.environ.get("DAILY_UNIT_LIMIT", 5))
DEFAULT_HISTORY_LINES = 10
LEADERBOARD_LIMIT = 10
UNIT_ANNOUNCE_CHANNEL = os.environ.get("UNIT_ANNOUNCE_CHANNEL") # Optional announcement channel

# --- Unit Configuration --- #
UNIT_NAME = os.environ.get("UNIT_NAME", "wow").lower() # Changed default to wow
UNIT_NAME_PLURAL = os.environ.get("UNIT_NAME_PLURAL", UNIT_NAME + "s").lower()

# --- Emoji Configuration (Loaded from YAML) --- #
EMOJI_CONFIG_FILE = "emoji_config.yml"
EMOJI_VALUES = {}
ALL_EMOJIS = []
PRIMARY_EMOJI = "star-struck" # Default primary, will be validated against loaded config

def load_emoji_config():
    """Loads emoji values from the YAML config file."""
    global EMOJI_VALUES, ALL_EMOJIS, PRIMARY_EMOJI
    try:
        with open(EMOJI_CONFIG_FILE, 'r') as f:
            config_data = yaml.safe_load(f)
            if config_data and 'emoji_values' in config_data:
                EMOJI_VALUES = config_data['emoji_values']
                # Validate values are integers > 0
                valid_emojis = {}
                for emoji, value in EMOJI_VALUES.items():
                    if isinstance(value, int) and value > 0:
                        valid_emojis[emoji] = value
                    else:
                        config_logger.warning(f"Invalid value '{value}' for emoji '{emoji}' in {EMOJI_CONFIG_FILE}. Must be a positive integer. Ignoring.")
                EMOJI_VALUES = valid_emojis
                ALL_EMOJIS = list(EMOJI_VALUES.keys())
                config_logger.info(f"Loaded {len(ALL_EMOJIS)} emojis with values from {EMOJI_CONFIG_FILE}")
                
                # Determine PRIMARY_EMOJI (can still be overridden by env var, but must be in the loaded config)
                primary_from_env = os.environ.get("PRIMARY_EMOJI", PRIMARY_EMOJI).lower()
                if primary_from_env in EMOJI_VALUES:
                    PRIMARY_EMOJI = primary_from_env
                    config_logger.info(f"Using primary emoji: '{PRIMARY_EMOJI}'")
                else:
                    config_logger.warning(f"PRIMARY_EMOJI '{primary_from_env}' (from env or default) not found in {EMOJI_CONFIG_FILE}. Using first loaded emoji '{ALL_EMOJIS[0]}' as primary fallback.")
                    PRIMARY_EMOJI = ALL_EMOJIS[0] if ALL_EMOJIS else "question"
                    
            else:
                config_logger.error(f"Could not find 'emoji_values' key in {EMOJI_CONFIG_FILE}. Using default emoji values.")
                EMOJI_VALUES = {PRIMARY_EMOJI: 1}
                ALL_EMOJIS = [PRIMARY_EMOJI]

    except FileNotFoundError:
        config_logger.error(f"Emoji config file not found: {EMOJI_CONFIG_FILE}. Using default emoji values: {{ '{PRIMARY_EMOJI}': 1 }}")
        EMOJI_VALUES = {PRIMARY_EMOJI: 1}
        ALL_EMOJIS = [PRIMARY_EMOJI]
    except yaml.YAMLError as e:
        config_logger.error(f"Error parsing YAML file {EMOJI_CONFIG_FILE}: {e}. Using default emoji values.")
        EMOJI_VALUES = {PRIMARY_EMOJI: 1}
        ALL_EMOJIS = [PRIMARY_EMOJI]
    except Exception as e:
        config_logger.error(f"Unexpected error loading emoji config: {e}. Using default emoji values.")
        EMOJI_VALUES = {PRIMARY_EMOJI: 1}
        ALL_EMOJIS = [PRIMARY_EMOJI]

# Load the emoji config immediately
load_emoji_config()

# --- Logging Configuration (Apply final level) --- #
LOG_LEVEL = log_level_str # Already set via basicConfig

# --- Ensure required environment variables are set --- #
if not SLACK_BOT_TOKEN:
    raise ValueError("Missing required environment variable: SLACK_BOT_TOKEN")
if not SLACK_APP_TOKEN:
    raise ValueError("Missing required environment variable: SLACK_APP_TOKEN")
if not EMOJI_VALUES:
    raise ValueError("Emoji configuration failed to load, and no defaults available. Bot cannot start.")        