# Conversation Logging System

## Overview

The bot now permanently saves all conversations to a SQLite database for training data collection and analysis.

## Database

**File:** `conversation_logs.db`

**Table:** `conversations`

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment primary key |
| `user_id` | TEXT | Discord user ID |
| `user_name` | TEXT | Discord username/display name |
| `channel_id` | TEXT | Channel ID where conversation happened |
| `user_message` | TEXT | What the user said |
| `bot_response` | TEXT | What the bot replied |
| `timestamp` | DATETIME | When conversation happened |
| `tokens_used` | INTEGER | Number of tokens used (0 for static responses) |
| `model_used` | TEXT | Model name (e.g., 'claude-3-5-haiku-20241022', 'static_fallback') |

## Features

### 1. Automatic Logging
- Every conversation is automatically saved
- Includes user info, messages, tokens, and model used
- Persists across bot restarts

### 2. Commands

#### `!export`
Exports all conversations to a CSV file.

**Usage:**
```
!export
```

**Output:**
- Creates `conversation_export_YYYYMMDD_HHMMSS.csv`
- Contains all conversation data
- Sent as Discord file attachment

#### `!stats`
Shows conversation statistics.

**Usage:**
```
!stats
```

**Shows:**
- Total conversations
- Total unique users
- Recent conversations (last 24 hours)
- Total tokens used
- Models used breakdown

#### `!history [user]`
Shows conversation history for a user.

**Usage:**
```
!history              # Show your own history
!history @username    # Show history for mentioned user
!history username      # Show history for username
```

**Shows:**
- Last 10 conversations
- User message and bot response
- Timestamp, tokens, and model used

## Files

- **`conversation_logger.py`** - Database operations and logging
- **`bot.py`** - Updated to save conversations automatically
- **`conversation_logs.db`** - SQLite database (created automatically)

## Usage Example

```python
# Conversations are automatically logged when bot responds
# No code changes needed - it happens automatically!

# View stats
!stats

# Export all data
!export

# View your history
!history
```

## Benefits

1. **Training Data Collection** - All conversations saved for future model training
2. **Never Lose Data** - Conversations persist even after bot restarts
3. **Analytics** - Track usage, tokens, and model performance
4. **User History** - Review past conversations
5. **Export** - Easy CSV export for analysis

## Database Location

The database file `conversation_logs.db` is created in the bot's root directory.

To view the database:
- Use DB Browser for SQLite (GUI)
- Use `sqlite3` command line tool
- Use Python script: `python view_database.py`

## Notes

- Database is separate from memory system (`bot_memory.db`)
- This is for permanent logging, memory system is for conversation context
- Both systems work together independently
- CSV exports include all fields for easy analysis



