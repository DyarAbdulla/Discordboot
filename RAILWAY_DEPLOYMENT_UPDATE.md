# 🚀 Railway Deployment Update Guide

## Quick Deployment Steps

### Option 1: Automatic Deployment (GitHub Integration)

If your Railway project is connected to GitHub:

1. **Commit all changes:**
   ```bash
   git add .
   git commit -m "Comprehensive bot upgrade - Multi-API system, analytics, fun features"
   git push origin main
   ```

2. **Railway will automatically:**
   - Detect the push
   - Install new dependencies from `requirements.txt`
   - Deploy the updated bot
   - Restart the service

3. **Monitor deployment:**
   - Go to Railway dashboard → Your project → "Deployments" tab
   - Watch the build logs for any errors
   - Check that all dependencies install successfully

### Option 2: Manual Deployment

If not using GitHub integration:

1. **Go to Railway Dashboard:**
   - Open your project
   - Click "Settings" → "Source"
   - Upload your updated code or connect repository

2. **Trigger deployment:**
   - Railway will automatically redeploy when code changes
   - Or manually click "Redeploy" in the Deployments tab

---

## ✅ Pre-Deployment Checklist

### 1. Environment Variables

Make sure these are set in Railway → Variables:

**Required API Keys:**
```
CLAUDE_API_KEY=your_claude_key
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
DISCORD_TOKEN=your_discord_token
```

**Configuration:**
```
PRIMARY_API=claude
ENABLE_FALLBACK=true
COST_OPTIMIZATION=true
MONTHLY_BUDGET=50
```

### 2. Dependencies

All new dependencies are in `requirements.txt`:
- `google-generativeai>=0.3.0` (Gemini)
- `groq>=0.4.0` (Groq)
- `openai>=1.0.0` (OpenRouter)
- `reportlab>=4.0.0` (PDF export)
- `langdetect>=1.0.9` (Language detection)

Railway will automatically install these during deployment.

### 3. Verify Files

Make sure these new files are included:
- `utils/api_manager.py`
- `utils/cache.py`
- `utils/analytics.py`
- `utils/export_manager.py`
- `utils/language_detector.py`
- `cogs/api_commands.py`
- `cogs/fun_commands.py`

---

## 🔍 Post-Deployment Verification

### 1. Check Logs

After deployment, check Railway logs for:

**Success indicators:**
```
[OK] Multi-API Manager initialized!
[OK] Claude API initialized
[OK] Gemini API initialized
[OK] Groq API initialized
[OK] OpenRouter API initialized
[OK] Cache Manager initialized
[OK] Analytics Tracker initialized
[OK] Export manager initialized
[OK] Fun commands cog loaded
[OK] API commands cog loaded
[OK] Slash commands cog loaded
[OK] Synced X slash command(s)
```

**If you see errors:**
- Missing API keys → Add them in Railway Variables
- Import errors → Check requirements.txt is updated
- Module not found → Verify all files are committed

### 2. Test in Discord

**Test APIs:**
```
/api test
```
Should show all APIs working.

**Test API Status:**
```
/api status
```
Should show health of all providers.

**Test Fun Commands:**
```
/joke
/story
/riddle
/fact
```

**Test Export:**
```
/export json
```

### 3. Verify Features

✅ **Multi-API Routing:**
- Simple questions should use Gemini (cheaper)
- Complex questions should use Claude
- Fast responses should use Groq

✅ **Caching:**
- Ask the same question twice
- Second response should be faster (cached)

✅ **Analytics:**
- Use `/stats` to see statistics
- Check that interactions are being tracked

---

## 🐛 Troubleshooting

### Issue: "Module not found" errors

**Solution:**
1. Check `requirements.txt` includes all dependencies
2. Verify Railway is installing from requirements.txt
3. Check build logs for installation errors
4. Manually trigger a redeploy

### Issue: "API key not found"

**Solution:**
1. Go to Railway → Variables
2. Verify all API keys are set correctly
3. Check for typos in variable names (case-sensitive)
4. Redeploy after adding variables

### Issue: "Slash commands not appearing"

**Solution:**
1. Wait 1-5 minutes for Discord to sync commands
2. Check logs for "Synced X slash command(s)"
3. Try restarting Discord client
4. Use `/help` to see if commands are available

### Issue: "Bot not responding"

**Solution:**
1. Check Railway logs for errors
2. Verify DISCORD_TOKEN is set correctly
3. Check bot is online in Discord
4. Verify intents are enabled in Discord Developer Portal

### Issue: "Export not working"

**Solution:**
1. PDF export requires `reportlab` - check it's installed
2. Verify `exports/` directory can be created
3. Check file permissions
4. Try different export formats (JSON, CSV work without reportlab)

---

## 📊 Monitoring After Deployment

### 1. Watch Costs

Use `/api costs` regularly to monitor spending:
- Daily costs per API
- Monthly totals
- Budget alerts

### 2. Check Performance

Use `/api stats` to see:
- Response times per API
- Success rates
- Total usage

### 3. Monitor Logs

Check Railway logs for:
- Error rates
- Slow responses
- API failures
- Cache hit rates

---

## 🔄 Rollback (If Needed)

If something goes wrong:

1. **Go to Railway Dashboard:**
   - Open your project
   - Click "Deployments" tab
   - Find the previous working deployment
   - Click "Redeploy"

2. **Or revert Git commit:**
   ```bash
   git revert HEAD
   git push origin main
   ```

---

## ✅ Success Checklist

After deployment, verify:

- [ ] Bot is online in Discord
- [ ] `/api test` shows all APIs working
- [ ] `/api status` shows healthy providers
- [ ] `/joke` and other fun commands work
- [ ] `/export json` creates export file
- [ ] `/stats` shows analytics data
- [ ] Simple questions use Gemini (check footer)
- [ ] Complex questions use Claude (check footer)
- [ ] No errors in Railway logs
- [ ] Costs are being tracked (`/api costs`)

---

## 🎉 Deployment Complete!

Once all checks pass, your bot is successfully updated with:
- ✅ Multi-API system
- ✅ Analytics tracking
- ✅ Caching system
- ✅ Fun commands
- ✅ Export system
- ✅ Enhanced multilingual support

**Your premium Discord bot is now live! 🚀**

---

## 📞 Need Help?

If you encounter issues:
1. Check Railway logs for detailed error messages
2. Verify all environment variables are set
3. Test APIs individually with `/api test`
4. Check Discord bot permissions and intents

