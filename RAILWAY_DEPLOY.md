# Railway Deployment Guide for AI Boot

## 📋 Files Created

1. **Procfile** - Tells Railway how to run your bot
2. **runtime.txt** - Specifies Python version (3.11.0)
3. **requirements.txt** - All dependencies (already exists)
4. **.dockerignore** - Excludes unnecessary files from build
5. **railway.json** - Railway configuration (optional)

## 🚀 Deployment Steps

### 1. Push to GitHub
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push
```

### 2. Deploy on Railway

1. Go to [Railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will automatically detect the Procfile

### 3. Set Environment Variables

In Railway dashboard, add these environment variables:

**Required:**
- `DISCORD_TOKEN` - Your Discord bot token
- `CLAUDE_API_KEY` - Your Claude API key

**Optional (already in config.json):**
- `PREFIX` - Command prefix (default: "!")
- `RATE_LIMIT_PER_MINUTE` - Rate limit (default: 5)

### 4. Deploy

Railway will:
- Install Python 3.11.0
- Install dependencies from requirements.txt
- Run `python bot.py` as specified in Procfile
- Auto-restart on crashes

## ✅ Auto-Restart Features

The bot is configured to:
- Exit with error code on fatal errors (Railway will restart)
- Handle exceptions gracefully
- Log errors for debugging

## 📊 Monitoring

- Check Railway logs for bot output
- View `!info` command in Discord for bot stats
- Check `api_usage.log` for API call tracking

## 🔧 Troubleshooting

**Bot not starting?**
- Check environment variables are set
- Check Railway logs for errors
- Verify DISCORD_TOKEN and CLAUDE_API_KEY are correct

**Bot keeps restarting?**
- Check Railway logs for crash reasons
- Verify API keys are valid
- Check rate limits aren't being hit

## 📝 Notes

- Railway automatically restarts the bot if it crashes
- Logs are available in Railway dashboard
- Environment variables are secure (not exposed)
- Bot runs 24/7 on Railway's infrastructure

---

**Your bot is ready for Railway! 🚂**

