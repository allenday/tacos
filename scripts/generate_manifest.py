import os
import sys
import yaml
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

try:
    from src import config
except ValueError as e:
    class DummyConfig:
        def __init__(self):
            self.UNIT_NAME = os.environ.get("UNIT_NAME", "kudos").lower()
            self.UNIT_NAME_PLURAL = os.environ.get("UNIT_NAME_PLURAL", self.UNIT_NAME + "s").lower()
            self.PRIMARY_EMOJI = os.environ.get("PRIMARY_EMOJI", "star-struck").lower()
            self.SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "xoxb-dummy-token")
            self.SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "xapp-dummy-token")
    
    config = DummyConfig()
    print("Warning: Using dummy config for manifest generation. This is fine for creating the manifest.")
    print("Note: You will need real tokens when running the actual bot.")

def check_env_configuration():
    """Verify that the .env configuration is valid for manifest generation."""
    issues = []
    
    # if not config.SLACK_BOT_TOKEN:
    #     issues.append("Missing required environment variable: SLACK_BOT_TOKEN")
    # if not config.SLACK_APP_TOKEN:
    #     issues.append("Missing required environment variable: SLACK_APP_TOKEN")
    
    if not config.UNIT_NAME or not config.UNIT_NAME.isalpha():
        issues.append(f"UNIT_NAME must contain only alphabetic characters: '{config.UNIT_NAME}'")
    
    if not config.PRIMARY_EMOJI or not config.PRIMARY_EMOJI.replace('-', '').replace('_', '').isalnum():
        issues.append(f"PRIMARY_EMOJI contains invalid characters: '{config.PRIMARY_EMOJI}'")
    
    if issues:
        print("Environment configuration issues:")
        for issue in issues:
            print(f"- {issue}")
        return False
    
    return True

def generate_manifest():
    """Generate a Slack app manifest based on the unit name configuration."""
    unit_name = config.UNIT_NAME
    unit_name_plural = config.UNIT_NAME_PLURAL
    unit_name_cap = unit_name.capitalize()

    cmd_prefix = f"{unit_name.lower()}_"

    manifest = {
        "display_information": {
            "name": f"{unit_name_cap} Bot",
            "description": f"A simple bot for giving and tracking virtual {unit_name_plural} within a Slack workspace.",
            "background_color": "#f5f5dc"
        },
        "features": {
            "bot_user": {
                "display_name": f"{unit_name_cap} Bot",
                "always_online": True
            },
            "app_home": {
                "home_tab_enabled": False,
                "messages_tab_enabled": True,
                "messages_tab_read_only_enabled": False
            },
            "slash_commands": [
                {
                    "command": f"/{cmd_prefix}give",
                    "description": f"Give {unit_name_plural} to a user. Usage - /{cmd_prefix}give <amount> <@user> <note>",
                    "usage_hint": "<amount> <@user> <note>",
                    "should_escape": False
                },
                {
                    "command": f"/{cmd_prefix}stats",
                    "description": f"Show {unit_name} statistics (leaderboard)",
                    "usage_hint": "",
                    "should_escape": False
                },
                {
                    "command": f"/{cmd_prefix}history",
                    "description": f"Show {unit_name} giving/receiving history. Usage - /{cmd_prefix}history [@user] [lines]",
                    "usage_hint": "[@user] [lines]",
                    "should_escape": False
                },
                {
                    "command": f"/{cmd_prefix}received",
                    "description": f"Show your {unit_name} receiving history. Usage - /{cmd_prefix}received [lines]",
                    "usage_hint": "[lines]",
                    "should_escape": False
                },
                {
                    "command": f"/{cmd_prefix}remaining",
                    "description": f"Check how many {unit_name_plural} you (or @user) can give. Usage - /{cmd_prefix}remaining [@user]",
                    "usage_hint": "[@user]",
                    "should_escape": False
                },
                {
                    "command": f"/{cmd_prefix}help",
                    "description": f"Show help information for the {unit_name_cap} Bot",
                    "usage_hint": "",
                    "should_escape": False
                }
            ]
        },
        "oauth_config": {
            "scopes": {
                "bot": [
                    "chat:write",
                    "commands",
                    "im:write",
                    "chat:write.public",
                    "channels:read",
                    "users:read"
                ]
            }
        },
        "settings": {
            "interactivity": {
                "is_enabled": False
            },
            "org_deploy_enabled": False,
            "socket_mode_enabled": True,
            "token_rotation_enabled": False
        }
    }

    if unit_name.lower() != "taco" and unit_name.lower() != "tacos":
        legacy_prefix = "tacos_"
        for cmd in manifest["features"]["slash_commands"]:
            cmd_suffix = cmd["command"].split("/")[1].split("_")[1]
            
            legacy_cmd = cmd.copy()
            legacy_cmd["command"] = f"/{legacy_prefix}{cmd_suffix}"
            
            legacy_cmd["description"] = f"[Legacy] {legacy_cmd['description']}"
            
            manifest["features"]["slash_commands"].append(legacy_cmd)

    with open(Path(__file__).parent.parent / "manifest.yml", "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
        
    print(f"Generated manifest.yml with {unit_name} as the command prefix")
    return manifest

if __name__ == "__main__":
    if check_env_configuration():
        generate_manifest()
    else:
        print("Failed to generate manifest due to configuration issues.")
        sys.exit(1)
