# Memory System Usage Example

## How the Memory System Works in Practice

### Example Conversation Flow

**Day 1 - Initial Conversation:**
```
User: "Hi! I'm learning Python"
Bot: "That's great! Python is an excellent language to start with..."
[Stored in conversations table]
```

**Day 2 - Bot Restarts:**
```
User: "What did we talk about yesterday?"
Bot: "We discussed your Python learning journey..."
[Bot loads summary from database, remembers context]
```

**After 50+ Messages:**
```
[System automatically summarizes old messages]
[Keeps last 20 messages in short-term memory]
[Stores summary in summaries table]
[Deletes old messages from conversations table]
```

### Database Queries

**Get Recent Messages:**
```python
messages = memory_manager.get_recent_messages(
    user_id="123456789",
    channel_id="987654321",
    limit=30
)
# Returns: [{"role": "user", "content": "..."}, ...]
```

**Get Conversation Context:**
```python
messages, summaries = memory_manager.get_conversation_context(
    user_id="123456789",
    channel_id="987654321"
)
# Returns:
# - messages: Recent messages for API
# - summaries: List of summary strings for system prompt
```

**Create Summary:**
```python
summary_id = memory_manager.create_summary(
    user_id="123456789",
    channel_id="987654321",
    summary_text="User discussed Python learning...",
    message_count=25,
    start_timestamp=datetime(2025, 12, 10),
    end_timestamp=datetime(2025, 12, 11)
)
```

### API Request Example

**What gets sent to Claude API:**

```python
# System Prompt (includes summaries)
system_prompt = """
You are AI Boot, a friendly Discord bot...

Previous conversation summaries (for context):
- Previous conversation summary (25 messages, 2025-12-10 to 2025-12-11): 
  User discussed their interest in Python programming and asked about 
  basic concepts. They mentioned wanting to build a Discord bot.
- Previous conversation summary (30 messages, 2025-12-11 to 2025-12-12): 
  User asked about database design and we discussed SQLite vs PostgreSQL. 
  They're working on a project that needs persistent storage.
"""

# Messages Array (recent messages)
messages = [
    {"role": "user", "content": "Can you remind me what we discussed about databases?"},
    {"role": "assistant", "content": "We talked about SQLite vs PostgreSQL..."},
    {"role": "user", "content": "Which one should I use for my bot?"}
]
```

### Testing the Memory System

**1. Test Message Storage:**
```python
from utils.memory_manager import MemoryManager

mm = MemoryManager()
mm.add_message("user123", "channel456", "user", "Hello!")
mm.add_message("user123", "channel456", "assistant", "Hi there!")
```

**2. Test Context Retrieval:**
```python
messages, summaries = mm.get_conversation_context("user123", "channel456")
print(f"Recent messages: {len(messages)}")
print(f"Summaries: {len(summaries)}")
```

**3. Test Statistics:**
```python
stats = mm.get_stats()
print(f"Total messages: {stats['total_messages']}")
print(f"Total summaries: {stats['total_summaries']}")
print(f"Unique users: {stats['unique_users']}")
```

## Integration Points

### In bot.py

The memory system is automatically integrated:

1. **Message Received** → Stored in database
2. **Response Generated** → Uses context from database
3. **Response Sent** → Stored in database
4. **Too Many Messages** → Auto-summarizes old ones

### Manual Summarization

You can manually trigger summarization:

```python
# In bot.py, call:
await bot._summarize_old_messages(user_id, channel_id)
```

### Cleanup

Old messages are automatically cleaned up:

```python
# Delete messages older than 30 days
deleted = memory_manager.cleanup_old_messages(days=30)
```

## Database File Location

- **Default**: `bot_memory.db` (in project root)
- **Configurable**: Set `memory_db_path` in `config.json`

## Important Notes

✅ **Persistent**: Database survives bot restarts  
✅ **Per-User**: Each user has separate history  
✅ **Per-Channel**: Separate history per channel/DM  
✅ **Efficient**: Only recent messages sent to API  
✅ **Scalable**: Old conversations summarized, not deleted  

⚠️ **Not Fine-Tuning**: Model is not being trained  
✅ **Context Injection**: Past conversations provided as context  






