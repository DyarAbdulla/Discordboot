# Kurdish Language Support - Implementation Guide

## ✅ Implementation Complete!

Your Discord bot now has comprehensive Kurdish language support with automatic detection and culturally appropriate responses.

## 🌍 Features Implemented

### 1. **Kurdish Language Detection**
   - **Sorani (Central Kurdish)**: Detects Arabic script Kurdish (ئە, پ, ژ, گ, چ, ۆ, ش)
   - **Kurmanji (Northern Kurdish)**: Detects Latin script Kurdish (ç, ş, ê, î, û)
   - **Automatic Detection**: Detects Kurdish from user messages
   - **Confidence Scoring**: Provides confidence scores for detection accuracy
   - **Pattern Matching**: Uses common Kurdish words, phrases, and characters

### 2. **Intelligent Response System**
   - **Full Kurdish Responses**: Bot responds completely in Kurdish when Kurdish is detected
   - **Dialect Matching**: Matches the user's dialect (Sorani or Kurmanji)
   - **Cultural Appropriateness**: Uses culturally appropriate greetings and expressions
   - **Mixed Language Support**: Handles Kurdish-English mixed conversations

### 3. **Kurdish Greetings & Expressions**
   - **Sorani Greetings**: سڵاو (hello), چۆنی (how are you), سوپاس (thanks)
   - **Kurmanji Greetings**: Merheba (hello), Çawa yî (how are you), Spas (thanks)
   - **Contextual Responses**: Appropriate responses for different situations
   - **Fallback Support**: Kurdish fallback responses when Claude API is unavailable

### 4. **Language Preference Storage**
   - **Per-User Memory**: Remembers each user's language preference
   - **Per-Channel Memory**: Different language preferences per channel
   - **Persistent Storage**: Language preferences stored in database
   - **Automatic Updates**: Updates preference when user switches languages

### 5. **Claude AI Integration**
   - **Enhanced System Prompt**: Includes Kurdish examples and instructions
   - **Language Context**: Passes detected language to Claude API
   - **Dialect Awareness**: Claude knows which Kurdish dialect to use
   - **Natural Responses**: Claude generates natural Kurdish responses

## 📁 Files Created/Modified

### New Files:
1. **`utils/kurdish_detector.py`** - Kurdish language detection utility
   - Detects Sorani and Kurmanji dialects
   - Provides confidence scores
   - Includes Kurdish greetings and expressions

### Modified Files:
1. **`claude_handler.py`** - Updated system prompt with Kurdish support
   - Added Kurdish language guidelines
   - Included Kurdish response examples
   - Added language detection parameters

2. **`bot.py`** - Integrated Kurdish detection
   - Detects Kurdish in user messages
   - Stores language preferences
   - Passes language context to Claude

3. **`responses.py`** - Added Kurdish fallback responses
   - Sorani responses dictionary
   - Kurmanji responses dictionary
   - Language-aware response selection

4. **`cogs/slash_commands.py`** - Updated slash commands
   - Kurdish detection in `/ask` command
   - Language-aware responses

5. **`utils/memory_manager.py`** - Added preference storage
   - `set_user_preference()` method
   - `get_user_preference()` method
   - User preferences table in database

## 🎯 How It Works

### Detection Flow:
1. User sends a message in Kurdish
2. Bot detects Kurdish using pattern matching
3. Determines dialect (Sorani/Kurmanji)
4. Stores language preference for user/channel
5. Passes language context to Claude API
6. Claude responds in Kurdish matching the dialect

### Response Flow:
1. **Claude Available**: Uses Claude AI with Kurdish system prompt
2. **Claude Unavailable**: Uses Kurdish fallback responses
3. **Language Matching**: Always matches user's language
4. **Dialect Matching**: Matches user's Kurdish dialect

## 📝 Kurdish Examples

### Sorani Examples:
- **User**: "سڵاو"
- **Bot**: "سڵاو! بەخێربێیت 👋 چۆن دەتوانم یارمەتیت بدەم؟"

- **User**: "چۆنی؟"
- **Bot**: "من باشم، سوپاس بۆ پرسیارەکەت! تۆ چۆنی؟ 😊"

### Kurmanji Examples:
- **User**: "Merheba"
- **Bot**: "Merheba! Bi xêr hatî 👋 Çawa dikarim alîkariya te bikim?"

- **User**: "Çawa yî?"
- **Bot**: "Ez baş im, spas ji bo pirsê te! Tu çawa yî? 😊"

## 🔧 Configuration

### Language Detection:
- Automatic detection on every message
- Confidence threshold: 0.4+ for detection
- Stores preference after detection

### Preferences Stored:
- `language`: 'ku', 'en', 'ar'
- `kurdish_dialect`: 'sorani', 'kurmanji'

### Database:
- Preferences stored in `user_preferences` table
- Per-user, per-channel isolation
- Automatic updates on language change

## 🚀 Usage

### For Users:
1. Simply speak Kurdish to the bot
2. Bot automatically detects and responds in Kurdish
3. Language preference is remembered for future conversations
4. Works with both Sorani and Kurmanji dialects

### For Developers:
```python
# Detect Kurdish
from utils.kurdish_detector import KurdishDetector

result = KurdishDetector.detect_kurdish("سڵاو")
# Returns: ('sorani', 0.85)

# Get Kurdish greeting
greeting = KurdishDetector.get_kurdish_greeting('sorani')
# Returns: "سڵاو"
```

## 🌟 Features

### ✅ Implemented:
- ✅ Sorani (Arabic script) detection
- ✅ Kurmanji (Latin script) detection
- ✅ Automatic language detection
- ✅ Full Kurdish responses
- ✅ Dialect matching
- ✅ Cultural greetings
- ✅ Language preference storage
- ✅ Mixed language support
- ✅ Fallback responses
- ✅ Claude AI integration

### 🎨 Cultural Appropriateness:
- Warm and hospitable tone (Kurdish cultural value)
- Appropriate greetings for time of day
- Respectful expressions
- Natural conversational flow

## 📊 Detection Accuracy

The detector uses multiple methods:
1. **Greeting Detection**: High confidence (3x weight)
2. **Pattern Matching**: Common Kurdish words/phrases
3. **Character Detection**: Kurdish-specific characters
4. **Confidence Scoring**: Weighted scoring system

## 🔮 Future Enhancements

Potential improvements:
- More Kurdish expressions
- Regional dialect variations
- Kurdish-to-English translation
- Kurdish command support
- Kurdish help documentation

## 📚 Resources

- Kurdish language patterns
- Cultural expressions
- Greeting variations
- Common phrases

---

**Made with ❤️ for the Kurdish community**


