#!/usr/bin/env python3
"""
Discord Gemini Bot - Demo and Test Suite
Run this to verify all improvements are working correctly
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("📦 Testing imports...")
    try:
        import discord
        import google.generativeai as genai
        import dotenv
        import bot
        print("   ✅ All required modules imported successfully")
        return True
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False

def test_validation_functions():
    """Test all validation functions"""
    print("\n🔧 Testing validation functions...")
    
    # Import bot module
    import bot
    
    # Test API key validation
    valid_keys = [
        'AIzaSyBTesting123456789012345678901234567',
        'AIzaSyDifferentKey123456789012345678901234567890'
    ]
    invalid_keys = [
        'invalid_key',
        'AIza',  # Too short
        '',
        None,
        123
    ]
    
    print("   🔑 API Key validation:")
    for key in valid_keys:
        result = bot.validate_api_key(key)
        print(f"      ✅ Valid key test: {result}")
        if not result:
            return False
    
    for key in invalid_keys:
        result = bot.validate_api_key(key)
        print(f"      ✅ Invalid key rejected: {not result}")
        if result:
            return False
    
    # Test model name validation
    valid_models = [
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-1.0-pro',
        'gemini-2.0-flash-thinking',
    ]
    invalid_models = [
        'invalid-model',
        'gemini',
        'openai-gpt4',
        '',
        None
    ]
    
    print("   🤖 Model name validation:")
    for model in valid_models:
        result = bot.validate_model_name(model)
        print(f"      ✅ Valid model '{model}': {result}")
        if not result:
            return False
    
    for model in invalid_models:
        result = bot.validate_model_name(model)
        print(f"      ✅ Invalid model '{model}' rejected: {not result}")
        if result:
            return False
    
    # Test error sanitization
    print("   🔐 Error message sanitization:")
    test_cases = [
        ('Error with AIzaSyTest123456789012345678901234567', 'API_KEY_REDACTED'),
        ('Bearer token123456 authentication failed', 'TOKEN_REDACTED'),
        ('Normal error message', None)
    ]
    
    for original, expected_redaction in test_cases:
        sanitized = bot.sanitize_error_message(original)
        if expected_redaction:
            result = expected_redaction in sanitized and original != sanitized
            print(f"      ✅ Sanitization test: {result}")
            if not result:
                print(f"         Original: {original}")
                print(f"         Sanitized: {sanitized}")
                return False
        else:
            result = original == sanitized
            print(f"      ✅ No change needed: {result}")
            if not result:
                return False
    
    return True

def test_bot_state():
    """Test the BotState class"""
    print("\n📊 Testing BotState functionality...")
    
    import bot
    from datetime import datetime, timedelta
    
    # Create a test state
    state = bot.BotState()
    
    # Test cooldown functionality
    user_id = 12345
    print("   ⏰ Cooldown system:")
    
    # Initially no cooldown
    result = not state.is_user_on_cooldown(user_id)
    print(f"      ✅ No initial cooldown: {result}")
    if not result:
        return False
    
    # Set cooldown
    state.set_user_cooldown(user_id)
    result = state.is_user_on_cooldown(user_id)
    print(f"      ✅ Cooldown active after setting: {result}")
    if not result:
        return False
    
    # Test statistics
    print("   📈 Usage statistics:")
    initial_queries = state.usage_stats["queries"]
    initial_errors = state.usage_stats["errors"]
    
    state.increment_stat("queries")
    state.increment_stat("errors")
    
    result = (state.usage_stats["queries"] == initial_queries + 1 and 
             state.usage_stats["errors"] == initial_errors + 1)
    print(f"      ✅ Statistics tracking: {result}")
    if not result:
        return False
    
    return True

def test_file_operations():
    """Test secure file operations"""
    print("\n📁 Testing secure file operations...")
    
    import bot
    import os
    import tempfile
    
    # Test secure temp file creation
    test_content = "This is test content for the secure file."
    
    try:
        temp_file = bot.create_secure_temp_file(test_content)
        print(f"      ✅ Secure temp file created: {os.path.exists(temp_file)}")
        
        # Verify content
        with open(temp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result = content == test_content
        print(f"      ✅ Content preserved: {result}")
        
        # Clean up
        os.remove(temp_file)
        print(f"      ✅ File cleanup successful: {not os.path.exists(temp_file)}")
        
        return result
        
    except Exception as e:
        print(f"      ❌ File operation error: {e}")
        return False

def test_enhanced_features():
    """Test the new enhanced features"""
    print("\n🆕 Testing enhanced features...")
    
    import bot
    from datetime import datetime
    
    # Test UserPreferences dataclass
    prefs = bot.UserPreferences()
    print(f"      ✅ Default preferences created: {prefs.temperature == bot.DEFAULT_TEMPERATURE}")
    
    # Test ConversationHistory
    conv_history = bot.ConversationHistory()
    conv_history.add_message(12345, "user", "Hello")
    conv_history.add_message(12345, "model", "Hi there!")
    
    history = conv_history.get_history(12345)
    result = len(history) == 2 and history[0].content == "Hello"
    print(f"      ✅ Conversation history tracking: {result}")
    if not result:
        return False
    
    # Test content filtering
    safe_query = "What is the weather like?"
    unsafe_query = "How to make something dangerous"
    
    safe_result, _ = bot.check_content_filter(safe_query)
    unsafe_result, _ = bot.check_content_filter(unsafe_query)
    
    result = safe_result and not unsafe_result
    print(f"      ✅ Content filtering: {result}")
    if not result:
        return False
    
    # Test response formatting
    test_response = "This is a test response"
    formatted = bot.format_response_by_preference(test_response, "detailed")
    result = "Detailed Response" in formatted
    print(f"      ✅ Response formatting: {result}")
    if not result:
        return False
    
    # Test bot state enhancements
    state = bot.BotState()
    state.update_user_preference(12345, "temperature", 0.8)
    user_prefs = state.get_user_preferences(12345)
    result = user_prefs.temperature == 0.8
    print(f"      ✅ User preference management: {result}")
    if not result:
        return False
    
    return True

def test_security_features():
    """Test security features"""
    print("\n🛡️ Testing security features...")
    
    # Run the security scanner
    import subprocess
    try:
        result = subprocess.run([sys.executable, 'security_check.py'], 
                              capture_output=True, text=True, cwd='.')
        
        success = result.returncode == 0
        print(f"      ✅ Security scan passed: {success}")
        
        if not success:
            print(f"      Security scan output:\n{result.stdout}")
            print(f"      Security scan errors:\n{result.stderr}")
        
        return success
        
    except Exception as e:
        print(f"      ❌ Security scan error: {e}")
        return False

def main():
    """Run all tests"""
    print("🤖 Discord Gemini Bot - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Validation Functions", test_validation_functions),
        ("Bot State Management", test_bot_state),
        ("File Operations", test_file_operations),
        ("Enhanced Features", test_enhanced_features),
        ("Security Features", test_security_features),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n🧪 Running {name}...")
        try:
            if test_func():
                print(f"   ✅ {name} PASSED")
                passed += 1
            else:
                print(f"   ❌ {name} FAILED")
        except Exception as e:
            print(f"   💥 {name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The bot is ready for deployment.")
        print("\n🚀 Quick Start:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your DISCORD_BOT_TOKEN to .env")
        print("   3. Run: python3 bot.py")
        print("   4. Use /apikey to set your Gemini API key (Admin only)")
        print("   5. Use /model to select a model (Admin only)")
        print("   6. Start asking questions with /ask!")
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())