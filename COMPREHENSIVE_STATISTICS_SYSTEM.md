# Comprehensive Statistics System - Implementation Guide

## ✅ Implementation Complete!

Your Discord bot now has a comprehensive statistics system that tracks detailed metrics and displays beautiful charts!

## 🎯 Features Implemented

### 1. **Personal Statistics (`!stats`)**
   - Messages per day (with chart)
   - Most active hours
   - Language distribution
   - Commands used
   - Account retention info
   - Response times
   - Activity charts

### 2. **Server Statistics (`!serverstats`)** - Admin Only
   - Total messages and users
   - Most active users
   - Messages per day (with chart)
   - Most active hours
   - Language distribution
   - Popular questions/topics
   - Commands used
   - User retention

### 3. **Global Statistics (`!globalstats`)** - Owner Only
   - Total messages across all servers
   - Total users and servers
   - API costs per day/week/month
   - Token usage
   - Error rate
   - Language distribution
   - Most active servers
   - Commands used
   - User retention

### 4. **Automatic Tracking**
   - Messages per user/server/day
   - Most active users/times
   - Popular questions/topics
   - Average response time
   - API costs per day/week/month
   - Most used commands
   - Language distribution (English vs Kurdish)
   - Error rate
   - User retention (returning users)

## 📁 Files Created/Modified

### New Files:
1. **`utils/statistics_tracker.py`** - Comprehensive statistics tracker
   - Database schema for all statistics
   - Methods to track various metrics
   - Methods to retrieve statistics
   - Chart generation utilities

### Modified Files:
1. **`bot.py`**
   - Added statistics tracker initialization
   - Integrated tracking into message handling
   - Added `!stats` command (personal stats)
   - Added `!serverstats` command (admin only)
   - Added `!globalstats` command (owner only)
   - Tracks messages, commands, languages, API usage, errors

## 🎯 Database Schema

### `message_stats` Table:
- Tracks messages per user/server/day/hour
- Language detection
- Command usage
- Hourly activity patterns

### `question_stats` Table:
- Tracks questions asked
- Topics/categories
- Language used

### `api_stats` Table:
- API calls per day
- Tokens used
- Success/failure rates
- Estimated costs
- Model used

### `error_stats` Table:
- Error types
- Error messages
- User/server context
- Timestamps

### `user_retention` Table:
- First seen date
- Last seen date
- Total messages
- Days active

## 🔧 Commands

### `!stats` - Personal Statistics
Shows your personal statistics:
- Total messages (30 days)
- Activity chart (last 7 days)
- Most active hours
- Language distribution
- Commands used
- Response times
- Account info (first seen, days active)

### `!serverstats` - Server Statistics (Admin Only)
Shows server-wide statistics:
- Total messages and users
- Most active users
- Activity charts
- Language distribution
- Popular questions
- Commands used
- User retention

### `!globalstats` - Global Statistics (Owner Only)
Shows statistics across all servers:
- Total messages/users/servers
- API costs and usage
- Error rates
- Language distribution
- Most active servers
- Commands used

## 📊 Visual Charts

### Text-Based Charts:
- Activity charts (messages per day)
- Bar charts for distributions
- Time-based charts
- ASCII art visualization

### Chart Format:
```
01/15  ████████ 150
01/16  ████████████ 200
01/17  ██████ 100
```

## 🎯 Tracked Metrics

### Messages:
- Per user/server/day/hour
- Language detection
- Command vs regular messages
- Time-based patterns

### Questions:
- Question text
- Topics/categories
- Language used
- Frequency

### API Usage:
- Tokens used per day
- API calls (success/failure)
- Estimated costs
- Model used

### Errors:
- Error types
- Error messages
- User/server context
- Frequency

### User Retention:
- First seen date
- Last seen date
- Total messages
- Days active
- Returning users

## 📈 Example Outputs

### Personal Stats:
```
📊 Personal Statistics - UserName

💬 Total Messages (30 days): 150
📅 Account Info:
   First Seen: 2024-01-01
   Last Seen: 2024-01-15
   Days Active: 10

📈 Activity (Last 7 Days):
01/09  ████████ 20
01/10  ████████████ 30
01/11  ██████ 15

🕐 Most Active Hours:
14:00: 25 messages
18:00: 20 messages

🌍 Language Distribution:
EN: 100 messages
KU: 50 messages

⚙️ Commands Used:
!ask: 10 times
!help: 5 times
```

### Server Stats:
```
📊 Server Statistics - ServerName

📊 Overview:
Total Messages: 1,500
Unique Users: 50
Returning Users: 30

👥 Most Active Users:
User1: 200 messages
User2: 150 messages

📈 Activity (Last 7 Days):
[Chart]

🌍 Language Distribution:
EN: 1,000 messages (66.7%)
KU: 500 messages (33.3%)

❓ Popular Questions:
1. What is AI? (10x)
2. How do I use Python? (8x)
```

### Global Stats:
```
📊 Global Statistics (All Servers)

📊 Overview:
Total Messages: 10,000
Unique Users: 500
Total Servers: 10
Returning Users: 300

💰 API Usage & Costs:
Total Cost: $5.25
Total Tokens: 7,000,000
API Calls: 10,000
Error Rate: 2.5%

💵 Daily API Costs (Last 7 Days):
01/09  ████ $0.50
01/10  ████████ $1.00
```

## 🌟 Benefits

### For Users:
- See your activity stats
- Track your usage
- Understand your patterns
- Personal insights

### For Admins:
- Server activity overview
- User engagement metrics
- Popular topics
- Language preferences

### For Owners:
- Global bot performance
- API cost tracking
- Error monitoring
- Usage patterns

## 🔍 Technical Details

### Tracking:
- Automatic tracking on every message
- Command tracking
- Language detection tracking
- API usage tracking
- Error tracking

### Storage:
- SQLite database
- Efficient indexing
- Daily aggregation
- Historical data

### Charts:
- Text-based ASCII charts
- Time-based visualization
- Bar charts for distributions
- Easy to read format

## 📝 Permissions

### Commands:
- `!stats` - Everyone
- `!serverstats` - Administrators only
- `!globalstats` - Bot owner only

### Security:
- Permission checks
- Server isolation
- User privacy
- Data protection

---

**Made with ❤️ for comprehensive analytics**




