"""
AI Boot - Discord Bot with Claude AI Integration
Intelligent conversational bot powered by Claude Sonnet 4
"""

import discord
from discord.ext import commands
import os
import json
import asyncio
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict, deque

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
        else:
            print("[ERROR] Claude handler module not available - using static responses")
        
        # Conversation context storage: {channel_id: {'messages': deque, 'last_activity': datetime}}
        # Stores last 8 messages per channel for context
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
    
    async def _cleanup_old_conversations(self):
        """Background task to clear conversation context after 30 minutes of inactivity"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                now = datetime.now()
                timeout = timedelta(minutes=self.config.get("context_timeout_minutes", 30))
                
                # Find and remove old conversations
                channels_to_remove = []
                for channel_id, conv_data in self.conversations.items():
                    if now - conv_data['last_activity'] > timeout:
                        channels_to_remove.append(channel_id)
                
                for channel_id in channels_to_remove:
                    del self.conversations[channel_id]
                    print(f"Cleared conversation context for channel {channel_id} (inactive)")
            
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
        
        # Check if message is a command (starts with prefix)
        if message.content.startswith(self.config.get("prefix", "!")):
            # Let commands handle it
            await self.process_commands(message)
            return
        
        # Check if bot is mentioned or message is a DM
        bot_mentioned = self.user in message.mentions
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
                
                # Get conversation context for this channel (last 8 messages)
                conv_data = self.conversations[message.channel.id]
                context_messages = list(conv_data['messages'])
                
                # Update last activity time
                conv_data['last_activity'] = datetime.now()
                
                # Add user message to context
                context_messages.append({"role": "user", "content": content})
                
                # Try Claude API first, fallback to static responses if it fails
                response_text = None
                used_claude = False
                
                # ALWAYS try Claude API if available
                if self.use_claude and self.claude_handler:
                    print(f"[DEBUG] Calling Claude API for: {content[:50]}...")
                    # Call Claude API with user name for context
                    result = await self.claude_handler.generate_response(
                        messages=context_messages,
                        user_name=message.author.display_name
                    )
                    
                    if result["success"]:
                        response_text = result["response"]
                        used_claude = True
                        self.claude_responses += 1
                        print(f"[DEBUG] Claude API success! Response length: {len(response_text)}")
                    else:
                        # API failed, use fallback message
                        print(f"[DEBUG] Claude API error: {result['error']}")
                        response_text = "Sorry, I'm having trouble thinking right now. Try again in a moment!"
                        self.fallback_responses += 1
                else:
                    # Claude not available, use static responses
                    print(f"[DEBUG] Claude not available. use_claude={self.use_claude}, handler={self.claude_handler is not None}")
                    response_text = find_response(content)
                    self.fallback_responses += 1
                
                # Add bot response to context
                context_messages.append({"role": "assistant", "content": response_text})
                
                # Update conversation history (keeps last 8 messages)
                conv_data['messages'] = deque(
                    context_messages,
                    maxlen=self.config.get("max_context_messages", 8)
                )
                
                # Send response
                await message.reply(response_text)
                
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
                    self._log_message(message, response_text, used_claude)
            
            except Exception as e:
                print(f"Error processing message: {e}")
                # Try fallback response
                try:
                    fallback = "Sorry, I'm having trouble thinking right now. Try again in a moment!"
                    await message.channel.send(fallback)
                except:
                    pass
    
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
                f"`{prefix}commands` - List commands"
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
            mode = "Claude AI (claude-haiku-4-20250514)"
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
        ]
        
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        await ctx.send(embed=embed)
    
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
