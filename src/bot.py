import logging
import sys
import datetime # Added for timestamp formatting in completion message
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError # Added

# Project imports
from . import config, database, commands

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
# reaction_flows = {}

# --- Helper Function for Transaction Completion --- #
# def _complete_taco_transaction(client, giver_id, recipient_id, amount, note, original_channel_id, original_message_ts):
#     """Handles the final steps: DB insert, notifications, announcements (handles threads)."""
#     success = database.add_transaction(
#         giver_id=giver_id,
#         recipient_id=recipient_id,
#         amount=amount,
#         note=note,
#         source_channel_id=original_channel_id
#     )
#     if not success:
#         try:
#             # Notify giver in DM about the failure
#             im_response = client.conversations_open(users=giver_id)
#             if im_response and im_response.get("ok"):
#                 client.chat_postMessage(
#                     channel=im_response["channel"]["id"],
#                     text="Sorry, there was an error recording your taco transaction. Please try again."
#                 )
#         except Exception as e:
#              logger.error(f"Failed to notify giver {giver_id} about transaction failure: {e}")
#         return False # Indicate failure
#
#     # Transaction added successfully, proceed with notifications
#     taco_word = "taco" if amount == 1 else "tacos"
#     # Use config.TACO_REACTION_EMOJI here if needed, or revert to static :taco:
#     emoji = getattr(config, 'TACO_REACTION_EMOJI', 'taco') # Safely get emoji
#     completion_text = f"You gave {amount} :{emoji}: to <@{recipient_id}>! Reason: {note}"
#     recipient_text = f"You received {amount} :{emoji}: from <@{giver_id}>! Reason: {note}"
#     public_text = f":{emoji}: <@{giver_id}> gave {amount} {taco_word} to <@{recipient_id}>! Reason: {note}"
#
#     # 1. Notify giver (in DM, since reaction flow happens there)
#     try:
#         im_response = client.conversations_open(users=giver_id)
#         if im_response and im_response.get("ok"):
#             client.chat_postMessage(
#                 channel=im_response["channel"]["id"],
#                 text=completion_text
#             )
#     except Exception as e:
#         logger.error(f"Error sending completion DM to giver {giver_id}: {e}")
#
#     # 2. Notify recipient (DM)
#     try:
#         im_response = client.conversations_open(users=recipient_id)
#         if im_response and im_response.get("ok"):
#             client.chat_postMessage(
#                 channel=im_response["channel"]["id"],
#                 text=recipient_text
#             )
#         else:
#              logger.error(f"Could not open IM channel for recipient {recipient_id}: {im_response.get('error')}")
#     except Exception as e:
#         logger.error(f"Error sending DM notification to recipient {recipient_id}: {e}")
#
#     # 3. Announce in original channel (potentially in thread)
#     try:
#         client.chat_postMessage(
#             channel=original_channel_id,
#             text=public_text,
#             thread_ts=original_message_ts # Reply in thread if it originated there
#         )
#     except SlackApiError as e:
#         logger.error(f"Error posting public message to original channel {original_channel_id} (ts: {original_message_ts}): {e}")
#
#     # 4. Announce in central tacos channel (if different and configured)
#     announce_channel_name = config.TACO_ANNOUNCE_CHANNEL
#     if announce_channel_name:
#         # Get channel ID for comparison (more reliable than name)
#         try:
#             # Find the announcement channel ID (requires channels:read scope)
#             announce_channel_id = None
#             for page in client.conversations_list(types="public_channel", limit=200):
#                 for channel in page["channels"]:
#                     if channel["name"] == announce_channel_name:
#                         announce_channel_id = channel["id"]
#                         break
#                 if announce_channel_id:
#                     break
#
#             if announce_channel_id and announce_channel_id != original_channel_id:
#                 client.chat_postMessage(
#                     channel=announce_channel_id, # Use channel ID
#                     text=public_text
#                     # Note: We DON'T post to the thread in the announcement channel,
#                     # just the main channel announcement.
#                 )
#             elif not announce_channel_id:
#                  logger.warning(f"Announcement channel '#{announce_channel_name}' not found.")
#
#         except SlackApiError as e:
#             if e.response["error"] == "missing_scope" and "channels:read" in str(e):
#                 logger.warning("Missing 'channels:read' scope to look up announcement channel ID by name. Cannot post announcement.")
#             else:
#                 logger.error(f"Error posting to announcement channel #{announce_channel_name}: {e}")
#         except Exception as e:
#              logger.error(f"Unexpected error looking up or posting to announcement channel #{announce_channel_name}: {e}")
#
#     return True # Indicate success


# --- Register Command Handlers --- #

@app.command("/tacos_give")
def handle_tacos_command(ack, body, say, client):
    text = body.get("text", "").strip()
    logger.info(f"Received /tacos command: {text}")

    # Assume /tacos is always for giving
    commands.handle_give_command(ack, body, say, client)

@app.command("/tacos_stats")
def handle_stats_slash_command(ack, body, client):
    logger.info("Received /tacos_stats command")
    # Body text is ignored for stats/leaderboard
    commands.handle_stats_command(ack, body, client)

@app.command("/tacos_history")
def handle_history_slash_command(ack, body, say):
    logger.info(f"Received /tacos_history command: {body.get('text')}")
    # Pass the text directly to the handler (it expects args like [@user] [lines])
    commands.handle_history_command(ack, body, say)

@app.command("/tacos_received")
def handle_received_slash_command(ack, body, say):
    logger.info(f"Received /tacos_received command: {body.get('text')}")
    # Pass the text directly to the handler (it expects args like [lines])
    commands.handle_received_command(ack, body, say)

@app.command("/tacos_help")
def handle_help_slash_command(ack, body, client):
    logger.info("Received /tacos_help command")
    # Body text is ignored for help
    commands.handle_help_command(ack, body, client) # Pass client directly

@app.command("/tacos_remaining")
def handle_remaining_slash_command(ack, body, client):
    logger.info(f"Received /tacos_remaining command: {body.get('text')}")
    commands.handle_remaining_command(ack, body, client)

# --- Event Handlers --- #

# @app.event("reaction_added")
# def handle_reaction_added(event, client, say):
#     # SIMPLIFIED FOR DIAGNOSTICS
#     logger.info(f"*** DIAGNOSTIC: handle_reaction_added function was called! Event: {event}")
#     # End of simplified handler

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
    logger.info("Starting Taco Bot using Socket Mode...")
    # Explicitly print tokens right before use
    logger.debug(f"--- MAIN: Using SLACK_BOT_TOKEN='{config.SLACK_BOT_TOKEN}'")
    logger.debug(f"--- MAIN: Using SLACK_APP_TOKEN='{config.SLACK_APP_TOKEN}'")
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    # Add error handling for SocketModeHandler connection issues
    try:
        handler.start()
    except Exception as e:
        logger.critical(f"Failed to start SocketModeHandler: {e}")
        sys.exit(1)

# --- Diagnostic Handler for Messages --- #
# @app.event("message")
# def handle_message_events(body, logger):
#     # This handler specifically catches messages posted in channels/DMs etc.
#     # It's different from the @app.message() decorator which handles DMs for the reaction flow.
#     # Avoid processing message subtypes like edits/deletes or bot messages for this log.
#     if body.get("event", {}).get("subtype") is None and "bot_id" not in body.get("event", {}):
#         logger.info(f"DIAGNOSTIC: Received message event: {body}")
# --- End Diagnostic Handler --- #

# @app.message() # Temporarily disable this handler
# def handle_dm_replies(message, client, say):
#     # ... (DM processing logic removed)

if __name__ == "__main__":
    main() 