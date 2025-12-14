# dyarboot - Simple Discord Bot (Testing Mode)

A simple Discord bot that uses keyword matching with static responses. **No AI API keys needed!** Perfect for testing and development.

## ✨ Features

- **Keyword Matching**: Responds to common phrases and keywords
- **No API Required**: Uses pre-written responses (no API keys needed!)
- **Natural Chat**: Responds to @mentions and DMs
- **Reactions**: Adds emoji reactions to messages
- **Rate Limiting**: Prevents spam (5 messages per minute per user)
- **Simple Commands**: !help, !ping, !info, !commands

## 📋 Prerequisites

- **Python 3.8 or higher**
- **Discord Bot Token** (get from [Discord Developer Portal](https://discord.com/developers/applications))

## 🚀 Quick Setup

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Create .env File

1. Copy `env.example` to `.env`:
   ```bash
   copy env.example .env
   ```
   (On Mac/Linux: `cp env.example .env`)

2. Open `.env` and add your Discord bot token:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

**That's it!** No API keys needed for testing mode.

### Step 3: Run the Bot

```bash
python bot.py
```

You should see:
```
==================================================
dyarboot is ready!
Logged in as: dyarboot#1234
Bot ID: 123456789012345678
Servers: 1
Mode: Static Responses (No AI API)
==================================================
```

## 🎮 Commands

- `!help` - Show all commands and keywords
- `!ping` - Check if bot is online
- `!info` - Show bot information
- `!commands` - List all commands

## 💬 Keywords the Bot Understands

### Greetings
- "hello", "hi", "hey" → "Hello! 👋 How can I help you today?"
- "good morning" → "Good morning! Hope you have a great day! ☀️"
- "how are you" → "I'm doing great! Thanks for asking. How about you? 😊"

### Questions
- "what is your name" → "My name is dyarboot! I'm here to help you. 🤖"
- "help" → "I can chat with you! Try saying hello, ask me questions, or use !commands"
- "what can you do" → "I can chat with you, answer simple questions, and have fun conversations!"

### Fun
- "joke" → "Why did the chicken cross the road? To get to the other side! 🐔😄"
- "thank" → "You're welcome! Happy to help! 😊"
- "bye", "goodbye" → "Goodbye! See you later! 👋"

### General
- "weather" → "I can't check the weather yet, but I hope it's nice where you are! ☀️"
- "time" → Shows current time

### Default
- If no keywords match → "I heard you! I'm still learning, but I'm here to chat!"

## 🎯 How to Use

1. **@Mention**: Type `@dyarboot hello` in any channel
2. **DM**: Send a direct message to the bot
3. **Commands**: Use `!help` to see all options

## 🔧 Configuration

Edit `config.json` to customize:

```json
{
  "prefix": "!",
  "rate_limit_per_minute": 5,
  "enable_logging": true,
  "log_file": "bot.log"
}
```

## 🚀 Upgrading to AI (Future)

The code includes TODO comments showing where to add AI API integration:

1. In `bot.py`, line ~150: `# TODO: Replace with AI API call here`
2. Add API keys to `.env` file
3. Install AI dependencies: `pip install openai anthropic`
4. Replace `find_response()` call with AI API call

See `responses.py` for the current static response system.

## 🐛 Troubleshooting

### Bot doesn't respond

1. **Check bot is online**: Look for green dot next to bot name
2. **Check permissions**: Bot needs "Send Messages" permission
3. **Check intents**: Enable "Message Content Intent" in Discord Developer Portal
   - Go to https://discord.com/developers/applications
   - Select your bot application
   - Go to "Bot" section
   - Enable "MESSAGE CONTENT INTENT" under "Privileged Gateway Intents"

### Import errors

- Run: `pip install --upgrade discord.py python-dotenv`
- Check Python version: `python --version` (need 3.8+)

### Bot crashes

- Check `.env` file has `DISCORD_TOKEN` set
- Verify Discord token is correct
- Check error message in console

## 📁 Project Structure

```
dyarboot/
├── bot.py              # Main bot file
├── responses.py        # Static responses dictionary
├── config.json         # Bot configuration
├── requirements.txt    # Dependencies (only discord.py!)
├── .env               # Environment variables (create this)
├── env.example         # Example environment file
└── README.md          # This file
```

## 🔒 Security

- **Never commit `.env` file**: It contains your Discord token
- **Keep token secret**: Don't share it publicly
- **Rotate token**: If exposed, regenerate it in Discord Developer Portal

## 📝 Logging

Conversations are logged to `bot.log` by default. To disable, set `"enable_logging": false` in `config.json`.

## 🎉 That's It!

No API keys, no complex setup - just add your Discord token and run! Perfect for testing and development.

---

**Happy testing with dyarboot! 🚀**
