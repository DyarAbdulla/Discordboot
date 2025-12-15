# Permission System - Implementation Guide

## ✅ Implementation Complete!

Your Discord bot now has a comprehensive tiered permission system!

## 🔐 Permission Levels

### 1. **👑 Owner**
- **Access**: Full access to all features
- **Rate Limit**: Unlimited (999,999 messages/minute)
- **Features**:
  - All commands
  - Unlimited rate limit
  - Premium features
  - Admin features
  - Owner-only commands

### 2. **🛡️ Admin**
- **Access**: Server administrators
- **Rate Limit**: 20 messages/minute
- **Features**:
  - Moderation commands
  - Server management
  - Higher rate limit
  - All regular features

### 3. **⭐ Premium**
- **Access**: Special supporters
- **Rate Limit**: 15 messages/minute
- **Features**:
  - Premium features
  - Higher rate limit
  - Priority support
  - Longer AI responses

### 4. **👤 Regular**
- **Access**: Standard users
- **Rate Limit**: 5 messages/minute
- **Features**:
  - Standard features
  - Basic rate limit
  - Regular AI responses

## 📁 Files Modified

### Modified Files:
1. **`bot.py`**
   - Added permission system with 4 levels
   - Implemented tiered rate limits
   - Added permission checking methods
   - Added premium feature checks
   - Added permission commands

## 🎯 How It Works

### Permission Hierarchy:
```
Owner (Level 4)
    ↓
Admin (Level 3)
    ↓
Premium (Level 2)
    ↓
Regular (Level 1)
```

### Permission Detection:
1. **Owner Check**: Bot owner ID
2. **Admin Check**: Discord server administrator permission
3. **Premium Check**: Premium users set
4. **Regular**: Default for all users

### Rate Limits:
- **Owner**: Unlimited (999,999/min)
- **Admin**: 20 messages/minute
- **Premium**: 15 messages/minute
- **Regular**: 5 messages/minute

## 💡 Commands

### **!permissions** (or !perms, !perm)
Show your permission level and rate limits

**Usage:**
```
!permissions
```

**Output:**
```
🔐 Your Permissions

Level: ⭐ Premium
Description: Premium supporter
Rate Limit: 15 messages/minute

✨ Features:
• Premium features
• Higher rate limit
• Priority support
```

### **!setpremium @user [add/remove]** (Owner only)
Grant or revoke premium access

**Usage:**
```
!setpremium @user add - Grant premium
!setpremium @user remove - Remove premium
!setpremium list - List premium users
```

## 🌟 Premium Features

### Enhanced Features:
- **Longer Stories**: Premium users get 4-5 paragraph stories vs 2-3 for regular
- **Higher Rate Limit**: 15 messages/minute vs 5 for regular
- **Priority Support**: Premium users get priority in support

### Future Premium Features:
- Extended conversation context
- Custom AI personalities
- Advanced image analysis
- More API calls per day

## 🚀 Benefits

### For Users:
- **Clear Permissions**: Know your access level
- **Fair Limits**: Rate limits based on support level
- **Premium Benefits**: Extra features for supporters

### For Server Owners:
- **Tiered Access**: Different levels for different users
- **Premium Rewards**: Reward supporters with premium
- **Admin Control**: Server admins have moderation access

## 📊 Permission Checking

### Automatic Checks:
- **Rate Limits**: Automatically applied based on level
- **Command Access**: Commands check permission levels
- **Feature Access**: Premium features check premium status

### Manual Checks:
```python
# Check if user has permission
if self._has_permission(user_id, 'premium', guild):
    # Grant premium feature
    pass

# Check premium feature access
if self._check_premium_feature(user_id):
    # Grant premium feature
    pass
```

## 💡 Best Practices

### For Owners:
1. Grant premium to supporters
2. Use `!setpremium list` to manage premium users
3. Premium is per-user, not per-server

### For Admins:
1. Automatically have admin access
2. Can use moderation commands
3. Higher rate limit for server management

### For Premium Users:
1. Enjoy enhanced features
2. Higher rate limit
3. Priority support

## 🔍 Technical Details

### Permission Storage:
- **Premium Users**: Set of user IDs (in-memory)
- **Owner**: Bot owner ID from application info
- **Admin**: Discord server permission check
- **Regular**: Default for all users

### Rate Limiting:
- **Per-Level**: Different limits per permission level
- **Per-User**: Tracks messages per user
- **Time-Based**: 1-minute sliding window

### Permission Methods:
- `_get_user_permission_level()`: Get user's level
- `_get_rate_limit_for_level()`: Get rate limit for level
- `_has_permission()`: Check if user has required level
- `_check_premium_feature()`: Check premium access

---

**Made with ❤️ for tiered access control!**

