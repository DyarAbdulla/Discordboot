# Persistent Memory Feature - Implementation Guide

## ✅ Implementation Complete!

Your Discord bot now has powerful persistent memory features that remember users across sessions and personalize responses!

## 🎯 Features Implemented

### 1. **User Facts Storage**
   - Stores important facts about users (name, interests, preferences)
   - Automatic fact extraction from conversations
   - Manual fact teaching via `!teach` command
   - Importance scoring for facts

### 2. **Memory Commands**
   - `!remember` - Show what bot remembers about you
   - `!forget` - Clear your memory (with confirmation)
   - `!teach [fact]` - Teach bot something about you

### 3. **Automatic Fact Extraction**
   - Extracts facts from natural conversation
   - Recognizes patterns like "my name is", "i like", "i'm from"
   - Stores facts with appropriate importance scores

### 4. **Personalized Responses**
   - AI uses stored facts in responses
   - Natural integration without mentioning stored facts
   - Context-aware personalization

### 5. **Database Storage**
   - `user_facts` table for storing facts
   - `user_preferences` table for preferences
   - Persistent across bot restarts
   - Per-user and per-channel isolation

## 📁 Files Created/Modified

### Modified Files:
1. **`utils/memory_manager.py`**
   - Added `user_facts` table to database schema
   - Added `add_user_fact()` method
   - Added `get_user_fact()` method
   - Added `get_all_user_facts()` method
   - Added `delete_user_fact()` method
   - Added `clear_user_memory()` method
   - Added `get_user_memory_summary()` method

2. **`bot.py`**
   - Added `!remember` command
   - Added `!forget` command
   - Added `!teach` command
   - Added `_extract_and_store_facts()` method
   - Enhanced Claude API calls to include user facts
   - Automatic fact extraction from messages

3. **`claude_handler.py`**
   - Added `user_facts` parameter to `generate_response()`
   - Enhanced system prompt to include user facts
   - Natural integration of facts into responses

4. **`cogs/slash_commands.py`**
   - Updated `/ask` command to include user facts

## 🎯 How It Works

### Fact Storage:
1. User says something like "My name is John"
2. Bot automatically extracts fact: `name = John`
3. Stores in database with importance score
4. Fact available for future conversations

### Fact Usage:
1. User asks a question
2. Bot retrieves user facts from database
3. Includes facts in Claude API system prompt
4. Claude uses facts naturally in response

### Memory Commands:
- `!remember` - Shows all stored facts and preferences
- `!forget confirm` - Clears all memory (requires confirmation)
- `!teach [fact]` - Manually teach bot a fact

## 📊 Database Schema

### `user_facts` Table:
```sql
CREATE TABLE user_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    fact_key TEXT NOT NULL,
    fact_value TEXT NOT NULL,
    importance_score REAL DEFAULT 0.5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, channel_id, fact_key)
)
```

## 🔧 Commands

### `!remember`
Shows what the bot remembers about you:
- All stored facts
- User preferences
- Conversation statistics

### `!forget`
Clears your memory:
- Requires `!forget confirm` to execute
- Deletes facts, preferences, conversations, summaries
- Cannot be undone

### `!teach [fact]`
Teach bot something about you:
- Examples:
  - `!teach My name is John`
  - `!teach I like programming`
  - `!teach My favorite color is blue`
  - `!teach I'm from New York`

## 🎯 Automatic Fact Extraction

The bot automatically extracts facts from messages containing:
- "my name is" → stores as `name`
- "i am" / "i'm" → stores as `name`
- "call me" → stores as `name`
- "i like" → stores as `likes`
- "i love" → stores as `loves`
- "i prefer" → stores as `preference`
- "my favorite X is Y" → stores as `favorite_X`
- "i'm from" / "i live in" → stores as `location`
- "i work as" / "i'm a" → stores as `occupation`
- "i'm allergic to" → stores as `allergy`

## 💡 Example Usage

### Teaching Facts:
```
User: !teach My name is John
Bot: ✅ Learned! I'll remember: Name = John

User: !teach I like programming
Bot: ✅ Learned! I'll remember: Likes = programming
```

### Automatic Extraction:
```
User: My name is Sarah and I'm from London
Bot: [Responds normally, but also stores:]
     - name = Sarah
     - location = London
```

### Using Memory:
```
User: What's my name?
Bot: Your name is John! [Uses stored fact]

User: What do I like?
Bot: You like programming! [Uses stored fact]
```

### Viewing Memory:
```
User: !remember
Bot: 🧠 What I Remember About UserName
     📚 Facts I Know:
     ⭐ Name: John
     📝 Likes: programming
     📝 Location: London
     
     ⚙️ Preferences:
     • Language: en
     
     💬 Conversation History:
     I've had 15 conversation(s) with you
```

## 🌟 Benefits

### For Users:
- Bot remembers personal information
- More personalized conversations
- Continuous experience across sessions
- Easy to teach and manage facts

### For Bot:
- Better user experience
- More natural conversations
- Context-aware responses
- Improved engagement

## 🔍 Technical Details

### Fact Importance Scores:
- **High (0.8-0.9)**: Name, location, allergies
- **Medium (0.6-0.7)**: Likes, preferences, occupation
- **Low (0.5)**: General facts

### Fact Storage:
- Per-user and per-channel isolation
- Facts persist across bot restarts
- Automatic updates when facts change
- Last accessed tracking

### Integration:
- Facts included in Claude system prompt
- Natural usage without mentioning storage
- Limited to top 15 facts per request
- Token-efficient implementation

## 📝 Example Responses

### Before (No Memory):
```
User: What's my name?
Bot: I don't know your name. What would you like me to call you?
```

### After (With Memory):
```
User: What's my name?
Bot: Your name is John! How can I help you today, John?
```

### Personalized Response:
```
User: What should I do today?
Bot: Since you like programming, John, maybe work on that project you mentioned? 
     Or explore something new in London!
```

## 🚀 Future Enhancements

Potential improvements:
- Fact expiration/decay
- Fact confidence scores
- Multi-user fact management
- Fact export/import
- Fact sharing between channels

---

**Made with ❤️ for personalized conversations**


