import logging
import sys
import re  # Add import for regex
import datetime # Added for timestamp formatting in completion message
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError # Added

# Project imports
from . import config, database, commands, command_utils

# --- Logging Setup --- #
# Set root logger level first
logging.basicConfig(level=logging.DEBUG) # Use DEBUG level
# Set specific logger levels
logging.getLogger("__main__").setLevel(config.LOG_LEVEL) # Your app's main logger
logging.getLogger("slack_bolt").setLevel(logging.DEBUG) # Bolt framework
logging.getLogger("slack_sdk").setLevel(logging.DEBUG) # Underlying SDK

logger = logging.getLogger(__name__)

# --- Initialize Database --- #
try:
    database.init_db()
except Exception as e:
    logger.critical(f"Failed to initialize database: {e}")
    sys.exit(1) # Exit if DB initialization fails

# --- Initialize Slack Bolt App --- #
app = App(token=config.SLACK_BOT_TOKEN)

# --- In-memory state for reaction flows --- #
# Structure: { giver_user_id: { step: str, recipient_id: str, original_channel_id: str, original_ts: str, amount: int|None } }
reaction_flows = {}

processed_reactions = {}

# --- Helper Function for Transaction Completion --- #
def _complete_unit_transaction(client, giver_id, recipient_id, amount, note, original_channel_id, original_message_ts):
    """Handles the final steps: DB insert, notifications, announcements (handles threads)."""
    success = database.add_transaction(
        giver_id=giver_id,
        recipient_id=recipient_id,
        amount=amount,
        note=note,
        source_channel_id=original_channel_id,
        original_message_ts=original_message_ts,
        original_channel_id=original_channel_id
    )
    if not success:
        try:
            # Notify giver in DM about the failure
            im_response = client.conversations_open(users=giver_id)
            if im_response and im_response.get("ok"):
                client.chat_postMessage(
                    channel=im_response["channel"]["id"],
                    text=f"Sorry, there was an error recording your {config.UNIT_NAME} transaction. Please try again."
                )
        except Exception as e:
             logger.error(f"Failed to notify giver {giver_id} about transaction failure: {e}")
        return False # Indicate failure

    # Transaction added successfully, proceed with notifications
    unit_word = config.UNIT_NAME if amount == 1 else config.UNIT_NAME_PLURAL
    emoji = commands.get_emoji()
    completion_text = f"You gave {amount} :{emoji}: to <@{recipient_id}>! Reason: {note}"
    recipient_text = f"You received {amount} :{emoji}: from <@{giver_id}>! Reason: {note}"
    public_text = f":{emoji}: <@{giver_id}> gave {amount} {unit_word} to <@{recipient_id}>! Reason: {note}"

    # 1. Notify giver (in DM, since reaction flow happens there)
    try:
        im_response = client.conversations_open(users=giver_id)
        if im_response and im_response.get("ok"):
            client.chat_postMessage(
                channel=im_response["channel"]["id"],
                text=completion_text
            )
    except Exception as e:
        logger.error(f"Error sending completion DM to giver {giver_id}: {e}")

    # 2. Notify recipient (DM)
    try:
        im_response = client.conversations_open(users=recipient_id)
        if im_response and im_response.get("ok"):
            client.chat_postMessage(
                channel=im_response["channel"]["id"],
                text=recipient_text
            )
        else:
             logger.error(f"Could not open IM channel for recipient {recipient_id}: {im_response.get('error')}")
    except Exception as e:
        logger.error(f"Error sending DM notification to recipient {recipient_id}: {e}")

    # 3. Announce in original channel (potentially in thread)
    try:
        client.chat_postMessage(
            channel=original_channel_id,
            text=public_text,
            thread_ts=original_message_ts # Reply in thread if it originated there
        )
    except SlackApiError as e:
        logger.error(f"Error posting public message to original channel {original_channel_id} (ts: {original_message_ts}): {e}")

    # 4. Announce in central unit channel (if different and configured)
    announce_channel_name = config.UNIT_ANNOUNCE_CHANNEL
    if announce_channel_name:
        # Get channel ID for comparison (more reliable than name)
        try:
            # Find the announcement channel ID (requires channels:read scope)
            announce_channel_id = None
            for page in client.conversations_list(types="public_channel", limit=200):
                for channel in page["channels"]:
                    if channel["name"] == announce_channel_name:
                        announce_channel_id = channel["id"]
                        break
                if announce_channel_id:
                    break

            if announce_channel_id and announce_channel_id != original_channel_id:
                client.chat_postMessage(
                    channel=announce_channel_id, # Use channel ID
                    text=public_text
                    # Note: We DON'T post to the thread in the announcement channel,
                    # just the main channel announcement.
                )
            elif not announce_channel_id:
                 logger.warning(f"Announcement channel '#{announce_channel_name}' not found.")

        except SlackApiError as e:
            if e.response["error"] == "missing_scope" and "channels:read" in str(e):
                logger.warning("Missing 'channels:read' scope to look up announcement channel ID by name. Cannot post announcement.")
            else:
                logger.error(f"Error posting to announcement channel #{announce_channel_name}: {e}")
        except Exception as e:
             logger.error(f"Unexpected error looking up or posting to announcement channel #{announce_channel_name}: {e}")

    return True # Indicate success


# --- Register Command Handlers --- #

def handle_give_command(ack, body, say, client):
    text = body.get("text", "").strip()
    logger.info(f"Received {command_utils.get_command_name(command_utils.CMD_GIVE)} command: {text}")
    # Assume give command is always for giving
    commands.handle_give_command(ack, body, say, client)

def handle_stats_slash_command(ack, body, say, client):
    logger.info(f"Received {command_utils.get_command_name(command_utils.CMD_STATS)} command")
    # Body text is ignored for stats/leaderboard
    commands.handle_stats_command(ack, body, client)

def handle_history_slash_command(ack, body, say, client):
    logger.info(f"Received {command_utils.get_command_name(command_utils.CMD_HISTORY)} command: {body.get('text')}")
    # Pass the text directly to the handler (it expects args like [@user] [lines])
    commands.handle_history_command(ack, body, say, client)

def handle_received_slash_command(ack, body, say, client):
    logger.info(f"Received {command_utils.get_command_name(command_utils.CMD_RECEIVED)} command: {body.get('text')}")
    # Pass the text directly to the handler (it expects args like [lines])
    commands.handle_received_command(ack, body, say, client)

def handle_help_slash_command(ack, body, say, client):
    logger.info(f"Received {command_utils.get_command_name(command_utils.CMD_HELP)} command")
    # Body text is ignored for help
    commands.handle_help_command(ack, body, client)

def handle_remaining_slash_command(ack, body, say, client):
    logger.info(f"Received {command_utils.get_command_name(command_utils.CMD_REMAINING)} command: {body.get('text')}")
    commands.handle_remaining_command(ack, body, client)

def register_command_handlers():
    """Register all command handlers with dynamic prefixes."""
    
    app.command(command_utils.get_command_name(command_utils.CMD_GIVE))(handle_give_command)
    app.command(command_utils.get_command_name(command_utils.CMD_STATS))(handle_stats_slash_command)
    app.command(command_utils.get_command_name(command_utils.CMD_HISTORY))(handle_history_slash_command)
    app.command(command_utils.get_command_name(command_utils.CMD_RECEIVED))(handle_received_slash_command)
    app.command(command_utils.get_command_name(command_utils.CMD_HELP))(handle_help_slash_command)
    app.command(command_utils.get_command_name(command_utils.CMD_REMAINING))(handle_remaining_slash_command)
    
    logger.info(f"Registered command handlers with prefix: {command_utils.get_command_prefix()}")

register_command_handlers()

# --- Event Handlers --- #

@app.event("reaction_added")
def handle_reaction_added(event, client, say):
    logger.info(f"Reaction added event: {event}")
    
    reaction = event.get("reaction", "")
    # Check if the reaction emoji is one we've configured with a point value
    if reaction not in config.EMOJI_VALUES:
        logger.info(f"Ignoring reaction '{reaction}' as it's not in the configured emoji values list from {config.EMOJI_CONFIG_FILE}")
        return
    
    # Get the point value for this specific emoji
    reaction_amount = config.EMOJI_VALUES.get(reaction, 0) # Default to 0 if somehow not found after above check
    if reaction_amount <= 0:
        logger.warning(f"Emoji '{reaction}' has a non-positive value ({reaction_amount}) configured. Ignoring.")
        return
    
    user_id = event.get("user")
    
    item = event.get("item", {})
    channel_id = item.get("channel")
    message_ts = item.get("ts")
    
    if not (user_id and channel_id and message_ts):
        logger.error("Missing required information from reaction event")
        return
    
    reaction_key = f"{user_id}-{channel_id}-{message_ts}-{reaction}"
    if reaction_key in processed_reactions:
        logger.info(f"Ignoring already processed reaction {reaction_key}")
        return
        
    processed_reactions[reaction_key] = True
    
    try:
        message_response = client.conversations_history(
            channel=channel_id,
            latest=message_ts,
            inclusive=True,
            limit=1
        )
        
        if not message_response.get("ok") or not message_response.get("messages"):
            # Check for specific not_in_channel error for reactions
            if message_response.get("error") == "not_in_channel":
                logger.warning(
                    f"Bot is not in channel {channel_id}. Cannot process reaction on message {message_ts}. "
                    f"Bot must be a member of the channel to read message history for reactions."
                )
                # Optionally, notify the reacting user that the bot needs to be in the channel.
                try:
                    im_response = client.conversations_open(users=user_id)
                    if im_response.get("ok"):
                        client.chat_postMessage(
                            channel=im_response["channel"]["id"],
                            text=f"I couldn't process your :{reaction}: reaction in <#{channel_id}> because I'm not a member of that channel. Please ask someone to add me, or react in a channel I'm in!"
                        )
                except Exception as dm_err:
                    logger.error(f"Failed to send DM to user {user_id} about not_in_channel issue: {dm_err}")
            else:
                logger.error(f"Failed to fetch message {channel_id}/{message_ts} or no messages returned: {message_response.get('error', 'Unknown error')}")
            return
        
        message = message_response["messages"][0]
        
        if "bot_id" not in message:
            logger.info("Ignoring reaction on non-bot message")
            return
        
        text = message.get("text", "")
        
        # Extract original recipient
        recipient_match = re.search(r"to <@([UW][A-Z0-9]+)>!", text)
        if not recipient_match:
            logger.info(f"Message '{text}' doesn't appear to be a {config.UNIT_NAME} giving announcement (recipient parse failed)")
            return
        recipient_id = recipient_match.group(1)

        # Extract original note from the bot's announcement message
        # Default note if parsing fails or original reason was effectively empty
        parsed_original_note = f"Reaction :{reaction}: (original reason not captured)" 
        reason_match = re.search(r"Reason: (.*)", text, re.IGNORECASE)
        
        if reason_match:
            extracted_reason = reason_match.group(1).strip()
            if extracted_reason: # Ensure the extracted reason is not empty after stripping
                parsed_original_note = extracted_reason
                logger.info(f"Extracted original note for reaction: '{parsed_original_note}'")
            else:
                logger.warning(f"Original reason was empty after 'Reason:' in bot message: '{text}'. Using default note.")
        else:
            logger.warning(f"Could not parse original reason using 'Reason: (.*)' from bot message: '{text}'. Using default note.")
        
        if user_id == recipient_id:
            logger.info(f"User {user_id} tried to react to give themselves {config.UNIT_NAME_PLURAL}")
            return
        
        # Check daily limit for the reactor - comparing against the specific reaction amount
        given_last_24h = database.get_units_given_last_24h(user_id)
        if given_last_24h + reaction_amount > config.DAILY_UNIT_LIMIT:
            remaining_units = config.DAILY_UNIT_LIMIT - given_last_24h
            try:
                im_response = client.conversations_open(users=user_id)
                if im_response and im_response.get("ok"):
                    client.chat_postMessage(
                        channel=im_response["channel"]["id"],
                        text=f"You've already given {given_last_24h} {config.UNIT_NAME_PLURAL} in the last 24 hours (limit: {config.DAILY_UNIT_LIMIT}). Your :{reaction}: reaction ({reaction_amount} points) would exceed the limit (remaining: {remaining_units})."
                    )
            except Exception as e:
                logger.error(f"Error sending limit DM to user {user_id}: {e}")
            return
            
        _complete_unit_transaction(
            client=client,
            giver_id=user_id,
            recipient_id=recipient_id,
            amount=reaction_amount, # Use the specific amount for this reaction emoji
            note=parsed_original_note, # Use the extracted (or default) original note
            original_channel_id=channel_id,
            original_message_ts=message_ts
        )
    except Exception as e:
        logger.error(f"Error processing reaction: {e}")


# @app.event("app_mention")
# def handle_app_mention(event, client, say):
#     # This handler specifically catches app mentions
#     # It's different from the @app.message() decorator which handles DMs for the reaction flow.
#     # Avoid processing message subtypes like edits/deletes or bot messages for this log.
#     if event.get("event", {}).get("subtype") is None and "bot_id" not in event.get("event", {}):
#         logger.info(f"DIAGNOSTIC: Received app mention event: {event}")

# --- Global Error Handler --- #
@app.error
def global_error_handler(error, body, logger):
    logger.exception(f"Error occurred: {error}\nBody: {body}")

# --- Start the App --- #
def main():
    logger.info(f"Starting {config.UNIT_NAME.capitalize()} Bot using Socket Mode...")
    # Explicitly print tokens right before use
    logger.debug(f"--- MAIN: Using SLACK_BOT_TOKEN='{config.SLACK_BOT_TOKEN}'")
    logger.debug(f"--- MAIN: Using SLACK_APP_TOKEN='{config.SLACK_APP_TOKEN}'")
    
    try:
        from scripts.generate_manifest import generate_manifest
        generate_manifest()
        logger.info(f"Generated manifest.yml with {config.UNIT_NAME} as the command prefix")
    except Exception as e:
        logger.error(f"Failed to generate manifest.yml: {e}")
    
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    # Add error handling for SocketModeHandler connection issues
    try:
        handler.start()
    except Exception as e:
        logger.critical(f"Failed to start SocketModeHandler: {e}")
        sys.exit(1)

# --- Diagnostic Handler for Messages --- #
@app.event("message")
def handle_message_events(body, logger):
    # This handler specifically catches messages posted in channels/DMs etc.
    # It's different from the @app.message() decorator which handles DMs for the reaction flow.
    # Avoid processing message subtypes like edits/deletes or bot messages for this log.
    if body.get("event", {}).get("subtype") is None and "bot_id" not in body.get("event", {}):
        logger.info(f"DIAGNOSTIC: Received message event: {body}")
# --- End Diagnostic Handler --- #

# @app.message() # Temporarily disable this handler
# def handle_dm_replies(message, client, say):
#     # ... (DM processing logic removed)

if __name__ == "__main__":
    main()                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                