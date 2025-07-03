# Discord Gemini Bot

This Discord bot allows users to interact with Google's Gemini models directly from Discord. Administrators can set the Gemini API Key and choose a specific Gemini model. Once configured, any user can use the `/ask` command to query the selected model.

## Features

-   **Admin-only API Key Configuration**: Securely set your Gemini API key using the `/apikey` command.
-   **Admin-only Model Selection**: Choose which Gemini model to use (e.g., `gemini-1.5-flash`, `gemini-1.5-pro`) via the `/model` command.
-   **Gemini Querying**: Users can ask questions or provide prompts to the configured Gemini model using the `/ask` command.
-   **Handles Long Responses**: If a response from Gemini is too long for a single Discord message, it will be sent as a text file.
-   **Permissions Control**: Critical commands (`/apikey`, `/model`) are restricted to server administrators.

## Prerequisites

-   Python 3.8 or newer.
-   A Discord Bot Token.
-   A Google Gemini API Key.

## Setup Instructions

1.  **Clone the Repository or Download Files:**
    If this bot is part of a repository, clone it. Otherwise, ensure you have `bot.py` (and potentially this `README.md`).

2.  **Install Dependencies:**
    Navigate to the bot's directory in your terminal and install the required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```
    If a `requirements.txt` file is not provided, you can install them manually:
    ```bash
    pip install discord.py google-generativeai python-dotenv
    ```

3.  **Create a `.env` File:**
    In the same directory as `bot.py`, create a file named `.env`. This file will store your sensitive credentials. Add your Discord Bot Token to this file:
    ```
    DISCORD_BOT_TOKEN=your_actual_discord_bot_token_here
    ```
    Replace `your_actual_discord_bot_token_here` with your bot's token from the [Discord Developer Portal](https://discord.com/developers/applications).

4.  **Obtain a Gemini API Key:**
    If you don't have one, obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

5.  **Run the Bot:**
    Execute the `bot.py` script:
    ```bash
    python bot.py
    ```
    You should see console output indicating the bot has logged in.

## Bot Commands

Once the bot is running and invited to your Discord server:

1.  **`/apikey [key]` (Admin Only)**
    *   **Description**: Sets the Google Gemini API key for the bot. This is required for the bot to function.
    *   **Usage**: `/apikey key:your_gemini_api_key_here`
    *   **Example**: `/apikey key:AIzaSy*******************`
    *   The bot will confirm if the key was set successfully or if an error occurred. This message is only visible to you.

2.  **`/model [model_name]` (Admin Only)**
    *   **Description**: Selects the Gemini model to be used for queries.
    *   **Usage**: `/model model_name:name_of_the_model`
    *   **Examples**:
        *   `/model model_name:gemini-1.5-flash`
        *   `/model model_name:gemini-1.5-pro-latest`
        *   `/model model_name:gemini-pro` (for the general availability `gemini-pro` model if `gemini-1.0-pro` is intended)
    *   Refer to the [official Gemini models documentation](https://ai.google.dev/gemini-api/docs/models/gemini) for available model names.
    *   The bot will respond with "`[model_name]` selected!".

3.  **`/ask [query]` (All Users)**
    *   **Description**: Sends your query to the currently configured Gemini model.
    *   **Usage**: `/ask query:Your question or prompt here`
    *   **Example**: `/ask query:What is the airspeed velocity of an unladen swallow?`
    *   The bot will respond with the answer from the Gemini model. If the API key or model is not set, it will inform you.

## Important Notes

*   **API Key Security**: Your Gemini API Key is sensitive. The `/apikey` command stores it in the bot's memory for the current session. For production environments, consider more robust secret management strategies if the bot is hosted persistently. The `.env` file for the Discord token is a good first step for local development. Make sure to instantly delete the response from the bot when doing the `/apikey` command. This will prevent users from stealing it.
*   **Administrator Permissions**: Ensure that only trusted users have administrator permissions on your Discord server, as they will be able to set the API key and model.
*   **Rate Limits & Quotas**: Be mindful of Gemini API rate limits and quotas. High usage might require checking your Google Cloud project settings.
*   **Error Handling**: The bot includes basic error handling for API communication and command usage. Check the bot's console output for more detailed error logs if needed.

## Troubleshooting

*   **Bot not responding/commands not appearing**:
    *   Ensure the bot is running (check your terminal).
    *   Ensure you've correctly set the `DISCORD_BOT_TOKEN` in the `.env` file.
    *   Make sure the bot has been invited to your server with the correct permissions (at least `Send Messages`, `Read Message History`, and `Use Application Commands`).
    *   Sometimes, slash commands take a little while to register globally or for a specific guild after the bot starts. Try restarting the bot or waiting a few minutes.
*   **`/ask` command errors**:
    *   Ensure an admin has successfully used `/apikey` with a valid key.
    *   Ensure an admin has successfully used `/model` with a valid and available model name.
    *   Check the bot's console for any specific error messages from the Gemini API.
*   **"Missing Permissions"**: You are trying to use an admin-only command (`/apikey`, `/model`) without having administrator rights on the server.
