# OpenRouter API Key Setup

## ✅ Your OpenRouter API Key

Your OpenRouter API key has been configured for:
- **DeepSeek R1** 🧮 (math, reasoning, logic)
- **Gemini 2.0 Flash** ⚡ (via OpenRouter - optional)

```
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
```

## 🚀 Setup Steps for Railway

### Step 1: Add to Railway Environment Variables

1. Go to your Railway project dashboard
2. Click on your Discord bot service
3. Go to **Variables** tab
4. Add/Update the variable:
   - **Variable Name**: `OPENROUTER_API_KEY`
   - **Value**: `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`

### Step 2: Deploy

Railway will automatically redeploy when you add/update the variable.

### Step 3: Verify in Logs

Check logs for:
```
[OK] ✅ DeepSeek R1 API initialized via OpenRouter
[OK] ✅ OpenRouter API initialized successfully
```

## 🎯 What This Enables

### 1. DeepSeek R1 via OpenRouter 🧮
- Math problems: "Solve x² + 5x + 6 = 0"
- Logic puzzles: "Reason through this puzzle"
- Coding tasks: "Debug this algorithm"
- Step-by-step reasoning

### 2. Gemini 2.0 Flash (Optional) ⚡
Currently, Gemini uses direct Google AI API (`GEMINI_API_KEY`). 

If you want to use Gemini via OpenRouter instead:
- Model ID: `google/gemini-2.0-flash-exp`
- Would require code changes to route through OpenRouter
- **Current setup uses Google AI directly (recommended)**

## 📊 Current Setup

| Provider | API Key Source | Status |
|----------|---------------|--------|
| **DeepSeek R1** 🧮 | OpenRouter | ✅ Enabled |
| **Gemini 2.0 Flash** ⚡ | Google AI (direct) | ✅ Enabled |
| Claude 🧠 | Anthropic (direct) | ✅ Enabled |
| Groq 💨 | Groq (direct) | ✅ Enabled |

## 🔒 Security Note

⚠️ **Never commit API keys to GitHub!** This key is for Railway deployment only.

## ✅ Verification

After deployment, test:
1. `/api-status` - Should show OpenRouter/DeepSeek status
2. "Solve: x² + 5x + 6 = 0" - Should use DeepSeek R1 🧮
3. Check logs for initialization messages

---

**Key Added**: ✅ Ready to deploy!

