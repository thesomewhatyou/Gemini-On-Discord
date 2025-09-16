#!/bin/bash
# Discord Gemini Bot Deployment Script
# This script helps set up and deploy the bot

set -e  # Exit on any error

echo "🤖 Discord Gemini Bot Deployment Script"
echo "========================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or newer."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi

echo "✅ pip3 found"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Run security check
echo ""
echo "🔒 Running security scan..."
python3 security_check.py

# Run test suite
echo ""
echo "🧪 Running test suite..."
python3 test_suite.py

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  .env file not found!"
    echo "📋 Creating .env from template..."
    cp .env.example .env
    echo "✅ .env file created from template"
    echo ""
    echo "🔧 Please edit .env and add your Discord bot token:"
    echo "   DISCORD_BOT_TOKEN=your_actual_token_here"
    echo ""
    echo "📖 To get a Discord bot token:"
    echo "   1. Go to https://discord.com/developers/applications"
    echo "   2. Create a new application"
    echo "   3. Go to 'Bot' section"
    echo "   4. Create a bot and copy the token"
    echo "   5. Invite the bot to your server with appropriate permissions"
    echo ""
else
    echo "✅ .env file found"
fi

echo ""
echo "🎉 Deployment preparation complete!"
echo ""
echo "🚀 To start the bot:"
echo "   python3 bot.py"
echo ""
echo "💡 First-time setup (after starting the bot):"
echo "   1. Use /apikey <your_gemini_api_key> (Admin only)"
echo "   2. Use /model gemini-1.5-flash (Admin only)"
echo "   3. Users can now use /ask <question>"
echo ""
echo "📊 Available commands:"
echo "   /ask      - Ask the AI a question (All users)"
echo "   /status   - Check bot status (All users)"
echo "   /models   - List available models (All users)"
echo "   /help     - Show help information (All users)"
echo "   /apikey   - Set API key (Admins only)"
echo "   /model    - Select model (Admins only)"
echo ""
echo "🛡️ Security features enabled:"
echo "   ✅ Input validation and sanitization"
echo "   ✅ Rate limiting (5-second cooldown per user)"
echo "   ✅ Error message sanitization"
echo "   ✅ Secure file handling"
echo "   ✅ Memory-only API key storage"
echo ""
echo "📋 For troubleshooting, check:"
echo "   - bot.log for detailed logs"
echo "   - Run 'python3 security_check.py' for security scan"
echo "   - Run 'python3 test_suite.py' to verify functionality"