import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
import logging
import tempfile
import secrets
import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
MAX_RESPONSE_LENGTH = 1990  # Discord message limit minus buffer
MAX_QUERY_LENGTH = 2000     # Maximum query length
TEMP_FILE_PREFIX = "gemini_response_"
VALID_MODEL_PATTERN = r"^gemini-[0-9]+\.[0-9]+(-[a-z]+)?(-[a-z0-9]+)?$"
COOLDOWN_SECONDS = 5        # Cooldown between /ask commands

# --- Bot Configuration ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# --- Global Variables for Gemini ---
# Using class-based approach for better encapsulation
class BotState:
    def __init__(self):
        self.gemini_api_key: Optional[str] = None
        self.selected_model_name: Optional[str] = None
        self.gemini_model: Optional[Any] = None
        self.user_cooldowns: Dict[int, datetime] = {}
        self.usage_stats: Dict[str, int] = {"queries": 0, "errors": 0}
    
    def is_user_on_cooldown(self, user_id: int) -> bool:
        """Check if user is on cooldown"""
        if user_id not in self.user_cooldowns:
            return False
        return datetime.now() - self.user_cooldowns[user_id] < timedelta(seconds=COOLDOWN_SECONDS)
    
    def set_user_cooldown(self, user_id: int):
        """Set cooldown for user"""
        self.user_cooldowns[user_id] = datetime.now()
    
    def increment_stat(self, stat: str):
        """Increment usage statistics"""
        if stat in self.usage_stats:
            self.usage_stats[stat] += 1

bot_state = BotState()

# --- Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Event: Bot Ready ---
@bot.event
async def on_ready():
    """Event handler for when bot is ready"""
    logger.info(f'Logged in as {bot.user.name}')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info('Guilds connected to:')
    for guild in bot.guilds:
        logger.info(f'- {guild.name} (id: {guild.id})')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")

def validate_api_key(api_key: str) -> bool:
    """Validate Gemini API key format"""
    if not api_key or not isinstance(api_key, str):
        return False
    # Basic validation - should start with 'AIza' and be at least 35 characters
    return api_key.startswith('AIza') and len(api_key) >= 35

def validate_model_name(model_name: str) -> bool:
    """Validate Gemini model name format"""
    if not model_name or not isinstance(model_name, str):
        return False
    return re.match(VALID_MODEL_PATTERN, model_name) is not None

def sanitize_error_message(error: str) -> str:
    """Sanitize error messages to prevent information disclosure"""
    # Remove potential API keys or sensitive info
    sanitized = re.sub(r'AIza[a-zA-Z0-9_-]{35,}', '[API_KEY_REDACTED]', str(error))
    sanitized = re.sub(r'Bearer [a-zA-Z0-9_.-]+', '[TOKEN_REDACTED]', sanitized)
    return sanitized

def create_secure_temp_file(content: str) -> str:
    """Create a secure temporary file with random name"""
    with tempfile.NamedTemporaryFile(
        mode='w', 
        prefix=TEMP_FILE_PREFIX,
        suffix=f"_{secrets.token_hex(8)}.txt",
        delete=False,
        encoding='utf-8'
    ) as f:
        f.write(content)
        return f.name

# --- Placeholder for Commands (will be implemented in next steps) ---

# --- Slash Command: /apikey ---
@bot.tree.command(name="apikey", description="Set the Gemini API Key (Admins Only).")
@app_commands.describe(key="Your Gemini API Key")
@commands.has_permissions(administrator=True)
async def apikey(interaction: discord.Interaction, key: str):
    """
    Sets the Gemini API Key. Only users with administrator permissions can use this.
    """
    # Validate API key format
    if not validate_api_key(key):
        await interaction.response.send_message(
            "❌ Invalid API key format. Please ensure you're using a valid Gemini API key.",
            ephemeral=True
        )
        logger.warning(f"Invalid API key format provided by {interaction.user.name}")
        return
    
    bot_state.gemini_api_key = key
    try:
        genai.configure(api_key=bot_state.gemini_api_key)
        await interaction.response.send_message(
            "✅ Gemini API Key has been set successfully! Please delete this message for security.",
            ephemeral=True
        )
        logger.info(f"Gemini API Key configured by {interaction.user.name}")
        
        # Re-initialize model if one was already selected
        if bot_state.selected_model_name and bot_state.gemini_model is None:
            try:
                bot_state.gemini_model = genai.GenerativeModel(bot_state.selected_model_name)
                logger.info(f"Re-initialized model {bot_state.selected_model_name} after API key update")
            except Exception as model_error:
                logger.error(f"Failed to re-initialize model: {sanitize_error_message(model_error)}")
                
    except Exception as e:
        error_msg = sanitize_error_message(e)
        await interaction.response.send_message(
            f"❌ Failed to configure Gemini API Key: {error_msg}",
            ephemeral=True
        )
        logger.error(f"Error setting Gemini API Key: {error_msg}")
        bot_state.increment_stat("errors")

@apikey.error
async def apikey_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Error handler for apikey command"""
    if isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You do not have administrator permissions to use this command.",
            ephemeral=True
        )
    else:
        error_msg = sanitize_error_message(str(error))
        await interaction.response.send_message(
            f"❌ An error occurred: {error_msg}",
            ephemeral=True
        )
        logger.error(f"Error in /apikey command: {error_msg}")
        bot_state.increment_stat("errors")

# --- Slash Command: /model ---
@bot.tree.command(name="model", description="Select the Gemini Model to use (Admins Only).")
@app_commands.describe(model_name="Name of the Gemini model (e.g., gemini-1.5-flash)")
@commands.has_permissions(administrator=True)
async def model(interaction: discord.Interaction, model_name: str):
    """
    Sets the Gemini model to be used for queries. Only admins can use this.
    """
    # Validate model name format
    if not validate_model_name(model_name):
        await interaction.response.send_message(
            "❌ Invalid model format. Please use a valid Gemini model name (e.g., 'gemini-1.5-flash', 'gemini-1.5-pro').",
            ephemeral=True
        )
        logger.warning(f"Invalid model name '{model_name}' provided by {interaction.user.name}")
        return

    bot_state.selected_model_name = model_name

    if bot_state.gemini_api_key:
        try:
            # Initialize the model instance when selected
            bot_state.gemini_model = genai.GenerativeModel(bot_state.selected_model_name)
            await interaction.response.send_message(
                f"✅ Gemini model selected: `{bot_state.selected_model_name}`!",
                ephemeral=False
            )
            logger.info(f"Gemini model set to {bot_state.selected_model_name} by {interaction.user.name}")
        except Exception as e:
            # This can happen if the API key is invalid or the model name doesn't exist
            error_msg = sanitize_error_message(str(e))
            await interaction.response.send_message(
                f"❌ Error initializing model `{bot_state.selected_model_name}`. "
                f"Please ensure your API key is correct and the model name is valid. Details: {error_msg}",
                ephemeral=True
            )
            logger.error(f"Error initializing Gemini model {bot_state.selected_model_name}: {error_msg}")
            # Reset to avoid using a partially configured or invalid model
            bot_state.selected_model_name = None
            bot_state.gemini_model = None
            bot_state.increment_stat("errors")
    else:
        # If API key is not set, we can still set the model name, but can't initialize the model object yet.
        # The model object will be initialized when /ask is called, or if /apikey is called after /model.
        await interaction.response.send_message(
            f"📝 Gemini model name set to: `{bot_state.selected_model_name}`. "
            "Note: API key is not yet set. The model will be fully initialized once the API key is provided.",
            ephemeral=False
        )
        logger.info(f"Gemini model name set to {bot_state.selected_model_name} by {interaction.user.name} (API key pending)")


@model.error
async def model_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Error handler for model command"""
    if isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You do not have administrator permissions to use this command.",
            ephemeral=True
        )
    else:
        error_msg = sanitize_error_message(str(error))
        await interaction.response.send_message(
            f"❌ An error occurred: {error_msg}",
            ephemeral=True
        )
        logger.error(f"Error in /model command: {error_msg}")
        bot_state.increment_stat("errors")

# --- Slash Command: /ask ---
@bot.tree.command(name="ask", description="Ask a question to the configured Gemini model.")
@app_commands.describe(query="Your question or prompt for the Gemini model.")
@commands.cooldown(1, COOLDOWN_SECONDS, commands.BucketType.user)
async def ask(interaction: discord.Interaction, query: str):
    """
    Sends a query to the configured Gemini model and returns the response.
    """
    # Check cooldown
    if bot_state.is_user_on_cooldown(interaction.user.id):
        await interaction.response.send_message(
            f"⏰ Please wait {COOLDOWN_SECONDS} seconds between queries.",
            ephemeral=True
        )
        return
    
    # Validate query length
    if len(query) > MAX_QUERY_LENGTH:
        await interaction.response.send_message(
            f"❌ Query too long. Maximum length is {MAX_QUERY_LENGTH} characters.",
            ephemeral=True
        )
        return
    
    # Basic content filtering
    if not query.strip():
        await interaction.response.send_message(
            "❌ Please provide a valid query.",
            ephemeral=True
        )
        return

    if not bot_state.gemini_api_key:
        await interaction.response.send_message(
            "❌ The Gemini API Key has not been set. An administrator needs to use the `/apikey` command.",
            ephemeral=True
        )
        return

    if not bot_state.selected_model_name:
        await interaction.response.send_message(
            "❌ A Gemini model has not been selected. An administrator needs to use the `/model` command.",
            ephemeral=True
        )
        return

    # Attempt to initialize the model if it hasn't been already
    # (e.g., if /model was called before /apikey)
    if bot_state.gemini_model is None:
        try:
            genai.configure(api_key=bot_state.gemini_api_key) # Ensure genai is configured
            bot_state.gemini_model = genai.GenerativeModel(bot_state.selected_model_name)
            logger.info(f"Gemini model '{bot_state.selected_model_name}' initialized on demand by /ask command.")
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            await interaction.response.send_message(
                f"❌ Error initializing Gemini model '{bot_state.selected_model_name}' for your query. "
                f"Please check admin settings or contact an admin. Details: {error_msg}",
                ephemeral=True
            )
            logger.error(f"Failed to initialize {bot_state.selected_model_name} during /ask command: {error_msg}")
            bot_state.increment_stat("errors")
            return

    if bot_state.gemini_model is None: # Should not happen if above logic is correct, but as a safeguard
        await interaction.response.send_message(
            "❌ Model could not be initialized. Please ask an Admin to check the `/model` and `/apikey` settings.",
            ephemeral=True
        )
        return

    # Set user cooldown
    bot_state.set_user_cooldown(interaction.user.id)
    
    await interaction.response.defer(ephemeral=False) # Defer while we wait for API

    try:
        logger.info(f"User {interaction.user.name} asked: '{query[:100]}...' using model {bot_state.selected_model_name}")
        bot_state.increment_stat("queries")
        
        # For simplicity, using generate_content. For chat history, use start_chat.
        response = await bot_state.gemini_model.generate_content_async(query)

        # Check if the response has parts and text
        if response and response.parts:
            # Concatenate text from all parts
            full_response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            if not full_response_text.strip(): # Handle cases where parts exist but text is empty
                 full_response_text = "The model generated an empty response."
        elif hasattr(response, 'text') and response.text: # Fallback for simpler response structures
            full_response_text = response.text
        else: # Handle cases where response might be empty or in an unexpected format
            candidate = response.candidates[0] if response.candidates else None
            if candidate and candidate.content and candidate.content.parts:
                full_response_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
            else:
                full_response_text = "Sorry, I couldn't get a valid response from the model. The response structure was unexpected."
                logger.warning(f"Unexpected response structure: {response}")

        # Discord has a 2000 character limit per message.
        # If the response is longer, we need to split it or send as a file.
        if len(full_response_text) > MAX_RESPONSE_LENGTH:
            # Sending as a file for longer responses
            temp_file = None
            try:
                temp_file = create_secure_temp_file(full_response_text)
                await interaction.followup.send(
                    f"📄 The response from **{bot_state.selected_model_name}** was too long to display directly. "
                    "Here it is as a text file:",
                    file=discord.File(temp_file, filename="gemini_response.txt")
                )
            except Exception as file_e:
                logger.error(f"Error sending response as file: {sanitize_error_message(file_e)}")
                await interaction.followup.send(
                    f"⚠️ The response from **{bot_state.selected_model_name}** was too long to display directly, "
                    "and I encountered an error trying to send it as a file. "
                    "The first 1900 characters are:\n```\n"
                    f"{full_response_text[:1900]}...\n```"
                )
            finally:
                # Clean up temporary file
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temp file {temp_file}: {cleanup_error}")
        else:
            # Format response nicely
            formatted_response = f"**Query:** {query}\n\n**{bot_state.selected_model_name} says:**\n{full_response_text}"
            await interaction.followup.send(formatted_response)

    except Exception as e:
        error_message = f"❌ An error occurred while communicating with the Gemini API: {sanitize_error_message(str(e))}"
        logger.error(f"Gemini API error for user {interaction.user.name}: {sanitize_error_message(str(e))}")
        bot_state.increment_stat("errors")
        
        # Check for specific error types if possible, e.g., API key issues, model not found, quota limits
        if "API_KEY_INVALID" in str(e) or "API_KEY_MISSING" in str(e) or "403" in str(e):
             error_message += "\n💡 Please ensure the Gemini API key is correctly set by an administrator using `/apikey`."
        elif "MODEL_NOT_FOUND" in str(e) or "404" in str(e): # Simple check for model not found
             error_message += f"\n💡 The model '{bot_state.selected_model_name}' might be invalid or unavailable. " \
                             "Please ask an administrator to check the model name using `/model`."
        elif "QUOTA_EXCEEDED" in str(e) or "429" in str(e):
             error_message += "\n💡 API quota exceeded. Please try again later or contact an administrator."

        # Check if the interaction has already been responded to or deferred
        if interaction.is_done():
            await interaction.followup.send(error_message)
        else:
            # This path might not be typically hit if we defer() correctly
            await interaction.response.send_message(error_message, ephemeral=True)


# --- Slash Command: /status ---
@bot.tree.command(name="status", description="Check bot status and configuration.")
async def status(interaction: discord.Interaction):
    """Show current bot status and configuration"""
    api_key_status = "✅ Set" if bot_state.gemini_api_key else "❌ Not set"
    model_status = f"✅ {bot_state.selected_model_name}" if bot_state.selected_model_name else "❌ Not selected"
    model_ready = "✅ Ready" if bot_state.gemini_model else "❌ Not initialized"
    
    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="API Key", value=api_key_status, inline=True)
    embed.add_field(name="Model", value=model_status, inline=True)
    embed.add_field(name="Model Ready", value=model_ready, inline=True)
    embed.add_field(name="Total Queries", value=bot_state.usage_stats["queries"], inline=True)
    embed.add_field(name="Total Errors", value=bot_state.usage_stats["errors"], inline=True)
    embed.add_field(name="Cooldown", value=f"{COOLDOWN_SECONDS}s", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Slash Command: /models ---
@bot.tree.command(name="models", description="List available Gemini models.")
async def models(interaction: discord.Interaction):
    """List available Gemini models"""
    embed = discord.Embed(
        title="🔧 Available Gemini Models",
        description="Here are some commonly available Gemini models:",
        color=discord.Color.green()
    )
    
    models_info = [
        ("gemini-1.5-flash", "Fast and efficient, good for most tasks"),
        ("gemini-1.5-pro", "More capable, better for complex tasks"),
        ("gemini-1.5-flash-latest", "Latest version of flash model"),
        ("gemini-1.5-pro-latest", "Latest version of pro model"),
    ]
    
    for model_name, description in models_info:
        embed.add_field(
            name=model_name,
            value=description,
            inline=False
        )
    
    embed.add_field(
        name="💡 Note",
        value="Use `/model <model_name>` to select a model (Admin only)",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Slash Command: /help ---
@bot.tree.command(name="help", description="Show help information.")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    embed = discord.Embed(
        title="🤖 Gemini Discord Bot Help",
        description="This bot allows you to interact with Google's Gemini AI models.",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="👤 User Commands",
        value="`/ask <query>` - Ask a question to the AI\n"
              "`/status` - Check bot status\n"
              "`/models` - List available models\n"
              "`/help` - Show this help message",
        inline=False
    )
    
    embed.add_field(
        name="👑 Admin Commands",
        value="`/apikey <key>` - Set the Gemini API key\n"
              "`/model <name>` - Select the AI model to use",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Security Features",
        value="• API keys are stored securely in memory\n"
              "• Input validation and sanitization\n"
              "• Rate limiting and cooldowns\n"
              "• Error message sanitization",
        inline=False
    )
    
    embed.add_field(
        name="📋 Setup",
        value="1. Admin sets API key with `/apikey`\n"
              "2. Admin selects model with `/model`\n"
              "3. Users can start asking questions with `/ask`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Run the Bot ---
if __name__ == "__main__":
    if DISCORD_BOT_TOKEN is None:
        logger.error("DISCORD_BOT_TOKEN not found. Please set it in your .env file or environment variables.")
        print("Error: DISCORD_BOT_TOKEN not found. Please set it in your .env file or environment variables.")
    else:
        logger.info("Starting Discord bot...")
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except discord.errors.LoginFailure:
            logger.error("Failed to log in. Please check your Discord Bot Token.")
            print("Error: Failed to log in. Please check your Discord Bot Token.")
        except KeyboardInterrupt:
            logger.info("Bot shutdown requested by user.")
            print("Bot shutdown requested by user.")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            print(f"An unexpected error occurred: {e}")
        finally:
            logger.info("Bot has shut down.")
            print("Bot has shut down.")
