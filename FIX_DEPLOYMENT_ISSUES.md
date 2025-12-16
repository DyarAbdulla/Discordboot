# 🔧 Fix Deployment Issues

## ❌ Current Problems Detected

Based on your logs, the bot is running in **"Static Responses (Fallback)"** mode instead of **"Multi-API"** mode. This means the Multi-API Manager isn't initializing properly.

### Issues Found:

1. **Multi-API Manager Not Initializing**
   - Bot shows: `Mode: Static Responses (Fallback)`
   - Should show: `Mode: Multi-API`
   - This means `self.api_manager` is `None`

2. **API Routing Not Working**
   - Math query used Claude instead of DeepSeek R1
   - Should use DeepSeek for: "Solve: x² + 5x + 6 = 0"

3. **Invalid Environment Variables**
   - `Gemini 2.0 Flash_API_KEY` - **This shouldn't exist!**
   - Should only use: `GEMINI_API_KEY`
   - Remove `DEEPSEEK_API_KEY` if using OpenRouter

## ✅ Fixes Needed

### Fix 1: Clean Up Railway Variables

Go to Railway → Variables tab and:

**DELETE these invalid variables:**
- ❌ `Gemini 2.0 Flash_API_KEY` (delete this)
- ❌ `DEEPSEEK_API_KEY` (delete if using OpenRouter)

**KEEP these required variables:**
- ✅ `DISCORD_TOKEN`
- ✅ `CLAUDE_API_KEY`
- ✅ `GEMINI_API_KEY` (for Gemini 2.0 Flash)
- ✅ `GROQ_API_KEY`
- ✅ `OPENROUTER_API_KEY` (for DeepSeek R1)

**Configuration variables:**
- ✅ `PRIMARY_API=claude`
- ✅ `ENABLE_FALLBACK=true`
- ✅ `COST_OPTIMIZATION=true`
- ✅ `MONTHLY_BUDGET=50`

### Fix 2: Check Multi-API Manager Initialization

The bot is catching exceptions during initialization. Check Railway logs for:

```
[WARNING] Multi-API Manager not available: <error message>
```

This will tell us why it's failing.

### Fix 3: Verify API Keys Are Set

Make sure all API keys are correctly set:

1. **CLAUDE_API_KEY** - Should start with `sk-ant-`
2. **GEMINI_API_KEY** - Should start with `AIzaSy`
3. **GROQ_API_KEY** - Should start with `gsk_`
4. **OPENROUTER_API_KEY** - Should start with `sk-or-v1-`

## 🔍 Debugging Steps

### Step 1: Check Initialization Logs

Look in Railway logs for these messages:

**If working correctly, you should see:**
```
[INFO] Initializing Multi-API Manager...
[OK] ✅ Claude API initialized successfully
[OK] ✅ Gemini 2.0 Flash Experimental initialized successfully
[OK] ✅ Groq API initialized successfully
[OK] ✅ OpenRouter API initialized successfully
[OK] ✅ DeepSeek R1 API initialized via OpenRouter
[INFO] Multi-API routing active - 5 provider(s) available
```

**If failing, you'll see:**
```
[WARNING] Multi-API Manager not available: <error>
```

### Step 2: Check for Import Errors

Common causes:
- Missing Python packages (check `requirements.txt`)
- Syntax errors in `utils/api_manager.py`
- Environment variable issues

### Step 3: Test After Fixes

1. **Redeploy** after cleaning up variables
2. **Check logs** for initialization messages
3. **Test commands:**
   - `/api-status` - Should show detailed API status
   - `@AI Boot hello` - Should use Gemini 2.0 Flash
   - "Solve: x² + 5x + 6 = 0" - Should use DeepSeek R1

## 🚀 Quick Fix Checklist

- [ ] Delete `Gemini 2.0 Flash_API_KEY` from Railway
- [ ] Delete `DEEPSEEK_API_KEY` from Railway (if using OpenRouter)
- [ ] Verify `GEMINI_API_KEY` is set correctly
- [ ] Verify `OPENROUTER_API_KEY` is set correctly
- [ ] Check `PRIMARY_API=claude` (no extra quotes)
- [ ] Redeploy on Railway
- [ ] Check logs for initialization errors
- [ ] Test `/api-status` command
- [ ] Test math query routing

## 📊 Expected Behavior After Fix

Once fixed, you should see:

1. **On Startup:**
   ```
   Mode: Multi-API
   Available APIs: claude, gemini, groq, openrouter, deepseek
   ```

2. **When Testing:**
   - Simple queries → Gemini 2.0 Flash ⚡
   - Math queries → DeepSeek R1 🧮
   - Complex queries → Claude 🧠

3. **API Status Command:**
   - Should show detailed health check
   - Shows all providers with ✅/❌ status
   - Shows response times and costs

## 🐛 Common Issues & Solutions

### Issue: "Multi-API Manager not available"
**Cause:** Import error or initialization exception
**Fix:** Check Railway logs for the actual error message

### Issue: "Mode: Static Responses"
**Cause:** API Manager failed to initialize
**Fix:** Fix the underlying error (usually missing env vars or import issues)

### Issue: Math queries use Claude instead of DeepSeek
**Cause:** Multi-API Manager not initialized, so routing doesn't work
**Fix:** Fix API Manager initialization first

### Issue: `/api-status` shows generic response
**Cause:** Command handler might not be loaded or API Manager is None
**Fix:** Ensure `api_commands.py` cog is loaded in `setup_hook`

---

**After fixing these issues, the bot should fully utilize the Multi-API system!** 🚀

