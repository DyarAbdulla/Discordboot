"""
Conversation Cog - Handles natural conversations and mentions
"""

import discord
from discord.ext import commands
import asyncio
from typing import Optional, Dict
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

from utils.api_handler import APIHandler
from utils.context_manager import ContextManager
from utils.database import Database
from utils.image_analyzer import ImageAnalyzer
from utils.moderation import Moderation
from utils.web_search import WebSearch


class Conversation(commands.Cog):
    """Handles conversation interactions with the bot"""
    
    def __init__(self, bot):
        """
        Initialize conversation cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.api_handler = APIHandler()
        self.context_manager = ContextManager(
            max_messages=self.bot.config.get("max_context_messages", 15),
            summarize_threshold=self.bot.config.get("summarize_threshold", 0.8)
        )
        # Connect API handler to context manager for summarization
        self.context_manager.set_api_handler(self.api_handler)
        
        self.database = Database()
        self.image_analyzer = ImageAnalyzer()
        self.moderation = Moderation()
        self.web_search = WebSearch()
        
        # Rate limiting: {user_id: [timestamps]}
        self.rate_limits: Dict[int, List[datetime]] = defaultdict(list)
        self.rate_limit_per_minute = self.bot.config.get("rate_limit_per_minute", 5)
        
        # Load preferences
        self.context_manager.load_preferences()
        
        # Initialize database
        asyncio.create_task(self.database.initialize())
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user is within rate limit
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if within limit, False if rate limited
        """
        now = datetime.now()
        # Remove timestamps older than 1 minute
        self.rate_limits[user_id] = [
            ts for ts in self.rate_limits[user_id]
            if now - ts < timedelta(minutes=1)
        ]
        
        # Check if limit exceeded
        if len(self.rate_limits[user_id]) >= self.rate_limit_per_minute:
            return False
        
        # Add current timestamp
        self.rate_limits[user_id].append(now)
        return True
    
    def _detect_language(self, text: str) -> str:
        """
        Simple language detection (basic implementation)
        In production, use a proper language detection library
        
        Args:
            text: Text to detect language for
            
        Returns:
            Language code (default: 'en')
        """
        # Basic implementation - can be enhanced with langdetect library
        # For now, return default
        return self.bot.config.get("default_language", "en")
    
    async def _generate_response(
        self,
        channel_id: int,
        user_message: str,
        user_id: int,
        server_id: Optional[int] = None
    ) -> str:
        """
        Generate AI response for user message
        
        Args:
            channel_id: Discord channel ID
            user_message: User's message content
            user_id: User's Discord ID
            server_id: Optional server ID for preferences
            
        Returns:
            Generated response text
        """
        # Get user personality preference
        personality = "friendly"
        if server_id:
            personality = self.context_manager.get_user_preference(
                server_id, user_id, "personality", "friendly"
            )
        
        # Add user message to context (will auto-summarize if needed)
        await self.context_manager.add_message(
            channel_id, "user", user_message, user_id, auto_summarize=True
        )
        
        # Get conversation context (includes summaries if any)
        context = self.context_manager.get_context(channel_id)
        
        # Generate response
        response = await self.api_handler.generate_response(
            messages=context,
            personality=personality
        )
        
        # Add bot response to context (will auto-summarize if needed)
        await self.context_manager.add_message(
            channel_id, "assistant", response, auto_summarize=True
        )
        
        return response
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Handle incoming messages
        
        Args:
            message: Discord message object
        """
        # Ignore messages from bots (including ourselves)
        if message.author.bot:
            return
        
        # Ignore empty messages
        if not message.content:
            return
        
        # Check if bot is mentioned or message is a reply to bot
        bot_mentioned = self.bot.user in message.mentions
        is_reply_to_bot = (
            message.reference and
            message.reference.resolved and
            message.reference.resolved.author == self.bot.user
        )
        
        # Check if message starts with command prefix (let commands.py handle it)
        if message.content.startswith(self.bot.config.get("prefix", "!")):
            return
        
        # Only respond to mentions or replies
        if not (bot_mentioned or is_reply_to_bot):
            # Check for images even if not mentioned
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        await self._handle_image(message, attachment)
            return
        
        # Moderation check
        server_id = message.guild.id if message.guild else None
        if server_id and self.moderation.enabled:
            is_toxic = await self.moderation.is_toxic(message.content)
            if is_toxic:
                action = await self.moderation.get_moderation_action(message.content)
                if action == "delete":
                    try:
                        await message.delete()
                        await message.channel.send(
                            f"⚠️ Message from {message.author.mention} was removed for toxic content.",
                            delete_after=5
                        )
                    except:
                        pass
                    return
                elif action == "warn":
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, please keep messages respectful.",
                        delete_after=10
                    )
        
        # Check rate limit
        if not self._check_rate_limit(message.author.id):
            embed = discord.Embed(
                title="⏱️ Rate Limited",
                description="I'm being rate limited. Please wait a moment before asking again.",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed)
            return
        
        # Show typing indicator
        async with message.channel.typing():
            try:
                # Small delay for typing indicator
                await asyncio.sleep(self.bot.config.get("typing_indicator_delay", 0.5))
                
                # Get server ID (None for DMs)
                server_id = message.guild.id if message.guild else None
                
                # Clean message content (remove mention)
                content = message.content
                if bot_mentioned:
                    # Remove bot mention from content
                    content = content.replace(f"<@{self.bot.user.id}>", "").strip()
                    content = content.replace(f"<@!{self.bot.user.id}>", "").strip()
                
                # Check for web search request
                use_web_search = any(keyword in content.lower() for keyword in [
                    "search", "find", "latest", "current", "recent", "news", "what's happening"
                ])
                
                # Handle images in message
                image_description = None
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            image_description = await self.image_analyzer.analyze_image(
                                attachment.url,
                                "Describe this image in detail."
                            )
                            content += f"\n[User sent an image: {image_description}]"
                
                # Generate response
                if use_web_search and self.web_search:
                    response = await self.web_search.search_and_summarize(content, self.api_handler)
                else:
                    response = await self._generate_response(
                        channel_id=message.channel.id,
                        user_message=content,
                        user_id=message.author.id,
                        server_id=server_id
                    )
                
                # Save to database
                if self.database:
                    await self.database.add_conversation_message(
                        server_id, message.channel.id, message.author.id, "user", content
                    )
                    await self.database.add_conversation_message(
                        server_id, message.channel.id, self.bot.user.id, "assistant", response
                    )
                    await self.database.increment_stat(server_id, message.channel.id, "message")
                
                # Create embed response
                embed = discord.Embed(
                    description=response,
                    color=discord.Color.blue()
                )
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url
                )
                
                if image_description:
                    embed.add_field(
                        name="🖼️ Image Analysis",
                        value=image_description[:1024],
                        inline=False
                    )
                
                # Truncate if too long
                max_length = self.bot.config.get("max_message_length", 2000)
                if len(response) > max_length:
                    embed.description = response[:max_length-3] + "..."
                
                # Send response
                await message.reply(embed=embed)
                
                # Log conversation if enabled
                if self.bot.config.get("enable_logging", True):
                    self._log_conversation(message, response)
            
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description="I'm having trouble connecting to my AI brain, please try again!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed)
                
                # Log error
                if self.bot.config.get("enable_logging", True):
                    self._log_error(message, str(e))
    
    async def _handle_image(self, message: discord.Message, attachment: discord.Attachment):
        """
        Handle image analysis when user sends image
        
        Args:
            message: Discord message
            attachment: Image attachment
        """
        try:
            async with message.channel.typing():
                description = await self.image_analyzer.analyze_image(
                    attachment.url,
                    "Describe this image in detail. What do you see?"
                )
                
                embed = discord.Embed(
                    title="🖼️ Image Analysis",
                    description=description,
                    color=discord.Color.purple()
                )
                embed.set_image(url=attachment.url)
                embed.set_footer(text=f"Analyzed image from {message.author.display_name}")
                
                await message.reply(embed=embed)
        except Exception as e:
            await message.channel.send(f"❌ Could not analyze image: {str(e)}")
    
    def _log_conversation(self, message: discord.Message, response: str):
        """
        Log conversation to file
        
        Args:
            message: User message
            response: Bot response
        """
        try:
            log_file = self.bot.config.get("log_file", "bot.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            server_name = message.guild.name if message.guild else "DM"
            channel_name = message.channel.name if hasattr(message.channel, 'name') else "DM"
            
            log_entry = (
                f"[{timestamp}] {server_name}#{channel_name} | "
                f"{message.author.name}: {message.content} | "
                f"Bot: {response}\n"
            )
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error logging conversation: {e}")
    
    def _log_error(self, message: discord.Message, error: str):
        """
        Log error to file
        
        Args:
            message: Message that caused error
            error: Error message
        """
        try:
            log_file = self.bot.config.get("log_file", "bot.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            log_entry = (
                f"[{timestamp}] ERROR | "
                f"User: {message.author.name} | "
                f"Message: {message.content} | "
                f"Error: {error}\n"
            )
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error logging error: {e}")


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(Conversation(bot))

