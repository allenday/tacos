"""Utilities for handling command prefixes and names."""

from . import config

def get_command_prefix():
    """Get the command prefix based on the unit name."""
    return f"{config.UNIT_NAME.lower()}_"

def get_command_name(suffix):
    """Generate a command name with the appropriate prefix."""
    return f"/{get_command_prefix()}{suffix}"

CMD_GIVE = "give"
CMD_STATS = "stats"
CMD_HISTORY = "history"
CMD_RECEIVED = "received" 
CMD_REMAINING = "remaining"
CMD_HELP = "help"

command_handlers = {}
