# DeepSeek R1 Setup Guide

## ✅ Quick Setup for Railway

Your OpenRouter API key for DeepSeek R1 is already configured in the code. To activate it on Railway:

### 1. Add to Railway Environment Variables

1. Go to your Railway project dashboard
2. Click on your service
3. Go to **Variables** tab
4. Add new variable:
   - **Variable Name**: `OPENROUTER_API_KEY`
   - **Value**: `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`

### 2. Deploy

Railway will automatically redeploy when you add the variable. Check logs for:
```
[OK] ✅ DeepSeek R1 API initialized via OpenRouter
```

## 🧮 What DeepSeek R1 Does

DeepSeek R1 is automatically used for:
- **Math problems**: "Solve x² + 5x + 6 = 0"
- **Logic puzzles**: "Reason through this puzzle"
- **Coding tasks**: "Debug this algorithm"
- **Step-by-step reasoning**: "Analyze this problem step by step"

## 🎯 Smart Routing

The bot automatically routes queries:
- **Reasoning/Math** → DeepSeek R1 🧮 (best for logic)
- **Simple questions** → Gemini (cheapest)
- **Fast responses** → Groq (fastest)
- **Complex analysis** → Claude (best overall)
- **Code generation** → DeepSeek or Claude

## 📊 Cost Savings

DeepSeek R1 is very cheap ($0.00014/$0.00028 per 1M tokens) and excellent for reasoning tasks, saving money while improving quality!

## 🧪 Test It

After deployment, test with:
- `/api-status` - Should show DeepSeek status
- "Solve: x² + 5x + 6 = 0" - Should use DeepSeek
- "Explain binary search algorithm" - Should use DeepSeek

## 🔒 Security Note

⚠️ **Never commit API keys to GitHub!** This key is configured for Railway deployment only.

