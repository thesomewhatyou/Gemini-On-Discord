# Discord Gemini Bot

This Discord bot allows users to interact with Google's Gemini models directly from Discord. Administrators can set the Gemini API Key and choose a specific Gemini model. Once configured, any user can use the `/ask` command to query the selected model.

## ✨ Features

### Core Features
-   **Admin-only API Key Configuration**: Securely set your Gemini API key using the `/apikey` command.
-   **Admin-only Model Selection**: Choose which Gemini model to use (e.g., `gemini-1.5-flash`, `gemini-1.5-pro`) via the `/model` command.
-   **AI Querying**: Users can ask questions or provide prompts to the configured Gemini model using the `/ask` command.
-   **Smart Response Handling**: Automatically handles long responses by sending them as text files when they exceed Discord's message limit.
-   **Permissions Control**: Critical commands (`/apikey`, `/model`) are restricted to server administrators.

### 🛡️ Security Enhancements
-   **Input Validation**: Comprehensive validation of API keys, model names, and user queries
-   **Rate Limiting**: Built-in cooldown system to prevent spam and API abuse
-   **Error Sanitization**: Sensitive information is automatically removed from error messages
-   **Secure File Handling**: Temporary files use cryptographically secure random names
-   **Memory-only Storage**: API keys are stored securely in memory only (not on disk)

### 🧠 Advanced AI Features
-   **Conversation History**: AI maintains context across multiple queries for more natural conversations
-   **User Preferences**: Customize AI behavior with adjustable temperature, max tokens, and response formats
-   **Content Filtering**: Multi-level content filtering (low/medium/high) to prevent inappropriate queries
-   **Response Formatting**: Choose between standard, detailed, or concise response formats
-   **Smart Context Management**: Automatic conversation history management with export capabilities

### 📊 Additional Features
-   **Enhanced Status Monitoring**: Detailed bot status with user-specific information and usage statistics
-   **Model Information**: `/models` command lists available Gemini models with descriptions
-   **Comprehensive Help**: `/help` command provides detailed usage instructions for all features
-   **Usage Statistics**: Tracks queries, errors, and filtered content for monitoring purposes
-   **Personal Settings**: Per-user customizable AI interaction preferences

## Prerequisites

-   Python 3.8 or newer
-   A Discord Bot Token
-   A Google Gemini API Key

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

### 👤 User Commands

1.  **`/ask [query]`**
    *   **Description**: Ask a question or provide a prompt to the configured Gemini model.
    *   **Usage**: `/ask query:What is the capital of France?`
    *   **Enhanced Features**: 
        - 🧠 **Conversation History**: AI remembers previous messages for context
        - 🎛️ **Personal Settings**: Uses your custom temperature and token settings
        - 🚫 **Content Filtering**: Automatically filters inappropriate content
        - 📝 **Response Formats**: Respects your preferred response format (standard/detailed/concise)
        - ⏰ **Rate Limiting**: 5-second cooldown between queries per user
    *   The bot will respond with the AI-generated answer, maintaining conversation context.

2.  **`/preferences [setting] [value]`** ⭐ NEW
    *   **Description**: View and customize your AI interaction preferences.
    *   **Usage**: `/preferences` (view all) or `/preferences setting:temperature value:0.8`
    *   **Available Settings**:
        - `temperature` (0.0-1.0): Controls AI creativity (0.0 = focused, 1.0 = creative)
        - `max_tokens` (1-2048): Maximum response length
        - `conversation_history` (true/false): Enable/disable conversation memory
        - `content_filter_level` (low/medium/high): Content filtering strictness
        - `response_format` (text/detailed/concise): Response formatting style

3.  **`/conversation [action]`** ⭐ NEW
    *   **Description**: Manage your conversation history and context.
    *   **Actions**:
        - `view`: See your recent conversation history
        - `clear`: Reset conversation history and start fresh
        - `export`: Download your conversation history as a text file
    *   **Usage**: `/conversation action:view`

4.  **`/status`**
    *   **Description**: Check bot status, configuration, and your personal settings.
    *   **Enhanced Info**: Now shows conversation history count, active chat status, and your preferences

5.  **`/models`**
    *   **Description**: List available Gemini models and their descriptions.
    *   **Usage**: `/models`

6.  **`/help`**
    *   **Description**: Display comprehensive help information including new features.
    *   **Updated**: Now includes documentation for all enhanced features

### 👑 Administrator Commands

1.  **`/apikey [key]`** (Admin Only)
    *   **Description**: Sets the Google Gemini API key for the bot. This is required for the bot to function.
    *   **Usage**: `/apikey key:your_gemini_api_key_here`
    *   **Example**: `/apikey key:AIzaSy*******************`
    *   **Security**: The bot will confirm if the key was set successfully. **Always delete the response message immediately for security!**

2.  **`/model [model_name]`** (Admin Only)
    *   **Description**: Selects the Gemini model to be used for queries.
    *   **Usage**: `/model model_name:name_of_the_model`
    *   **Examples**:
        *   `/model model_name:gemini-1.5-flash`
        *   `/model model_name:gemini-1.5-pro`
        *   `/model model_name:gemini-1.5-flash-latest`
    *   The bot will confirm the model selection and test if it can be initialized with the current API key.

## 🛡️ Security & Important Notes

### Security Features
*   **Enhanced Input Validation**: All inputs (API keys, model names, queries) are validated and sanitized
*   **Rate Limiting**: Built-in cooldown system prevents spam and API abuse
*   **Error Sanitization**: Sensitive information is automatically removed from error messages
*   **Secure File Handling**: Temporary files use cryptographically secure random names
*   **Memory-only Storage**: API keys are stored securely in memory only, never on disk

### Enhanced User Experience
*   **Conversation Memory**: The bot now remembers your previous messages and maintains context across the conversation, making interactions more natural and coherent.
*   **Personal AI Settings**: Customize how the AI responds to you with adjustable temperature (creativity), max tokens (response length), and response formatting.
*   **Smart Content Filtering**: Multi-level content filtering automatically prevents inappropriate queries while allowing legitimate use cases.
*   **Flexible Response Formats**: Choose how you want responses formatted - standard text, detailed explanations, or concise summaries.
*   **Conversation Management**: Export your chat history, view recent conversations, or clear history to start fresh.

### Security Best Practices
*   **API Key Security**: Your Gemini API Key is sensitive. The `/apikey` command stores it in the bot's memory for the current session. For production environments, consider more robust secret management strategies if the bot is hosted persistently. **Always delete the response message immediately after using `/apikey`** to prevent users from stealing it.
*   **Administrator Permissions**: Ensure that only trusted users have administrator permissions on your Discord server, as they will be able to set the API key and model.
*   **Rate Limits & Quotas**: Be mindful of Gemini API rate limits and quotas. The bot includes built-in rate limiting, but high usage might require checking your Google Cloud project settings.
*   **Monitoring**: Use the `/status` command to monitor bot usage and check for any unusual activity.

### Error Handling & Logging
*   **Comprehensive Logging**: All bot activities are logged to `bot.log` for debugging and monitoring
*   **Graceful Error Handling**: The bot includes robust error handling for API communication and command usage
*   **User-Friendly Messages**: Error messages are sanitized and user-friendly while preserving helpful information for administrators

## Troubleshooting

### Common Issues

*   **Bot not responding/commands not appearing**:
    *   Ensure the bot is running (check your terminal or log files)
    *   Ensure you've correctly set the `DISCORD_BOT_TOKEN` in the `.env` file
    *   Make sure the bot has been invited to your server with the correct permissions (at least `Send Messages`, `Read Message History`, and `Use Application Commands`)
    *   Sometimes, slash commands take a little while to register globally or for a specific guild after the bot starts. Try restarting the bot or waiting a few minutes.

*   **`/ask` command errors**:
    *   Ensure an admin has successfully used `/apikey` with a valid key
    *   Ensure an admin has successfully used `/model` with a valid and available model name
    *   Check the bot's console/log for any specific error messages from the Gemini API
    *   Use `/status` to verify bot configuration

*   **"Missing Permissions"**: You are trying to use an admin-only command (`/apikey`, `/model`) without having administrator rights on the server.

*   **Rate limiting errors**: If you're hitting rate limits, wait before making more requests. The bot has built-in cooldowns to help prevent this.

### 🔧 Development & Maintenance

*   **Security Scanning**: Run `python3 security_check.py` to scan for potential security issues
*   **Log Monitoring**: Check `bot.log` for detailed activity logs and error information
*   **Configuration**: Copy `.env.example` to `.env` and configure your tokens
*   **Dependencies**: All required packages are listed in `requirements.txt`

### Getting Help

If you encounter issues not covered here:
1. Check the bot's log file (`bot.log`) for detailed error information
2. Use the `/status` command to verify bot configuration
3. Ensure all prerequisites are met and dependencies are installed
4. Review the security scanner output for any potential issues
