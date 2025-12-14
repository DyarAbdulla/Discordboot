# Memory Architecture - Persistent Conversation History

## Overview

This Discord bot implements a **two-tier memory system** for persistent conversation history:

1. **Short-term Memory**: Last N messages (default: 30) sent directly to the API
2. **Long-term Memory**: Summarized older conversations stored separately and loaded as context

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Discord Message                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Memory Manager (SQLite DB)                   │
│  ┌──────────────────┐      ┌──────────────────────┐     │
│  │ conversations    │      │ summaries            │     │
│  │ (short-term)    │      │ (long-term)         │     │
│  └──────────────────┘      └──────────────────────┘     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│         Get Conversation Context                        │
│  • Recent messages (last 30)                            │
│  • Previous summaries                                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Claude API Request                          │
│  • System prompt + summaries                            │
│  • Recent messages                                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Store Response                             │
│  • Save to database                                     │
│  • Check if summarization needed                        │
└─────────────────────────────────────────────────────────┘
```

## Database Schema

### `conversations` Table (Short-term Memory)
Stores individual messages for recent context.

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,           -- Discord user ID
    channel_id TEXT NOT NULL,        -- Channel ID (or DM channel ID)
    role TEXT NOT NULL,              -- 'user' or 'assistant'
    content TEXT NOT NULL,           -- Message content
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_channel (user_id, channel_id),
    INDEX idx_timestamp (timestamp)
)
```

### `summaries` Table (Long-term Memory)
Stores conversation summaries for persistent context.

```sql
CREATE TABLE summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,           -- Discord user ID
    channel_id TEXT NOT NULL,        -- Channel ID
    summary_text TEXT NOT NULL,       -- Summary of conversation
    message_count INTEGER NOT NULL,   -- Number of messages summarized
    start_timestamp DATETIME NOT NULL,
    end_timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_channel (user_id, channel_id)
)
```

## How It Works

### 1. Message Storage
When a user sends a message:
- User message is stored in `conversations` table
- Bot response is stored in `conversations` table
- Both are linked by `user_id` and `channel_id`

### 2. Context Loading
When generating a response:
- Load recent messages (last 30) from `conversations`
- Load all summaries from `summaries` for this user/channel
- Combine into API request:
  - **System prompt** includes summaries (long-term memory)
  - **Messages array** includes recent messages (short-term memory)

### 3. Summarization
When conversation gets too long (default: 50 messages):
- Keep last 20 messages in short-term memory
- Summarize older messages using Claude API
- Store summary in `summaries` table
- Delete summarized messages from `conversations` table

### 4. Persistence Across Restarts
- Database persists on disk (`bot_memory.db`)
- On bot restart:
  - Load summaries from `summaries` table
  - Load recent messages from `conversations` table
  - Continue conversations naturally

## Example API Request

```python
# System prompt includes summaries
system_prompt = """
You are AI Boot, a friendly Discord bot...
Previous conversation summaries (for context):
- Previous conversation summary (25 messages, 2025-12-10 to 2025-12-11): User discussed their interest in programming and asked about Python basics. They mentioned wanting to build a Discord bot.
- Previous conversation summary (30 messages, 2025-12-11 to 2025-12-12): User asked about database design and we discussed SQLite vs PostgreSQL. They're working on a project.
"""

# Messages array includes recent messages
messages = [
    {"role": "user", "content": "What did we talk about yesterday?"},
    {"role": "assistant", "content": "We discussed your Discord bot project..."},
    {"role": "user", "content": "Can you remind me about the database options?"}
]
```

## Configuration

Edit `config.json`:

```json
{
  "short_term_memory_limit": 30,    // Max recent messages to keep
  "summarize_threshold": 50,         // Summarize when this many messages
  "memory_db_path": "bot_memory.db" // Database file path
}
```

## Key Features

✅ **Persistent Memory**: Conversations survive bot restarts  
✅ **Efficient**: Only recent messages sent to API (saves tokens)  
✅ **Scalable**: Old conversations summarized, not deleted  
✅ **Per-User**: Each user has separate conversation history  
✅ **Per-Channel**: Separate history for each channel/DM  
✅ **No Fine-Tuning**: Uses context, not model training  

## Best Practices for Scaling

1. **Database Optimization**:
   - Use PostgreSQL for production (replace SQLite)
   - Add connection pooling
   - Index frequently queried columns

2. **Summarization Strategy**:
   - Summarize more aggressively (lower threshold)
   - Use cheaper model for summarization
   - Batch summarize multiple conversations

3. **Memory Limits**:
   - Set per-user message limits
   - Clean up very old summaries (>90 days)
   - Compress summaries periodically

4. **Performance**:
   - Cache recent conversations in memory
   - Async database operations
   - Background summarization task

## Files

- `utils/memory_manager.py` - Database operations and memory management
- `utils/summarizer.py` - Conversation summarization using Claude API
- `bot.py` - Integration with Discord bot
- `claude_handler.py` - Updated to accept summaries

## Important Notes

⚠️ **This is NOT fine-tuning**: The model is not being trained or modified.  
✅ **This is context injection**: Past conversations are provided as context, similar to how you might remind a friend about a previous conversation.

