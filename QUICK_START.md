# 🚀 Quick Start Guide for dyarboot

## ✅ Prerequisites Check

Before running, make sure you have:

1. **Python 3.8+ installed**
   ```bash
   python --version
   # or
   python3 --version
   ```

2. **Discord token in `.env` file**
   ```env
   DISCORD_TOKEN=your_token_here
   ```

3. **Message Content Intent enabled** in Discord Developer Portal

---

## 🎯 Quick Run Options

### **Option 1: Use Run Script (Easiest!)**

**Windows:**
```bash
run_bot.bat
```

**Mac/Linux:**
```bash
chmod +x run_bot.sh
./run_bot.sh
```

### **Option 2: Manual Commands**

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

### **Option 3: Ask Cursor AI**

Just type in Cursor's chat:
```
Run bot.py for me. First install requirements.txt, then start the bot.
```

---

## 📋 What You'll See When It Works

```
==================================================
dyarboot is ready!
Logged in as: dyarboot#1234
Bot ID: 123456789012345678
Servers: 1
Mode: Static Responses (No AI API)
==================================================
```

---

## 🧪 Test the Bot

Once running, try these in Discord:

- `@dyarboot hello` → Should respond with greeting
- `@dyarboot joke` → Should tell a joke  
- `!help` → Show all commands
- `!ping` → Check bot status

---

## ⚠️ Common Issues

### Bot doesn't respond?

1. **Check bot is online** - Look for green dot in Discord
2. **Check permissions** - Bot needs "Send Messages"
3. **Check intents** - Enable "Message Content Intent" in Developer Portal

### Import errors?

```bash
pip install --upgrade discord.py python-dotenv
```

### Token errors?

- Check `.env` file exists
- Verify token is correct (no extra spaces)
- Make sure token is on one line

---

## 🆘 Need Help?

Ask Cursor AI:
```
I got this error: [paste error]
Fix this and explain what was wrong.
```

OR

```
The bot won't start. Check dependencies and fix issues.
```

---

**Happy botting! 🤖**

