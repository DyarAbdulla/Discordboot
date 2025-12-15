# Update Railway API Key - URGENT

## Steps to Update

**IMPORTANT:** Copy your new API key from the message you sent. Do NOT paste it in this file.

1. **Go to Railway Dashboard**
   - Visit: https://railway.app
   - Open your project: `cooperative-contentment`
   - Click on the `Discordboot` service

2. **Update Environment Variable**
   - Click the "Variables" tab
   - Find `CLAUDE_API_KEY` in the list
   - Click to edit it
   - Replace the entire value with the new API key above
   - Click "Save" or "Update"

3. **Redeploy the Bot**
   - Go to the "Deployments" tab
   - Click the three dots (⋯) on the latest deployment
   - Select "Redeploy"
   - Wait 1-2 minutes for deployment to complete

4. **Verify It Works**
   - Check Railway logs for:
     - `[OK] CLAUDE_API_KEY found`
     - `[OK] Claude API handler initialized successfully!`
     - `Mode: Claude AI` (NOT "Static Responses")
   - Test in Discord:
     - Send: `@AI Boot What is AI?`
     - Should get a detailed AI response, NOT "I'm still learning..."

## Important Notes

- **DO NOT** commit the API key to GitHub
- The API key is only stored in Railway environment variables
- After updating, the bot will automatically restart
- If you see "Static Responses" mode, the API key is not being loaded correctly
