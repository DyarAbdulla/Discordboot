# Quick Setup Guide for dyarboot

## Step-by-Step Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create .env File

1. Copy `env.example` to `.env`:
   - Windows: `copy env.example .env`
   - Mac/Linux: `cp env.example .env`

2. Open `.env` in a text editor and add:
   - Your existing **dyarboot Discord bot token** (keep the same one!)
   - Your **OpenAI API key** OR **Anthropic API key**

Example `.env` file:
```env
DISCORD_TOKEN=your_existing_dyarboot_token_here
OPENAI_API_KEY=sk-your-openai-key-here
USE_OPENAI=true
```

### 3. Run the Bot

```bash
python bot.py
```

That's it! The bot should connect and be ready to chat.

## Testing

1. In Discord, mention the bot: `@dyarboot Hello!`
2. Or use a command: `!help`
3. Or reply to any bot message

## Troubleshooting

**Bot doesn't respond?**
- Make sure "Message Content Intent" is enabled in Discord Developer Portal
- Check that bot has "Send Messages" permission
- Verify API keys are correct in `.env`

**Import errors?**
- Run: `pip install --upgrade discord.py openai anthropic python-dotenv`

**API errors?**
- Check your API key is valid
- Make sure you have credits/quota on your API account

