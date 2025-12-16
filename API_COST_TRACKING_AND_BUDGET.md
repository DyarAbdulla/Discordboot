# API Cost Tracking and Budget Management - Implementation Guide

## ✅ Implementation Complete!

Your Discord bot now has comprehensive API cost tracking and budget management with automatic alerts!

## 🎯 Features Implemented

### 1. **Accurate Cost Calculation**
   - Tracks input and output tokens separately
   - Uses Claude 3.5 Haiku pricing:
     - Input: $0.25 per 1M tokens
     - Output: $1.25 per 1M tokens
   - Accurate cost per message
   - Daily/weekly/monthly totals

### 2. **Budget Management**
   - Set monthly budget with `!budget [amount]`
   - View current budget and spending
   - Automatic budget reset at start of month
   - Budget alerts at 50%, 75%, and 90%

### 3. **Cost Breakdown**
   - Total costs by time period
   - Costs by user
   - Costs by server
   - Daily cost charts
   - Token usage breakdown

### 4. **Automatic Alerts**
   - DM bot owner at 50% budget usage
   - DM at 75% budget usage
   - DM at 90% budget usage (critical)
   - One alert per threshold per month

### 5. **Rate Limiting**
   - Blocks API calls if budget exceeded
   - Friendly error message to users
   - Owner can update budget to resume

### 6. **Commands**
   - `!costs` - Show API spending breakdown
   - `!budget` - View current budget
   - `!budget [amount]` - Set monthly budget (Owner only)

## 📁 Files Modified

### Modified Files:
1. **`utils/statistics_tracker.py`**
   - Enhanced cost calculation (input/output tokens)
   - Added budget settings table
   - Added cost breakdown methods
   - Added budget management methods

2. **`claude_handler.py`**
   - Returns input/output tokens separately
   - Accurate token tracking

3. **`bot.py`**
   - Added budget checking before API calls
   - Added budget alerting system
   - Added `!costs` command
   - Added `!budget` command
   - Budget rate limiting

## 🎯 How It Works

### Cost Calculation:
1. Track input tokens separately
2. Track output tokens separately
3. Calculate: `(input_tokens / 1M) * $0.25 + (output_tokens / 1M) * $1.25`
4. Store in database with user/server context

### Budget Alerts:
1. Check current month spending
2. Compare to budget
3. Send alert if threshold reached
4. Mark alert as sent (one per threshold)

### Rate Limiting:
1. Check budget before API call
2. If exceeded → Block request
3. Show friendly error message
4. Owner can update budget to resume

## 📊 Commands

### `!costs` - Show API Spending
Shows comprehensive cost breakdown:
- Total costs (daily/weekly/monthly)
- Token usage (input/output)
- Top users by cost
- Top servers by cost
- Daily cost charts
- Budget status

### `!budget` - View Budget
Shows current budget settings:
- Monthly budget amount
- Current month spending
- Usage percentage
- Remaining budget

### `!budget [amount]` - Set Budget (Owner Only)
Sets monthly budget:
- Updates budget amount
- Resets alerts
- Shows confirmation

## 💰 Cost Breakdown

### By Time Period:
- **Daily**: Last 7 days
- **Weekly**: Last 7 days
- **Monthly**: Current month

### By User:
- Top 10 users by cost
- Per-user spending
- User-specific breakdown

### By Server:
- Top 10 servers by cost
- Per-server spending
- Server-specific breakdown

## 🚨 Budget Alerts

### Alert Thresholds:
- **50%**: Warning alert
- **75%**: High usage alert
- **90%**: Critical alert

### Alert Content:
- Current spending
- Budget amount
- Usage percentage
- Remaining budget
- Action suggestions

### Alert Frequency:
- One alert per threshold per month
- Resets at start of new month
- Sent via Discord DM to owner

## 📈 Example Outputs

### Costs Command:
```
💰 API Costs & Spending

📊 Overview (Current Month):
Total Cost: $12.45
Total Tokens: 16,600,000
Input Tokens: 11,620,000
Output Tokens: 4,980,000
API Calls: 1,000
Success Rate: 98.5%

✅ Budget Status:
Monthly Budget: $50.00
Current Month: $12.45
Usage: 24.9%
Remaining: $37.55

📈 Daily Costs (Last 7 Days):
01/15  ████ $1.50
01/16  ████████ $3.00
01/17  ████ $1.80

👥 Top Users by Cost:
User1: $3.50
User2: $2.80
User3: $1.90
```

### Budget Command:
```
💰 Monthly Budget

Budget Amount: $50.00/month
Current Spending: $12.45
Usage: 24.9%
Remaining: $37.55
```

## 🔧 Configuration

### Pricing (Claude 3.5 Haiku):
- **Input Tokens**: $0.25 per 1M tokens
- **Output Tokens**: $1.25 per 1M tokens

### Budget Settings:
- **Type**: Monthly
- **Alert Thresholds**: 50%, 75%, 90%
- **Reset**: Automatic at start of month

## 🌟 Benefits

### For Owner:
- Track spending accurately
- Set budget limits
- Get alerts before overspending
- Detailed cost breakdowns
- Prevent surprises

### For Bot:
- Automatic budget enforcement
- Rate limiting when exceeded
- Accurate cost tracking
- Per-user/server tracking

## 📝 Database Schema

### `api_stats` Table:
- `date` - Date of usage
- `user_id` - User who made request
- `server_id` - Server where request was made
- `input_tokens` - Input tokens used
- `output_tokens` - Output tokens used
- `tokens_used` - Total tokens
- `estimated_cost` - Calculated cost
- `model_used` - Model name

### `budget_settings` Table:
- `budget_type` - Type (monthly)
- `budget_amount` - Budget amount
- `alert_50_sent` - 50% alert sent flag
- `alert_75_sent` - 75% alert sent flag
- `alert_90_sent` - 90% alert sent flag
- `last_alert_date` - Last alert date

## 🚀 Usage Examples

### Set Budget:
```
Owner: !budget 50
Bot: ✅ Budget Updated!
     Monthly budget set to $50.00
     Current spending: $12.45
     Usage: 24.9%
```

### View Costs:
```
User: !costs
Bot: Shows comprehensive cost breakdown
```

### Budget Alert:
```
Owner receives DM:
⚠️ Budget Alert

Your API usage has reached 75% of your monthly budget!

Current Spending: $37.50
Budget: $50.00
Usage: 75.0%

⚠️ Budget is getting high. Monitor usage carefully.
```

## 💡 Best Practices

### Budget Management:
1. Set realistic monthly budget
2. Monitor costs regularly
3. Review top users/servers
4. Adjust budget as needed
5. Use alerts to stay informed

### Cost Optimization:
1. Review daily costs
2. Identify high-cost users/servers
3. Optimize prompts if needed
4. Use caching when possible
5. Monitor token usage

---

**Made with ❤️ for budget-conscious bot operation**




