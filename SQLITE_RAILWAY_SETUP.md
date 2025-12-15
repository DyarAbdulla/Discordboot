# SQLite Database Setup for Railway

## ✅ Current Status

Your bot **already has SQLite conversation logging** implemented! It automatically:
- ✅ Saves every user message and bot response
- ✅ Tracks user info, timestamps, tokens used
- ✅ Has commands: `!export`, `!stats`, `!history`
- ✅ Auto-saves after every conversation

## 📊 Database File

**File:** `conversation_logs.db`

**Location:** Bot's working directory (same folder as `bot.py`)

**Schema:**
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER DEFAULT 0,
    model_used TEXT DEFAULT 'unknown'
);
```

---

## ⚠️ Railway Persistence Issue

**Problem:** Railway uses ephemeral storage. SQLite files are **deleted on every deployment**.

**Solutions:**

### Option 1: Use PostgreSQL (RECOMMENDED)

PostgreSQL is persistent and automatically backed up. See `RAILWAY_POSTGRESQL_SETUP.md`.

**To switch to PostgreSQL:**
1. Add PostgreSQL service on Railway
2. Add `DATABASE_URL` environment variable
3. Bot automatically uses PostgreSQL instead of SQLite

### Option 2: Railway Volumes (Limited Support)

Railway doesn't officially support persistent volumes for SQLite, but you can try:

1. **Add Volume Service:**
   - Railway Dashboard → "+ New" → "Volume"
   - Mount path: `/data`
   - Mount to: Your bot service

2. **Update Bot to Use Volume:**
   - Set environment variable: `SQLITE_DB_PATH=/data/conversation_logs.db`
   - Update `bot.py` to use this path (see below)

3. **Note:** This may not work reliably. PostgreSQL is recommended.

### Option 3: Regular Backups (Workaround)

Backup SQLite database regularly to external storage (S3, etc.):

1. **Set up automated backups** (see `backup_sqlite.py`)
2. **Upload to cloud storage** after each backup
3. **Download on startup** if database doesn't exist

---

## 🔧 Making SQLite Use Custom Path

If you want to use a volume path, update `bot.py`:

```python
# In bot.py __init__ method, around line 128:
self.conversation_logger = ConversationLogger(
    db_path=os.getenv("SQLITE_DB_PATH", "conversation_logs.db")
)
```

Then set environment variable in Railway:
- `SQLITE_DB_PATH=/data/conversation_logs.db` (if using volume)
- Or leave unset to use default: `conversation_logs.db`

---

## 💾 Backup SQLite Database

### Method 1: Bot Command

```
!export
```

Exports all conversations to CSV file, sent as Discord attachment.

### Method 2: Backup Script

```bash
python backup_sqlite.py
```

Creates timestamped backup of SQLite database.

### Method 3: Manual Backup

```bash
# Copy database file
cp conversation_logs.db conversation_logs_backup.db

# Or export to CSV
python -c "from conversation_logger import ConversationLogger; logger = ConversationLogger(); logger.export_to_csv('backup.csv')"
```

### Method 4: Railway CLI (Download Database)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Download database file (if accessible)
railway run bash
# Then inside container:
cp conversation_logs.db /tmp/
# Download from Railway dashboard → Service → Files
```

---

## 📋 Commands Available

### `!export`
Exports all conversations to CSV file.

**Usage:**
```
!export
```

**Output:**
- Creates CSV file with all conversations
- Sends as Discord file attachment
- Includes: id, user_id, user_name, channel_id, user_message, bot_response, timestamp, tokens_used, model_used

### `!stats`
Shows conversation statistics.

**Usage:**
```
!stats
```

**Shows:**
- Total conversations
- Total users
- Recent conversations (24h)
- Total tokens used
- Models used breakdown

### `!history [user]`
Shows conversation history.

**Usage:**
```
!history              # Your own history
!history @username    # Specific user
!history username      # Search by username
```

**Shows:**
- Last 10 conversations
- User message and bot response
- Timestamp, tokens, model

---

## 🔄 Auto-Save Feature

**Already Implemented!** The bot automatically saves every conversation:

1. User sends message
2. Bot generates response
3. Bot saves to database automatically:
   ```python
   self.conversation_logger.log_conversation(
       user_id=str(message.author.id),
       user_name=message.author.display_name,
       channel_id=str(message.channel.id),
       user_message=content,
       bot_response=response_text,
       tokens_used=tokens_used,
       model_used=model_used
   )
   ```

**No configuration needed** - it works automatically!

---

## 📊 Data Collected for Training

Every conversation saves:

- **User Info:**
  - `user_id` - Discord user ID
  - `user_name` - Discord username/display name
  - `channel_id` - Channel where conversation happened

- **Messages:**
  - `user_message` - What user said
  - `bot_response` - What bot replied

- **Metadata:**
  - `timestamp` - When conversation happened
  - `tokens_used` - Number of tokens used (for cost tracking)
  - `model_used` - Which model was used (claude-3-5-haiku, static_fallback, etc.)

**Perfect for training your own AI model!**

---

## 🚀 Railway Deployment Checklist

### For SQLite (Not Recommended)
- [ ] Understand SQLite files will be lost on deployment
- [ ] Set up regular backups
- [ ] Consider using PostgreSQL instead

### For PostgreSQL (Recommended)
- [ ] Add PostgreSQL service on Railway
- [ ] Add `DATABASE_URL` environment variable
- [ ] Bot automatically uses PostgreSQL
- [ ] Data persists across deployments

---

## 🎯 Recommendation

**For Railway deployment, use PostgreSQL:**

1. **Persistent** - Data survives deployments
2. **Automatic Backups** - Railway handles backups
3. **Scalable** - Handles millions of conversations
4. **Production Ready** - Best for production bots

**SQLite is fine for:**
- Local development
- Testing
- Small personal bots (if you don't mind losing data on redeploy)

---

## 📚 Related Files

- `conversation_logger.py` - SQLite/PostgreSQL logger
- `backup_sqlite.py` - SQLite backup script
- `RAILWAY_POSTGRESQL_SETUP.md` - PostgreSQL setup guide
- `RAILWAY_DEPLOYMENT_GUIDE.md` - Complete deployment guide

---

## ✅ Summary

**Your bot already has SQLite conversation logging!**

✅ Auto-saves every conversation  
✅ Tracks all metadata (user, tokens, model)  
✅ Commands: `!export`, `!stats`, `!history`  
✅ Ready for training data collection  

**For Railway:** Use PostgreSQL for persistence (see `RAILWAY_POSTGRESQL_SETUP.md`)

**For Local:** SQLite works perfectly!

---

**Your conversation data is being collected! 🎉**




