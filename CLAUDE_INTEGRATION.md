# Claude API Integration Guide

## ✅ Integration Complete!

dyarboot now uses Claude AI (claude-sonnet-4-20250514) for intelligent conversations!

## 🎯 Features Implemented

### 1. **Claude API Integration**
   - Uses Anthropic Claude API with model: `claude-sonnet-4-20250514`
   - Async API calls for better performance
   - Friendly, helpful, conversational personality

### 2. **Conversation Context**
   - Maintains last 10 messages per channel
   - Context-aware responses
   - Remembers conversation history

### 3. **Rate Limiting**
   - Max 5 messages per minute per user
   - Prevents API abuse and spam

### 4. **Error Handling**
   - Graceful fallback to static responses if API fails
   - Comprehensive error logging
   - User-friendly error messages

### 5. **Typing Indicator**
   - Shows typing indicator while AI is thinking
   - Better user experience

### 6. **API Usage Tracking**
   - Logs all API calls to `api_usage.log`
   - Tracks tokens used, success rate, errors
   - View stats with `!info` command

### 7. **Fallback System**
   - If Claude API fails, uses static keyword responses
   - Ensures bot always responds
   - Seamless user experience

## 📁 Files Updated

1. **bot.py** - Main bot with Claude integration
2. **claude_handler.py** - NEW: Claude API handler
3. **requirements.txt** - Added `anthropic` package
4. **config.json** - Added `max_context_messages` setting
5. **responses.py** - Kept as fallback system

## 🔧 Environment Variables

Make sure your `.env` file has:

```env
DISCORD_TOKEN=your_discord_token_here
CLAUDE_API_KEY=your_claude_api_key_here
```

## 🚀 How It Works

1. User sends message to bot (@mention or DM)
2. Bot checks rate limit (5 messages/min)
3. Bot shows typing indicator
4. Bot gets conversation context (last 10 messages)
5. Bot calls Claude API with context
6. If successful → Send AI response
7. If failed → Use static fallback response
8. Update conversation context
9. Log everything

## 📊 Monitoring

### View API Stats
Use `!info` command to see:
- Total API calls
- Success rate
- Total tokens used
- Claude vs Fallback response counts

### Check Logs
- `bot.log` - All conversations
- `api_usage.log` - Detailed API call logs

## 🐛 Troubleshooting

### Bot uses fallback responses?
- Check `CLAUDE_API_KEY` in `.env`
- Check API key is valid
- Check internet connection
- View `api_usage.log` for errors

### Rate limiting issues?
- Default: 5 messages/minute per user
- Adjust in `config.json`: `rate_limit_per_minute`

### Context not working?
- Check `max_context_messages` in `config.json`
- Default: 10 messages per channel

## 💡 Code Comments

All code includes detailed comments explaining:
- What each function does
- How Claude API is called
- Where fallback happens
- How context is managed

## 🎉 Ready to Use!

The bot is now ready with Claude AI integration. Just restart it and start chatting!

```bash
python bot.py
```

