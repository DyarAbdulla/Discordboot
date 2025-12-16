# 🔑 API Key Update Guide

## ✅ Changes Made

### 1. DeepSeek API Key Support
- ✅ Code now **prefers `DEEPSEEK_API_KEY`** over `OPENROUTER_API_KEY`
- ✅ If `DEEPSEEK_API_KEY` is provided, uses direct DeepSeek API
- ✅ Falls back to OpenRouter if `DEEPSEEK_API_KEY` not found

### 2. Gemini API Key
- ⚠️ **IMPORTANT**: Code expects `GEMINI_API_KEY` (exact name)
- ❌ **Don't rename** to `Gemini 2.0 Flash_API_KEY` - it won't work!
- ✅ Keep it as: `GEMINI_API_KEY`

## 📋 Railway Variables Setup

### ✅ Required Variables:

1. **`GEMINI_API_KEY`** ⚠️ **KEEP THIS NAME!**
   - Your Gemini 2.0 Flash API key
   - Value: Your Google AI API key
   - **DO NOT rename to "Gemini 2.0 Flash_API_KEY"**

2. **`DEEPSEEK_API_KEY`** ✅ **NEW - Use This Instead of OpenRouter**
   - Your direct DeepSeek API key
   - Value: Your DeepSeek API key from https://platform.deepseek.com/
   - This is now **preferred** over OpenRouter

### 🗑️ Variables to DELETE:

- ❌ `Gemini 2.0 Flash_API_KEY` - DELETE this (use `GEMINI_API_KEY` instead)
- ❌ `OPENROUTER_API_KEY` - DELETE if using direct DeepSeek API

### ✅ Optional (Keep These):

- `CLAUDE_API_KEY` - Claude API
- `GROQ_API_KEY` - Groq API
- `DISCORD_TOKEN` - Discord bot token
- `PRIMARY_API` - Set to "claude"
- `ENABLE_FALLBACK` - Set to "true"
- `COST_OPTIMIZATION` - Set to "true"
- `MONTHLY_BUDGET` - Your budget

## 🚀 Setup Steps

### Step 1: Update Railway Variables

1. Go to Railway → Your Project → Variables tab
2. **DELETE:**
   - `Gemini 2.0 Flash_API_KEY`
   - `OPENROUTER_API_KEY` (if using direct DeepSeek)
3. **VERIFY/ADD:**
   - `GEMINI_API_KEY` = Your Gemini key (keep this name!)
   - `DEEPSEEK_API_KEY` = Your DeepSeek key (new)

### Step 2: Redeploy

Railway will auto-redeploy when you update variables.

### Step 3: Verify in Logs

Check logs for:
```
[OK] ✅ Gemini 2.0 Flash Experimental initialized successfully
[OK] ✅ DeepSeek R1 API initialized (direct API)
```

## 🎯 How It Works Now

### DeepSeek Initialization Priority:

1. **First**: Try `DEEPSEEK_API_KEY` (direct API) ✅ **PREFERRED**
2. **Fallback**: Use `OPENROUTER_API_KEY` (via OpenRouter)

### Gemini:

- Always uses: `GEMINI_API_KEY` (must be exact name)
- Model: `gemini-2.0-flash-exp`

## ❓ Why Keep `GEMINI_API_KEY` Name?

The code explicitly looks for `GEMINI_API_KEY`:
```python
api_key = os.getenv("GEMINI_API_KEY")
```

If you rename it to `Gemini 2.0 Flash_API_KEY`, the code won't find it and Gemini won't work!

## ✅ Final Variable List

```
DISCORD_TOKEN=your_discord_token
CLAUDE_API_KEY=your_claude_key
GEMINI_API_KEY=your_gemini_key          ← Keep this name!
DEEPSEEK_API_KEY=your_deepseek_key      ← Use this instead of OpenRouter
GROQ_API_KEY=your_groq_key
PRIMARY_API=claude
ENABLE_FALLBACK=true
COST_OPTIMIZATION=true
MONTHLY_BUDGET=50
```

---

**After updating variables, redeploy and check logs!** 🚀

