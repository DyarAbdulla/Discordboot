# 🔧 Integration Guide - Using the New Multi-API System

## Overview

The bot now uses a **Multi-API Manager** that intelligently routes queries to the best API provider. This guide shows how to update existing code to use the new system.

---

## 🎯 Quick Start

### Old Way (Claude Only):
```python
if self.bot.use_claude and self.bot.claude_handler:
    result = await self.bot.claude_handler.generate_response(
        messages=api_messages,
        user_name=user_name,
        summaries=summary_texts
    )
```

### New Way (Multi-API):
```python
if self.bot.api_manager:
    result = await self.bot.api_manager.generate_response(
        messages=api_messages,
        system_prompt=system_prompt,
        user_name=user_name,
        query=user_query,  # For intelligent routing
        detected_language=detected_language,
        has_image=has_image
    )
    
    # Result includes:
    # - result["response"] - The response text
    # - result["success"] - Success boolean
    # - result["provider"] - Which API was used (claude, gemini, groq, openrouter)
    # - result["response_time"] - Response time in seconds
    # - result["cost"] - Cost in USD
    # - result["query_type"] - Query classification (simple, speed, complex, etc.)
```

---

## 📝 Key Changes

### 1. API Manager Initialization

The API manager is automatically initialized in `bot.py`. It:
- Checks for all API keys (Claude, Gemini, Groq, OpenRouter)
- Initializes available providers
- Sets up cost tracking and budget management

### 2. Response Format

The new API manager returns a dictionary with more information:

```python
{
    "response": "The actual response text",
    "success": True,
    "provider": "claude",  # or "gemini", "groq", "openrouter"
    "response_time": 1.23,
    "cost": 0.0015,
    "query_type": "complex",
    "input_tokens": 100,
    "output_tokens": 50
}
```

### 3. Using Cache

The cache manager is automatically used by the API manager, but you can also use it directly:

```python
if self.bot.cache_manager:
    # Check cache first
    cached = self.bot.cache_manager.get(query, context={"language": detected_language})
    if cached:
        return cached
    
    # Generate response...
    
    # Cache the response
    self.bot.cache_manager.set(query, result, context={"language": detected_language})
```

### 4. Analytics Tracking

Log interactions to analytics:

```python
if self.bot.analytics_tracker:
    await self.bot.analytics_tracker.log_interaction(
        user_id=str(user.id),
        username=user.display_name,
        server_id=str(server.id) if server else None,
        channel_id=str(channel.id),
        query_text=query,
        bot_response=response,
        api_provider=result.get("provider"),
        response_time=result.get("response_time", 0),
        tokens_used=result.get("input_tokens", 0) + result.get("output_tokens", 0),
        cost=result.get("cost", 0),
        language_detected=detected_language,
        success=result.get("success", True)
    )
```

---

## 🔄 Updating Conversation Handlers

### Example: Updating `cogs/slash_commands.py`

**Before:**
```python
if self.bot.use_claude and self.bot.claude_handler:
    result = await self.bot.claude_handler.generate_response(
        messages=api_messages,
        user_name=interaction.user.display_name,
        summaries=summary_texts if summary_texts else None,
        detected_language=detected_language,
        kurdish_dialect=kurdish_dialect,
        user_facts=user_facts
    )
```

**After:**
```python
# Build system prompt (from claude_handler or create new one)
system_prompt = self._get_system_prompt(detected_language, kurdish_dialect, user_facts)

if self.bot.api_manager:
    result = await self.bot.api_manager.generate_response(
        messages=api_messages,
        system_prompt=system_prompt,
        user_name=interaction.user.display_name,
        query=question,  # For intelligent routing
        detected_language=detected_language,
        has_image=False  # Set to True if image attached
    )
    
    if result["success"]:
        response_text = result["response"]
        api_provider = result["provider"]
        response_time = result["response_time"]
        cost = result["cost"]
        
        # Create embed with provider info
        embed = EmbedHelper.create_ai_response_embed(
            content=response_text,
            user_name=interaction.user.display_name,
            user_avatar=interaction.user.display_avatar.url,
            response_time=f"{response_time:.2f}s",
            api_provider=api_provider,
            cached=result.get("cached", False),
            detected_language=detected_language
        )
        
        await interaction.followup.send(embed=embed)
        
        # Log to analytics
        if self.bot.analytics_tracker:
            await self.bot.analytics_tracker.log_interaction(
                user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                server_id=str(interaction.guild.id) if interaction.guild else None,
                channel_id=str(interaction.channel.id),
                query_text=question,
                bot_response=response_text,
                api_provider=api_provider,
                response_time=response_time,
                tokens_used=result.get("input_tokens", 0) + result.get("output_tokens", 0),
                cost=cost,
                language_detected=detected_language,
                success=True
            )
    else:
        # Handle error
        embed = EmbedHelper.create_error_embed(
            title="❌ Error",
            description="I'm having trouble connecting right now.",
            error_details=result.get("error", "Unknown error")
        )
        await interaction.followup.send(embed=embed)
else:
    # Fallback to old Claude handler or static responses
    if self.bot.use_claude and self.bot.claude_handler:
        # Use old handler...
```

---

## 🎨 Using Enhanced Embeds

The embed helper now supports provider information:

```python
from utils.embed_helper import EmbedHelper, EmbedColors

# AI Response with provider info
embed = EmbedHelper.create_ai_response_embed(
    content=response_text,
    user_name=user.display_name,
    user_avatar=user.display_avatar.url,
    response_time="1.23s",
    api_provider="groq",  # Shows "⚡ Powered by Groq"
    cached=False,
    detected_language="en"
)

# Error embed with suggestions
embed = EmbedHelper.create_error_embed(
    title="❌ Error",
    description="Something went wrong.",
    error_details="API connection failed",
    suggested_action="Try again in a moment or use /api status to check API health"
)

# Translation embed
embed = EmbedHelper.create_translation_embed(
    original_text="Hello",
    translated_text="سڵاو",
    source_lang="en",
    target_lang="ku",
    detected_language="ku"
)
```

---

## 📊 Analytics Queries

Get statistics:

```python
# User stats
user_stats = await self.bot.analytics_tracker.get_user_stats(user_id)

# Server stats
server_stats = await self.bot.analytics_tracker.get_server_stats(server_id)

# Global stats
global_stats = await self.bot.analytics_tracker.get_global_stats(days=30)

# Cost analytics
cost_analytics = await self.bot.analytics_tracker.get_cost_analytics(days=30)

# Leaderboard
top_users = await self.bot.analytics_tracker.get_leaderboard("messages", limit=10)
```

---

## 🔧 Configuration

Update `config.json`:

```json
{
  "primary_api": "claude",
  "enable_fallback": true,
  "cost_optimization": true,
  "monthly_budget": 50,
  "cache_enabled": true,
  "cache_max_size": 1000,
  "analytics_enabled": true,
  "max_context_messages": 15
}
```

---

## ⚠️ Backward Compatibility

The old `claude_handler` is still available for backward compatibility:
- If `api_manager` is not available, falls back to `claude_handler`
- If `claude_handler` is not available, falls back to static responses

This ensures the bot always works, even if some APIs are unavailable.

---

## 🚀 Best Practices

1. **Always check if api_manager exists** before using it
2. **Log all interactions** to analytics for tracking
3. **Use cache** for common queries to save costs
4. **Handle errors gracefully** with user-friendly messages
5. **Show provider info** in embeds so users know which API was used
6. **Monitor costs** using `/api costs` regularly
7. **Test APIs** using `/api test` after deployment

---

## 📝 Example: Complete Integration

```python
async def handle_message(self, message):
    """Handle a user message with full integration"""
    
    # 1. Check cache
    if self.bot.cache_manager:
        cached = self.bot.cache_manager.get(message.content)
        if cached:
            await message.reply(embed=EmbedHelper.create_ai_response_embed(
                content=cached["response"],
                api_provider=cached.get("provider", "cached"),
                cached=True
            ))
            return
    
    # 2. Detect language
    detected_language = detect_language(message.content)
    
    # 3. Get conversation context
    messages = get_conversation_context(message.channel.id)
    
    # 4. Generate response using API manager
    if self.bot.api_manager:
        result = await self.bot.api_manager.generate_response(
            messages=messages,
            system_prompt=get_system_prompt(),
            user_name=message.author.display_name,
            query=message.content,
            detected_language=detected_language
        )
        
        if result["success"]:
            # 5. Cache response
            if self.bot.cache_manager:
                self.bot.cache_manager.set(message.content, result)
            
            # 6. Create embed
            embed = EmbedHelper.create_ai_response_embed(
                content=result["response"],
                user_name=message.author.display_name,
                api_provider=result["provider"],
                response_time=f"{result['response_time']:.2f}s",
                detected_language=detected_language
            )
            
            # 7. Send response
            await message.reply(embed=embed)
            
            # 8. Log to analytics
            if self.bot.analytics_tracker:
                await self.bot.analytics_tracker.log_interaction(
                    user_id=str(message.author.id),
                    username=message.author.display_name,
                    server_id=str(message.guild.id) if message.guild else None,
                    channel_id=str(message.channel.id),
                    query_text=message.content,
                    bot_response=result["response"],
                    api_provider=result["provider"],
                    response_time=result["response_time"],
                    tokens_used=result.get("input_tokens", 0) + result.get("output_tokens", 0),
                    cost=result["cost"],
                    language_detected=detected_language,
                    success=True
                )
        else:
            # Handle error
            await message.reply(embed=EmbedHelper.create_error_embed(
                description="I'm having trouble right now. Please try again."
            ))
```

---

**🎉 Your bot is now using the premium multi-API system!**

