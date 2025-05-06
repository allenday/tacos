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

4.  **Configure Slack App:**
    *   Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app or use an existing one.
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
            *   _(Optional but recommended)_ `users:read` (to potentially retrieve user details later)
        *   Scroll back to the top of the "OAuth & Permissions" page.
        *   Click **"Install to Workspace"** (or "Reinstall App" if you added scopes later).
        *   Follow the prompts to authorize the app.
        *   After installation, you will see the **"Bot User OAuth Token" (it starts with `xoxb-`)**. **Copy this token**. You will need this for the `SLACK_BOT_TOKEN` in your `.env` file.
    *   **Slash Commands:**
        *   Instead of manually creating slash commands, use the generated `manifest.yml` file:
            *   In the left sidebar under "Features", click on **"App Manifest"**.
            *   Click on **"Update from manifest"**.
            *   Paste the contents of the generated `manifest.yml` file.
            *   Click **"Save Changes"**.
            
        *   Alternatively, you can manually create the commands with your chosen unit name:
            *   Command: `/{unit_name}_give` (Suggest Description: `Give {unit_name_plural} to a user. Usage: /{unit_name}_give <amount> <@user> <note>`)
            *   Command: `/{unit_name}_stats` (Suggest Description: `Show {unit_name} statistics (leaderboard)`)
            *   Command: `/{unit_name}_history` (Suggest Description: `Show {unit_name} giving/receiving history. Usage: [@user] [lines]`)
            *   Command: `/{unit_name}_received` (Suggest Description: `Show your {unit_name} receiving history. Usage: [lines]`)
            *   Command: `/{unit_name}_help` (Suggest Description: `Show help information for the {unit_name_cap} Bot`)
            *   Command: `/{unit_name}_remaining` (Suggest Description: `Check how many {unit_name_plural} you (or @user) can give. Usage: [@user]`)

5.  **Configure Environment Variables:**
    *   Create a file named `.env` in the project root directory (use `.env.example` as a template).
    *   Add the following variables:
        ```dotenv
        # Unit Configuration (Optional)
        UNIT_NAME="kudos"  # Default is "kudos" if not specified
        UNIT_NAME_PLURAL="kudos"  # Default is UNIT_NAME + "s" if not specified
        PRIMARY_EMOJI="star-struck"
        
        # Slack API Tokens (Required)
        SLACK_BOT_TOKEN=xoxb-your-token
        SLACK_APP_TOKEN=xapp-your-token
        
        # Database Configuration (Optional - Defaults to kudos.db)
        # DATABASE_FILE="kudos.db"
        
        # Bot Configuration (Optional - Defaults shown)
        # DAILY_UNIT_LIMIT=5
        # UNIT_ANNOUNCE_CHANNEL="kudos-announce" # Channel name (no #) for public announcements
        # UNIT_REACTION_EMOJI="star-struck" # Emoji name (without colons) to trigger reaction flow
        ```
    *   Replace the placeholder values with your actual tokens.

6.  **Generate the Manifest:**
    *   After setting up your `.env` file, run:
        ```bash
        python3 scripts/generate_manifest.py
        ```
    *   This will create a `manifest.yml` file with the correct command names based on your configured unit name.
    *   If your unit name is not "taco" or "tacos", the manifest will include both the new unit-based commands and legacy "tacos_" commands for backward compatibility.

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