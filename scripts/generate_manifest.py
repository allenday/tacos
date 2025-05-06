"""
Manifest Generator for Slack App

This script generates a manifest.yml file for a Slack app based on the configured unit name.
It handles missing environment variables gracefully and prevents memory issues.
"""
import os
import sys
import yaml
from pathlib import Path
import traceback

sys.setrecursionlimit(1000)

parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)

class DummyConfig:
    """Fallback configuration when environment variables are missing."""
    def __init__(self):
        self.UNIT_NAME = os.environ.get("UNIT_NAME", "kudos").lower()
        self.UNIT_NAME_PLURAL = os.environ.get("UNIT_NAME_PLURAL", self.UNIT_NAME + "s").lower()
        self.PRIMARY_EMOJI = os.environ.get("PRIMARY_EMOJI", "star-struck").lower()
        self.SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "xoxb-dummy-token")
        self.SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "xapp-dummy-token")

try:
    from src import config
    print("Using configuration from environment variables.")
except Exception as e:
    config = DummyConfig()
    print(f"Warning: Using dummy config for manifest generation due to: {str(e)}")
    print("This is fine for creating the manifest. You will need real tokens when running the actual bot.")

def check_env_configuration():
    """Verify that the configuration is valid for manifest generation."""
    try:
        issues = []
        
        # if not config.SLACK_BOT_TOKEN:
        #     issues.append("Missing required environment variable: SLACK_BOT_TOKEN")
        # if not config.SLACK_APP_TOKEN:
        #     issues.append("Missing required environment variable: SLACK_APP_TOKEN")
        
        if not config.UNIT_NAME:
            issues.append(f"UNIT_NAME is empty")
        elif not all(c.isalpha() or c == '-' for c in config.UNIT_NAME):
            issues.append(f"UNIT_NAME must contain only alphabetic characters or hyphens: '{config.UNIT_NAME}'")
        
        if not config.PRIMARY_EMOJI:
            issues.append(f"PRIMARY_EMOJI is empty")
        elif not all(c.isalnum() or c in '-_' for c in config.PRIMARY_EMOJI):
            issues.append(f"PRIMARY_EMOJI contains invalid characters: '{config.PRIMARY_EMOJI}'")
        
        if issues:
            print("Environment configuration issues:")
            for issue in issues:
                print(f"- {issue}")
            return False
        
        return True
    except Exception as e:
        print(f"Error checking environment configuration: {str(e)}")
        traceback.print_exc()
        return False

def create_slash_command(cmd_prefix, command, description, usage_hint=None):
    """Helper function to create a slash command entry."""
    cmd = {
        "command": f"/{cmd_prefix}{command}",
        "description": description,
        "should_escape": False
    }
    
    if usage_hint and usage_hint.strip():
        cmd["usage_hint"] = usage_hint
        
    return cmd

def generate_manifest():
    """Generate a Slack app manifest based on the unit name configuration."""
    try:
        unit_name = config.UNIT_NAME
        unit_name_plural = config.UNIT_NAME_PLURAL
        unit_name_cap = unit_name.capitalize()

        cmd_prefix = f"{unit_name.lower()}_"
        
        slash_commands = [
            create_slash_command(cmd_prefix, "give", 
                f"Give {unit_name_plural} to a user. Usage - /{cmd_prefix}give <amount> <@user> <note>",
                "<amount> <@user> <note>"),
            create_slash_command(cmd_prefix, "stats", 
                f"Show {unit_name} statistics (leaderboard)"),
            create_slash_command(cmd_prefix, "history", 
                f"Show {unit_name} giving/receiving history. Usage - /{cmd_prefix}history [@user] [lines]",
                "[@user] [lines]"),
            create_slash_command(cmd_prefix, "received", 
                f"Show your {unit_name} receiving history. Usage - /{cmd_prefix}received [lines]",
                "[lines]"),
            create_slash_command(cmd_prefix, "remaining", 
                f"Check how many {unit_name_plural} you (or @user) can give. Usage - /{cmd_prefix}remaining [@user]",
                "[@user]"),
            create_slash_command(cmd_prefix, "help", 
                f"Show help information for the {unit_name_cap} Bot")
        ]
        
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
                "slash_commands": slash_commands
            },
            "oauth_config": {
                "scopes": {
                    "bot": [
                        "chat:write",
                        "commands",
                        "im:write",
                        "chat:write.public",
                        "channels:read",
                        "users:read",
                        "reactions:read",
                        "reactions:write"
                    ]
                }
            },
            "settings": {
                "interactivity": {
                    "is_enabled": False
                },
                "org_deploy_enabled": False,
                "socket_mode_enabled": True,
                "token_rotation_enabled": False,
                "event_subscriptions": {
                    "request_url": "https://slack.com/socket-mode",
                    "bot_events": [
                        "reaction_added",
                        "message.channels"
                    ]
                }
            }
        }


        manifest_path = Path(__file__).parent.parent / "manifest.yml"
        with open(manifest_path, "w") as f:
            f.write("---\n")  # Add YAML document start marker
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, width=120)
        
        print(f"Generated manifest.yml with {unit_name} as the command prefix")
        print(f"Manifest saved to: {manifest_path}")
        return manifest
    
    except Exception as e:
        print(f"Error generating manifest: {str(e)}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    try:
        if check_env_configuration():
            manifest = generate_manifest()
            if manifest:
                print("Manifest generation completed successfully.")
                sys.exit(0)
            else:
                print("Failed to generate manifest.")
                sys.exit(1)
        else:
            print("Failed to generate manifest due to configuration issues.")
            sys.exit(1)
    except Exception as e:
        print(f"Unhandled error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
