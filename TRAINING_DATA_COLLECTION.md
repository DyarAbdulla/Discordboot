# Training Data Collection Guide

## 🎯 Overview

Your Discord bot automatically collects conversation data perfect for training your own AI model when API limits run out!

## ✅ What's Already Implemented

### 1. Automatic Conversation Logging ✅
- Every user message is saved
- Every bot response is saved
- Happens automatically - no configuration needed

### 2. Complete Metadata Tracking ✅
- User ID and username
- Channel ID
- Timestamp
- Tokens used (for cost tracking)
- Model used (claude-3-5-haiku, static_fallback, etc.)

### 3. Commands for Data Access ✅
- `!export` - Export all conversations to CSV
- `!stats` - View statistics
- `!history [user]` - View conversation history

### 4. Database Storage ✅
- SQLite database: `conversation_logs.db`
- PostgreSQL support (Railway)
- Persistent storage

---

## 📊 Data Format

### Database Schema

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,              -- Discord user ID
    user_name TEXT NOT NULL,            -- Discord username
    channel_id TEXT NOT NULL,           -- Channel ID
    user_message TEXT NOT NULL,         -- User's message
    bot_response TEXT NOT NULL,          -- Bot's response
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER DEFAULT 0,       -- Tokens used
    model_used TEXT DEFAULT 'unknown'   -- Model name
);
```

### CSV Export Format

When you use `!export`, you get a CSV file with:

| Column | Description |
|--------|-------------|
| `id` | Conversation ID |
| `user_id` | Discord user ID |
| `user_name` | Discord username |
| `channel_id` | Channel ID |
| `user_message` | What user said |
| `bot_response` | What bot replied |
| `timestamp` | When it happened |
| `tokens_used` | Tokens used |
| `model_used` | Model name |

---

## 📥 Exporting Data for Training

### Method 1: Bot Command (Easiest)

```
!export
```

- Creates CSV file with all conversations
- Sent as Discord file attachment
- Download and use for training

### Method 2: Backup Script

```bash
# Export to CSV
python backup_sqlite.py csv

# Or backup database file
python backup_sqlite.py db

# Or both
python backup_sqlite.py all
```

### Method 3: Direct Database Access

```python
from conversation_logger import ConversationLogger

logger = ConversationLogger()
conversations = logger.get_all_conversations()

# Save to CSV
logger.export_to_csv("training_data.csv")
```

---

## 🎓 Preparing Data for Training

### Step 1: Export Data

```bash
# Use bot command
!export

# Or use script
python backup_sqlite.py csv
```

### Step 2: Clean Data (Optional)

You may want to:
- Remove test conversations
- Filter by model (only use Claude responses, not fallback)
- Remove sensitive information
- Format for your training framework

### Step 3: Format for Training

Common formats:

**JSON Format:**
```json
[
  {
    "user": "What is AI?",
    "assistant": "AI stands for Artificial Intelligence..."
  },
  {
    "user": "How does it work?",
    "assistant": "AI works by..."
  }
]
```

**CSV Format (already provided):**
```csv
user_message,bot_response
"What is AI?","AI stands for Artificial Intelligence..."
"How does it work?","AI works by..."
```

**Text Format:**
```
User: What is AI?
Assistant: AI stands for Artificial Intelligence...

User: How does it work?
Assistant: AI works by...
```

---

## 📈 Statistics

### View Current Data

```
!stats
```

Shows:
- Total conversations collected
- Total users
- Recent activity
- Tokens used
- Models breakdown

### View History

```
!history              # Your conversations
!history @username    # Specific user
```

---

## 🔄 Continuous Collection

### Automatic Collection

The bot **automatically collects data**:
- Every conversation is saved
- No manual intervention needed
- Data accumulates over time

### Check Collection Status

```bash
# View statistics
python backup_sqlite.py stats

# Or use bot command
!stats
```

---

## 💾 Backup Strategy

### Regular Backups

**Recommended:** Backup weekly or monthly

```bash
# Weekly backup script
python backup_sqlite.py csv
# Upload to cloud storage (S3, Google Drive, etc.)
```

### Railway Deployment

**If using Railway:**
- Use PostgreSQL (persistent)
- Or set up automated backups
- See `RAILWAY_DEPLOYMENT_GUIDE.md`

---

## 🎯 Training Your Model

### When API Limits Run Out

1. **Export all data:**
   ```
   !export
   ```

2. **Prepare training data:**
   - Clean and format data
   - Split into train/validation sets
   - Remove low-quality conversations

3. **Train your model:**
   - Use your preferred framework (PyTorch, TensorFlow, etc.)
   - Fine-tune a base model
   - Use your collected conversations

### Data Quality Tips

- **Filter by model:** Only use `claude-3-5-haiku` responses (not `static_fallback`)
- **Filter by tokens:** Remove very short or very long conversations
- **Filter by users:** Remove test accounts or bots
- **Clean text:** Remove Discord formatting, mentions, etc.

---

## 📊 Example Training Data

### Raw Data (from database)
```
user_message: "What is AI?"
bot_response: "AI stands for Artificial Intelligence..."
tokens_used: 45
model_used: "claude-3-5-haiku"
```

### Formatted for Training
```json
{
  "messages": [
    {"role": "user", "content": "What is AI?"},
    {"role": "assistant", "content": "AI stands for Artificial Intelligence..."}
  ]
}
```

---

## 🔍 Data Analysis

### Check Data Quality

```python
from conversation_logger import ConversationLogger

logger = ConversationLogger()
conversations = logger.get_all_conversations()

# Filter by model
claude_conversations = [c for c in conversations if c['model_used'] == 'claude-3-5-haiku']

# Filter by tokens
quality_conversations = [c for c in claude_conversations if 10 < c['tokens_used'] < 500]

# Count
print(f"Total: {len(conversations)}")
print(f"Claude: {len(claude_conversations)}")
print(f"Quality: {len(quality_conversations)}")
```

---

## ✅ Checklist

### Setup
- [x] Conversation logging enabled
- [x] Auto-save after every conversation
- [x] Commands available (`!export`, `!stats`, `!history`)

### Collection
- [ ] Bot running and collecting conversations
- [ ] Regular backups scheduled
- [ ] Data quality checked

### Training Preparation
- [ ] Export data (`!export`)
- [ ] Clean and format data
- [ ] Prepare for training framework
- [ ] Ready to train!

---

## 📚 Related Files

- `conversation_logger.py` - Database logger
- `backup_sqlite.py` - Backup script
- `SQLITE_RAILWAY_SETUP.md` - SQLite setup
- `RAILWAY_POSTGRESQL_SETUP.md` - PostgreSQL setup

---

## 🎉 Summary

**Your bot is already collecting training data!**

✅ Every conversation is saved automatically  
✅ Complete metadata tracked  
✅ Easy export with `!export` command  
✅ Ready for model training  

**Just let the bot run and collect conversations!**

When you're ready to train:
1. Run `!export`
2. Download CSV file
3. Format for your training framework
4. Train your model!

---

**Happy training! 🚀**


