"""
Commands Cog - Handles bot commands
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional
import json
import os

from utils.api_handler import APIHandler
from utils.context_manager import ContextManager


class BotCommands(commands.Cog):
    """Handles bot commands"""
    
    def __init__(self, bot):
        """
        Initialize commands cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.start_time = datetime.now()
        self.message_count = 0
        self.api_handler = APIHandler()
        self.context_manager = bot.get_cog("Conversation").context_manager if bot.get_cog("Conversation") else None
    
    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        """
        Show all available commands
        
        Args:
            ctx: Command context
        """
        prefix = self.bot.config.get("prefix", "!")
        
        embed = discord.Embed(
            title="🤖 Bot Commands",
            description="Here are all available commands:",
            color=discord.Color.blue()
        )
        
        commands_list = [
            (f"{prefix}help", "Show this help message"),
            (f"{prefix}clear", "Clear conversation history for this channel"),
            (f"{prefix}summarize", "Manually summarize conversation history"),
            (f"{prefix}context", "Show conversation context statistics"),
            (f"{prefix}personality [type]", "Change bot's personality (friendly/professional/funny/helpful)"),
            (f"{prefix}status", "Show bot statistics"),
            (f"{prefix}ask [question]", "Ask a question directly"),
        ]
        
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        embed.add_field(
            name="💬 Natural Conversation",
            value=f"Just @mention me or reply to my messages to chat naturally!",
            inline=False
        )
        
        embed.set_footer(text="Made with ❤️ using discord.py")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="clear")
    async def clear_command(self, ctx: commands.Context):
        """
        Clear conversation history for this channel
        
        Args:
            ctx: Command context
        """
        if self.context_manager:
            self.context_manager.clear_context(ctx.channel.id)
        
        embed = discord.Embed(
            title="✅ Cleared",
            description="Conversation history cleared for this channel!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="summarize")
    async def summarize_command(self, ctx: commands.Context):
        """
        Manually trigger summarization of conversation history
        
        Args:
            ctx: Command context
        """
        conversation_cog = self.bot.get_cog("Conversation")
        if not conversation_cog or not conversation_cog.context_manager:
            await ctx.send("❌ Conversation system not available!")
            return
        
        context_manager = conversation_cog.context_manager
        channel_id = ctx.channel.id
        
        # Check if there are enough messages to summarize
        message_count = len(context_manager.contexts.get(channel_id, []))
        if message_count < 3:
            embed = discord.Embed(
                title="ℹ️ Not Enough Messages",
                description="Need at least 3 messages to create a summary.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        await ctx.send("🔄 Summarizing conversation history...")
        
        try:
            # Manually trigger summarization
            summary = await context_manager._summarize_old_messages(channel_id)
            
            if summary:
                # Apply the summarization
                messages_to_keep = int(context_manager.max_messages * 0.4)
                messages_to_remove = message_count - messages_to_keep
                
                if messages_to_remove > 0:
                    context_manager.contexts[channel_id] = context_manager.contexts[channel_id][messages_to_remove:]
                    
                    summary_message = {
                        "role": "system",
                        "content": f"[Previous conversation summary: {summary}]"
                    }
                    context_manager.contexts[channel_id].insert(0, summary_message)
                
                embed = discord.Embed(
                    title="✅ Summarized",
                    description=f"Conversation summarized! Reduced from {message_count} to {len(context_manager.contexts[channel_id])} messages.",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Summary",
                    value=summary[:500] + ("..." if len(summary) > 500 else ""),
                    inline=False
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Could not generate summary. Please try again.")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="context")
    async def context_command(self, ctx: commands.Context):
        """
        Show conversation context statistics
        
        Args:
            ctx: Command context
        """
        conversation_cog = self.bot.get_cog("Conversation")
        if not conversation_cog or not conversation_cog.context_manager:
            await ctx.send("❌ Conversation system not available!")
            return
        
        context_manager = conversation_cog.context_manager
        channel_id = ctx.channel.id
        
        messages = context_manager.contexts.get(channel_id, [])
        message_count = len(messages)
        max_messages = context_manager.max_messages
        threshold = int(max_messages * context_manager.summarize_threshold)
        
        # Count message types
        user_count = sum(1 for m in messages if m.get("role") == "user")
        assistant_count = sum(1 for m in messages if m.get("role") == "assistant")
        summary_count = sum(1 for m in messages if m.get("role") == "system")
        
        embed = discord.Embed(
            title="📊 Context Statistics",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Total Messages", value=str(message_count), inline=True)
        embed.add_field(name="Max Messages", value=str(max_messages), inline=True)
        embed.add_field(name="Usage", value=f"{message_count}/{max_messages}", inline=True)
        
        embed.add_field(name="User Messages", value=str(user_count), inline=True)
        embed.add_field(name="Bot Responses", value=str(assistant_count), inline=True)
        embed.add_field(name="Summaries", value=str(summary_count), inline=True)
        
        # Progress bar
        percentage = (message_count / max_messages) * 100
        bar_length = 20
        filled = int(bar_length * (message_count / max_messages))
        bar = "█" * filled + "░" * (bar_length - filled)
        
        embed.add_field(
            name="Status",
            value=f"`{bar}` {percentage:.1f}%",
            inline=False
        )
        
        if message_count >= threshold:
            embed.add_field(
                name="⚠️ Note",
                value="Context is near capacity. Summarization will occur automatically.",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="personality")
    async def personality_command(self, ctx: commands.Context, personality: Optional[str] = None):
        """
        Change bot's personality
        
        Args:
            ctx: Command context
            personality: Personality type (friendly/professional/funny/helpful)
        """
        valid_personalities = ["friendly", "professional", "funny", "helpful"]
        
        if not personality:
            current = "friendly"
            if ctx.guild and self.context_manager:
                current = self.context_manager.get_user_preference(
                    ctx.guild.id, ctx.author.id, "personality", "friendly"
                )
            
            embed = discord.Embed(
                title="🎭 Personality Settings",
                description=f"Current personality: **{current.capitalize()}**",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="Available personalities:",
                value="\n".join([f"• {p.capitalize()}" for p in valid_personalities]),
                inline=False
            )
            
            embed.add_field(
                name="Usage:",
                value=f"`{self.bot.config.get('prefix', '!')}personality [type]`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        personality = personality.lower()
        
        if personality not in valid_personalities:
            await ctx.send(
                f"❌ Invalid personality! Choose from: {', '.join(valid_personalities)}"
            )
            return
        
        # Save preference
        if ctx.guild and self.context_manager:
            self.context_manager.set_user_preference(
                ctx.guild.id, ctx.author.id, "personality", personality
            )
            self.context_manager.save_preferences()
        
        await ctx.send(
            f"✅ Personality changed to **{personality.capitalize()}**! "
            f"I'll use this tone in our conversations."
        )
    
    @commands.command(name="status")
    async def status_command(self, ctx: commands.Context):
        """
        Show bot statistics
        
        Args:
            ctx: Command context
        """
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        embed = discord.Embed(
            title="📊 Bot Status",
            color=discord.Color.green()
        )
        
        embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        embed.add_field(name="💬 Messages Processed", value=self.message_count, inline=True)
        embed.add_field(name="🏓 Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        # Server count
        server_count = len(self.bot.guilds)
        embed.add_field(name="🌐 Servers", value=server_count, inline=True)
        
        # User count
        user_count = len(set(self.bot.get_all_members()))
        embed.add_field(name="👥 Users", value=user_count, inline=True)
        
        # API provider
        use_openai = os.getenv("USE_OPENAI", "true").lower() == "true"
        api_provider = "OpenAI" if use_openai else "Anthropic Claude"
        embed.add_field(name="🤖 AI Provider", value=api_provider, inline=True)
        
        embed.set_footer(text=f"Bot started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="ask")
    async def ask_command(self, ctx: commands.Context, *, question: str):
        """
        Ask a question directly
        
        Args:
            ctx: Command context
            question: Question to ask
        """
        if not question:
            await ctx.send(f"❌ Please provide a question! Usage: `{self.bot.config.get('prefix', '!')}ask [question]`")
            return
        
        # Show typing indicator
        async with ctx.channel.typing():
            try:
                # Get conversation cog
                conversation_cog = self.bot.get_cog("Conversation")
                if not conversation_cog:
                    await ctx.send("❌ Conversation system not available!")
                    return
                
                # Check rate limit
                if not conversation_cog._check_rate_limit(ctx.author.id):
                    await ctx.send("I'm being rate limited. Please wait a moment before asking again.")
                    return
                
                # Get server ID
                server_id = ctx.guild.id if ctx.guild else None
                
                # Generate response
                response = await conversation_cog._generate_response(
                    channel_id=ctx.channel.id,
                    user_message=question,
                    user_id=ctx.author.id,
                    server_id=server_id
                )
                
                # Truncate if too long
                max_length = self.bot.config.get("max_message_length", 2000)
                if len(response) > max_length:
                    response = response[:max_length-3] + "..."
                
                await ctx.send(response)
                self.message_count += 1
                
            except Exception as e:
                await ctx.send("I'm having trouble connecting to my AI brain, please try again!")
                if self.bot.config.get("enable_logging", True):
                    conversation_cog._log_error(ctx.message, str(e))
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
        Handle command errors
        
        Args:
            ctx: Command context
            error: Error that occurred
        """
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Use `{self.bot.config.get('prefix', '!')}help` for usage.")
            return
        
        # Generic error message
        await ctx.send("Oops! Something went wrong. Please contact the server admin.")
        
        # Log error
        if self.bot.config.get("enable_logging", True):
            conversation_cog = self.bot.get_cog("Conversation")
            if conversation_cog:
                conversation_cog._log_error(ctx.message, str(error))


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(BotCommands(bot))

