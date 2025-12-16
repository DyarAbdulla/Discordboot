# 🔑 Adding API Keys to Railway

## ⚠️ IMPORTANT SECURITY NOTE

**NEVER commit API keys to Git!** Always use environment variables in Railway.

---

## 🚀 Quick Setup

### Step 1: Go to Railway Dashboard

1. Open your Railway project: https://railway.app
2. Select your Discord bot project
3. Click on **"Variables"** tab

### Step 2: Add Environment Variables

Add these environment variables with your API keys:

```
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### Step 3: Add Configuration Variables

Also add these configuration variables:

```
PRIMARY_API=claude
ENABLE_FALLBACK=true
COST_OPTIMIZATION=true
MONTHLY_BUDGET=50
```

### Step 4: Verify Existing Keys

Make sure you already have:
```
CLAUDE_API_KEY=your_claude_key_here
DISCORD_TOKEN=your_discord_token_here
```

---

## 📋 Complete Environment Variables List

Here's the complete list of all environment variables your bot needs:

### Required:
- `DISCORD_TOKEN` - Your Discord bot token
- `CLAUDE_API_KEY` - Claude API key (existing)

### New Multi-API Keys:
- `GEMINI_API_KEY` - Google Gemini API key
- `GROQ_API_KEY` - Groq API key
- `OPENROUTER_API_KEY` - OpenRouter API key (also enables DeepSeek R1 🧮)
- `DEEPSEEK_API_KEY` - (Optional) Direct DeepSeek API key (if not using OpenRouter)

### Configuration:
- `PRIMARY_API` - Primary API provider (default: "claude")
- `ENABLE_FALLBACK` - Enable automatic fallback (default: "true")
- `COST_OPTIMIZATION` - Enable cost optimization (default: "true")
- `MONTHLY_BUDGET` - Monthly budget in USD (default: "50")

---

## ✅ Verification Steps

After adding the keys:

1. **Redeploy your bot** (Railway will automatically redeploy when you add variables)

2. **Check logs** for initialization messages:
   ```
   [OK] Multi-API Manager initialized!
   [OK] Claude API initialized
   [OK] Gemini API initialized
   [OK] Groq API initialized
   [OK] OpenRouter API initialized
   ```

3. **Test APIs** using Discord command:
   ```
   /api test
   ```
   This will test all APIs and show their status.

4. **Check API status**:
   ```
   /api status
   ```
   This shows health of all APIs.

---

## 🔒 Security Best Practices

1. ✅ **DO**: Store keys in Railway environment variables
2. ✅ **DO**: Use different keys for development and production
3. ✅ **DO**: Rotate keys regularly
4. ❌ **DON'T**: Commit keys to Git
5. ❌ **DON'T**: Share keys in Discord or chat
6. ❌ **DON'T**: Hardcode keys in your code

---

## 🐛 Troubleshooting

### "API key not found" error:
- Check that the variable name is exactly correct (case-sensitive)
- Make sure you saved the variable in Railway
- Redeploy the bot after adding variables

### "API initialization failed":
- Verify the API key is correct
- Check if the API key has the right permissions
- Check Railway logs for detailed error messages

### "No providers available":
- Make sure at least one API key is set correctly
- Check that the API libraries are installed (they should be in requirements.txt)

---

## 📊 After Setup

Once all APIs are configured:

1. **Monitor costs**: Use `/api costs` to see spending
2. **Check performance**: Use `/api stats` to see which APIs are fastest
3. **Test routing**: Ask simple questions (should use Gemini) and complex questions (should use Claude)

---

## 🎉 Success!

Your bot now has access to:
- 🧠 **Claude** - Best for complex reasoning
- 💎 **Gemini** - Free tier, great for simple queries
- ⚡ **Groq** - Fastest responses
- 🌐 **OpenRouter** - Backup/alternative models
- 🧮 **DeepSeek R1** - Best for math, logic, and step-by-step reasoning (via OpenRouter)

The bot will automatically route queries to the best API based on:
- Query complexity
- Speed requirements
- Cost optimization
- API availability

Enjoy your premium multi-API Discord bot! 🚀

