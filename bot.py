"""
AI Boot - Discord Bot with Claude AI Integration
Intelligent conversational bot powered by Claude Sonnet 4
"""

import discord
from discord.ext import commands
import os
import json
import asyncio
import sqlite3
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Optional

# Load environment variables from .env file FIRST (before importing claude_handler)
load_dotenv()

# Import Claude handler and static responses (fallback)
try:
    from claude_handler import ClaudeHandler
    CLAUDE_AVAILABLE = True
    print("[OK] Claude handler module imported successfully")
except Exception as e:
    print(f"[ERROR] Warning: Claude handler not available: {e}")
    import traceback
    traceback.print_exc()
    CLAUDE_AVAILABLE = False

from responses import find_response, get_reaction

# Import memory management
try:
    from utils.memory_manager import MemoryManager
    from utils.summarizer import ConversationSummarizer
    MEMORY_AVAILABLE = True
    print("[OK] Memory manager module imported successfully")
except Exception as e:
    print(f"[ERROR] Warning: Memory manager not available: {e}")
    import traceback
    traceback.print_exc()
    MEMORY_AVAILABLE = False

# Import conversation logger for permanent storage
try:
    from conversation_logger import ConversationLogger
    CONVERSATION_LOGGER_AVAILABLE = True
    print("[OK] Conversation logger module imported successfully")
except Exception as e:
    print(f"[ERROR] Warning: Conversation logger not available: {e}")
    import traceback
    traceback.print_exc()
    CONVERSATION_LOGGER_AVAILABLE = False


class AIBootBot(commands.Bot):
    """Main bot class for AI Boot with Claude AI integration"""
    
    def __init__(self):
        """Initialize the bot"""
        # Load configuration
        self.config = self._load_config()
        
        # Set up Discord intents (permissions)
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        intents.members = True
        
        # Initialize bot with command prefix
        super().__init__(
            command_prefix=self.config.get("prefix", "!"),
            intents=intents,
            help_command=None  # We'll create custom help
        )
        
        # Initialize Claude API handler
        self.claude_handler = None
        self.use_claude = False
        
        # Check if CLAUDE_API_KEY exists in environment
        claude_key = os.getenv("CLAUDE_API_KEY")
        if not claude_key:
            print("[ERROR] CLAUDE_API_KEY not found in .env file!")
            print("[ERROR] Bot will use static responses")
        else:
            print(f"[OK] CLAUDE_API_KEY found (length: {len(claude_key)})")
        
        if CLAUDE_AVAILABLE:
            try:
                print("[INFO] Attempting to initialize Claude API handler...")
                self.claude_handler = ClaudeHandler()
                self.use_claude = True
                print("[OK] Claude API handler initialized successfully!")
                print(f"[OK] Using model: {self.claude_handler.model}")
            except Exception as e:
                print(f"[ERROR] Could not initialize Claude API: {e}")
                import traceback
                traceback.print_exc()
                print("[ERROR] Bot will use static responses as fallback")
                self.use_claude = False
                self.claude_handler = None  # Ensure it's None
        else:
            print("[ERROR] Claude handler module not available - using static responses")
            self.use_claude = False
            self.claude_handler = None
        
        # Initialize memory manager for persistent storage
        self.memory_manager = None
        self.summarizer = None
        if MEMORY_AVAILABLE:
            try:
                self.memory_manager = MemoryManager(
                    db_path=self.config.get("memory_db_path", "bot_memory.db"),
                    short_term_limit=self.config.get("short_term_memory_limit", 30)
                )
                if self.use_claude and self.claude_handler:
                    self.summarizer = ConversationSummarizer(self.claude_handler)
                print("[OK] Memory manager initialized")
            except Exception as e:
                print(f"[ERROR] Failed to initialize memory manager: {e}")
                self.memory_manager = None
        
        # Initialize conversation logger for permanent conversation storage
        self.conversation_logger = None
        if CONVERSATION_LOGGER_AVAILABLE:
            try:
                self.conversation_logger = ConversationLogger(
                    db_path="conversation_logs.db"
                )
                print("[OK] Conversation logger initialized")
            except Exception as e:
                print(f"[ERROR] Failed to initialize conversation logger: {e}")
                self.conversation_logger = None
        
        # Conversation context storage: {channel_id: {'messages': deque, 'last_activity': datetime}}
        # This is now a fallback - primary storage is in database
        self.conversations = defaultdict(lambda: {
            'messages': deque(maxlen=8),
            'last_activity': datetime.now()
        })
        
        # Rate limiting: {user_id: [timestamps]}
        self.rate_limits = defaultdict(list)
        self.rate_limit_per_minute = self.config.get("rate_limit_per_minute", 5)
        
        # Bot statistics
        self.start_time = datetime.now()
        self.message_count = 0
        self.claude_responses = 0
        self.fallback_responses = 0
        self.version = "2.0.1"  # Version tracking for deployment verification
        
        # Start background task to clean old conversations
        self.cleanup_task = None
    
    def _load_config(self) -> dict:
        """Load configuration from config.json"""
        try:
            with open("config.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: config.json not found, using defaults")
            return {
                "prefix": "!",
                "rate_limit_per_minute": 5,
                "max_context_messages": 8,
                "context_timeout_minutes": 30
            }
    
    async def setup_hook(self):
        """Called when bot is starting up"""
        # Start background task to clean old conversations
        self.cleanup_task = asyncio.create_task(self._cleanup_old_conversations())
    
    async def _summarize_old_messages(self, user_id: str, channel_id: str):
        """
        Summarize old messages when conversation gets too long
        This creates long-term memory from past interactions
        """
        if not self.memory_manager or not self.summarizer:
            return
        
        try:
            # Get messages that need to be summarized (all except the most recent ones)
            all_messages = self.memory_manager.get_recent_messages(
                user_id=user_id,
                channel_id=channel_id,
                limit=100  # Get more messages to summarize
            )
            
            # Keep recent messages (last 20), summarize the rest
            if len(all_messages) <= 20:
                return  # Not enough to summarize
            
            messages_to_summarize = all_messages[:-20]  # All except last 20
            recent_messages = all_messages[-20:]  # Keep these
            
            if not messages_to_summarize:
                return
            
            # Get timestamps
            start_time = datetime.fromisoformat(messages_to_summarize[0]["timestamp"])
            end_time = datetime.fromisoformat(messages_to_summarize[-1]["timestamp"])
            
            # Extract preferences from messages (for importance scoring)
            from utils.importance_scorer import ImportanceScorer
            preferences = ImportanceScorer.extract_preferences(
                [{"role": m["role"], "content": m["content"]} for m in messages_to_summarize]
            )
            
            # Create summary using Claude
            summary_text = await self.summarizer.summarize_messages(
                messages=[{"role": m["role"], "content": m["content"]} for m in messages_to_summarize],
                user_name=None
            )
            
            # Add preferences to summary if found
            if preferences:
                summary_text += f"\n\nUser preferences mentioned: {', '.join(preferences[:3])}"
            
            # Calculate importance score (higher if preferences found)
            base_importance = 0.5
            if preferences:
                base_importance = 0.7  # Preferences are important
            if any("prefer" in msg.get("content", "").lower() or "like" in msg.get("content", "").lower() 
                   for msg in messages_to_summarize):
                base_importance = max(base_importance, 0.8)  # Very important
            
            # Store summary in database with importance score
            self.memory_manager.create_summary(
                user_id=user_id,
                channel_id=channel_id,
                summary_text=summary_text,
                message_count=len(messages_to_summarize),
                start_timestamp=start_time,
                end_timestamp=end_time,
                importance_score=base_importance
            )
            
            print(f"[INFO] Summarized {len(messages_to_summarize)} messages for user {user_id}")
            
        except Exception as e:
            print(f"[ERROR] Failed to summarize messages: {e}")
            import traceback
            traceback.print_exc()
    
    async def _cleanup_old_conversations(self):
        """Background task to clear conversation context and manage memory decay"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                now = datetime.now()
                timeout = timedelta(minutes=self.config.get("context_timeout_minutes", 30))
                
                # Find and remove old conversations from in-memory cache
                channels_to_remove = []
                for channel_id, conv_data in self.conversations.items():
                    if now - conv_data['last_activity'] > timeout:
                        channels_to_remove.append(channel_id)
                
                for channel_id in channels_to_remove:
                    del self.conversations[channel_id]
                    print(f"Cleared conversation context for channel {channel_id} (inactive)")
                
                # Memory decay: merge/drop old summaries
                if self.memory_manager:
                    try:
                        # Get all unique user/channel combinations
                        conn = sqlite3.connect(self.memory_manager.db_path)
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT DISTINCT user_id, channel_id FROM summaries
                        """)
                        user_channels = cursor.fetchall()
                        conn.close()
                        
                        # Process each user/channel
                        total_processed = 0
                        for user_id, channel_id in user_channels:
                            processed = self.memory_manager.merge_old_summaries(
                                user_id=user_id,
                                channel_id=channel_id,
                                max_age_days=90,  # Process summaries older than 90 days
                                min_importance=0.3
                            )
                            total_processed += processed
                        
                        if total_processed > 0:
                            print(f"[INFO] Memory decay: Processed {total_processed} old summaries")
                        
                        # Clean up old messages (but keep important ones)
                        self.memory_manager.cleanup_old_messages(
                            days=60,  # Clean messages older than 60 days
                            min_importance=0.4  # Keep important messages
                        )
                    except Exception as e:
                        print(f"[ERROR] Error in memory decay cleanup: {e}")
            
            except Exception as e:
                print(f"Error in cleanup task: {e}")
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user is within rate limit
        Max 5 messages per minute per user
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
    
    async def on_ready(self):
        """Called when bot is ready and connected"""
        mode = "Claude AI" if self.use_claude else "Static Responses (Fallback)"
        
        print(f"\n{'='*50}")
        print(f"AI Boot is ready!")
        print(f"Logged in as: {self.user.name}#{self.user.discriminator}")
        print(f"Bot ID: {self.user.id}")
        print(f"Servers: {len(self.guilds)}")
        print(f"Mode: {mode}")
        if self.use_claude and self.claude_handler:
            print(f"Claude Model: {self.claude_handler.model}")
        print(f"{'='*50}\n")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{self.config.get('prefix', '!')}help"
        )
        await self.change_presence(activity=activity)
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore messages from bots (including ourselves)
        if message.author.bot:
            return
        
        # Ignore empty messages
        if not message.content:
            return
        
        # Clean message content (remove mention) for command checking
        content = message.content
        bot_mentioned = self.user in message.mentions
        if bot_mentioned:
            # Remove bot mentions to check for commands
            content = content.replace(f"<@{self.user.id}>", "").strip()
            content = content.replace(f"<@!{self.user.id}>", "").strip()
        
        # Check if message is a command (starts with prefix, even after removing mentions)
        prefix = self.config.get("prefix", "!")
        if content.startswith(prefix):
            # Let commands handle it (use original message content)
            print(f"[DEBUG] Processing command: {message.content}")
            try:
                await self.process_commands(message)
            except Exception as e:
                print(f"[ERROR] Error processing command: {e}")
                import traceback
                traceback.print_exc()
            return
        
        # Check if bot is mentioned or message is a DM
        is_dm = isinstance(message.channel, discord.DMChannel)
        
        # Only respond to mentions or DMs
        if not (bot_mentioned or is_dm):
            return
        
        # Check rate limit (max 5 messages per minute per user)
        if not self._check_rate_limit(message.author.id):
            await message.channel.send(
                "Whoa, slow down! Let's chat in a minute 😊"
            )
            return
        
        # Show typing indicator while AI is thinking
        async with message.channel.typing():
            try:

                # Clean message content (remove mention)
                content = message.content
                if bot_mentioned:
                    content = content.replace(f"<@{self.user.id}>", "").strip()
                    content = content.replace(f"<@!{self.user.id}>", "").strip()
                
                # Skip if message is empty after cleaning
                if not content:
                    return
                
                # Store user message in database (persistent memory)
                # PER-USER ISOLATION: Each user has separate memory
                user_id = str(message.author.id)
                channel_id = str(message.channel.id)
                
                # Validate user_id for security (prevent injection)
                if not user_id or len(user_id) > 50:
                    print(f"[ERROR] Invalid user_id: {user_id}")
                    return
                
                if self.memory_manager:
                    # Check if this is a name/preference statement for higher importance
                    content_lower = content.lower()
                    is_preference = any(keyword in content_lower for keyword in [
                        "my name is", "i am", "i'm", "call me", "prefer", "like", "remember"
                    ])
                    
                    # Calculate importance score if it's a preference
                    importance_score = None
                    if is_preference:
                        from utils.importance_scorer import ImportanceScorer
                        message_dict = {"role": "user", "content": content}
                        importance_score = ImportanceScorer.score_message(message_dict, is_user_message=True)
                        print(f"[INFO] High importance message detected (score: {importance_score:.2f}): {content[:50]}...")
                    
                    self.memory_manager.add_message(
                        user_id=user_id,
                        channel_id=channel_id,
                        role="user",
                        content=content,
                        importance_score=importance_score  # Will auto-calculate if None
                    )
                
                # Get conversation context from database (summaries + recent messages)
                if self.memory_manager:
                    api_messages, summary_texts = self.memory_manager.get_conversation_context(
                        user_id=user_id,
                        channel_id=channel_id,
                        include_summaries=True
                    )
                    
                    # Add current user message if not already in context
                    if not api_messages or api_messages[-1]["content"] != content:
                        api_messages.append({"role": "user", "content": content})
                    
                    # Check if we need to summarize old messages (if we have too many)
                    if len(api_messages) > self.config.get("summarize_threshold", 50) and self.summarizer:
                        await self._summarize_old_messages(user_id, channel_id)
                        # Reload context after summarization
                        api_messages, summary_texts = self.memory_manager.get_conversation_context(
                            user_id=user_id,
                            channel_id=channel_id,
                            include_summaries=True
                        )
                        if not api_messages or api_messages[-1]["content"] != content:
                            api_messages.append({"role": "user", "content": content})
                else:
                    # Fallback to in-memory storage
                    conv_data = self.conversations[message.channel.id]
                    api_messages = list(conv_data['messages'])
                    api_messages.append({"role": "user", "content": content})
                    summary_texts = []
                    conv_data['last_activity'] = datetime.now()
                
                # Try Claude API first, fallback to static responses if it fails
                response_text = None
                used_claude = False
                tokens_used = 0
                model_used = "unknown"
                
                # ALWAYS try Claude API if available
                if self.use_claude and self.claude_handler:
                    print(f"[DEBUG] Calling Claude API for: {content[:50]}...")
                    # Call Claude API with conversation history and summaries
                    result = await self.claude_handler.generate_response(
                        messages=api_messages,
                        user_name=message.author.display_name,
                        summaries=summary_texts if summary_texts else None
                    )
                    
                    if result["success"]:
                        response_text = result["response"]
                        used_claude = True
                        tokens_used = result.get("tokens_used", 0)
                        model_used = self.claude_handler.model
                        self.claude_responses += 1
                        print(f"[DEBUG] Claude API success! Response length: {len(response_text)}")
                    else:
                        # API failed, log error and use fallback message
                        error_msg = result.get('error', 'Unknown error')
                        print(f"[ERROR] Claude API failed: {error_msg}")
                        print(f"[ERROR] Full result: {result}")
                        # Try static response as fallback instead of generic error
                        response_text = find_response(content)
                        model_used = "static_fallback"
                        self.fallback_responses += 1
                        print(f"[DEBUG] Using fallback response: {response_text[:50]}...")
                else:
                    # Claude not available, use static responses
                    print(f"[DEBUG] Claude not available. use_claude={self.use_claude}, handler={self.claude_handler is not None}")
                    response_text = find_response(content)
                    model_used = "static_fallback"
                    self.fallback_responses += 1
                
                # Store bot response in database (persistent memory)
                if self.memory_manager:
                    self.memory_manager.add_message(
                        user_id=user_id,
                        channel_id=channel_id,
                        role="assistant",
                        content=response_text
                    )
                else:
                    # Fallback to in-memory storage
                    conv_data = self.conversations[message.channel.id]
                    conv_data['messages'].append({"role": "assistant", "content": response_text})
                    # Keep last N messages
                    max_context = self.config.get("max_context_messages", 8)
                    if len(conv_data['messages']) > max_context:
                        conv_data['messages'] = deque(
                            list(conv_data['messages'])[-max_context:],
                            maxlen=max_context
                        )
                
                # Send response (only once)
                response_sent = False
                try:
                    await message.reply(response_text)
                    response_sent = True
                except Exception as send_error:
                    print(f"[ERROR] Failed to send response: {send_error}")
                    # Try sending without reply
                    try:
                        await message.channel.send(response_text)
                        response_sent = True
                    except:
                        pass
                
                # Only continue if response was sent successfully
                if response_sent:
                    # Log conversation to permanent database
                    if self.conversation_logger:
                        try:
                            self.conversation_logger.log_conversation(
                                user_id=str(message.author.id),
                                user_name=message.author.display_name,
                                channel_id=str(message.channel.id),
                                user_message=content,
                                bot_response=response_text,
                                tokens_used=tokens_used,
                                model_used=model_used
                            )
                            print(f"[OK] Conversation logged: User={message.author.display_name}, Tokens={tokens_used}, Model={model_used}")
                        except Exception as e:
                            print(f"[ERROR] Failed to log conversation: {e}")
                    
                    # Add reaction to user's message
                    reaction_emoji = get_reaction(content)
                    try:
                        await message.add_reaction(reaction_emoji)
                    except:
                        pass  # Ignore if reaction fails
                    
                    # Update statistics
                    self.message_count += 1
                    
                    # Log conversation
                    if self.config.get("enable_logging", True):
                        try:
                            self._log_message(message, response_text, used_claude)
                        except:
                            pass  # Ignore logging errors
            
            except Exception as e:
                print(f"[ERROR] Error processing message: {e}")
                import traceback
                traceback.print_exc()
                # Only send fallback if we haven't sent a response yet
                # Check if response was already sent by checking if exception happened after response
                try:
                    # Try fallback response using keyword matching
                    fallback = find_response(message.content)
                    await message.channel.send(fallback)
                except Exception as fallback_error:
                    print(f"[ERROR] Fallback also failed: {fallback_error}")
                    # Last resort - only if nothing was sent
                    try:
                        await message.channel.send("I'm having some technical difficulties. Please try again in a moment!")
                    except:
                        pass  # If even this fails, give up
    
    def _log_message(self, message: discord.Message, response: str, used_claude: bool):
        """Log conversation to file"""
        try:
            log_file = self.config.get("log_file", "bot.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            server = message.guild.name if message.guild else "DM"
            channel = message.channel.name if hasattr(message.channel, 'name') else "DM"
            source = "Claude" if used_claude else "Fallback"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(
                    f"[{timestamp}] [{source}] {server}#{channel} | "
                    f"{message.author.name}: {message.content} | "
                    f"Bot: {response}\n"
                )
        except Exception as e:
            print(f"Error logging: {e}")
    
    # ========== COMMANDS ==========
    
    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        """Show all available commands"""
        prefix = self.config.get("prefix", "!")
        
        embed = discord.Embed(
            title="🤖 AI Boot Commands",
            description="Here's what I can do:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 Commands",
            value=(
                f"`{prefix}help` - Show this help\n"
                f"`{prefix}ping` - Check if I'm online\n"
                f"`{prefix}info` - Bot information\n"
                f"`{prefix}commands` - List commands\n"
                f"`{prefix}about` - Bot description & languages\n"
                f"`{prefix}export` - Export conversations to CSV\n"
                f"`{prefix}stats` - Show conversation statistics\n"
                f"`{prefix}history [user]` - Show conversation history"
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
        await ctx.send(embed=embed)
    
    @commands.command(name="ping")
    async def ping_command(self, ctx: commands.Context):
        """Check if bot is online"""
        latency = round(self.latency * 1000)
        await ctx.send(f"Pong! 🏓 Latency: {latency}ms")
    
    @commands.command(name="info")
    async def info_command(self, ctx: commands.Context):
        """Show bot information"""
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        embed = discord.Embed(
            title="🤖 AI Boot Information",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Bot Name", value="AI Boot", inline=True)
        embed.add_field(name="Status", value="Online ✅", inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Messages Processed", value=str(self.message_count), inline=True)
        embed.add_field(name="Latency", value=f"{round(self.latency * 1000)}ms", inline=True)
        embed.add_field(name="Servers", value=str(len(self.guilds)), inline=True)
        
        # Show AI mode and stats
        if self.use_claude and self.claude_handler:
            mode = f"Claude AI (claude-3-5-haiku-20241022) - v{self.version}"
            stats = self.claude_handler.get_stats()
            embed.add_field(
                name="AI Mode",
                value=mode,
                inline=False
            )
            embed.add_field(
                name="API Statistics",
                value=(
                    f"Total Calls: {stats['total_calls']}\n"
                    f"Success Rate: {stats['success_rate']:.1f}%\n"
                    f"Total Tokens: {stats['total_tokens']:,}\n"
                    f"Claude Responses: {self.claude_responses}\n"
                    f"Fallback Responses: {self.fallback_responses}"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="Mode",
                value="Static Responses (Claude API not configured)",
                inline=False
            )
        
        embed.set_footer(text=f"Bot started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        await ctx.send(embed=embed)
    
    @commands.command(name="commands")
    async def commands_command(self, ctx: commands.Context):
        """List all available commands"""
        prefix = self.config.get("prefix", "!")
        
        embed = discord.Embed(
            title="📋 Available Commands",
            description=f"Use `{prefix}` prefix for all commands",
            color=discord.Color.purple()
        )
        
        commands_list = [
            (f"{prefix}help", "Show help and information"),
            (f"{prefix}ping", "Check if bot is online"),
            (f"{prefix}info", "Show bot information and stats"),
            (f"{prefix}commands", "List all commands"),
            (f"{prefix}about", "Show bot description and languages"),
            (f"{prefix}export", "Export all conversations to CSV"),
            (f"{prefix}stats", "Show conversation statistics"),
            (f"{prefix}history [user]", "Show conversation history"),
        ]
        
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="about")
    async def about_command(self, ctx: commands.Context):
        """Show bot information in multiple languages"""
        
        embed = discord.Embed(
            title="🤖 AI Boot - Intelligent Discord Assistant",
            description=(
                "✨ **About Me:**\n"
                "I'm AI Boot, your friendly AI-powered Discord bot! "
                "I can have natural conversations, answer questions, help with tasks, "
                "and chat in multiple languages.\n\n"
                
                "🌍 **Supported Languages:**\n"
                "• **English** 🇬🇧\n"
                "• **Kurdish** (کوردی) 🇹🇯\n"
                "• **Arabic** (العربية) 🇸🇦\n\n"
                
                "💬 **How to Use:**\n"
                "• Just @mention me (@AI Boot) in any channel\n"
                "• Send me a direct message (DM)\n"
                "• Reply to my messages\n"
                "• Use commands like `!help`, `!info`, `!ping`\n\n"
                
                "🎯 **Features:**\n"
                "• Natural AI conversations powered by Claude AI\n"
                "• Multi-language support\n"
                "• Conversation context memory\n"
                "• Helpful responses and assistance\n"
                "• Fun and engaging interactions\n\n"
                
                "💡 **Tip:** Try asking me anything in English, Kurdish, or Arabic - I understand all three!"
            ),
            color=discord.Color.blue()
        )
        
        embed.set_footer(text="Created by DyarAbdulla ❤️")
        
        # Try to set bot avatar as thumbnail
        try:
            if self.user.avatar:
                embed.set_thumbnail(url=self.user.avatar.url)
        except:
            pass
        
        await ctx.send(embed=embed)
    
    @commands.command(name="export")
    async def export_command(self, ctx: commands.Context):
        """Export all conversations to CSV file"""
        if not self.conversation_logger:
            await ctx.send("❌ Conversation logger not available!")
            return
        
        try:
            await ctx.send("📊 Exporting conversations to CSV... This may take a moment.")
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_export_{timestamp}.csv"
            
            # Export to CSV
            filepath = self.conversation_logger.export_to_csv(output_path=filename)
            
            # Send file to Discord
            with open(filepath, 'rb') as f:
                file = discord.File(f, filename=filename)
                await ctx.send(
                    f"✅ **Export Complete!**\n"
                    f"📁 File: `{filename}`\n"
                    f"📊 All conversations exported successfully!",
                    file=file
                )
            
            print(f"[OK] Exported conversations to {filepath}")
        except Exception as e:
            await ctx.send(f"❌ Error exporting conversations: {str(e)}")
            print(f"[ERROR] Export failed: {e}")
            import traceback
            traceback.print_exc()
    
    @commands.command(name="stats")
    async def stats_command(self, ctx: commands.Context):
        """Show conversation statistics"""
        if not self.conversation_logger:
            await ctx.send("❌ Conversation logger not available!")
            return
        
        try:
            stats = self.conversation_logger.get_stats()
            
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
            
            embed.set_footer(text="Data collected for training purposes")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error getting statistics: {str(e)}")
            print(f"[ERROR] Stats command failed: {e}")
            import traceback
            traceback.print_exc()
    
    @commands.command(name="history")
    async def history_command(self, ctx: commands.Context, *, user: Optional[str] = None):
        """Show conversation history
        
        Usage:
        !history - Show your recent conversations
        !history @username - Show conversations for a specific user
        !history username - Show conversations for a username
        """
        if not self.conversation_logger:
            await ctx.send("❌ Conversation logger not available!")
            return
        
        try:
            # Determine which user to show history for
            user_id = None
            user_name = None
            
            if user:
                # Check if user is a mention
                if user.startswith("<@") and user.endswith(">"):
                    # Extract user ID from mention
                    user_id = user.replace("<@", "").replace("!", "").replace(">", "")
                else:
                    # Search by username
                    user_name = user
            
            # If no user specified, show history for command author
            if not user_id and not user_name:
                user_id = str(ctx.author.id)
            
            # Get history
            history = self.conversation_logger.get_user_history(
                user_id=user_id,
                user_name=user_name,
                limit=10
            )
            
            if not history:
                await ctx.send("📭 No conversation history found!")
                return
            
            # Create embed with history
            display_name = history[0]['user_name'] if history else "Unknown"
            embed = discord.Embed(
                title=f"💬 Conversation History - {display_name}",
                description=f"Showing last {len(history)} conversations",
                color=discord.Color.blue()
            )
            
            # Show conversations (limit to fit Discord embed limits)
            for i, conv in enumerate(history[:5], 1):  # Show max 5 in embed
                timestamp = conv['timestamp'][:19] if len(conv['timestamp']) > 19 else conv['timestamp']
                user_msg = conv['user_message'][:200] + "..." if len(conv['user_message']) > 200 else conv['user_message']
                bot_msg = conv['bot_response'][:200] + "..." if len(conv['bot_response']) > 200 else conv['bot_response']
                
                embed.add_field(
                    name=f"💬 Conversation #{i} - {timestamp}",
                    value=(
                        f"**User:** {user_msg}\n"
                        f"**Bot:** {bot_msg}\n"
                        f"*Tokens: {conv['tokens_used']} | Model: {conv['model_used']}*"
                    ),
                    inline=False
                )
            
            if len(history) > 5:
                embed.set_footer(text=f"Showing 5 of {len(history)} conversations. Use !export for full history.")
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error getting history: {str(e)}")
            print(f"[ERROR] History command failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle command errors"""
        # Ignore unknown commands silently
        if isinstance(error, commands.CommandNotFound):
            return
        
        # Handle missing required arguments
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = self.config.get("prefix", "!")
            await ctx.send(f"❌ Missing required argument! Use `{prefix}help` for usage.")
            return
        
        # Handle other command errors
        print(f"[ERROR] Command error: {error}")
        import traceback
        traceback.print_exc()
        
        # Send user-friendly error message
        try:
            await ctx.send("❌ An error occurred while processing that command. Please try again!")
        except:
            pass  # If we can't send message, ignore
    
    async def close(self):
        """Called when bot is shutting down"""
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
        await super().close()


async def main():
    """Main function to run the bot"""
    # Get Discord token from environment
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        print("ERROR: DISCORD_TOKEN not found in .env file!")
        print("Please create a .env file with your Discord bot token.")
        print("Example: DISCORD_TOKEN=your_token_here")
        return
    
    # Create and run bot
    bot = AIBootBot()
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        print("\nShutting down AI Boot...")
        await bot.close()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        await bot.close()
        # Exit with error code for Railway to restart
        os._exit(1)


if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAI Boot stopped by user")
