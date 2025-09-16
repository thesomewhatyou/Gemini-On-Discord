import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
import logging
import tempfile
import secrets
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import asyncio
from dotenv import load_dotenv

# Load env
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
MAX_CONVERSATION_HISTORY = 10  # Maximum messages to keep in conversation history
DEFAULT_TEMPERATURE = 0.7   # Default model temperature
DEFAULT_MAX_TOKENS = 1000   # Default max output tokens

# Content filtering keywords - basic implementation
BLOCKED_CONTENT = [
    'violence', 'harmful', 'illegal', 'explicit', 'nsfw', 
    'dangerous', 'offensive', 'hate speech'
]

# --- Bot Configuration ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# --- Data Classes for Enhanced Features ---
@dataclass
class UserPreferences:
    """User-specific preferences for AI interactions"""
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    use_conversation_history: bool = True
    content_filter_level: str = "medium"  # low, medium, high
    preferred_response_format: str = "text"  # text, detailed, concise

@dataclass 
class ConversationMessage:
    """Represents a message in conversation history"""
    role: str  # "user" or "model" 
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

class ConversationHistory:
    """Manages conversation history for users"""
    def __init__(self):
        self.conversations: Dict[int, List[ConversationMessage]] = {}
    
    def add_message(self, user_id: int, role: str, content: str):
        """Add a message to user's conversation history"""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        self.conversations[user_id].append(ConversationMessage(role, content))
        
        # Keep only recent messages
        if len(self.conversations[user_id]) > MAX_CONVERSATION_HISTORY * 2:  # *2 for user+model pairs
            self.conversations[user_id] = self.conversations[user_id][-MAX_CONVERSATION_HISTORY * 2:]
    
    def get_history(self, user_id: int) -> List[ConversationMessage]:
        """Get conversation history for user"""
        return self.conversations.get(user_id, [])
    
    def clear_history(self, user_id: int):
        """Clear conversation history for user"""
        if user_id in self.conversations:
            del self.conversations[user_id]
    
    def get_context_for_gemini(self, user_id: int) -> List[Dict[str, str]]:
        """Format conversation history for Gemini API"""
        history = self.get_history(user_id)
        context = []
        for msg in history[-MAX_CONVERSATION_HISTORY:]:  # Get recent messages
            context.append({
                "role": msg.role,
                "parts": [{"text": msg.content}]
            })
        return context
# --- Global Variables for Gemini --- Is Grammarly deadass correcting my code
# Using a class-based approach for better encapsulation
class BotState:
    def __init__(self):
        self.gemini_api_key: Optional[str] = None
        self.selected_model_name: Optional[str] = None
        self.gemini_model: Optional[Any] = None
        self.user_cooldowns: Dict[int, datetime] = {}
        self.usage_stats: Dict[str, int] = {"queries": 0, "errors": 0, "filtered_queries": 0}
        self.user_preferences: Dict[int, UserPreferences] = {}
        self.conversation_history = ConversationHistory()
        self.active_chats: Dict[int, Any] = {}  # Active Gemini chat sessions per user
    
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
    
    def get_user_preferences(self, user_id: int) -> UserPreferences:
        """Get user preferences, creating defaults if needed"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreferences()
        return self.user_preferences[user_id]
    
    def update_user_preference(self, user_id: int, setting: str, value: Any):
        """Update a specific user preference"""
        prefs = self.get_user_preferences(user_id)
        if hasattr(prefs, setting):
            setattr(prefs, setting, value)
            return True
        return False

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
    # Holy shit it is correcting my code Grammarly sybau 
    return api_key.startswith('AIza') and len(api_key) >= 35

def validate_model_name(model_name: str) -> bool:
    """Validate Gemini model name format"""
    if not model_name or not isinstance(model_name, str):
        return False
    return re.match(VALID_MODEL_PATTERN, model_name) is not None

def sanitize_error_message(error: str) -> str:
    """Sanitize error messages to prevent information disclosure"""
    # Remove potential API keys or sensitive info
    sanitized = re.sub(r'AIza[a-zA-Z0-9_-]{31,}', '[API_KEY_REDACTED]', str(error))
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

def check_content_filter(text: str, filter_level: str = "medium") -> tuple[bool, str]:
    """
    Basic content filtering
    Returns (is_safe, reason) tuple
    """
    text_lower = text.lower()
    
    # High filter level - strict checking
    if filter_level == "high":
        blocked_words = BLOCKED_CONTENT + ['inappropriate', 'controversial', 'sensitive']
    # Medium filter level - moderate checking  
    elif filter_level == "medium":
        blocked_words = BLOCKED_CONTENT
    # Low filter level - minimal checking
    else:
        blocked_words = ['violence', 'illegal', 'dangerous']
    
    for word in blocked_words:
        if word in text_lower:
            return False, f"Content contains potentially inappropriate material: '{word}'"
    
    # Check for excessive length or suspicious patterns
    if len(text) > MAX_QUERY_LENGTH:
        return False, f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters"
    
    return True, "Content passed filtering"

def format_response_by_preference(response: str, format_type: str) -> str:
    """Format response based on user preference"""
    if format_type == "concise":
        # Try to shorten response while keeping key information
        lines = response.split('\n')
        if len(lines) > 3:
            return '\n'.join(lines[:3]) + '\n...\n*(Response truncated for concise format)*'
        return response
    elif format_type == "detailed":
        # Add more context and formatting
        return f"**Detailed Response:**\n\n{response}\n\n*Generated with enhanced detail formatting*"
    else:  # text (default)
        return response

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
        # We can't initialize the model obj so we just gotta cache it. That's a later question
        # The model object will be initialized when /ask is called, or if /apikey is called after /model.
        await interaction.response.send_message(
            f"📝 Gemini model name set to: `{bot_state.selected_model_name}`. "
            "Note: API key is not yet set. The model will be fully initialized once the API key is provided.",
            ephemeral=False
        )
        logger.info(f"Gemini model name set to {bot_state.selected_model_name} by {interaction.user.name} (API key pending)")

        # Grammarly fuckign sucks i just want to write code
        # STOP CORRECTING MY CODE COMMENTS 
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
    Enhanced with conversation history and content filtering.
    """
    user_id = interaction.user.id
    
    # Check cooldown
    if bot_state.is_user_on_cooldown(user_id):
        await interaction.response.send_message(
            f"⏰ Please wait {COOLDOWN_SECONDS} seconds between queries.",
            ephemeral=True
        )
        return
    
    # Get user preferences
    user_prefs = bot_state.get_user_preferences(user_id)
    
    # Content filtering
    is_safe, filter_reason = check_content_filter(query, user_prefs.content_filter_level)
    if not is_safe:
        await interaction.response.send_message(
            f"🚫 Content Filter: {filter_reason}",
            ephemeral=True
        )
        bot_state.increment_stat("filtered_queries")
        return
    
    # Basic query validation
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

    # Initialize model if needed
    if bot_state.gemini_model is None:
        try:
            genai.configure(api_key=bot_state.gemini_api_key)
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

    # Set user cooldown
    bot_state.set_user_cooldown(user_id)
    
    await interaction.response.defer(ephemeral=False)

    try:
        logger.info(f"User {interaction.user.name} asked: '{query[:100]}...' using model {bot_state.selected_model_name}")
        bot_state.increment_stat("queries")
        
        # Use conversation history if enabled
        if user_prefs.use_conversation_history:
            # Get or create chat session for this user
            if user_id not in bot_state.active_chats:
                # Create new chat with conversation history
                history = bot_state.conversation_history.get_context_for_gemini(user_id)
                bot_state.active_chats[user_id] = bot_state.gemini_model.start_chat(history=history)
            
            chat = bot_state.active_chats[user_id]
            
            # Generate configuration for the model
            generation_config = genai.types.GenerationConfig(
                temperature=user_prefs.temperature,
                max_output_tokens=user_prefs.max_tokens,
            )
            
            response = await chat.send_message_async(query, generation_config=generation_config)
            
            # Store in conversation history
            bot_state.conversation_history.add_message(user_id, "user", query)
            
        else:
            # Single query without history
            generation_config = genai.types.GenerationConfig(
                temperature=user_prefs.temperature,
                max_output_tokens=user_prefs.max_tokens,
            )
            
            response = await bot_state.gemini_model.generate_content_async(
                query, 
                generation_config=generation_config
            )

        # Extract response text. We milk it like a cow. Sorry Google that's on you pal
        if response and response.parts:
            full_response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            if not full_response_text.strip():
                 full_response_text = "The model generated an empty response."
        elif hasattr(response, 'text') and response.text:
            full_response_text = response.text
        else:
            candidate = response.candidates[0] if response.candidates else None
            if candidate and candidate.content and candidate.content.parts:
                full_response_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
            else:
                full_response_text = "Sorry, I couldn't get a valid response from the model. The response structure was unexpected."
                logger.warning(f"Unexpected response structure: {response}")

        # Store model response in conversation history
        if user_prefs.use_conversation_history:
            bot_state.conversation_history.add_message(user_id, "model", full_response_text)

        # Format response based on user preference
        formatted_response = format_response_by_preference(full_response_text, user_prefs.preferred_response_format)

        # Handle long responses by sending a text file. It should work 
        if len(formatted_response) > MAX_RESPONSE_LENGTH:
            temp_file = None
            try:
                temp_file = create_secure_temp_file(formatted_response)
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
                    f"{formatted_response[:1900]}...\n```"
                )
            finally:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temp file {temp_file}: {cleanup_error}")
        else:
            # Send formatted response. It probably works.
            history_indicator = "🧠 " if user_prefs.use_conversation_history else ""
            final_response = f"{history_indicator}**Query:** {query}\n\n**{bot_state.selected_model_name} says:**\n{formatted_response}"
            await interaction.followup.send(final_response)

    except Exception as e:
        error_message = f"❌ An error occurred while communicating with the Gemini API: {sanitize_error_message(str(e))}"
        logger.error(f"Gemini API error for user {interaction.user.name}: {sanitize_error_message(str(e))}")
        bot_state.increment_stat("errors")
        
        # Check for specific error types. This one definitely does NOT work
        if "API_KEY_INVALID" in str(e) or "API_KEY_MISSING" in str(e) or "403" in str(e):
             error_message += "\n💡 Please ensure the Gemini API key is correctly set by an administrator using `/apikey`."
        elif "MODEL_NOT_FOUND" in str(e) or "404" in str(e):
             error_message += f"\n💡 The model '{bot_state.selected_model_name}' might be invalid or unavailable. " \
                             "Please ask an administrator to check the model name using `/model`."
        elif "QUOTA_EXCEEDED" in str(e) or "429" in str(e):
             error_message += "\n💡 API quota exceeded. Please try again later or contact an administrator."

        if interaction.is_done():
            await interaction.followup.send(error_message)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)


# --- Slash Command: /preferences ---
@bot.tree.command(name="preferences", description="View and manage your AI interaction preferences.")
@app_commands.describe(
    setting="The preference setting to change",
    value="The new value for the setting"
)
@app_commands.choices(setting=[
    app_commands.Choice(name="temperature", value="temperature"),
    app_commands.Choice(name="max_tokens", value="max_tokens"),
    app_commands.Choice(name="conversation_history", value="use_conversation_history"),
    app_commands.Choice(name="content_filter_level", value="content_filter_level"),
    app_commands.Choice(name="response_format", value="preferred_response_format"),
])
async def preferences(interaction: discord.Interaction, setting: str = None, value: str = None):
    """View or update user preferences for AI interactions"""
    user_id = interaction.user.id
    user_prefs = bot_state.get_user_preferences(user_id)
    
    # If no setting specified, show current preferences
    if setting is None:
        embed = discord.Embed(
            title="🎛️ Your AI Preferences",
            color=discord.Color.blue(),
            description="Current settings for your AI interactions"
        )
        
        embed.add_field(
            name="Temperature",
            value=f"{user_prefs.temperature} (0.0 = focused, 1.0 = creative)",
            inline=True
        )
        embed.add_field(
            name="Max Tokens",
            value=f"{user_prefs.max_tokens}",
            inline=True
        )
        embed.add_field(
            name="Conversation History",
            value="✅ Enabled" if user_prefs.use_conversation_history else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Content Filter",
            value=user_prefs.content_filter_level.title(),
            inline=True
        )
        embed.add_field(
            name="Response Format",
            value=user_prefs.preferred_response_format.title(),
            inline=True
        )
        embed.add_field(
            name="📖 How to Change",
            value="Use `/preferences setting:<name> value:<new_value>` to update a setting",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validate and update setting
    if value is None:
        await interaction.response.send_message(
            "❌ Please provide a value for the setting.",
            ephemeral=True
        )
        return
    
    try:
        # Convert and validate value based on setting
        if setting == "temperature":
            new_value = float(value)
            if not 0.0 <= new_value <= 1.0:
                raise ValueError("Temperature must be between 0.0 and 1.0")
        elif setting == "max_tokens":
            new_value = int(value)
            if not 1 <= new_value <= 2048:
                raise ValueError("Max tokens must be between 1 and 2048")
        elif setting == "use_conversation_history":
            new_value = value.lower() in ['true', 'yes', '1', 'on', 'enabled']
        elif setting == "content_filter_level":
            if value.lower() not in ['low', 'medium', 'high']:
                raise ValueError("Content filter level must be 'low', 'medium', or 'high'")
            new_value = value.lower()
        elif setting == "preferred_response_format":
            if value.lower() not in ['text', 'detailed', 'concise']:
                raise ValueError("Response format must be 'text', 'detailed', or 'concise'")
            new_value = value.lower()
        else:
            await interaction.response.send_message(
                "❌ Invalid setting. Use the dropdown to select a valid setting.",
                ephemeral=True
            )
            return
        
        # Update the preference
        if bot_state.update_user_preference(user_id, setting, new_value):
            await interaction.response.send_message(
                f"✅ Updated {setting} to: `{new_value}`",
                ephemeral=True
            )
            logger.info(f"User {interaction.user.name} updated {setting} to {new_value}")
        else:
            await interaction.response.send_message(
                "❌ Failed to update preference.",
                ephemeral=True
            )
            
    except ValueError as e:
        await interaction.response.send_message(
            f"❌ Invalid value: {str(e)}",
            ephemeral=True
        )

# --- Slash Command: /conversation ---
# I can't read Python. I should've chose JavaScript 
@bot.tree.command(name="conversation", description="Manage your conversation history.")
@app_commands.describe(action="Action to perform on conversation history")
@app_commands.choices(action=[
    app_commands.Choice(name="view", value="view"),
    app_commands.Choice(name="clear", value="clear"),
    app_commands.Choice(name="export", value="export"),
])
async def conversation(interaction: discord.Interaction, action: str):
    """Manage conversation history"""
    user_id = interaction.user.id
    
    if action == "view":
        history = bot_state.conversation_history.get_history(user_id)
        if not history:
            await interaction.response.send_message(
                "📝 You have no conversation history yet. Start chatting with `/ask` to build up history!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🧠 Your Conversation History",
            color=discord.Color.green(),
            description=f"Last {len(history)} messages"
        )
        
        for i, msg in enumerate(history[-10:], 1):  # Show last 10 messages
            role_emoji = "👤" if msg.role == "user" else "🤖"
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            embed.add_field(
                name=f"{role_emoji} {msg.role.title()} - {msg.timestamp.strftime('%H:%M')}",
                value=content_preview,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    elif action == "clear":
        bot_state.conversation_history.clear_history(user_id)
        # Also clear active chat session
        if user_id in bot_state.active_chats:
            del bot_state.active_chats[user_id]
        
        await interaction.response.send_message(
            "🗑️ Conversation history cleared! Your next query will start a fresh conversation.",
            ephemeral=True
        )
        logger.info(f"User {interaction.user.name} cleared their conversation history")
        
    elif action == "export":
        history = bot_state.conversation_history.get_history(user_id)
        if not history:
            await interaction.response.send_message(
                "📝 You have no conversation history to export.",
                ephemeral=True
            )
            return
        
        # Create export content
        export_content = f"Conversation History Export for {interaction.user.name}\n"
        export_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_content += "=" * 50 + "\n\n"
        
        for msg in history:
            export_content += f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {msg.role.upper()}:\n"
            export_content += f"{msg.content}\n\n"
        
        # Send as file
        temp_file = None
        try:
            temp_file = create_secure_temp_file(export_content)
            await interaction.response.send_message(
                "📄 Here's your conversation history export:",
                file=discord.File(temp_file, filename=f"conversation_history_{datetime.now().strftime('%Y%m%d')}.txt"),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error exporting conversation history: {sanitize_error_message(str(e))}")
            await interaction.response.send_message(
                "❌ Failed to export conversation history.",
                ephemeral=True
            )
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

# --- Slash Command: /status ---
@bot.tree.command(name="status", description="Check bot status and configuration.")
async def status(interaction: discord.Interaction):
    """Show current bot status and configuration"""
    user_id = interaction.user.id
    user_prefs = bot_state.get_user_preferences(user_id)
    
    api_key_status = "✅ Set" if bot_state.gemini_api_key else "❌ Not set"
    model_status = f"✅ {bot_state.selected_model_name}" if bot_state.selected_model_name else "❌ Not selected"
    model_ready = "✅ Ready" if bot_state.gemini_model else "❌ Not initialized"
    
    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # Bot configuration
    embed.add_field(name="API Key", value=api_key_status, inline=True)
    embed.add_field(name="Model", value=model_status, inline=True)
    embed.add_field(name="Model Ready", value=model_ready, inline=True)
    
    # Usage statistics. I didn't test this
    embed.add_field(name="Total Queries", value=bot_state.usage_stats["queries"], inline=True)
    embed.add_field(name="Total Errors", value=bot_state.usage_stats["errors"], inline=True)
    embed.add_field(name="Filtered Queries", value=bot_state.usage_stats["filtered_queries"], inline=True)
    
    # User-specific status. I'm stupid so this probably won't work
    history_count = len(bot_state.conversation_history.get_history(user_id))
    has_active_chat = user_id in bot_state.active_chats
    
    embed.add_field(name="Your History", value=f"{history_count} messages", inline=True)
    embed.add_field(name="Active Chat", value="✅ Yes" if has_active_chat else "❌ No", inline=True)
    embed.add_field(name="History Enabled", value="✅ Yes" if user_prefs.use_conversation_history else "❌ No", inline=True)
    
    # Enhanced features
    embed.add_field(
        name="🎛️ Your Settings",
        value=f"Temperature: {user_prefs.temperature}\n"
              f"Max Tokens: {user_prefs.max_tokens}\n"
              f"Filter Level: {user_prefs.content_filter_level}\n"
              f"Response Format: {user_prefs.preferred_response_format}",
        inline=False
    )
    
    embed.add_field(
        name="💡 New Features",
        value="• Conversation history and context\n"
              "• Customizable AI parameters\n"
              "• Content filtering\n"
              "• Response format preferences\n"
              "• Usage `/preferences` and `/conversation`",
        inline=False
    )
    
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
        description="Advanced AI bot with conversation history, user preferences, and content filtering.",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="👤 User Commands",
        value="`/ask <query>` - Ask a question to the AI (with history & preferences)\n"
              "`/status` - Check bot status and your settings\n"
              "`/models` - List available AI models\n"
              "`/preferences` - View/change your AI preferences\n"
              "`/conversation` - Manage your conversation history\n"
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
        name="✨ New Features",
        value="• **Conversation History**: AI remembers your chat context\n"
              "• **Custom Preferences**: Adjust temperature, tokens, filters\n"
              "• **Content Filtering**: Automatic inappropriate content detection\n"
              "• **Response Formats**: Choose detailed, concise, or standard\n"
              "• **Export History**: Download your conversation history",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Security Features",
        value="• API keys stored securely in memory\n"
              "• Advanced input validation and sanitization\n"
              "• Rate limiting and per-user cooldowns\n"
              "• Content filtering with adjustable levels\n"
              "• Error message sanitization",
        inline=False
    )
    
    embed.add_field(
        name="📋 Quick Setup",
        value="1. Admin sets API key with `/apikey`\n"
              "2. Admin selects model with `/model`\n"
              "3. Users customize preferences with `/preferences`\n"
              "4. Start chatting with `/ask`!\n"
              "5. Manage history with `/conversation`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
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
        # I cannot actually tell if this will gracefully shutdown. If anything the user is probably running this on a cloud server and will shut the VM off without any sort of knowledge 
        # knowing that the bot will spasm out and die. 
        # TO-DO: Program it with feelings so the user feels pity
        finally:
            logger.info("Bot has shut down.")
            print("Bot has shut down.")

            
        # I hope Grammarly does not shut down gracefully
        # I cannot actually tell if this will gracefully shutdown. If anything the user is probably running this on a cloud server
        # and will shut the VM off without any sort of knowledge 
        # knowing that the bot will spasm out and die. 
        # TO-DO: Program it with feelings so the user feels pity
