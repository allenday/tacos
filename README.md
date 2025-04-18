# Taco Slack Bot

A simple Slack bot built with Python (`slack_bolt`) and SQLite to give and track virtual tacos within a workspace.

## Features

*   Give tacos: `/tacos_give <amount> <@user> <note>`
*   View Leaderboard: `/tacos_leaderboard`
*   View Stats: `/tacos_stats` (Shows leaderboard for now)
*   View Giving History: `/tacos_history [@user] [lines]`
*   View Receiving History: `/tacos_received [lines]`
*   Get Help: `/tacos_help`
*   Check Remaining Tacos: `/tacos_remaining [@user]`
*   Rolling 24-hour giving limit (configurable).
*   Optional public announcement channel for taco grants.

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
        *   In the left sidebar under "Features", click on **"Slash Commands"**.
        *   Create the following commands:
            *   Command: `/tacos` (Suggest Description: `Give tacos to a user. Usage: /tacos give <amount> <@user> <note>`)
            *   Command: `/tacos_leaderboard` (Suggest Description: `Show the taco leaderboard`)
            *   Command: `/tacos_stats` (Suggest Description: `Show taco stats (leaderboard)`)
            *   Command: `/tacos_history` (Suggest Description: `Show taco giving/receiving history. Usage: [@user] [lines]`)
            *   Command: `/tacos_received` (Suggest Description: `Show your taco receiving history. Usage: [lines]`)
            *   Command: `/tacos_help` (Suggest Description: `Show help information for the Taco Bot`)
            *   Command: `/tacos_remaining` (Suggest Description: `Check how many tacos you (or @user) can give. Usage: [@user]`)

5.  **Configure Environment Variables:**
    *   Create a file named `.env` in the project root directory (a template is provided).
    *   Add the following variables:
        ```dotenv
        # Slack API Tokens (Required)
        SLACK_BOT_TOKEN="xoxb-..." # Your Bot User OAuth Token
        SLACK_APP_TOKEN="xapp-..." # Your App-Level Token

        # Database Configuration (Optional - Defaults to tacos.db)
        # DATABASE_FILE="tacos.db"

        # Bot Configuration (Optional - Defaults shown)
        # DAILY_TACO_LIMIT=5
        # TACO_ANNOUNCE_CHANNEL="tacos" # Channel name (no #) for public announcements
        ```
    *   Replace the placeholder values with your actual tokens.

## Running the Bot

1.  Ensure your virtual environment is active (`source venv/bin/activate`).
2.  Make sure you have filled in your tokens in the `.env` file.
3.  Run the bot from the project's root directory:
    ```bash
    python -m src.bot
    ```
4.  The bot will connect using Socket Mode and log informational messages to the console. You should see a message like "Starting Taco Bot using Socket Mode..." and then "Bolt app is running!"

## Database

The bot uses an SQLite database file (default: `tacos.db`) created in the project root to store transaction history. This file is excluded from Git by the `.gitignore` file. 