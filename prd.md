# Taco Bot PRD

## 1. Overview

A Slack bot to facilitate the giving and tracking of virtual "tacos" within a workspace using SQLite for persistence.

## 2. Features

### 2.1 Commands

Users will interact with the bot using the following slash commands:

1.  **/tacos_give `<amount> <@username> <note>`**
    *   **Action:** Allows the calling user (`giver`) to give a specified `amount` (positive integer) of tacos to another Slack user (`recipient`).
    *   **Arguments:**
        *   `amount`: The number of tacos to give. Must be a positive integer.
        *   `@username`: A valid Slack user mention for the recipient.
        *   `@username`: A Slack user mention for the recipient (e.g., `<@U123ABC>`, or `@displayname`). The bot will attempt to resolve `@displayname` using the `users:read` scope.
        *   `note`: A brief text note explaining the reason for giving tacos.
    *   **Validation:**
        *   The `giver` cannot be the same as the `recipient`.
        *   The `giver` must not exceed their 24h giving limit (see Constraints).
        *   `amount` must be >= 1.
    *   **Outcome:** Records transaction, sends notifications (ephemeral, DM, announcement channel).

2.  **/tacos_stats**
    *   **Action:** Displays taco statistics. Currently shows the leaderboard of users ranked by the total number of tacos they have *received*.
    *   **Arguments:** None.
    *   **Output:** A formatted message listing the top N users (e.g., top 10) and their received taco counts.
    *   **Output:** An ephemeral message listing the top N users (e.g., top 10) and their received taco counts. If the command is run in the configured `TACO_ANNOUNCE_CHANNEL`, the message is posted publicly to that channel instead.

3.  **/tacos_history `[@username] [lines]`**
    *   **Action:** Shows recent taco transaction history.
    *   **Arguments (Optional):**
        *   `[@username]`: If provided, filters history to show only transactions where the specified user was the *recipient*.
        *   `[lines]`: The maximum number of recent transactions to display (default: 10, max: 50).
    *   **Output:** A formatted message listing the requested transactions. If `@username` is omitted, shows the calling user's *giving* history. If `@username` is provided, shows the *receiving* history for that user.

4.  **/tacos_received `[lines]`**
    *   **Action:** Shows the calling user's recent taco *receiving* history.
    *   **Arguments (Optional):**
        *   `lines`: The maximum number of recent transactions to display (default: 10, max: 50).
    *   **Output:** A formatted message listing the transactions where the calling user was the recipient.

5.  **/tacos_help**
    *   **Action:** Displays a help message detailing all available commands and rules.
    *   **Arguments:** None.
    *   **Output:** Sends the help text as a Direct Message to the calling user.
    *   **Output:** An ephemeral message (visible only to the calling user) in the channel where the command was run.

6.  **/tacos_remaining `[@username]`**
    *   **Action:** Checks how many tacos the specified user (or the calling user, if omitted) can still give in the next 24 hours.
    *   **Arguments (Optional):**
        *   `@username`: The user whose remaining limit should be checked.
    *   **Output:** An ephemeral message (visible only to the calling user) stating the remaining taco count.

### 2.2 Constraints & Rules

*   **Giving Limit:** A user can *give* a maximum of **5** tacos within any **rolling 24-hour period**. This limit applies to the total number of tacos given by a user via the `/tacos_give` command.
*   **No Self-Giving:** A user cannot use the `/tacos_give` command to give tacos to themselves.
*   **Non-Transferable:** Tacos are received as points/recognition. They cannot be transferred or spent by the recipient. The system only tracks giving and receiving.
*   **Database:** All transaction data must be stored persistently in an SQLite database file (e.g., `tacos.db`).
*   **Data Storage:** The database should store at least:
    *   Transaction ID (Primary Key)
    *   Giver User ID (Slack User ID)
    *   Recipient User ID (Slack User ID)
    *   Amount (Integer)
    *   Note (Text)
    *   Timestamp (e.g., ISO 8601 string or Unix timestamp)
    *   Source Channel ID (Slack Channel ID where transaction originated)

## 3. Technical Requirements

*   **Language:** Python
*   **Framework/Libraries:**
    *   Slack SDK (`slack_bolt` or similar) for Slack integration.
    *   `sqlite3` standard library module for database interaction.
*   **Configuration:** Bot tokens, database file path, daily limit, and announcement channel name should be configurable (e.g., via environment variables or a config file).

## 4. Future Considerations (Out of Scope for v1)

*   Weekly/Monthly Leaderboards
*   Customizable Taco Emoji/Name
*   Admin commands (e.g., adjust balances, reset limits)
*   More detailed user stats (`/taco stats [@username]`) 