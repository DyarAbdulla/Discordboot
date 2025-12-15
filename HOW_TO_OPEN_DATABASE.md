# How to Open the Bot Database

The bot uses SQLite database: **`bot_memory.db`**

## 📊 Database Schema

The database has 2 tables:

### 1. `conversations` - Individual Messages
- `id` - Message ID
- `user_id` - Discord user ID
- `channel_id` - Discord channel ID
- `role` - 'user' or 'assistant'
- `content` - Message text
- `importance_score` - Score (0.0 to 1.0)
- `timestamp` - When message was created
- `last_accessed` - Last time message was accessed

### 2. `summaries` - Conversation Summaries
- `id` - Summary ID
- `user_id` - Discord user ID
- `channel_id` - Discord channel ID
- `summary_text` - Summary content
- `message_count` - Number of messages summarized
- `importance_score` - Score (0.0 to 1.0)
- `start_timestamp` - First message timestamp
- `end_timestamp` - Last message timestamp
- `created_at` - When summary was created
- `last_accessed` - Last time summary was accessed

---

## 🔧 Method 1: DB Browser for SQLite (GUI - Recommended)

**Best for beginners!**

1. **Download DB Browser:**
   - Go to: https://sqlitebrowser.org/
   - Download "DB Browser for SQLite"
   - Install it

2. **Open Database:**
   - Open DB Browser
   - Click "Open Database"
   - Navigate to: `c:\discord boot\ai boot\bot_memory.db`
   - Click "Open"

3. **View Data:**
   - Click "Browse Data" tab
   - Select table: `conversations` or `summaries`
   - See all messages/summaries!

---

## 💻 Method 2: Command Line (SQLite)

**For advanced users**

### Windows PowerShell:

```powershell
# Navigate to bot folder
cd "c:\discord boot\ai boot"

# Open SQLite (if installed)
sqlite3 bot_memory.db
```

### If SQLite not installed:

1. **Download SQLite:**
   - Go to: https://www.sqlite.org/download.html
   - Download "sqlite-tools-win-x64" (for Windows)
   - Extract `sqlite3.exe` to a folder in your PATH

2. **Use SQLite commands:**

```sql
-- Open database
sqlite3 bot_memory.db

-- View all tables
.tables

-- View conversations table
SELECT * FROM conversations;

-- View summaries table
SELECT * FROM summaries;

-- Count messages per user
SELECT user_id, COUNT(*) as message_count 
FROM conversations 
GROUP BY user_id;

-- View recent messages
SELECT * FROM conversations 
ORDER BY timestamp DESC 
LIMIT 10;

-- Exit SQLite
.quit
```

---

## 🐍 Method 3: Python Script

**Easy way using Python:**

Create a file `view_database.py`:

```python
import sqlite3
import json
from datetime import datetime

# Connect to database
conn = sqlite3.connect('bot_memory.db')
cursor = conn.cursor()

# View conversations
print("=== CONVERSATIONS ===")
cursor.execute("SELECT * FROM conversations ORDER BY timestamp DESC LIMIT 10")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, User: {row[1]}, Role: {row[3]}")
    print(f"Content: {row[4][:100]}...")
    print(f"Timestamp: {row[5]}")
    print("-" * 50)

# View summaries
print("\n=== SUMMARIES ===")
cursor.execute("SELECT * FROM summaries ORDER BY created_at DESC LIMIT 5")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, User: {row[1]}")
    print(f"Summary: {row[3][:200]}...")
    print(f"Messages: {row[4]}, Created: {row[7]}")
    print("-" * 50)

conn.close()
```

Run it:
```powershell
python view_database.py
```

---

## 📝 Useful SQL Queries

```sql
-- View all conversations for a specific user
SELECT * FROM conversations WHERE user_id = 'USER_ID_HERE';

-- View all summaries
SELECT * FROM summaries;

-- Count total messages
SELECT COUNT(*) FROM conversations;

-- View messages with high importance
SELECT * FROM conversations WHERE importance_score > 0.7;

-- View recent summaries
SELECT * FROM summaries ORDER BY created_at DESC LIMIT 10;

-- Delete old messages (older than 30 days)
DELETE FROM conversations WHERE timestamp < datetime('now', '-30 days');
```

---

## ⚠️ Important Notes

1. **Database Location:**
   - Default: `bot_memory.db` (in bot folder)
   - Can be changed in `config.json`: `"memory_db_path": "bot_memory.db"`

2. **Database Created:**
   - Database is created automatically when bot starts
   - If database doesn't exist, run the bot first: `python bot.py`

3. **Backup Database:**
   ```powershell
   # Copy database file
   Copy-Item bot_memory.db bot_memory_backup.db
   ```

4. **Clear Database:**
   - Stop the bot
   - Delete `bot_memory.db` file
   - Bot will create a new empty database on next start

---

## 🎯 Quick Start

**Easiest way:**
1. Download DB Browser: https://sqlitebrowser.org/
2. Open `bot_memory.db` file
3. Browse data!

**Need help?** Check the database schema above to understand the columns.



