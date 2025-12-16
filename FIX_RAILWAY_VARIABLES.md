# 🔧 Fix Railway Environment Variables

## ❌ CRITICAL ISSUE FOUND

The `PRIMARY_API` variable in Railway is **MALFORMED**:
```
PRIMARY_API=""claude"PRIMARY_API=claude"
```

This is causing the bot to fail initialization!

## ✅ CORRECT FORMAT

The variable should be:
```
PRIMARY_API=claude
```

**OR** (if using quotes):
```
PRIMARY_API="claude"
```

## 📋 Steps to Fix in Railway:

1. Go to Railway Dashboard → Your Project → Discordboot Service
2. Click on **"Variables"** tab
3. Find `PRIMARY_API` in the list
4. Click the **three dots (⋯)** next to it → **Edit**
5. Change the value from: `""claude"PRIMARY_API=claude"`
6. To: `claude` (or `"claude"` with quotes)
7. Click **"Update Variables"**
8. Railway will automatically redeploy

## 🔍 Also Check These Variables:

Make sure all these are set correctly:

- `PRIMARY_API=claude` ✅ (FIX THIS ONE!)
- `ENABLE_FALLBACK=true` ✅
- `COST_OPTIMIZATION=true` ✅
- `MONTHLY_BUDGET=50` ✅
- `CLAUDE_API_KEY=sk-ant-...` ✅
- `GEMINI_API_KEY=AIzaSy...` ✅
- `GROQ_API_KEY=gsk_...` ✅
- `OPENROUTER_API_KEY=sk-or-v1-...` ✅
- `DISCORD_TOKEN=MTQ0...` ✅

## 🚀 After Fixing:

1. Railway will auto-redeploy
2. Check logs for:
   ```
   [INFO] Initializing Multi-API Manager...
   [INFO] Claude API initialized successfully
   [INFO] Gemini API initialized successfully
   [INFO] Groq API initialized successfully
   [INFO] OpenRouter API initialized successfully
   [INFO] Multi-API routing active - 4 provider(s) available
   ```
3. Bot should show: `Mode: Multi-API` instead of `Mode: Static Responses (Fallback)`

## ⚠️ IMPORTANT:

The `PRIMARY_API` variable must be **exactly** `claude` (no extra quotes, no duplicate text).




