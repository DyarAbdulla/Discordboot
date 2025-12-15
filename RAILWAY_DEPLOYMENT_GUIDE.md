# Railway Deployment Guide - Database Setup

## 🎯 Overview

This guide covers database setup for Railway deployment. **PostgreSQL is recommended** for production use.

## ✅ Option 1: PostgreSQL on Railway (RECOMMENDED)

### Why PostgreSQL?
- ✅ **Cloud Storage** - Data stored in Railway's managed database
- ✅ **Automatic Backups** - Railway handles backups automatically
- ✅ **Persistent** - Data survives bot restarts and deployments
- ✅ **Scalable** - Handles millions of conversations
- ✅ **Production Ready** - Best for production bots

### Setup Steps

#### 1. Add PostgreSQL to Railway

1. **Go to Railway Dashboard**
   - Visit: https://railway.app
   - Select your bot project

2. **Add PostgreSQL Service**
   - Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
   - Railway automatically creates PostgreSQL database
   - Wait for it to finish provisioning (takes ~30 seconds)

3. **Get DATABASE_URL**
   - Click on the PostgreSQL service
   - Go to **"Variables"** tab
   - Copy the `DATABASE_URL` value
   - Format: `postgresql://user:password@host:port/database`

#### 2. Add DATABASE_URL to Bot Service

1. **Go to Your Bot Service**
   - Click on your bot service (not PostgreSQL)

2. **Add Environment Variable**
   - Click **"Variables"** tab
   - Click **"+ New Variable"**
   - **Name:** `DATABASE_URL`
   - **Value:** Paste the `DATABASE_URL` from PostgreSQL service
   - Click **"Add"**

3. **Verify**
   - `DATABASE_URL` should appear in bot's environment variables
   - Railway will automatically redeploy your bot

#### 3. Verify Connection

**Check Bot Logs:**
1. Go to bot service → **"Deployments"** → Latest → **"View Logs"**
2. Look for:
   ```
   [OK] PostgreSQL connection pool initialized: host:port/database
   [OK] Using PostgreSQL database (Railway)
   [OK] PostgreSQL tables and indexes created
   ```

**Test Commands:**
- Send message to bot
- Run `!stats` - Should show statistics
- Run `!history` - Should show conversations

### Migration from SQLite to PostgreSQL

If you have existing SQLite data:

#### Step 1: Export SQLite Data

**On your local machine:**
```bash
# Export conversations
python -c "from conversation_logger import ConversationLogger; logger = ConversationLogger(); logger.export_to_csv('conversations_backup.csv')"

# Export memory (if needed)
python -c "import sqlite3; conn = sqlite3.connect('bot_memory.db'); import csv; cursor = conn.cursor(); cursor.execute('SELECT * FROM conversations'); rows = cursor.fetchall(); writer = csv.writer(open('memory_backup.csv', 'w')); writer.writerows(rows)"
```

#### Step 2: Set Up PostgreSQL

Follow steps above to add PostgreSQL to Railway.

#### Step 3: Import Data (Optional)

The bot will automatically start using PostgreSQL. Old SQLite data stays in local files as backup.

**To import old conversations:**
- Use `!export` from old SQLite database
- Manually import CSV if needed (or keep as backup)

### Backup PostgreSQL from Railway

#### Method 1: Railway Dashboard (Easiest)

1. **Go to PostgreSQL Service**
2. **Click "Backups" tab**
3. **Click "Create Backup"**
4. **Download backup** when ready

#### Method 2: Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Connect to PostgreSQL
railway connect postgres

# Export database
pg_dump -U postgres -d railway > backup.sql

# Or use Railway's backup command
railway backup postgres
```

#### Method 3: Using psql (External Tool)

1. **Get Connection String** from Railway PostgreSQL service
2. **Connect:**
   ```bash
   psql "postgresql://user:password@host:port/database"
   ```
3. **Export:**
   ```sql
   \copy conversations TO 'backup.csv' CSV HEADER;
   ```

#### Method 4: Automated Backup Script

Create `backup_postgres.py`:

```python
import os
import subprocess
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

# Export using pg_dump
subprocess.run([
    "pg_dump",
    DATABASE_URL,
    "-f", backup_file
])

print(f"Backup created: {backup_file}")
```

---

## ⚠️ Option 2: SQLite Persistence (NOT RECOMMENDED)

**Note:** Railway doesn't support persistent volumes for SQLite easily. SQLite files will be lost on every deployment unless you use external storage.

### Why SQLite is NOT Recommended on Railway

- ❌ **Ephemeral Storage** - Files deleted on every deployment
- ❌ **No Persistence** - Data lost on restart
- ❌ **Not Scalable** - Single file database
- ❌ **No Backups** - You must manually backup

### If You Must Use SQLite

#### Option A: Use External Storage (S3, etc.)

1. **Set up S3 or similar storage**
2. **Download database on startup**
3. **Upload database on shutdown**
4. **Complex and error-prone**

#### Option B: Use Railway Volumes (Limited Support)

Railway doesn't officially support persistent volumes for SQLite. PostgreSQL is strongly recommended instead.

---

## 📊 Database Comparison

| Feature | PostgreSQL (Railway) | SQLite (Local) |
|---------|---------------------|----------------|
| **Persistence** | ✅ Yes (automatic) | ⚠️ Only if volume mounted |
| **Backups** | ✅ Automatic | ❌ Manual |
| **Scalability** | ✅ Millions of rows | ⚠️ Limited |
| **Setup** | ✅ Easy (Railway) | ✅ Easy (local) |
| **Production** | ✅ Recommended | ❌ Not recommended |
| **Cost** | ✅ Free tier available | ✅ Free |

---

## 🔧 Environment Variables

### Required for PostgreSQL

```env
DATABASE_URL=postgresql://user:password@host:port/database
```

### Already Configured

```env
DISCORD_TOKEN=your_discord_token
CLAUDE_API_KEY=your_claude_api_key
```

---

## 📋 Quick Checklist

### PostgreSQL Setup
- [ ] PostgreSQL service created on Railway
- [ ] `DATABASE_URL` copied from PostgreSQL service
- [ ] `DATABASE_URL` added to bot service environment variables
- [ ] Bot redeployed
- [ ] Logs show PostgreSQL connection success
- [ ] Tested `!stats` command
- [ ] Verified conversations are being saved

### Backup Setup
- [ ] Understand backup methods
- [ ] Test backup creation
- [ ] Set up automated backups (optional)

---

## 🚨 Troubleshooting

### Bot Still Using SQLite

**Problem:** Logs show `[INFO] DATABASE_URL not set, using SQLite`

**Solution:**
1. Check `DATABASE_URL` is set in Railway environment variables
2. Verify PostgreSQL service is running
3. Restart/redeploy bot service

### Connection Failed

**Problem:** `Failed to connect to PostgreSQL`

**Solution:**
1. Check PostgreSQL service status in Railway
2. Verify `DATABASE_URL` format is correct
3. Check Railway logs for detailed errors

### Data Lost After Deployment

**Problem:** Conversations disappeared after redeploy

**Solution:**
- If using SQLite: This is expected - use PostgreSQL instead
- If using PostgreSQL: Check PostgreSQL service is still running

---

## 📚 Additional Resources

- **Railway PostgreSQL Docs:** https://docs.railway.app/databases/postgresql
- **PostgreSQL Setup Guide:** See `RAILWAY_POSTGRESQL_SETUP.md`
- **Backup Guide:** See backup methods above

---

## ✅ Recommendation

**Use PostgreSQL on Railway** for production deployment. It's:
- ✅ Persistent across deployments
- ✅ Automatically backed up
- ✅ Scalable and reliable
- ✅ Easy to set up

SQLite is fine for local development, but PostgreSQL is essential for production.

---

**Your bot is now ready for Railway deployment with persistent database! 🚀**


