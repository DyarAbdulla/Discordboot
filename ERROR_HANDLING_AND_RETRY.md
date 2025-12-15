# Error Handling and Automatic Retry - Implementation Guide

## ✅ Implementation Complete!

Your Discord bot now has robust error handling with automatic retries and graceful recovery!

## 🎯 Features Implemented

### 1. **Automatic Retry System**
   - Retries Claude API calls up to 3 times
   - Exponential backoff (1s, 2s, 4s delays)
   - Smart retry logic (skips retry on auth errors)
   - Tracks retry attempts

### 2. **Response Caching**
   - Caches successful responses for 24 hours
   - Uses cached responses as fallback if API fails
   - Cache key based on user message + system prompt
   - Automatic cache cleanup (keeps last 100)

### 3. **Friendly Error Messages**
   - User-friendly error messages
   - Language-aware fallbacks (Kurdish/English)
   - No technical jargon for users
   - Helpful suggestions

### 4. **Error Logging**
   - All errors logged to database
   - Detailed error information
   - User/server context
   - Timestamps for tracking

### 5. **Error Alerting**
   - Alerts bot owner on Discord if errors are frequent
   - Threshold: 10 errors per hour
   - One alert per hour maximum
   - Includes error summary

### 6. **Commands**
   - `!errors` - Show recent errors (Owner only)
   - `!retry` - Manually retry last failed request (Owner only)

## 📁 Files Modified

### Modified Files:
1. **`claude_handler.py`**
   - Added automatic retry logic (3 attempts)
   - Added response caching system
   - Enhanced error handling
   - Added `retry_last_failed_request()` method
   - Exponential backoff delays

2. **`bot.py`**
   - Enhanced error handling in message processing
   - Added error alerting system
   - Added `!errors` command
   - Added `!retry` command
   - Improved fallback messages
   - Owner detection in `setup_hook()`

## 🔧 How It Works

### Automatic Retry Flow:
1. User sends message
2. Bot attempts Claude API call
3. If fails → Wait 1 second → Retry
4. If fails → Wait 2 seconds → Retry
5. If fails → Wait 4 seconds → Retry
6. If all fail → Use cached response or fallback

### Response Caching:
1. Successful API response cached
2. Cache key: hash of user message + system prompt
3. Cache valid for 24 hours
4. Used as fallback if API fails

### Error Alerting:
1. Track errors per hour
2. If > 10 errors/hour → Alert owner
3. Alert includes error summary
4. One alert per hour maximum

## 📊 Retry Logic

### Retry Attempts:
- **Attempt 1**: Immediate
- **Attempt 2**: Wait 1 second
- **Attempt 3**: Wait 2 seconds
- **Attempt 4**: Wait 4 seconds (if enabled)

### Retry Conditions:
- ✅ Retries on: Network errors, timeout errors, rate limits
- ❌ Skips retry on: Authentication errors, invalid API key

### Fallback Order:
1. Cached response (if available)
2. Any cached response (fallback)
3. Static keyword response
4. Friendly error message

## 🎯 Commands

### `!errors` - Show Recent Errors (Owner Only)
Shows recent errors from database:
- Error type and message
- User/server context
- Timestamp
- Error frequency

### `!retry` - Retry Last Failed Request (Owner Only)
Manually retries the last failed API request:
- Uses stored request parameters
- Shows success/failure
- Indicates if cached/fallback used

## 📝 Error Messages

### User-Friendly Messages:
**English:**
```
I'm having a bit of trouble right now, but I'm still here! 
Try asking again in a moment, or rephrase your question. 
I'll do my best to help! 😊
```

**Kurdish (Sorani):**
```
ببورە، هەندێک کێشە هەیە. تکایە دواتر هەوڵ بدەوە.
```

**Kurdish (Kurmanji):**
```
Bibûre, hinek kêşe heye. Tika duar hewl bide.
```

## 🔍 Error Tracking

### Database Storage:
- Error type
- Error message
- User ID
- Server ID
- Timestamp

### Error Types:
- `API_ERROR` - Claude API failures
- `NETWORK_ERROR` - Network issues
- `TIMEOUT_ERROR` - Request timeouts
- `AUTH_ERROR` - Authentication failures

## 🚨 Error Alerting

### Alert Conditions:
- More than 10 errors per hour
- One alert per hour maximum
- Sent to bot owner via DM

### Alert Message:
```
⚠️ Error Alert

I've encountered 15 errors in the last hour.
This might indicate an issue with the Claude API or network.

Use !errors to see recent errors.
Use !retry to retry the last failed request.
```

## 💡 Example Scenarios

### Scenario 1: Temporary Network Issue
```
1. User asks question
2. API call fails (network error)
3. Wait 1s → Retry → Success!
4. User gets response (with retry note)
```

### Scenario 2: API Down
```
1. User asks question
2. All 3 retries fail
3. Use cached response
4. User gets response (from cache)
5. Owner gets alert if frequent
```

### Scenario 3: Invalid Request
```
1. User asks question
2. API call fails (auth error)
3. Skip retry (won't help)
4. Use fallback response
5. Log error for debugging
```

## 🌟 Benefits

### For Users:
- Always get a response (never silent failure)
- Friendly error messages
- No technical jargon
- Helpful suggestions

### For Owner:
- Error alerts for issues
- Error logs for debugging
- Manual retry capability
- Error frequency tracking

### For Bot:
- Never crashes
- Graceful recovery
- Better reliability
- Improved user experience

## 🔧 Configuration

### Retry Settings:
- **Max Retries**: 3
- **Backoff**: Exponential (1s, 2s, 4s)
- **Cache Duration**: 24 hours
- **Cache Size**: 100 entries

### Alert Settings:
- **Threshold**: 10 errors/hour
- **Alert Frequency**: Once per hour
- **Alert Method**: Discord DM to owner

## 📊 Error Statistics

Tracked in database:
- Total errors
- Errors by type
- Errors per user/server
- Error frequency
- Recent errors

## 🚀 Usage Examples

### View Errors:
```
Owner: !errors
Bot: Shows last 10 errors with details
```

### Retry Request:
```
Owner: !retry
Bot: Retries last failed request
     Shows success/failure
```

### Automatic Recovery:
```
User: @bot question
Bot: [API fails, retries 3 times]
     [Uses cached response]
     [Responds successfully]
```

---

**Made with ❤️ for reliable bot operation**



