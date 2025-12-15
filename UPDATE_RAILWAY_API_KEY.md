# How to Update Claude API Key in Railway

## 🔑 Quick Steps

### 1. Go to Railway Dashboard
1. Open https://railway.app
2. Select your project: **cooperative-contentment**
3. Click on **Discordboot** service

### 2. Update the API Key
1. Click on the **"Variables"** tab
2. Find `CLAUDE_API_KEY` in the list
3. Click on it to edit
4. Replace the old value with your new API key (paste your API key here)
5. Click **"Save"** or **"Update"**

**Note:** Your API key should start with `sk-ant-api03-` and be the full key without any spaces.

### 3. Restart the Bot
1. Go to **"Deployments"** tab
2. Click the **"Redeploy"** button (or three dots menu → Redeploy)
3. Wait for deployment to complete (1-2 minutes)

### 4. Verify It Works
1. Check Railway logs for: `[OK] CLAUDE_API_KEY found`
2. Test in Discord: Send `@AI Boot hello`
3. Should get AI response, not error message

## ✅ Verification Checklist

- [ ] API key updated in Railway Variables
- [ ] Bot redeployed
- [ ] Logs show `[OK] CLAUDE_API_KEY found`
- [ ] Bot responds with AI, not error message

## 🔍 If Still Not Working

1. **Check Railway Logs:**
   - Go to Discordboot → Deployments → View Logs
   - Look for errors about API key

2. **Verify API Key Format:**
   - Should start with `sk-ant-api03-`
   - Should be the full key (no spaces)

3. **Check Environment Variables:**
   - Make sure `CLAUDE_API_KEY` is set (not `ANTHROPIC_API_KEY`)
   - Make sure there are no extra spaces

## 📝 Notes

- Railway automatically restarts the bot when you update variables
- But sometimes you need to manually redeploy
- The API key is secure and hidden in Railway (shown as `********`)

