import logging
import re
import datetime # Added for timestamp formatting
from slack_sdk.errors import SlackApiError
from . import config, database
from slack_sdk.web import WebClient

logger = logging.getLogger(__name__)

# --- User ID Cache --- #
# Simple in-memory cache: { name_lower: user_id }
# Names could be display_name or real_name (lowercase)
user_cache = {}
# Limit cache size to prevent unbounded growth (optional)
MAX_CACHE_SIZE = 1000

USER_MENTION_REGEX = r"<@([UW][A-Z0-9]+)(?:\|[^>]+)?>"

def parse_user_mention(mention_text):
    """Extracts the user ID from a Slack user mention."""
    match = re.match(USER_MENTION_REGEX, mention_text)
    if match:
        return match.group(1)
    return None

def find_user_id_by_name(client: WebClient, name_to_find: str, logger: logging.Logger) -> str | None:
    """Finds a user ID by display name or real name using users.list, with basic caching."""
    name_lower = name_to_find.lower()

    # 1. Check cache
    if name_lower in user_cache:
        logger.debug(f"Cache hit for user name: {name_lower}")
        return user_cache[name_lower]

    logger.debug(f"Cache miss for user name: {name_lower}. Querying users.list API.")
    found_user_id = None
    try:
        # 2. Call users.list with pagination
        for page in client.users_list(limit=200): # Adjust limit as needed
            if found_user_id: break # Stop if found in a previous page
            for user in page.get("members", []):
                if user.get("deleted") or user.get("is_bot") or user.get("is_app_user"):
                    continue # Skip deleted/bot/app users

                profile = user.get("profile", {})
                display_name = profile.get("display_name_normalized") or profile.get("display_name", "")
                real_name = profile.get("real_name_normalized") or profile.get("real_name", "")
                user_name = user.get("name", "") # Get the username

                # --- DEBUG LOGGING --- #
                logger.debug(f"Checking user {user.get('id')} against '{name_lower}'. Display='{display_name.lower()}', Real='{real_name.lower()}', Username='{user_name.lower()}'")
                # --- END DEBUG LOGGING --- #

                # Match against display name, real name, OR username (case-insensitive)
                if name_lower == display_name.lower() or \
                   name_lower == real_name.lower() or \
                   name_lower == user_name.lower():
                    if found_user_id is not None:
                        # Ambiguous match!
                        logger.warning(f"Ambiguous user name '{name_to_find}'. Matched multiple users: {found_user_id} and {user.get('id')}. Cannot resolve.")
                        return None # Indicate ambiguity
                    found_user_id = user.get("id")
                    # Don't break yet, continue checking current page for duplicates

        # 3. Update cache if found and cache is not full
        if found_user_id and len(user_cache) < MAX_CACHE_SIZE:
            user_cache[name_lower] = found_user_id
            logger.debug(f"Cached user ID {found_user_id} for name {name_lower}")
        elif found_user_id:
             logger.warning("User cache full. Not caching new user.")

        return found_user_id

    except SlackApiError as e:
        if e.response["error"] == "missing_scope" and "users:read" in str(e):
            logger.error("Missing 'users:read' scope to look up users by name.")
        else:
            logger.error(f"Error calling users.list: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error looking up user by name '{name_to_find}': {e}")
        return None

def get_user_id_from_mention(client: WebClient, mention_text: str, logger: logging.Logger) -> str | None:
    """Attempts to get a User ID from mention text, handling <@ID> and @displayname formats."""
    # 1. Try parsing the standard <@ID> format first
    user_id = parse_user_mention(mention_text)
    if user_id:
        return user_id

    # 2. If not <@ID>, check if it looks like @displayname
    if mention_text.startswith("@"):
        name_part = mention_text[1:] # Remove the leading @
        if name_part: # Ensure there's actually a name after @
            # Attempt to find user by display name/real name via API
            return find_user_id_by_name(client, name_part, logger)

    # 3. If neither format matches or lookup fails
    return None

def handle_help_command(ack, body, client):
    """Handles the /tacos_help command by sending an ephemeral message."""
    ack() # Acknowledge the command immediately
    user_id = body["user_id"]
    channel_id = body["channel_id"]
    # client = say.client # Get the client object from the say utility context - Now passed directly

    emoji = get_emoji()
    unit_name = config.UNIT_NAME
    unit_name_plural = config.UNIT_NAME_PLURAL
    unit_name_cap = unit_name.capitalize()
    unit_name_plural_cap = unit_name_plural.capitalize()
    
    help_text = f"""
:{emoji}: *{unit_name_cap} Bot Help* :{emoji}:

Here are the available commands:

* `/tacos_give <amount> <@user> <note>`
  Give a specific number of {unit_name_plural} to someone with a reason. Uses the standard `@mention` (e.g. `<@U123>`) or attempts to look up `@displayname`.
  Example: `/tacos_give 3 @allenday great presentation!`

* `/tacos_stats`
  Show {unit_name} statistics (currently shows the leaderboard).

* `/tacos_history [@user] [lines]`
  Show recent {unit_name} *giving* history. Shows your giving history by default.
  If you specify `@user`, it shows the history of {unit_name_plural} *received* by that user.
  `[lines]` is optional (default: {config.DEFAULT_HISTORY_LINES}, max: 50).
  Example: `/tacos_history @allenday 5`
  Example: `/tacos_history 20`

* `/tacos_received [lines]`
  Show your recent {unit_name} *receiving* history.
  `[lines]` is optional (default: {config.DEFAULT_HISTORY_LINES}, max: 50).
  Example: `/tacos_received 15`

* `/tacos_remaining [@user]`
  Check how many {unit_name_plural} you (or `@user`, if specified) have left to give in the next 24 hours. Responds privately.

* `/tacos_help`
  Show this help message (visible only to you).

*Rules:*
- You can give a maximum of {config.DAILY_TACO_LIMIT} {unit_name_plural} per 24 hours.
- You cannot give {unit_name_plural} to yourself.
"""

    try:
        # Send ephemeral message
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=help_text
        )
    except Exception as e:
        logger.error(f"Error sending ephemeral help message to user {user_id} in channel {channel_id}: {e}")

def handle_remaining_command(ack, body, client):
    """Handles the /tacos_remaining command, checking tacos left to give."""
    ack()
    text = body.get("text", "").strip()
    calling_user_id = body["user_id"]
    channel_id = body["channel_id"]

    target_user_id = calling_user_id # Default to self
    target_user_mention = f"<@{calling_user_id}>"

    # Check if a specific user was mentioned
    if text:
        mentioned_user_id = parse_user_mention(text)
        if mentioned_user_id:
            target_user_id = mentioned_user_id
            target_user_mention = text # Keep the original mention text
        else:
            try:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=calling_user_id,
                    text=f"Invalid user format: `{text}`. Please use the @mention format to check another user, or no argument to check yourself."
                )
            except Exception as e:
                logger.error(f"Error sending ephemeral message for invalid user in remaining command: {e}")
            return

    # Get tacos given in the last 24h
    given_last_24h = database.get_tacos_given_last_24h(target_user_id)
    remaining_tacos = max(0, config.DAILY_TACO_LIMIT - given_last_24h)

    # Format the response message
    emoji = get_emoji()
    if target_user_id == calling_user_id:
        response_text = f"You have {remaining_tacos} :{emoji}: remaining to give in the next 24 hours (out of {config.DAILY_TACO_LIMIT})."
    else:
        response_text = f"{target_user_mention} has {remaining_tacos} :{emoji}: remaining to give in the next 24 hours (out of {config.DAILY_TACO_LIMIT})."

    # Send the ephemeral response
    try:
        client.chat_postEphemeral(
            channel=channel_id,
            user=calling_user_id,
            text=response_text
        )
    except Exception as e:
        logger.error(f"Error sending ephemeral message for remaining command: {e}") 

def handle_stats_command(ack, body, client):
    """Handles the /tacos_stats command. Shows leaderboard publicly if in announce channel, otherwise ephemerally."""
    ack()
    user_id = body["user_id"]
    channel_id = body["channel_id"]
    # client = say.client # Now passed directly

    leaders = database.get_leaderboard()

    if not leaders:
        # Send ephemeral error message
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"The leaderboard is empty! Start giving some :{get_emoji()}:!")
        except Exception as e:
            logger.error(f"Error sending ephemeral leaderboard empty message: {e}")
        return

    emoji = get_emoji()
    message = f":{emoji}: *{config.UNIT_NAME.capitalize()} Leaderboard* :{emoji}:\n\n"
    for i, leader in enumerate(leaders):
        message += f"{i+1}. <@{leader['recipient_id']}>: {leader['total_received']} {config.UNIT_NAME_PLURAL}\n"

    # Determine if we are in the announcement channel
    post_publicly = False
    announce_channel_name = config.TACO_ANNOUNCE_CHANNEL
    if announce_channel_name:
        try:
            # Look up channel info to compare IDs
            # Requires channels:read scope for public channels
            channel_info = client.conversations_info(channel=channel_id)
            if channel_info.get("ok") and channel_info.get("channel", {}).get("name") == announce_channel_name:
                post_publicly = True
        except SlackApiError as e:
            # Handle cases where bot isn't in the channel or lacks permissions gracefully
            if e.response["error"] == "channel_not_found" or e.response["error"] == "method_not_supported_for_channel_type":
                logger.debug(f"Cannot get info for channel {channel_id} to check if it's the announcement channel.")
            elif e.response["error"] == "missing_scope" and "channels:read" in str(e):
                logger.warning("Missing 'channels:read' scope to check if current channel is the announcement channel. Posting ephemerally.")
            else:
                logger.error(f"Error checking channel info for stats command: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking channel info for stats command: {e}")

    # Post the message
    try:
        if post_publicly:
            logger.info(f"Posting stats publicly in announcement channel {channel_id}")
            # Use say() utility which is simpler when client is available implicitly via context
            # Need to re-fetch 'say' if we use this pattern broadly or restructure
            # For now, using client.chat_postMessage directly
            client.chat_postMessage(channel=channel_id, text=message)
        else:
            logger.info(f"Posting stats ephemerally to user {user_id} in channel {channel_id}")
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=message
            )
    except Exception as e:
        logger.error(f"Error posting stats message (publicly: {post_publicly}): {e}")

def handle_history_command(ack, body, say, client):
    """Handles the /tacos_history command by sending an ephemeral message."""
    ack()
    text = body.get("text", "").strip()
    calling_user_id = body["user_id"]
    channel_id = body["channel_id"] # Get channel for ephemeral message
    # thread_ts = body.get("thread_ts") # Ephemeral messages don't support threads

    parts = text.split()

    lines = config.DEFAULT_HISTORY_LINES
    recipient_filter_id = None
    # Default: filter history by the user who invoked the command (giver)
    giver_filter_id = calling_user_id

    arg1 = parts[0] if parts else None
    arg2 = parts[1] if len(parts) > 1 else None

    # Parse arguments: /taco history [@user] [lines] or /taco history [lines]
    # If @user is present, we show history where they are the RECIPIENT.
    # Otherwise, we show history where the caller is the GIVER.
    if arg1:
        maybe_user = parse_user_mention(arg1)
        if maybe_user:
            # First argument is a user: filter by recipient
            recipient_filter_id = maybe_user
            giver_filter_id = None # Clear giver filter
            if arg2 and arg2.isdigit():
                try:
                    lines = int(arg2)
                except ValueError:
                    # Invalid number, ignore, use default lines
                    pass
            elif arg2:
                 # Use ephemeral error
                 error_text = f":warning: Invalid argument: `{arg2}`. Expected number of lines after @user. Using default {config.DEFAULT_HISTORY_LINES} lines."
                 try:
                     client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=error_text)
                 except Exception as e:
                    logger.error(f"Error sending ephemeral error message: {e}")
                 return # Stop processing if error
        elif arg1.isdigit():
            # First argument is lines: caller is giver
            try:
                lines = int(arg1)
            except ValueError:
                 # Use ephemeral error
                 error_text = f":warning: Invalid argument: `{arg1}`. Expected @user or number of lines. Showing your giving history."
                 try:
                     client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=error_text)
                 except Exception as e:
                    logger.error(f"Error sending ephemeral error message: {e}")
                 return # Stop processing
            if arg2:
                 # Use ephemeral warning
                 warning_text = f":warning: Invalid argument: `{arg2}`. Only expecting number of lines here. Ignoring extra argument."
                 try:
                     client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=warning_text)
                 except Exception as e:
                     logger.error(f"Error sending ephemeral warning message: {e}")
                 # Don't return, just ignore arg2
        else:
             # Use ephemeral error
             error_text = f":warning: Invalid argument: `{arg1}`. Expected @user or number of lines. Showing your giving history."
             try:
                 client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=error_text)
             except Exception as e:
                 logger.error(f"Error sending ephemeral error message: {e}")
             return # Stop processing

    # Ensure lines is within reasonable bounds (e.g., 1-50)
    lines = max(1, min(lines, 50))

    history = database.get_history(lines=lines, recipient_id=recipient_filter_id, giver_id=giver_filter_id)

    if not history:
        # Use ephemeral message for errors
        error_text = ""
        if recipient_filter_id:
            error_text = f":warning: No {config.UNIT_NAME} history found for <@{recipient_filter_id}>."
        elif giver_filter_id:
            error_text = f":warning: You haven't given any {config.UNIT_NAME_PLURAL} recently!"
        else: # Should not happen with current logic, but for completeness
            error_text = f":warning: No {config.UNIT_NAME} history found."

        try:
            client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=error_text)
        except Exception as e:
            logger.error(f"Error sending ephemeral 'no history' message: {e}")
        return

    # Build the success message
    title = ""
    emoji = get_emoji()
    unit_name_cap = config.UNIT_NAME.capitalize()
    if recipient_filter_id:
        title = f":{emoji}: *Recent {unit_name_cap} History for <@{recipient_filter_id}>* (Received) :{emoji}:\n\n"
    elif giver_filter_id:
        title = f":{emoji}: *Your Recent {unit_name_cap} Giving History* :{emoji}:\n\n"
    else:
        # Fallback message, should ideally not be reached with current logic
        title = f":{emoji}: *Recent {unit_name_cap} History* :{emoji}:\n\n"

    message_lines = []
    for entry in history:
        ts_str = entry['timestamp']
        try:
            # Attempt to parse ISO format timestamp for cleaner formatting
            ts_dt = datetime.datetime.fromisoformat(ts_str.replace(' ', 'T'))
            # Format like: Aug 07 15:30
            ts_formatted = ts_dt.strftime('%b %d %H:%M')
        except:
             # Fallback to simpler string splitting if parsing fails
             ts_formatted = ts_str.split('.')[0].replace('T', ' ') if isinstance(ts_str, str) else str(ts_str)

        # Include source channel if available
        source_channel_text = f" in <#{entry['source_channel_id']}>" if entry['source_channel_id'] else ""

        # Adjust message based on whether it's giver or recipient view
        if recipient_filter_id:
             message_lines.append(f"- `[{ts_formatted}]` Received {entry['amount']} from <@{entry['giver_id']}>{source_channel_text}: _{entry['note']}_ ")
        else: # Giver's view (default)
             message_lines.append(f"- `[{ts_formatted}]` Gave {entry['amount']} to <@{entry['recipient_id']}>{source_channel_text}: _{entry['note']}_ ")

    # Join message lines and send ephemerally
    success_text = title + "\n".join(message_lines)
    try:
        client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=success_text)
    except Exception as e:
        logger.error(f"Error sending ephemeral history message: {e}")

def handle_received_command(ack, body, say, client):
    """Handles the /taco received command by sending an ephemeral message."""
    ack()
    text = body.get("text", "").strip()
    calling_user_id = body["user_id"]
    channel_id = body["channel_id"] # Get channel for ephemeral message
    # thread_ts = body.get("thread_ts") # Ephemeral messages don't support threads

    parts = text.split()

    lines = config.DEFAULT_HISTORY_LINES

    # Parse arguments: /taco received [lines]
    if parts:
        arg1 = parts[0]
        if arg1.isdigit():
            try:
                lines = int(arg1)
            except ValueError:
                # Use ephemeral error
                error_text = f":warning: Invalid argument: `{arg1}`. Expected number of lines. Using default {config.DEFAULT_HISTORY_LINES}."
                try:
                    client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=error_text)
                except Exception as e:
                    logger.error(f"Error sending ephemeral error message: {e}")
                return # Stop processing
        else:
            # Use ephemeral error
            error_text = f":warning: Invalid argument: `{arg1}`. Expected number of lines. Using default {config.DEFAULT_HISTORY_LINES}."
            try:
                client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=error_text)
            except Exception as e:
                logger.error(f"Error sending ephemeral error message: {e}")
            return # Stop processing
        if len(parts) > 1:
            # Use ephemeral warning (don't return)
            warning_text = f":warning: Too many arguments. Only expecting optional number of lines. Ignoring extra arguments."
            try:
                client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=warning_text)
            except Exception as e:
                logger.error(f"Error sending ephemeral warning message: {e}")
            # Don't return, just ignore extra args

    # Ensure lines is within reasonable bounds (e.g., 1-50)
    lines = max(1, min(lines, 50))

    # Fetch history where the calling user is the recipient
    history = database.get_history(lines=lines, recipient_id=calling_user_id, giver_id=None)

    if not history:
        # Use ephemeral message
        error_text = f":warning: You haven't received any {config.UNIT_NAME_PLURAL} recently!"
        try:
            client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=error_text)
        except Exception as e:
            logger.error(f"Error sending ephemeral 'no history' message: {e}")
        return

    # Build the success message
    emoji = get_emoji()
    title = f":{emoji}: *Your Recent {config.UNIT_NAME.capitalize()} Receiving History* :{emoji}:\\n\\n"

    message_lines = []
    for entry in history:
        ts_str = entry['timestamp']
        try:
            ts_dt = datetime.datetime.fromisoformat(ts_str.replace(' ', 'T'))
            ts_formatted = ts_dt.strftime('%b %d %H:%M')
        except:
            ts_formatted = ts_str.split('.')[0].replace('T', ' ') if isinstance(ts_str, str) else str(ts_str)

        source_channel_text = f" in <#{entry['source_channel_id']}>" if entry['source_channel_id'] else ""

        message_lines.append(f"- `[{ts_formatted}]` Received {entry['amount']} from <@{entry['giver_id']}>{source_channel_text}: _{entry['note']}_")

    # Join message lines and send ephemerally
    success_text = title + "\\n".join(message_lines)
    try:
        client.chat_postEphemeral(channel=channel_id, user=calling_user_id, text=success_text)
    except Exception as e:
         logger.error(f"Error sending ephemeral received history message: {e}")

def handle_give_command(ack, body, say, client):
    """Handles the /tacos_give command."""
    ack()
    text = body.get("text", "").strip()
    giver_id = body["user_id"]
    channel_id = body["channel_id"] # Get source channel for DB logging

    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        # Send ephemeral error
        error_text = f":warning: Usage: `/tacos_give <amount> <@username> <note>`"
        try:
            client.chat_postEphemeral(channel=channel_id, user=giver_id, text=error_text)
        except Exception as e:
            logger.error(f"Error sending ephemeral usage error: {e}")
        return

    amount_str, recipient_mention, note = parts

    # Validate amount
    try:
        amount = int(amount_str)
        if amount <= 0:
            # Send ephemeral error
            error_text = ":warning: Amount must be a positive whole number."
            try:
                client.chat_postEphemeral(channel=channel_id, user=giver_id, text=error_text)
            except Exception as e:
                logger.error(f"Error sending ephemeral amount error: {e}")
            return
    except ValueError:
        # Send ephemeral error
        error_text = f":warning: Invalid amount: `{amount_str}`. Please provide a positive whole number."
        try:
            client.chat_postEphemeral(channel=channel_id, user=giver_id, text=error_text)
        except Exception as e:
            logger.error(f"Error sending ephemeral invalid amount error: {e}")
        return

    # --- Validate recipient using the new lookup function ---
    recipient_id = get_user_id_from_mention(client, recipient_mention, logger)

    if not recipient_id:
        # Updated error message for lookup failure - Send ephemeral error
        error_text = f":warning: Could not find a unique user matching `{recipient_mention}`. Please use the standard `@mention` format (selecting the user from the popup) or ensure the display name is correct."
        try:
            client.chat_postEphemeral(channel=channel_id, user=giver_id, text=error_text)
        except Exception as e:
            logger.error(f"Error sending ephemeral user lookup error: {e}")
        return

    # --- Business Logic Checks ---
    # 1. No self-giving
    if giver_id == recipient_id:
        # Send ephemeral error
        error_text = ":warning: You can't give tacos to yourself! Sharing is caring."
        try:
            client.chat_postEphemeral(channel=channel_id, user=giver_id, text=error_text)
        except Exception as e:
            logger.error(f"Error sending ephemeral self-give error: {e}")
        return

    # 2. Check daily limit (rolling 24h)
    try:
        given_last_24h = database.get_tacos_given_last_24h(giver_id)
        if given_last_24h + amount > config.DAILY_TACO_LIMIT:
            remaining = config.DAILY_TACO_LIMIT - given_last_24h
            # Send ephemeral error
            error_text = f":warning: You have given {given_last_24h} tacos in the last 24 hours. You can only give {remaining} more."
            try:
                client.chat_postEphemeral(channel=channel_id, user=giver_id, text=error_text)
            except Exception as e:
                logger.error(f"Error sending ephemeral limit error: {e}")
            return
    except Exception as e:
        logger.error(f"Error checking daily limit for {giver_id}: {e}")
        # Send ephemeral error
        error_text = ":warning: There was an internal error checking your taco limit. Please try again later."
        try:
            client.chat_postEphemeral(channel=channel_id, user=giver_id, text=error_text)
        except Exception as e:
            logger.error(f"Error sending ephemeral internal limit check error: {e}")
        return

    # --- Add transaction ---
    try:
        success = database.add_transaction(
            giver_id=giver_id,
            recipient_id=recipient_id,
            amount=amount,
            note=note,
            source_channel_id=channel_id # Pass channel ID
        )
    except Exception as e:
        logger.error(f"Error adding transaction to database: {e}")
        success = False

    if success:
        # --- Success Notifications --- #
        emoji = get_emoji()  # Get random emoji from configured list

        # Notify giver (ephemeral in original channel - should work if previous validation passed)
        giver_success_text = f"You gave {amount} :{emoji}: to <@{recipient_id}>! Reason: {note}"
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=giver_id,
                text=giver_success_text
            )
        except SlackApiError as e:
            # Log error, but don't stop other notifications if ephemeral fails
            logger.error(f"Error sending ephemeral confirmation to giver {giver_id} in channel {channel_id}: {e}")

        # Notify recipient (DM)
        try:
            recipient_text = f"You received {amount} :{emoji}: from <@{giver_id}>! Reason: {note}"
            im_response = client.conversations_open(users=recipient_id)
            if im_response and im_response.get("ok"):
                im_channel = im_response["channel"]["id"]
                client.chat_postMessage(
                    channel=im_channel,
                    text=recipient_text
                )
            else:
                 logger.error(f"Could not open IM channel for recipient {recipient_id}: {im_response.get('error')}")
        except SlackApiError as e:
            logger.error(f"Error sending DM notification to recipient {recipient_id}: {e}")
        except Exception as e:
             logger.error(f"Unexpected error opening IM or sending DM to {recipient_id}: {e}")

        # --- Announcements --- #
        unit_word = config.UNIT_NAME if amount == 1 else config.UNIT_NAME_PLURAL
        public_text = f":{emoji}: <@{giver_id}> gave {amount} {unit_word} to <@{recipient_id}>! Reason: {note}"

        # 1. Announce in original channel
        try:
            # Post publicly in the channel where the command was run
            client.chat_postMessage(
                channel=channel_id,
                text=public_text
            )
        except SlackApiError as e:
             logger.error(f"Error posting public message to original channel {channel_id}: {e}")
        except Exception as e:
             logger.error(f"Unexpected error posting public message to original channel {channel_id}: {e}")

        # 2. Announce in configured channel (if different from source)
        announce_channel_name = config.TACO_ANNOUNCE_CHANNEL
        if announce_channel_name:
            try:
                # Look up the source channel name for comparison (requires channels:read)
                is_announce_channel = False
                try:
                    # Need client object here - assumes handle_give_command has access
                    channel_info = client.conversations_info(channel=channel_id)
                    if channel_info.get("ok") and channel_info.get("channel", {}).get("name") == announce_channel_name:
                        is_announce_channel = True
                except SlackApiError as e:
                    logger.warning(f"Could not verify if source channel {channel_id} is announcement channel ({e.response['error']}). Assuming it is not.")
                except Exception as e:
                     logger.warning(f"Unexpected error verifying source channel {channel_id}: {e}")

                if not is_announce_channel:
                    unit_word = config.UNIT_NAME if amount == 1 else config.UNIT_NAME_PLURAL
                    public_text = f":{emoji}: <@{giver_id}> gave {amount} {unit_word} to <@{recipient_id}>! Reason: {note}"
                    # Post by name - requires chat:write.public if bot isn't in channel
                    client.chat_postMessage(
                        channel=f"#{announce_channel_name}",
                        text=public_text
                    )
                else:
                    logger.info("Skipping announcement post because command was run in the announcement channel.")
            except SlackApiError as e:
                logger.error(f"Error posting to announcement channel #{announce_channel_name}: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error posting to announcement channel #{announce_channel_name}: {e}")

    else:
        # General failure adding transaction - Send ephemeral error
        error_text = ":warning: Sorry, there was an internal error recording your taco transaction. Please try again later."
        try:
            client.chat_postEphemeral(channel=channel_id, user=giver_id, text=error_text)
        except Exception as e:
            logger.error(f"Error sending ephemeral transaction failure error: {e}")

def _send_error_dm(client, user_id, text, logger):
    """Helper function to send an error message via DM."""
    try:
        im_response = client.conversations_open(users=user_id)
        if im_response and im_response.get("ok"):
            dm_channel_id = im_response["channel"]["id"]
            client.chat_postMessage(channel=dm_channel_id, text=f":warning: Error: {text}")
        else:
            logger.error(f"Could not open IM channel for user {user_id} to send error: {im_response.get('error')}")
    except Exception as e:
        logger.error(f"Error sending error DM to user {user_id}: {e}")

import random  # Add at the top of the file if not already imported

def get_emoji():
    """Returns a random emoji from the configured emojis. Primary emoji has higher probability."""
    if random.random() < 0.7:
        return config.PRIMARY_EMOJI
    else:
        return random.choice(config.ALTERNATE_EMOJIS)

# ... (rest of the command handlers: handle_stats_command, handle_history_command, handle_received_command, handle_help_command, handle_remaining_command)                            