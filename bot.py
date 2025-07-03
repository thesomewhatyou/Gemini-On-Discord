import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Bot Configuration ---
# TODO: Replace 'YOUR_DISCORD_BOT_TOKEN' with your actual Discord bot token
# It's recommended to load the token from an environment variable for security.
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# --- Global Variables for Gemini ---
# !! IMPORTANT SECURITY NOTE !!
# Storing API keys directly in code is NOT recommended for production.
# Use environment variables or a secure secrets management solution.
GEMINI_API_KEY = None
SELECTED_MODEL_NAME = None # e.g., "gemini-1.5-flash"
# (https://ai.google.dev/gemini-api/docs/models/gemini for options)
gemini_model = None

# --- Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Event: Bot Ready ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('Guilds connected to:')
    for guild in bot.guilds:
        print(f'- {guild.name} (id: {guild.id})')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# --- Placeholder for Commands (will be implemented in next steps) ---

# --- Slash Command: /apikey ---
@bot.tree.command(name="apikey", description="Set the Gemini API Key (Admins Only).")
@app_commands.describe(key="Your Gemini API Key")
@commands.has_permissions(administrator=True)
async def apikey(interaction: discord.Interaction, key: str):
    """
    Sets the Gemini API Key. Only users with administrator permissions can use this.
    """
    global GEMINI_API_KEY
    GEMINI_API_KEY = key
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        await interaction.response.send_message("Gemini API Key has been set successfully!", ephemeral=True)
        print(f"Gemini API Key set by {interaction.user.name}")
    except Exception as e:
        await interaction.response.send_message(f"Failed to configure Gemini API Key: {e}", ephemeral=True)
        print(f"Error setting Gemini API Key: {e}")

@apikey.error
async def apikey_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
        print(f"Error in /apikey command: {error}")

# --- Slash Command: /model ---
@bot.tree.command(name="model", description="Select the Gemini Model to use (Admins Only).")
@app_commands.describe(model_name="Name of the Gemini model (e.g., gemini-1.5-flash)")
@commands.has_permissions(administrator=True)
async def model(interaction: discord.Interaction, model_name: str):
    """
    Sets the Gemini model to be used for queries. Only admins can use this.
    """
    global SELECTED_MODEL_NAME
    global gemini_model # The actual model instance

    # Basic validation for model name format (optional, but good practice)
    if not model_name or not isinstance(model_name, str) or not model_name.startswith("gemini-"):
        await interaction.response.send_message(
            "Invalid model format. Please use a valid Gemini model name (e.g., 'gemini-1.5-flash').",
            ephemeral=True
        )
        return

    SELECTED_MODEL_NAME = model_name

    if GEMINI_API_KEY:
        try:
            # Initialize the model instance when selected
            gemini_model = genai.GenerativeModel(SELECTED_MODEL_NAME)
            await interaction.response.send_message(f"Gemini model selected: `{SELECTED_MODEL_NAME}`!", ephemeral=False)
            print(f"Gemini model set to {SELECTED_MODEL_NAME} by {interaction.user.name}")
        except Exception as e:
            # This can happen if the API key is invalid or the model name doesn't exist
            await interaction.response.send_message(
                f"Error initializing model `{SELECTED_MODEL_NAME}`. "
                f"Please ensure your API key is correct and the model name is valid. Details: {e}",
                ephemeral=True
            )
            print(f"Error initializing Gemini model {SELECTED_MODEL_NAME}: {e}")
            # Reset to avoid using a partially configured or invalid model
            SELECTED_MODEL_NAME = None
            gemini_model = None
    else:
        # If API key is not set, we can still set the model name, but can't initialize the model object yet.
        # The model object will be initialized when /ask is called, or if /apikey is called after /model.
        await interaction.response.send_message(
            f"Gemini model name set to: `{SELECTED_MODEL_NAME}`. "
            "Note: API key is not yet set. The model will be fully initialized once the API key is provided.",
            ephemeral=False
        )
        print(f"Gemini model name set to {SELECTED_MODEL_NAME} by {interaction.user.name} (API key pending)")


@model.error
async def model_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
        print(f"Error in /model command: {error}")

# --- Slash Command: /ask ---
@bot.tree.command(name="ask", description="Ask a question to the configured Gemini model.")
@app_commands.describe(query="Your question or prompt for the Gemini model.")
async def ask(interaction: discord.Interaction, query: str):
    """
    Sends a query to the configured Gemini model and returns the response.
    """
    global gemini_model # Use the globally stored model instance

    if not GEMINI_API_KEY:
        await interaction.response.send_message(
            "The Gemini API Key has not been set. An administrator needs to use the `/apikey` command.",
            ephemeral=True
        )
        return

    if not SELECTED_MODEL_NAME:
        await interaction.response.send_message(
            "A Gemini model has not been selected. An administrator needs to use the `/model` command.",
            ephemeral=True
        )
        return

    # Attempt to initialize the model if it hasn't been already
    # (e.g., if /model was called before /apikey)
    if gemini_model is None:
        try:
            genai.configure(api_key=GEMINI_API_KEY) # Ensure genai is configured
            gemini_model = genai.GenerativeModel(SELECTED_MODEL_NAME)
            print(f"Gemini model '{SELECTED_MODEL_NAME}' initialized on demand by /ask command.")
        except Exception as e:
            await interaction.response.send_message(
                f"Error initializing Gemini model '{SELECTED_MODEL_NAME}' for your query. "
                f"Please check admin settings or contact an admin. Details: {e}",
                ephemeral=True
            )
            print(f"Failed to initialize {SELECTED_MODEL_NAME} during /ask command: {e}")
            return

    if gemini_model is None: # Should not happen if above logic is correct, but as a safeguard
        await interaction.response.send_message(
            "Model could not be initialized. Please ask an Admin to check the `/model` and `/apikey` settings.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=False) # Defer while we wait for API

    try:
        print(f"User {interaction.user.name} asked: '{query}' using model {SELECTED_MODEL_NAME}")
        # For simplicity, using generate_content. For chat history, use start_chat.
        response = await gemini_model.generate_content_async(query)

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
                print(f"Unexpected response structure: {response}")


        # Discord has a 2000 character limit per message.
        # If the response is longer, we need to split it or send as a file.
        # For now, let's truncate or send a message indicating it's too long.
        if len(full_response_text) > 1990:
            # Sending as a file for longer responses
            try:
                with open("gemini_response.txt", "w", encoding="utf-8") as f:
                    f.write(full_response_text)
                await interaction.followup.send(
                    f"The response from {SELECTED_MODEL_NAME} was too long to display directly. "
                    "Here it is as a text file:",
                    file=discord.File("gemini_response.txt")
                )
                os.remove("gemini_response.txt")
            except Exception as file_e:
                print(f"Error sending response as file: {file_e}")
                await interaction.followup.send(
                    f"The response from {SELECTED_MODEL_NAME} was too long to display directly, "
                    "and I encountered an error trying to send it as a file. "
                    "The first 1900 characters are:\n```\n"
                    f"{full_response_text[:1900]}...\n```"
                )
        else:
            await interaction.followup.send(f"**Query:** {query}\n**{SELECTED_MODEL_NAME} says:**\n{full_response_text}")

    except Exception as e:
        error_message = f"An error occurred while communicating with the Gemini API: {e}"
        print(error_message)
        # Check for specific error types if possible, e.g., API key issues, model not found, quota limits
        if "API_KEY_INVALID" in str(e) or "API_KEY_MISSING" in str(e):
             error_message += ("\nPlease ensure the Gemini API key is correctly set by an administrator using `/apikey`.")
        elif "MODEL_NOT_FOUND" in str(e) or "404" in str(e): # Simple check for model not found
             error_message += (f"\nThe model '{SELECTED_MODEL_NAME}' might be invalid or unavailable. "
                                "Please ask an administrator to check the model name using `/model`.")

        # Check if the interaction has already been responded to or deferred
        if interaction.is_done():
            await interaction.followup.send(error_message)
        else:
            # This path might not be typically hit if we defer() correctly
            await interaction.response.send_message(error_message, ephemeral=True)


# --- Run the Bot ---
if __name__ == "__main__":
    if DISCORD_BOT_TOKEN is None:
        print("Error: DISCORD_BOT_TOKEN not found. Please set it in your .env file or environment variables.")
    else:
        # Keep the main thread alive even after bot.run finishes (e.g., due to an error)
        # This is more for local development; a production setup might use a process manager.
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except discord.errors.LoginFailure:
            print("Error: Failed to log in. Please check your Discord Bot Token.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            print("Bot has shut down.")
