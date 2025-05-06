# Taco Slack Bot

A simple Slack bot built with Python (`slack_bolt`) and SQLite to give and track virtual tacos within a workspace.

## Features

*   Give units: `/{unit_name}_give <amount> <@user> <note>`
*   View Stats: `/{unit_name}_stats` (Shows leaderboard)
*   View Giving History: `/{unit_name}_history [@user] [lines]`
*   View Receiving History: `/{unit_name}_received [lines]`
*   Get Help: `/{unit_name}_help`
*   Check Remaining Units: `/{unit_name}_remaining [@user]`
*   Configurable unit name (defaults to "kudos")
*   Rolling 24-hour giving limit (configurable)
*   Optional public announcement channel for unit grants

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd tacos
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Create a file named `.env` in the project root directory (use `.env.example` as a template).
    *   Add the following variables:
        ```dotenv
        # Unit Configuration (Optional)
        UNIT_NAME="kudos"  # Default is "kudos" if not specified
        UNIT_NAME_PLURAL="kudos"  # Default is UNIT_NAME + "s" if not specified
        PRIMARY_EMOJI="star-struck"
        
        # Slack API Tokens (Required for running the bot, but not for manifest generation)
        SLACK_BOT_TOKEN=xoxb-your-token  # You'll get this after creating your Slack app
        SLACK_APP_TOKEN=xapp-your-token  # You'll get this after enabling Socket Mode
        
        # Database Configuration (Optional - Defaults to kudos.db)
        # DATABASE_FILE="kudos.db"
        
        # Bot Configuration (Optional - Defaults shown)
        # DAILY_UNIT_LIMIT=5
        # UNIT_ANNOUNCE_CHANNEL="kudos-announce" # Channel name (no #) for public announcements
        # UNIT_REACTION_EMOJI="star-struck" # Emoji name (without colons) to trigger reaction flow
        ```
    *   For now, you can leave the token placeholders as they are. You'll update them after creating your Slack app.

5.  **Generate the Manifest:**
    *   Run the following command to generate a `manifest.yml` file based on your configured unit name:
        ```bash
        python3 scripts/generate_manifest.py
        ```
    *   This will create a `manifest.yml` file with the correct command names based on your configured unit name.
    *   If your unit name is not "taco" or "tacos", the manifest will include both the new unit-based commands and legacy "tacos_" commands for backward compatibility.

6.  **Configure Slack App:**
    *   Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app.
    *   Choose the option to **"Create from an app manifest"** and paste the contents of your generated `manifest.yml` file.
    *   After creating the app, you'll need to:
        *   **Enable Socket Mode:**
            *   In the left sidebar under "Settings", click on **"Socket Mode"**.
            *   Toggle the switch to **"Enable Socket Mode"**.
        *   **Generate an App-Level Token (`SLACK_APP_TOKEN`):**
            *   In the left sidebar under "Settings", click on **"Basic Information"**.
            *   Scroll down to the **"App-Level Tokens"** section.
            *   Click **"Generate Token and Scopes"**.
            *   Give your token a name (e.g., `socket-mode-token`).
            *   Add the `connections:write` scope.
            *   Click **"Generate"**.
            *   **Copy the generated token (it starts with `xapp-`)**. You will need this for the `SLACK_APP_TOKEN` in your `.env` file.
        *   **OAuth & Permissions (`SLACK_BOT_TOKEN`):**
            *   In the left sidebar under "Features", click on **"OAuth & Permissions"**.
            *   Scroll down to the **"Scopes"** section.
            *   Under **"Bot Token Scopes"**, click **"Add an OAuth Scope"** and add the following scopes:
                *   `chat:write` (to send messages as the bot)
                *   `commands` (to enable slash commands)
                *   `im:write` (to open and send direct messages)
                *   `chat:write.public` (Allows posting in public channels the bot isn't explicitly in - for announcements)
                *   `channels:read` (Used to find the announcement channel ID by name)
                *   `users:read` (To look up user IDs by display name)
            *   Scroll back to the top of the "OAuth & Permissions" page.
            *   Click **"Install to Workspace"** (or "Reinstall App" if you added scopes later).
            *   Follow the prompts to authorize the app.
            *   After installation, you will see the **"Bot User OAuth Token" (it starts with `xoxb-`)**. **Copy this token**. You will need this for the `SLACK_BOT_TOKEN` in your `.env` file.
        *   **Update your `.env` file with the real tokens you obtained.**

## Running the Bot

1.  Ensure your virtual environment is active (`source venv/bin/activate`).
2.  Make sure you have filled in your tokens in the `.env` file.
3.  Run the bot from the project's root directory:
    ```bash
    python -m src.bot
    ```
4.  The bot will connect using Socket Mode and log informational messages to the console. You should see a message like "Starting {Unit Name} Bot using Socket Mode..." and then "Bolt app is running!"

## Database

The bot uses an SQLite database file (default: `tacos.db`) created in the project root to store transaction history. This file is excluded from Git by the `.gitignore` file.            

## Testing

1.  **Install Testing Dependencies:**
    ```bash
    pip install pytest pytest-cov
    ```

2.  **Run Tests:**
    ```bash
    pytest
    ```

3.  **Manual Testing:**
    After setting up the bot in your Slack workspace:
    * Test all commands with different configurations
    * Verify emoji randomization works correctly
    * Check that all messages use the configured unit name
    * Test with different users to ensure the leaderboard and history features work correctly                                                