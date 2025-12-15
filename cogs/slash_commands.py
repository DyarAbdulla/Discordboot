"""
Slash Commands Cog - Modern Discord slash commands
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from datetime import datetime
import asyncio
import random
import time

# Import responses for fallback
try:
    from responses import find_response
except ImportError:
    # Fallback if responses module not available
    def find_response(text: str, detected_language: str = None, kurdish_dialect: str = None) -> str:
        return "I'm here to help! How can I assist you?"

# Import Kurdish detector
try:
    from utils.kurdish_detector import KurdishDetector
    KURDISH_DETECTOR_AVAILABLE = True
except ImportError:
    KURDISH_DETECTOR_AVAILABLE = False

# Import embed helper
try:
    from utils.embed_helper import EmbedHelper, EmbedColors
    EMBED_HELPER_AVAILABLE = True
except ImportError:
    EMBED_HELPER_AVAILABLE = False


class SlashCommands(commands.Cog):
    """Handles Discord slash commands"""
    
    def __init__(self, bot):
        """
        Initialize slash commands cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
    
    @app_commands.command(name="help", description="Show bot help and available commands")
    async def help_slash(self, interaction: discord.Interaction):
        """Show all available commands"""
        prefix = self.bot.config.get("prefix", "!")
        
        embed = discord.Embed(
            title="🤖 AI Boot Commands",
            description="Here's what I can do:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 Slash Commands",
            value=(
                "`/help` - Show this help\n"
                "`/ask [question]` - Ask the bot anything\n"
                "`/stats` - Show bot statistics\n"
                "`/clear` - Clear conversation history\n"
                "`/personality [type]` - Change bot personality\n"
                "`/export` - Export conversation data\n"
                "`/summarize [user]` - Summarize conversation\n"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💬 Prefix Commands (Legacy)",
            value=(
                f"`{prefix}help` - Show help\n"
                f"`{prefix}ping` - Check if I'm online\n"
                f"`{prefix}info` - Bot information\n"
                f"`{prefix}commands` - List commands\n"
                f"`{prefix}about` - Bot description & languages\n"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💬 Chat with me",
            value=(
                "Just @mention me (@AI Boot) or send me a DM!\n"
                "I'll have a natural conversation with you using AI."
            ),
            inline=False
        )
        
        embed.set_footer(text="Made with ❤️ for Discord")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ask", description="Ask the bot anything")
    @app_commands.describe(question="Your question or message to the bot")
    async def ask_slash(self, interaction: discord.Interaction, question: str):
        """Ask the bot a question"""
        await interaction.response.defer()
        
        # Show typing indicator while processing
        # Note: Discord automatically shows typing for deferred interactions, but we can keep it active
        async with interaction.channel.typing():
            # Start timing the response
            start_time = None
            if self.bot.response_tracker:
                start_time = self.bot.response_tracker.start_timer()
            
            # Check rate limit using bot's method
            if hasattr(self.bot, '_check_rate_limit'):
                if not self.bot._check_rate_limit(interaction.user.id):
                    await interaction.followup.send("Whoa, slow down! Let's chat in a minute 😊")
                    return
        
        try:
            # Detect language (especially Kurdish)
            detected_language = 'en'
            kurdish_dialect = None
            if KURDISH_DETECTOR_AVAILABLE:
                lang_result = KurdishDetector.detect_language(question)
                detected_language = lang_result[0]
                
                # If Kurdish detected, determine dialect
                if detected_language == 'ku':
                    kurdish_result = KurdishDetector.detect_kurdish(question)
                    if kurdish_result:
                        kurdish_dialect, confidence = kurdish_result
                        print(f"[INFO] Kurdish detected in slash command: {kurdish_dialect} (confidence: {confidence:.2f})")
            
            # Use bot's message handling logic
            # Create a mock message-like object for processing
            user_id = str(interaction.user.id)
            channel_id = str(interaction.channel.id)
            
            # Store user message in database if memory manager is available
            if self.bot.memory_manager:
                self.bot.memory_manager.add_message(
                    user_id=user_id,
                    channel_id=channel_id,
                    role="user",
                    content=question
                )
            
            # Get conversation context
            api_messages = []
            summary_texts = []
            if self.bot.memory_manager:
                api_messages, summary_texts = self.bot.memory_manager.get_conversation_context(
                    user_id=user_id,
                    channel_id=channel_id,
                    include_summaries=True
                )
                if not api_messages or api_messages[-1]["content"] != question:
                    api_messages.append({"role": "user", "content": question})
            else:
                api_messages = [{"role": "user", "content": question}]
            
            # Get user facts for personalization
            user_facts = []
            if self.bot.memory_manager:
                facts_list = self.bot.memory_manager.get_all_user_facts(user_id, channel_id)
                user_facts = facts_list
            
            # Get user facts for personalization
            user_facts = []
            if self.bot.memory_manager:
                facts_list = self.bot.memory_manager.get_all_user_facts(user_id, channel_id)
                user_facts = facts_list
            
            # Generate response using Claude or fallback
            response_text = None
            tokens_used = 0
            model_used = "static_fallback"
            result = None
            
            if self.bot.use_claude and self.bot.claude_handler:
                result = await self.bot.claude_handler.generate_response(
                    messages=api_messages,
                    user_name=interaction.user.display_name,
                    summaries=summary_texts if summary_texts else None,
                    detected_language=detected_language,
                    kurdish_dialect=kurdish_dialect,
                    user_facts=user_facts
                )
                
                if result["success"]:
                    response_text = result["response"]
                    tokens_used = result.get("tokens_used", 0)
                    model_used = self.bot.claude_handler.model
                    self.bot.claude_responses += 1
                else:
                    # Fallback to static response
                    response_text = find_response(question, detected_language, kurdish_dialect)
                    self.bot.fallback_responses += 1
            else:
                # Use static responses
                response_text = find_response(question, detected_language, kurdish_dialect)
                self.bot.fallback_responses += 1
            
            # Store bot response
            if self.bot.memory_manager:
                self.bot.memory_manager.add_message(
                    user_id=user_id,
                    channel_id=channel_id,
                    role="assistant",
                    content=response_text
                )
            
            # Log conversation
            if self.bot.conversation_logger:
                # Determine tokens and model used
                tokens_used_log = 0
                model_used_log = "static_fallback"
                if self.bot.use_claude and self.bot.claude_handler:
                    if result and result.get("success"):
                        tokens_used_log = result.get("tokens_used", 0)
                        model_used_log = self.bot.claude_handler.model
                
                self.bot.conversation_logger.log_conversation(
                    user_id=user_id,
                    user_name=interaction.user.display_name,
                    channel_id=channel_id,
                    user_message=question,
                    bot_response=response_text,
                    tokens_used=tokens_used_log,
                    model_used=model_used_log
                )
            
            # Calculate response time and format it
            response_time = None
            response_time_text = None
            if start_time and self.bot.response_tracker:
                response_time = time.time() - start_time
                response_time_text = f"⏱️ Responded in {self.bot.response_tracker.format_response_time(response_time)}"
                
                # Record response time
                self.bot.response_tracker.record_response_time(
                    response_time=response_time,
                    user_id=user_id,
                    channel_id=channel_id,
                    used_claude=(self.bot.use_claude and result and result.get("success")),
                    model_used=model_used_log,
                    tokens_used=tokens_used_log
                )
            
            # Add human-like delay for very short responses (< 50 chars)
            # This makes the bot feel more natural
            if len(response_text) < 50 and response_time and response_time < 0.5:
                # Add random delay between 0.5-1.5 seconds for short responses
                delay = random.uniform(0.5, 1.5)
                await asyncio.sleep(delay)
                # Update response time to include delay
                if start_time and self.bot.response_tracker:
                    response_time = time.time() - start_time
                    response_time_text = f"⏱️ Responded in {self.bot.response_tracker.format_response_time(response_time)}"
            
            # Generate question suggestions (only for successful Claude responses)
            question_suggestions = []
            if self.bot.use_claude and self.bot.claude_handler and result and result.get("success"):
                try:
                    # Get recent conversation history for context
                    recent_history = api_messages[-10:] if api_messages else []
                    
                    question_suggestions = await self.bot.claude_handler.generate_question_suggestions(
                        user_question=question,
                        bot_answer=response_text,
                        conversation_history=recent_history,
                        user_facts=user_facts,
                        detected_language=detected_language,
                        kurdish_dialect=kurdish_dialect
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to generate question suggestions: {e}")
                    question_suggestions = []
            
            # Update statistics
            self.bot.message_count += 1
            
            # Create embed for AI response
            if EMBED_HELPER_AVAILABLE:
                # Split long content if needed
                content_chunks = EmbedHelper.split_long_content(response_text, max_length=4096)
                
                # Create main embed
                embed = EmbedHelper.create_ai_response_embed(
                    content=content_chunks[0],
                    user_name=interaction.user.display_name,
                    user_avatar=interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None,
                    response_time=response_time_text if response_time_text else None
                )
                
                # Add additional chunks as fields if needed
                for i, chunk in enumerate(content_chunks[1:], 1):
                    embed.add_field(
                        name=f"Continued...",
                        value=chunk[:1024],
                        inline=False
                    )
                
                # Add question suggestions if available
                if question_suggestions:
                    suggestions_text = "\n".join([f"❓ {q}" for q in question_suggestions])
                    embed.add_field(
                        name="💡 You might also want to know:",
                        value=suggestions_text[:1024],
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
            else:
                # Fallback: append response time to text
                if response_time_text:
                    if len(response_text) + len(response_time_text) + 2 > 2000:
                        max_length = 2000 - len(response_time_text) - 3
                        response_text = response_text[:max_length] + "..."
                    response_text += f"\n\n{response_time_text}"
                
                # Add suggestions to text response
                if question_suggestions:
                    response_text += "\n\n💡 **You might also want to know:**\n"
                    for q in question_suggestions:
                        response_text += f"❓ {q}\n"
                
                await interaction.followup.send(response_text)
        except Exception as e:
            await interaction.followup.send("I'm having trouble connecting to my AI brain, please try again!")
            print(f"[ERROR] Ask slash command error: {e}")
            import traceback
            traceback.print_exc()
    
    @app_commands.command(name="stats", description="Show bot statistics")
    async def stats_slash(self, interaction: discord.Interaction):
        """Show conversation statistics"""
        if not self.bot.conversation_logger:
            await interaction.response.send_message("❌ Conversation logger not available!", ephemeral=True)
            return
        
        try:
            stats = self.bot.conversation_logger.get_stats()
            
            embed = discord.Embed(
                title="📊 Conversation Statistics",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📝 Total Conversations",
                value=f"{stats['total_conversations']:,}",
                inline=True
            )
            
            embed.add_field(
                name="👥 Total Users",
                value=f"{stats['total_users']:,}",
                inline=True
            )
            
            embed.add_field(
                name="💬 Recent (24h)",
                value=f"{stats['recent_24h']:,}",
                inline=True
            )
            
            embed.add_field(
                name="🔢 Total Tokens Used",
                value=f"{stats['total_tokens']:,}",
                inline=False
            )
            
            # Models used
            if stats['models_used']:
                models_text = "\n".join([
                    f"• **{model}**: {count:,} conversations"
                    for model, count in stats['models_used'].items()
                ])
            else:
                models_text = "No data yet"
            
            embed.add_field(
                name="🤖 Models Used",
                value=models_text,
                inline=False
            )
            
            # Add bot stats
            uptime = datetime.now() - self.bot.start_time
            uptime_str = str(uptime).split('.')[0]
            embed.add_field(
                name="⏱️ Bot Uptime",
                value=uptime_str,
                inline=True
            )
            embed.add_field(
                name="💬 Messages Processed",
                value=f"{self.bot.message_count:,}",
                inline=True
            )
            embed.add_field(
                name="🏓 Latency",
                value=f"{round(self.bot.latency * 1000)}ms",
                inline=True
            )
            
            embed.set_footer(text="Data collected for training purposes")
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error getting statistics: {str(e)}", ephemeral=True)
            print(f"[ERROR] Stats slash command failed: {e}")
            import traceback
            traceback.print_exc()
    
    @app_commands.command(name="clear", description="Clear conversation history for this channel")
    async def clear_slash(self, interaction: discord.Interaction):
        """Clear conversation history"""
        try:
            # Clear in-memory conversations
            channel_id = interaction.channel.id
            if channel_id in self.bot.conversations:
                del self.bot.conversations[channel_id]
            
            # Clear from memory manager if available
            if self.bot.memory_manager:
                user_id = str(interaction.user.id)
                channel_id_str = str(channel_id)
                # Note: Memory manager doesn't have a direct clear method, 
                # but we can clear the in-memory cache
                pass
            
            # Also try conversation cog if available
            conversation_cog = self.bot.get_cog("Conversation")
            if conversation_cog and hasattr(conversation_cog, 'context_manager'):
                if conversation_cog.context_manager:
                    conversation_cog.context_manager.clear_context(channel_id)
            
            embed = discord.Embed(
                title="✅ Cleared",
                description="Conversation history cleared for this channel!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error clearing history: {str(e)}", ephemeral=True)
            print(f"[ERROR] Clear slash command failed: {e}")
    
    @app_commands.command(name="personality", description="Change bot personality")
    @app_commands.describe(personality="Personality type to use")
    @app_commands.choices(personality=[
        app_commands.Choice(name="Friendly", value="friendly"),
        app_commands.Choice(name="Professional", value="professional"),
        app_commands.Choice(name="Funny", value="funny"),
        app_commands.Choice(name="Helpful", value="helpful")
    ])
    async def personality_slash(
        self,
        interaction: discord.Interaction,
        personality: app_commands.Choice[str]
    ):
        """Change bot's personality"""
        try:
            # Try to save preference using conversation cog
            conversation_cog = self.bot.get_cog("Conversation")
            if conversation_cog and conversation_cog.context_manager and interaction.guild:
                conversation_cog.context_manager.set_user_preference(
                    interaction.guild.id,
                    interaction.user.id,
                    "personality",
                    personality.value
                )
                conversation_cog.context_manager.save_preferences()
            
            embed = discord.Embed(
                title="✅ Personality Changed",
                description=f"Personality changed to **{personality.value.capitalize()}**!\nI'll use this tone in our conversations.",
                color=discord.Color.purple()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error changing personality: {str(e)}", ephemeral=True)
            print(f"[ERROR] Personality slash command failed: {e}")
    
    @app_commands.command(name="export", description="Export conversation data to CSV")
    async def export_slash(self, interaction: discord.Interaction):
        """Export all conversations to CSV file"""
        if not self.bot.conversation_logger:
            await interaction.response.send_message("❌ Conversation logger not available!", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_export_{timestamp}.csv"
            
            # Export to CSV
            filepath = self.bot.conversation_logger.export_to_csv(output_path=filename)
            
            # Send file to Discord
            with open(filepath, 'rb') as f:
                file = discord.File(f, filename=filename)
                await interaction.followup.send(
                    f"✅ **Export Complete!**\n"
                    f"📁 File: `{filename}`\n"
                    f"📊 All conversations exported successfully!",
                    file=file,
                    ephemeral=True
                )
            
            print(f"[OK] Exported conversations to {filepath}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error exporting conversations: {str(e)}", ephemeral=True)
            print(f"[ERROR] Export slash command failed: {e}")
            import traceback
            traceback.print_exc()
    
    @app_commands.command(name="summarize", description="Summarize conversation history")
    @app_commands.describe(user="Optional user to summarize (mention)")
    async def summarize_slash(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Summarize conversation history"""
        if not self.bot.memory_manager:
            await interaction.response.send_message(
                "❌ Memory manager not available!",
                ephemeral=True
            )
            return
        
        if not self.bot.summarizer:
            await interaction.response.send_message(
                "❌ Summarizer not available! Claude API is required.",
                ephemeral=True
            )
            return
        
        # Determine target user
        target_user = user if user else interaction.user
        target_user_id = str(target_user.id)
        target_user_name = target_user.display_name
        channel_id = str(interaction.channel.id)
        
        await interaction.response.defer(ephemeral=False)
        
        try:
            # Get recent messages (last 20)
            recent_messages = self.bot.memory_manager.get_recent_messages(
                user_id=target_user_id,
                channel_id=channel_id,
                limit=20
            )
            
            if len(recent_messages) < 2:
                await interaction.followup.send(
                    f"📭 Not enough messages to summarize. Found {len(recent_messages)} message(s).",
                    ephemeral=True
                )
                return
            
            # Convert to API format
            api_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in recent_messages
            ]
            
            # Get timestamps
            start_time = datetime.fromisoformat(recent_messages[0]["timestamp"])
            end_time = datetime.fromisoformat(recent_messages[-1]["timestamp"])
            
            # Create summary with details extraction
            summary_result = await self.bot.summarizer.summarize_messages(
                messages=api_messages,
                user_name=target_user_name,
                extract_details=True
            )
            
            # Extract components
            summary_text = summary_result.get("summary", "No summary available.")
            key_topics = summary_result.get("key_topics", [])
            important_info = summary_result.get("important_info", [])
            
            # Create summary embed
            if EMBED_HELPER_AVAILABLE:
                embed = discord.Embed(
                    title=f"📝 Conversation Summary - {target_user_name}",
                    description=summary_text[:2000],
                    color=EmbedColors.BLUE
                )
                
                # Add key topics
                if key_topics:
                    topics_text = "\n".join([f"• {topic}" for topic in key_topics[:5]])
                    embed.add_field(
                        name="🔑 Key Topics",
                        value=topics_text[:1024],
                        inline=False
                    )
                
                # Add important information
                if important_info:
                    info_text = "\n".join([f"• {info}" for info in important_info[:5]])
                    embed.add_field(
                        name="💡 Important Information",
                        value=info_text[:1024],
                        inline=False
                    )
                
                # Add statistics
                embed.add_field(
                    name="📊 Statistics",
                    value=(
                        f"**Messages Analyzed**: {len(recent_messages)}\n"
                        f"**Time Range**: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}\n"
                        f"**User**: {target_user_name}"
                    ),
                    inline=False
                )
                
                embed.set_footer(text="Summary saved to database")
                
                await interaction.followup.send(embed=embed)
            else:
                # Fallback text format
                result_text = f"**📝 Conversation Summary - {target_user_name}**\n\n"
                result_text += f"{summary_text}\n\n"
                
                if key_topics:
                    result_text += "**🔑 Key Topics:**\n"
                    for topic in key_topics[:5]:
                        result_text += f"• {topic}\n"
                    result_text += "\n"
                
                if important_info:
                    result_text += "**💡 Important Information:**\n"
                    for info in important_info[:5]:
                        result_text += f"• {info}\n"
                
                result_text += f"\n**📊 Statistics:** {len(recent_messages)} messages analyzed"
                await interaction.followup.send(result_text)
            
            # Save summary to database
            try:
                summary_id = self.bot.memory_manager.create_summary(
                    user_id=target_user_id,
                    channel_id=channel_id,
                    summary_text=summary_text,
                    message_count=len(recent_messages),
                    start_timestamp=start_time,
                    end_timestamp=end_time,
                    importance_score=0.7
                )
                print(f"[OK] Summary created via slash command: ID={summary_id}")
            except Exception as e:
                print(f"[ERROR] Failed to save summary: {e}")
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error creating summary: {str(e)}",
                ephemeral=True
            )
            print(f"[ERROR] Summarize slash command failed: {e}")
            import traceback
            traceback.print_exc()


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(SlashCommands(bot))

