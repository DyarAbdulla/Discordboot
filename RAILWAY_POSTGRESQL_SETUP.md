# Railway PostgreSQL Setup Guide

## Overview

This guide will help you set up PostgreSQL database on Railway for your Discord bot. Railway provides managed PostgreSQL databases that are perfect for production use.

## Benefits of PostgreSQL on Railway

✅ **Cloud Storage** - Data stored in the cloud, not locally  
✅ **Automatic Backups** - Railway handles backups automatically  
✅ **Scalable** - Handles large amounts of data  
✅ **Reliable** - 99.9% uptime guarantee  
✅ **Easy Setup** - Simple configuration  
✅ **Free Tier Available** - Free PostgreSQL database included  

---

## Step 1: Create PostgreSQL Database on Railway

### Option A: Add to Existing Project

1. **Go to Railway Dashboard**
   - Visit: https://railway.app
   - Log in to your account
   - Select your bot project

2. **Add PostgreSQL Service**
   - Click **"+ New"** button
   - Select **"Database"** → **"Add PostgreSQL"**
   - Railway will automatically create a PostgreSQL database

3. **Get Connection String**
   - Click on the PostgreSQL service
   - Go to **"Variables"** tab
   - Copy the `DATABASE_URL` value
   - Format: `postgresql://user:password@host:port/database`

### Option B: Create New Project

1. **Create New Project**
   - Go to Railway Dashboard
   - Click **"New Project"**
   - Select **"Deploy from GitHub"** (if you have GitHub repo)
   - OR select **"Empty Project"**

2. **Add PostgreSQL**
   - Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
   - Railway creates the database automatically

3. **Copy DATABASE_URL**
   - Click PostgreSQL service → **"Variables"** tab
   - Copy `DATABASE_URL`

---

## Step 2: Add DATABASE_URL to Railway Environment Variables

### Method 1: Via Railway Dashboard (Recommended)

1. **Go to Your Bot Service**
   - In Railway dashboard, click on your bot service (not PostgreSQL)

2. **Add Environment Variable**
   - Click **"Variables"** tab
   - Click **"+ New Variable"**
   - **Name:** `DATABASE_URL`
   - **Value:** Paste the `DATABASE_URL` from PostgreSQL service
   - Click **"Add"**

3. **Verify**
   - The `DATABASE_URL` should now appear in your bot's environment variables
   - Railway will automatically redeploy your bot

### Method 2: Via Railway CLI

```bash
# Install Railway CLI (if not installed)
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Add DATABASE_URL
railway variables set DATABASE_URL="postgresql://user:password@host:port/database"
```

---

## Step 3: Install Dependencies

The bot already includes PostgreSQL support in `requirements.txt`:

```txt
psycopg2-binary>=2.9.9
```

**If deploying on Railway:**
- Railway automatically installs dependencies from `requirements.txt`
- No manual installation needed!

**If testing locally:**
```bash
pip install psycopg2-binary
```

---

## Step 4: Verify Connection

### Check Bot Logs

After Railway redeploys your bot, check the logs:

1. **Go to Railway Dashboard**
2. **Click on your bot service**
3. **Click "Deployments"** → **Latest deployment** → **"View Logs"**

**Look for:**
```
[OK] PostgreSQL connection pool initialized: host:port/database
[OK] Using PostgreSQL database (Railway)
[OK] PostgreSQL tables and indexes created
```

**If you see errors:**
- Check that `DATABASE_URL` is set correctly
- Verify PostgreSQL service is running
- Check connection string format

---

## Step 5: Test the Bot

1. **Send a message to your bot** in Discord
2. **Check if conversation is saved:**
   - Use `!stats` command
   - Use `!history` command
   - Use `!export` command

3. **Verify in Railway PostgreSQL:**
   - Go to PostgreSQL service
   - Click **"Query"** tab
   - Run: `SELECT COUNT(*) FROM conversations;`
   - Should show number of conversations

---

## Database Schema

The bot automatically creates this table:

```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    channel_id VARCHAR(50) NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER DEFAULT 0,
    model_used VARCHAR(50) DEFAULT 'unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes created automatically:**
- `idx_conversations_user_id` - Fast user lookups
- `idx_conversations_channel_id` - Fast channel lookups
- `idx_conversations_timestamp` - Fast time-based queries
- `idx_conversations_user_name` - Fast name searches

---

## How It Works

### Automatic Detection

The bot automatically detects PostgreSQL:

1. **Checks for `DATABASE_URL`** environment variable
2. **If found:** Uses PostgreSQL (Railway)
3. **If not found:** Falls back to SQLite (local file)

### Connection Pooling

- Uses connection pooling (1-10 connections)
- Efficient for high-traffic bots
- Automatic connection management

### SSL Required

Railway PostgreSQL requires SSL:
- Automatically enabled with `sslmode='require'`
- Secure connection guaranteed

---

## Troubleshooting

### Error: "DATABASE_URL not found"

**Solution:**
- Make sure `DATABASE_URL` is set in Railway environment variables
- Check that you copied the full connection string
- Verify PostgreSQL service is running

### Error: "Failed to connect to PostgreSQL"

**Solution:**
- Check PostgreSQL service status in Railway
- Verify `DATABASE_URL` format is correct
- Check Railway logs for detailed error messages

### Error: "psycopg2 not found"

**Solution:**
- Make sure `psycopg2-binary>=2.9.9` is in `requirements.txt`
- Railway will install it automatically on deploy

### Bot Still Using SQLite

**Solution:**
- Check bot logs for: `[INFO] DATABASE_URL not set, using SQLite`
- Verify `DATABASE_URL` is set in Railway environment variables
- Restart/redeploy the bot

---

## Migration from SQLite to PostgreSQL

### Option 1: Fresh Start (Recommended)

1. Set up PostgreSQL on Railway
2. Add `DATABASE_URL` to environment variables
3. Bot will start using PostgreSQL automatically
4. Old SQLite data stays in local file (backup)

### Option 2: Migrate Existing Data

1. **Export SQLite data:**
   ```bash
   python -c "from conversation_logger import ConversationLogger; logger = ConversationLogger(); logger.export_to_csv('export.csv')"
   ```

2. **Set up PostgreSQL** (follow steps above)

3. **Import data** (optional - can be done manually via SQL)

---

## Railway PostgreSQL Features

### Automatic Backups
- Railway automatically backs up your database
- Backups available in Railway dashboard

### Scaling
- Upgrade plan for more storage/performance
- Handles millions of conversations

### Monitoring
- View database metrics in Railway dashboard
- Connection count, query performance, etc.

---

## Environment Variables Summary

**Required for PostgreSQL:**
```env
DATABASE_URL=postgresql://user:password@host:port/database
```

**Already configured:**
```env
DISCORD_TOKEN=your_discord_token
CLAUDE_API_KEY=your_claude_api_key
```

---

## Quick Checklist

- [ ] PostgreSQL service created on Railway
- [ ] `DATABASE_URL` copied from PostgreSQL service
- [ ] `DATABASE_URL` added to bot service environment variables
- [ ] Bot redeployed on Railway
- [ ] Logs show PostgreSQL connection success
- [ ] Tested `!stats` command
- [ ] Verified conversations are being saved

---

## Support

If you encounter issues:

1. **Check Railway logs** for error messages
2. **Verify environment variables** are set correctly
3. **Test PostgreSQL connection** using Railway Query tab
4. **Check bot logs** for database initialization messages

---

## Next Steps

Once PostgreSQL is set up:

1. ✅ Conversations automatically saved to cloud
2. ✅ Use `!export` to download CSV files
3. ✅ Use `!stats` to view statistics
4. ✅ Use `!history` to view conversation history
5. ✅ Data persists across bot restarts
6. ✅ Ready for training data collection!

---

**Your bot is now using cloud PostgreSQL! 🎉**


