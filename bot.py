"""
AI Boot - Discord Bot with Claude AI Integration
Intelligent conversational bot powered by Claude Sonnet 4
Fixed syntax errors - all docstrings updated
"""

from responses import find_response, get_reaction
import discord
from discord.ext import commands
import os
import sys
import json
import asyncio
import sqlite3
import time
import random
import aiohttp
import shutil
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Optional, List, Dict

# Ensure utils directory is in Python path (fixes ModuleNotFoundError)
_bot_dir = os.path.dirname(os.path.abspath(__file__))
_utils_path = os.path.join(_bot_dir, 'utils')
if _utils_path not in sys.path:
    sys.path.insert(0, _utils_path)
    sys.path.insert(0, _bot_dir)

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


# Import embed helper
try:
    from utils.embed_helper import EmbedHelper, EmbedColors
    EMBED_HELPER_AVAILABLE = True
except ImportError:
    EMBED_HELPER_AVAILABLE = False
    print("[WARNING] Embed helper not available - using default embeds")

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

# Import Kurdish language detector
try:
    from utils.kurdish_detector import KurdishDetector
    KURDISH_DETECTOR_AVAILABLE = True
    print("[OK] Kurdish detector module imported successfully")
except Exception as e:
    print(f"[ERROR] Warning: Kurdish detector not available: {e}")
    import traceback
    traceback.print_exc()
    KURDISH_DETECTOR_AVAILABLE = False

# Import response time tracker
try:
    from utils.response_tracker import ResponseTracker
    RESPONSE_TRACKER_AVAILABLE = True
    print("[OK] Response tracker module imported successfully")
except Exception as e:
    print(f"[ERROR] Warning: Response tracker not available: {e}")
    import traceback
    traceback.print_exc()
    RESPONSE_TRACKER_AVAILABLE = False

# Import statistics tracker
try:
    from utils.statistics_tracker import StatisticsTracker
    STATISTICS_TRACKER_AVAILABLE = True
    print("[OK] Statistics tracker module imported successfully")
except Exception as e:
    print(f"[ERROR] Warning: Statistics tracker not available: {e}")
    import traceback
    traceback.print_exc()
    STATISTICS_TRACKER_AVAILABLE = False


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

        # Initialize Multi-API Manager (Priority 1 - Most Important!)
        self.api_manager = None
        self.api_initialization_complete = False
        try:
            from utils.api_manager import APIManager, APIProvider
            print("[INFO] Initializing Multi-API Manager...")
            self.api_manager = APIManager()
            print("[OK] Multi-API Manager initialized!")

            # Keep Claude handler for backward compatibility (image analysis, etc.)
            if APIProvider.CLAUDE in self.api_manager.providers:
                # Create a wrapper for backward compatibility
                from claude_handler import ClaudeHandler
                self.claude_handler = self._initialize_claude_handler_with_retry()
                self.use_claude = self.claude_handler is not None
            else:
                self.claude_handler = None
                self.use_claude = False
        except Exception as e:
            print(f"[WARNING] Multi-API Manager not available: {e}")
            import traceback
            traceback.print_exc()
            self.api_manager = None
            # Fallback to Claude-only mode
            self.claude_handler = None
            self.use_claude = False

        # Initialize Claude API handler (fallback if API manager not available)
        if not self.api_manager:
            claude_key = os.getenv("CLAUDE_API_KEY")
            if not claude_key:
                print("[ERROR] ❌ CLAUDE_API_KEY not found in .env file!")
                print("[ERROR] Bot will use static responses")
            else:
                print(f"[OK] CLAUDE_API_KEY found (length: {len(claude_key)})")

            if CLAUDE_AVAILABLE:
                self.claude_handler = self._initialize_claude_handler_with_retry()
                self.use_claude = self.claude_handler is not None
            else:
                print(
                    "[ERROR] ❌ Claude handler module not available - using static responses")
                self.use_claude = False
                self.claude_handler = None

        # Initialize Cache Manager
        self.cache_manager = None
        try:
            from utils.cache import CacheManager
            cache_enabled = self.config.get("cache_enabled", True)
            if cache_enabled:
                cache_max_size = self.config.get("cache_max_size", 1000)
                self.cache_manager = CacheManager(max_size=cache_max_size)
                print("[OK] Cache Manager initialized")
        except Exception as e:
            print(f"[WARNING] Cache Manager not available: {e}")
            self.cache_manager = None

        # Initialize Analytics Tracker
        self.analytics_tracker = None
        try:
            from utils.analytics import AnalyticsTracker
            analytics_enabled = self.config.get("analytics_enabled", True)
            if analytics_enabled:
                self.analytics_tracker = AnalyticsTracker(
                    db_path="analytics.db")
                print("[OK] Analytics Tracker initialized")
        except Exception as e:
            print(f"[WARNING] Analytics Tracker not available: {e}")
            self.analytics_tracker = None

        # Initialize memory manager for persistent storage
        self.memory_manager = None
        self.summarizer = None
        if MEMORY_AVAILABLE:
            try:
                self.memory_manager = MemoryManager(
                    db_path=self.config.get("memory_db_path", "bot_memory.db"),
                    short_term_limit=self.config.get(
                        "short_term_memory_limit", 15)
                )
                if self.use_claude and self.claude_handler:
                    self.summarizer = ConversationSummarizer(
                        self.claude_handler)
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
        # Increased context window to 15 messages
        max_context = self.config.get("max_context_messages", 15)
        self.conversations = defaultdict(lambda: {
            'messages': deque(maxlen=max_context),
            'last_activity': datetime.now()
        })

        # Rate limiting: {user_id: [timestamps]}
        self.rate_limits = defaultdict(list)
        self.rate_limit_per_minute = self.config.get(
            "rate_limit_per_minute", 5)

        # Image rate limiting: {user_id: [timestamps]} - 2 images per 24 hours
        self.image_requests = defaultdict(list)
        self.image_limit_per_24h = 2

        # Bot statistics
        self.start_time = datetime.now()
        self.message_count = 0
        self.claude_responses = 0
        self.fallback_responses = 0
        self.version = "2.0.1"  # Version tracking for deployment verification

        # Error alerting
        self.error_count_recent = 0  # Errors in last hour
        self.last_error_alert_time = None
        self.error_alert_threshold = 10  # Alert if more than 10 errors per hour
        self.owner_id = None  # Will be set in setup_hook

        # Initialize response time tracker
        self.response_tracker = None
        if RESPONSE_TRACKER_AVAILABLE:
            try:
                self.response_tracker = ResponseTracker(
                    db_path="response_times.db",
                    slow_threshold=self.config.get(
                        "slow_response_threshold", 5.0)
                )
                print("[OK] Response tracker initialized")
            except Exception as e:
                print(f"[ERROR] Failed to initialize response tracker: {e}")
                self.response_tracker = None

        # Initialize statistics tracker
        self.statistics_tracker = None
        if STATISTICS_TRACKER_AVAILABLE:
            try:
                self.statistics_tracker = StatisticsTracker(
                    db_path="statistics.db"
                )
                print("[OK] Statistics tracker initialized")
            except Exception as e:
                print(f"[ERROR] Failed to initialize statistics tracker: {e}")
                self.statistics_tracker = None

        # Start background task to clean old conversations
        self.cleanup_task = None

        # Budget rate limiting
        self.budget_exceeded = False

        # Initialize fun game state
        self.riddle_answers = {}
        self.trivia_answers = {}

        # Initialize translation settings (per server)
        self.auto_translate_servers = set()  # Server IDs with auto-translation enabled

        # Initialize moderation system
        self.moderation_enabled = {}  # {server_id: bool}
        self.user_warnings = {}  # {server_id: {user_id: [warnings]}}
        self.user_mutes = {}  # {server_id: {user_id: unmute_time}}
        self.user_bans = {}  # {server_id: {user_id: ban_info}}
        self.moderation_logs = []  # List of moderation actions
        self.blacklist = {}  # {server_id: set([words/phrases])}
        self.whitelist = {}  # {server_id: set([user_ids])}
        self.spam_tracker = {}  # {server_id: {user_id: [message_timestamps]}}
        # {server_id: {user_id: [messages]}} for spam detection
        self._recent_messages = {}
        self.nsfw_channels = set()  # Channel IDs where NSFW is allowed

        # Initialize permission system
        self.premium_users = set()  # Set of user IDs with premium access
        self.user_permissions = {}  # {user_id: permission_level} for custom permissions
        # Permission levels: 'owner', 'admin', 'premium', 'regular'
        # Rate limits per level: owner=unlimited, admin=20/min, premium=15/min, regular=5/min

        # Initialize response caching system
        self.response_cache = {}  # {cache_key: {response, timestamp, hits}}
        self.cache_duration = timedelta(hours=1)  # Default 1 hour cache
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0
        }
        # Common questions that should always be cached
        self.common_questions = [
            'what is ai', 'what is artificial intelligence', 'help', 'how do you work',
            'what can you do', 'who are you', 'what are you', 'explain ai',
            'tell me about ai', 'ai definition', 'what is machine learning'
        ]

        # Initialize webhook system
        self.webhooks = {}  # {webhook_id: {url, channel_id, server_id, type, config}}
        self.webhook_counter = 0  # For generating unique IDs
        self.webhook_server = None  # HTTP server for receiving webhooks
        self.webhook_port = int(os.getenv("WEBHOOK_PORT", "8080"))

        # Initialize backup system
        self.backup_dir = os.getenv("BACKUP_DIR", "backups")
        self.backup_retention_days = 7  # Keep last 7 days of backups
        self.backups = []  # List of backup metadata
        os.makedirs(self.backup_dir, exist_ok=True)

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
                "max_context_messages": 15,
                "context_timeout_minutes": 30,
                "follow_up_timeout_minutes": 2
            }

    def _initialize_claude_handler_with_retry(self, max_retries: int = 3) -> Optional[ClaudeHandler]:
        """
        Initialize Claude handler with automatic retry logic
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            ClaudeHandler instance or None if all retries fail
        """
        if not CLAUDE_AVAILABLE:
            print("[ERROR] ❌ Claude handler module not available")
            return None
        
        for attempt in range(max_retries):
            try:
                print(f"[INFO] Attempting to initialize Claude API handler (attempt {attempt + 1}/{max_retries})...")
                handler = ClaudeHandler()
                print("[OK] ✅ Claude API handler initialized successfully!")
                print(f"[OK] Using model: {handler.model}")
                return handler
            except ValueError as e:
                print(f"[ERROR] ❌ Claude API key not configured: {e}")
                print("[ERROR] Bot will use static responses as fallback")
                return None
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    print(f"[WARNING] Claude initialization attempt {attempt + 1}/{max_retries} failed: {error_msg}")
                    print(f"[INFO] Retrying in {2 ** attempt} seconds...")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"[ERROR] ❌ Failed to initialize Claude API after {max_retries} attempts: {e}")
                    if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
                        print("[ERROR] API key appears to be invalid or expired")
                    import traceback
                    traceback.print_exc()
                    return None
        
        return None

    async def _initialize_apis_with_health_checks(self):
        """
        Initialize all APIs with health checks and wait for them to be ready
        """
        print("\n" + "="*50)
        print("[INFO] Starting API initialization with health checks...")
        print("="*50)
        
        # Initialize API manager if not already done
        if not self.api_manager:
            try:
                from utils.api_manager import APIManager, APIProvider
                print("[INFO] Initializing Multi-API Manager...")
                self.api_manager = APIManager()
                print("[OK] Multi-API Manager initialized!")
            except Exception as e:
                print(f"[ERROR] ❌ Failed to initialize API Manager: {e}")
                self.api_manager = None
        
        # Perform health checks on all providers
        if self.api_manager:
            print("[INFO] Performing health checks on all API providers...")
            health_results = await self.api_manager.health_check_all(max_retries=3)
            
            # Log health check summary
            healthy_count = sum(1 for r in health_results.values() if r.get("success"))
            total_count = len(health_results)
            
            print(f"\n[INFO] Health check summary: {healthy_count}/{total_count} providers healthy")
            
            # Try to reinitialize failed providers
            from utils.api_manager import APIProvider
            for provider_name, result in health_results.items():
                if not result.get("success"):
                    try:
                        provider = APIProvider(provider_name)
                        print(f"[INFO] Attempting to reinitialize {provider_name}...")
                        if provider == APIProvider.CLAUDE:
                            self.api_manager._init_claude(max_retries=2)
                        elif provider == APIProvider.GEMINI:
                            self.api_manager._init_gemini(max_retries=2)
                        elif provider == APIProvider.GROQ:
                            self.api_manager._init_groq(max_retries=2)
                        elif provider == APIProvider.OPENROUTER:
                            self.api_manager._init_openrouter(max_retries=2)
                    except Exception as e:
                        print(f"[WARNING] Could not reinitialize {provider_name}: {e}")
        
        # Initialize/reinitialize Claude handler if needed
        if self.api_manager:
            from utils.api_manager import APIProvider
            if APIProvider.CLAUDE in self.api_manager.providers and not self.claude_handler:
                print("[INFO] Initializing Claude handler for backward compatibility...")
                self.claude_handler = self._initialize_claude_handler_with_retry(max_retries=3)
                self.use_claude = self.claude_handler is not None
        
        # Final status summary
        print("\n" + "="*50)
        print("[INFO] API Initialization Complete")
        print("="*50)
        
        if self.api_manager:
            providers = [p.value for p in self.api_manager.providers.keys()]
            status_map = {p.value: self.api_manager.provider_stats[p.value]["status"] for p in self.api_manager.providers.keys()}
            
            for provider_name, status in status_map.items():
                if status == "active":
                    print(f"[OK] ✅ {provider_name.capitalize()}: Active")
                elif status == "initialized":
                    print(f"[OK] ✅ {provider_name.capitalize()}: Initialized (ready for health check)")
                elif status == "error":
                    print(f"[ERROR] ❌ {provider_name.capitalize()}: Failed")
                elif status == "missing_key":
                    print(f"[WARNING] ⚠️ {provider_name.capitalize()}: Missing API key")
                else:
                    print(f"[INFO] ⚪ {provider_name.capitalize()}: {status}")
        
        if self.claude_handler:
            print(f"[OK] ✅ Claude Handler: Ready (Model: {self.claude_handler.model})")
        else:
            print(f"[WARNING] ⚠️ Claude Handler: Not available")
        
        print("="*50 + "\n")
        
        self.api_initialization_complete = True

    async def setup_hook(self):
        """Called when bot is starting up"""
        # Get application info to find owner
        try:
            app_info = await self.application_info()
            if app_info and app_info.owner:
                self.owner_id = app_info.owner.id
                print(
                    f"[OK] Bot owner: {app_info.owner.name} (ID: {self.owner_id})")
        except Exception as e:
            print(f"[WARNING] Could not get application info: {e}")
            self.owner_id = None

        # Start background task to clean old conversations
        self.cleanup_task = asyncio.create_task(
            self._cleanup_old_conversations())

        # Start webhook server (if method exists)
        if hasattr(self, '_start_webhook_server'):
            try:
                asyncio.create_task(self._start_webhook_server())
            except Exception as e:
                print(f"[WARNING] Could not start webhook server: {e}")
        else:
            print("[INFO] Webhook server method not available, skipping")

        # Start daily backup scheduler
        try:
            asyncio.create_task(self._backup_scheduler())
        except Exception as e:
            print(f"[WARNING] Could not start backup scheduler: {e}")

        # Reset monthly budget alerts if it's a new month
        if self.statistics_tracker:
            try:
                self.statistics_tracker.reset_monthly_alerts_if_needed()
                print("[OK] Monthly budget alerts checked/reset")
            except Exception as e:
                print(f"[WARNING] Could not reset monthly budget alerts: {e}")

        # Load slash commands cog
        try:
            from cogs.slash_commands import setup
            await setup(self)
            print("[OK] Slash commands cog loaded")
        except Exception as e:
            print(f"[ERROR] Failed to load slash commands cog: {e}")
            import traceback
            traceback.print_exc()

        # Load API management commands cog
        try:
            from cogs.api_commands import setup as api_setup
            await api_setup(self)
            print("[OK] API commands cog loaded")
        except Exception as e:
            print(f"[WARNING] Failed to load API commands cog: {e}")
            import traceback
            traceback.print_exc()

        # Load fun commands cog
        try:
            from cogs.fun_commands import setup as fun_setup
            await fun_setup(self)
            print("[OK] Fun commands cog loaded")
        except Exception as e:
            print(f"[WARNING] Failed to load fun commands cog: {e}")
            import traceback
            traceback.print_exc()

        # Initialize export manager
        try:
            from utils.export_manager import ExportManager
            self.export_manager = ExportManager()
            print("[OK] Export manager initialized")
        except Exception as e:
            print(f"[WARNING] Export manager not available: {e}")
            self.export_manager = None

        # Initialize APIs with health checks (wait for initialization)
        try:
            await self._initialize_apis_with_health_checks()
        except Exception as e:
            print(f"[ERROR] ❌ API initialization failed: {e}")
            import traceback
            traceback.print_exc()

        # Sync slash commands tree
        try:
            synced = await self.tree.sync()
            print(f"[OK] Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"[ERROR] Failed to sync slash commands: {e}")
            import traceback
            traceback.print_exc()

    async def _check_budget_alerts(self):
        """
        Check budget usage and send alerts if thresholds exceeded
        """
        if not self.statistics_tracker:
            return

        try:
            budget_settings = self.statistics_tracker.get_budget_settings()
            budget_amount = budget_settings.get("budget_amount", 0.0)

            if budget_amount <= 0:
                return  # No budget set

            current_cost = self.statistics_tracker.get_current_month_cost()
            usage_percent = (current_cost / budget_amount) * \
                100 if budget_amount > 0 else 0

            # Check if we need to send alerts
            alerts_to_send = []

            if usage_percent >= 90 and not budget_settings.get("alert_90_sent", False):
                alerts_to_send.append(90)
            elif usage_percent >= 75 and not budget_settings.get("alert_75_sent", False):
                alerts_to_send.append(75)
            elif usage_percent >= 50 and not budget_settings.get("alert_50_sent", False):
                alerts_to_send.append(50)

            # Send alerts
            for threshold in alerts_to_send:
                await self._send_budget_alert(threshold, current_cost, budget_amount, usage_percent)
                self.statistics_tracker.mark_budget_alert_sent(threshold)

        except Exception as e:
            print(f"[ERROR] Error in budget alert check: {e}")

    async def _send_budget_alert(self, threshold: int, current_cost: float, budget_amount: float, usage_percent: float):
        """
        Send budget alert to bot owner

        Args:
            threshold: Alert threshold (50, 75, or 90)
            current_cost: Current month cost
            budget_amount: Budget amount
            usage_percent: Usage percentage
        """
        try:
            owner_id = self.owner_id if hasattr(self, 'owner_id') else None
            if not owner_id and self.application:
                owner_id = self.application.owner.id if self.application.owner else None

            if owner_id:
                owner = await self.fetch_user(owner_id)
                if owner:
                    emoji = "⚠️" if threshold < 90 else "🚨"
                    alert_msg = (
                        f"{emoji} **Budget Alert**\n\n"
                        f"Your API usage has reached **{threshold}%** of your monthly budget!\n\n"
                        f"**Current Spending**: ${current_cost:.2f}\n"
                        f"**Budget**: ${budget_amount:.2f}\n"
                        f"**Usage**: {usage_percent:.1f}%\n\n"
                    )

                    if threshold >= 90:
                        alert_msg += (
                            "🚨 **CRITICAL**: Budget nearly exhausted!\n"
                            "Consider setting a higher budget or reviewing usage.\n"
                            "Use `!budget [amount]` to update your budget."
                        )
                    elif threshold >= 75:
                        alert_msg += (
                            "⚠️ Budget is getting high. Monitor usage carefully.\n"
                            "Use `!costs` to see detailed spending breakdown."
                        )
                    else:
                        alert_msg += (
                            "Budget halfway point reached.\n"
                            "Use `!costs` to see detailed spending breakdown."
                        )

                    if EMBED_HELPER_AVAILABLE:
                        color = EmbedColors.RED if threshold >= 90 else EmbedColors.YELLOW
                        embed = discord.Embed(
                            title=f"{emoji} Budget Alert - {threshold}% Used",
                            description=alert_msg,
                            color=color
                        )
                        embed.add_field(
                            name="💰 Spending",
                            value=f"${current_cost:.2f} / ${budget_amount:.2f}",
                            inline=True
                        )
                        embed.add_field(
                            name="📊 Usage",
                            value=f"{usage_percent:.1f}%",
                            inline=True
                        )
                        embed.set_footer(
                            text="Use !costs for detailed breakdown | !budget to update")
                        await owner.send(embed=embed)
                    else:
                        await owner.send(alert_msg)

                    print(
                        f"[ALERT] Sent budget alert to owner: {threshold}% threshold reached")

        except Exception as e:
            print(f"[ERROR] Failed to send budget alert: {e}")

    async def _check_error_alerts(self):
        """
        Check if errors are frequent and alert bot owner
        """
        try:
            # Reset error count if more than 1 hour passed
            if self.last_error_alert_time:
                time_since_alert = datetime.now() - self.last_error_alert_time
                if time_since_alert > timedelta(hours=1):
                    self.error_count_recent = 0

            # Check if threshold exceeded
            if self.error_count_recent >= self.error_alert_threshold:
                # Only alert once per hour
                if not self.last_error_alert_time or (datetime.now() - self.last_error_alert_time) > timedelta(hours=1):
                    self.last_error_alert_time = datetime.now()

                    # Get owner ID from application info
                    owner_id = self.owner_id if hasattr(
                        self, 'owner_id') else None
                    if not owner_id and self.application:
                        owner_id = self.application.owner.id if self.application.owner else None

                    if owner_id:
                        try:
                            owner = await self.fetch_user(owner_id)
                            if owner:
                                alert_msg = (
                                    f"⚠️ **Error Alert**\n\n"
                                    f"I've encountered {self.error_count_recent} errors in the last hour.\n"
                                    f"This might indicate an issue with the Claude API or network.\n\n"
                                    f"Use `!errors` to see recent errors.\n"
                                    f"Use `!retry` to retry the last failed request."
                                )

                                if EMBED_HELPER_AVAILABLE:
                                    embed = EmbedHelper.create_error_embed(
                                        title="⚠️ Frequent Errors Detected",
                                        description=f"{self.error_count_recent} errors in the last hour",
                                        details="Check `!errors` command for details"
                                    )
                                    await owner.send(embed=embed)
                                else:
                                    await owner.send(alert_msg)

                                print(
                                    f"[ALERT] Sent error alert to owner: {self.error_count_recent} errors")
                        except Exception as e:
                            print(
                                f"[ERROR] Failed to send error alert to owner: {e}")
        except Exception as e:
            print(f"[ERROR] Error in error alert check: {e}")

    def _check_image_rate_limit(self, user_id: int) -> tuple[bool, int, Optional[datetime]]:
        """
        Check if user has exceeded image analysis limit (2 per 24 hours)

        Args:
            user_id: Discord user ID

        Returns:
            Tuple of (is_allowed, remaining_count, next_reset_time)
            - is_allowed: True if user can send image, False if limit exceeded
            - remaining_count: Number of images user can still send
            - next_reset_time: When the oldest request will expire (24h from oldest)
        """
        now = datetime.now()
        user_requests = self.image_requests[user_id]

        # Remove requests older than 24 hours
        cutoff_time = now - timedelta(hours=24)
        user_requests[:] = [ts for ts in user_requests if ts > cutoff_time]

        # Check if limit exceeded
        if len(user_requests) >= self.image_limit_per_24h:
            # Find when the oldest request will expire
            if user_requests:
                oldest_request = min(user_requests)
                next_reset = oldest_request + timedelta(hours=24)
                return False, 0, next_reset
            return False, 0, None

        # User can send image
        remaining = self.image_limit_per_24h - len(user_requests)
        return True, remaining, None

    async def _handle_image_analysis(self, message: discord.Message, image_attachments: List[discord.Attachment]):
        """
        Handle image analysis requests

        Args:
            message: Discord message object
            image_attachments: List of image attachments
        """
        if not self.use_claude or not self.claude_handler:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Image Analysis Unavailable",
                    description="Claude API not available for image analysis!"
                )
                await message.reply(embed=embed)
            else:
                await message.reply("❌ Image analysis not available!")
            return

        # Check image rate limit (2 per 24 hours)
        user_id = message.author.id
        is_allowed, remaining, next_reset = self._check_image_rate_limit(
            user_id)

        if not is_allowed:
            # Detect language for error message
            detected_language = 'en'
            kurdish_dialect = None
            if KURDISH_DETECTOR_AVAILABLE and message.content:
                lang_result = KurdishDetector.detect_language(message.content)
                detected_language = lang_result[0]
                if detected_language == 'ku':
                    kurdish_result = KurdishDetector.detect_kurdish(
                        message.content)
                    if kurdish_result:
                        kurdish_dialect, _ = kurdish_result

            # Create user-friendly error message
            if next_reset:
                time_until_reset = next_reset - datetime.now()
                hours = int(time_until_reset.total_seconds() / 3600)
                minutes = int((time_until_reset.total_seconds() % 3600) / 60)

                if detected_language == 'ku':
                    if kurdish_dialect == 'Sorani':
                        error_msg = (
                            f"ببورە، سنووری وێنەت تێپەڕیوە! تۆ دەتوانیت تەنها ٢ وێنە لە ٢٤ کاتژمێردا بنێریت.\n"
                            f"تکایە دواتر هەوڵ بدەوە لە {hours} کاتژمێر و {minutes} خولەک."
                        )
                    else:
                        error_msg = (
                            f"Bibûre, sînûra wêneyê te têpêriye! Tu tenê dikarî 2 wêne di 24 saetan de bişînî.\n"
                            f"Tika duar hewl bide li {hours} saetan û {minutes} deqeyan."
                        )
                elif detected_language == 'ar':
                    error_msg = (
                        f"عذراً، لقد تجاوزت حد الصور! يمكنك إرسال صورتين فقط كل 24 ساعة.\n"
                        f"يرجى المحاولة مرة أخرى بعد {hours} ساعة و {minutes} دقيقة."
                    )
                else:
                    error_msg = (
                        f"Sorry, you've reached your image analysis limit! "
                        f"You can only analyze 2 images per 24 hours.\n"
                        f"Please try again in {hours} hour(s) and {minutes} minute(s)."
                    )
            else:
                if detected_language == 'ku':
                    if kurdish_dialect == 'Sorani':
                        error_msg = "ببورە، سنووری وێنەت تێپەڕیوە! تۆ دەتوانیت تەنها ٢ وێنە لە ٢٤ کاتژمێردا بنێریت."
                    else:
                        error_msg = "Bibûre, sînûra wêneyê te têpêriye! Tu tenê dikarî 2 wêne di 24 saetan de bişînî."
                elif detected_language == 'ar':
                    error_msg = "عذراً، لقد تجاوزت حد الصور! يمكنك إرسال صورتين فقط كل 24 ساعة."
                else:
                    error_msg = (
                        "Sorry, you've reached your image analysis limit! "
                        "You can only analyze 2 images per 24 hours."
                    )

            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="⚠️ Image Limit Reached",
                    description=error_msg
                )
                await message.reply(embed=embed)
            else:
                await message.reply(f"⚠️ {error_msg}")
            return

        try:
            # Show typing indicator
            async with message.channel.typing():
                # Get user question/prompt
                user_prompt = message.content.strip() if message.content else ""

                # Determine analysis type from prompt
                prompt_lower = user_prompt.lower()
                if not user_prompt or any(keyword in prompt_lower for keyword in ["what", "describe", "analyze", "see", "show"]):
                    analysis_prompt = "Describe this image in detail. What do you see? Identify objects, people, text, scenes, and any notable details."
                elif any(keyword in prompt_lower for keyword in ["read", "text", "ocr", "extract"]):
                    analysis_prompt = "Read and extract all text visible in this image. Include any signs, labels, captions, or written content."
                elif any(keyword in prompt_lower for keyword in ["identify", "what is", "what are"]):
                    analysis_prompt = "Identify and describe what you see in this image. What objects, people, or scenes are present?"
                else:
                    # Use user's prompt if provided
                    analysis_prompt = user_prompt if user_prompt else "Describe this image in detail."

                # Detect language
                detected_language = 'en'
                kurdish_dialect = None
                if KURDISH_DETECTOR_AVAILABLE and user_prompt:
                    lang_result = KurdishDetector.detect_language(user_prompt)
                    detected_language = lang_result[0]
                    if detected_language == 'ku':
                        kurdish_result = KurdishDetector.detect_kurdish(
                            user_prompt)
                        if kurdish_result:
                            kurdish_dialect, _ = kurdish_result

                # Get image URLs
                image_urls = [
                    attachment.url for attachment in image_attachments]

                # Analyze images
                if len(image_urls) == 1:
                    result = await self.claude_handler.analyze_image(
                        image_url=image_urls[0],
                        prompt=analysis_prompt,
                        user_name=message.author.display_name,
                        detected_language=detected_language,
                        kurdish_dialect=kurdish_dialect
                    )
                else:
                    result = await self.claude_handler.analyze_multiple_images(
                        image_urls=image_urls,
                        prompt=analysis_prompt,
                        user_name=message.author.display_name,
                        detected_language=detected_language,
                        kurdish_dialect=kurdish_dialect
                    )

                if result["success"]:
                    response_text = result["response"]
                    tokens_used = result.get("tokens_used", 0)
                    input_tokens = result.get("input_tokens", 0)
                    output_tokens = result.get("output_tokens", 0)

                    # Cache image analysis result
                    img_cache_key = self._get_cache_key(
                        f"{analysis_prompt}:{image_urls[0] if len(image_urls) == 1 else 'multiple'}", 'image')
                    img_cached = self._get_cached_response(img_cache_key)
                    is_cached = img_cached is not None

                    if not is_cached:
                        # Cache the result
                        self._cache_response(img_cache_key, response_text, {
                            'tokens_used': tokens_used,
                            'images_count': len(image_urls)
                        })

                    # Track API usage
                    if self.statistics_tracker:
                        try:
                            user_id = str(message.author.id)
                            server_id = str(
                                message.guild.id) if message.guild else None
                            self.statistics_tracker.track_api_usage(
                                tokens_used=tokens_used,
                                success=True,
                                model_used=self.claude_handler.model,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                user_id=user_id,
                                server_id=server_id
                            )
                            # Check budget
                            await self._check_budget_alerts()
                        except Exception as e:
                            print(
                                f"[ERROR] Failed to track image analysis usage: {e}")

                    # Create embed response
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_ai_response_embed(
                            content=response_text,
                            user_name=message.author.display_name,
                            user_avatar=message.author.display_avatar.url if hasattr(
                                message.author, 'display_avatar') else None
                        )

                        # Add cached indicator
                        if is_cached:
                            embed.set_footer(
                                text="⚡ Cached response • Faster & cost-free")

                        # Add image count info
                        if len(image_urls) > 1:
                            embed.add_field(
                                name="📷 Images Analyzed",
                                value=f"{len(image_urls)} images",
                                inline=True
                            )

                        # Add token usage
                        footer_text = f"Vision API • {tokens_used:,} tokens"
                        if is_cached:
                            footer_text = "⚡ Cached response • " + footer_text
                        embed.set_footer(text=footer_text)

                        await message.reply(embed=embed)
                    else:
                        response_with_info = response_text
                        if len(image_urls) > 1:
                            response_with_info = f"**Analyzed {len(image_urls)} images:**\n\n{response_text}"
                        await message.reply(response_with_info)

                    # Track image request (only count once per message, regardless of number of images)
                    self.image_requests[user_id].append(datetime.now())
                    print(
                        f"[OK] Image analysis successful: {len(image_urls)} image(s), {tokens_used} tokens")
                    print(
                        f"[INFO] Image request tracked for user {user_id}. Remaining: {remaining - 1} images in 24h")
                else:
                    error_msg = result.get("error", "Unknown error")
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_error_embed(
                            title="❌ Image Analysis Failed",
                            description="Could not analyze image",
                            error_details=error_msg
                        )
                        await message.reply(embed=embed)
                    else:
                        await message.reply(f"❌ Failed to analyze image: {error_msg}")

                    # Track error
                    if self.statistics_tracker:
                        try:
                            self.statistics_tracker.track_error(
                                error_type="IMAGE_ANALYSIS_ERROR",
                                error_message=error_msg[:200],
                                user_id=str(message.author.id),
                                server_id=str(
                                    message.guild.id) if message.guild else None
                            )
                        except:
                            pass

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Error",
                    description="Error analyzing image",
                    error_details=str(e)
                )
                await message.reply(embed=embed)
            else:
                await message.reply(f"❌ Error: {str(e)}")
            print(f"[ERROR] Image analysis failed: {e}")
            import traceback
            traceback.print_exc()

    async def _check_message_moderation(self, message: discord.Message) -> bool:
        """
        Check message for moderation violations

        Returns:
            True if message should be blocked, False otherwise
        """
        if not message.guild:
            return False

        server_id = message.guild.id
        user_id = message.author.id

        # Check if user is whitelisted
        if server_id in self.whitelist and user_id in self.whitelist[server_id]:
            return False

        # Check if user is banned
        if server_id in self.user_bans and user_id in self.user_bans[server_id]:
            ban_info = self.user_bans[server_id][user_id]
            if ban_info.get('permanent') or ban_info.get('until', datetime.max) > datetime.now():
                return True

        # Check if user is muted
        if server_id in self.user_mutes and user_id in self.user_mutes[server_id]:
            mute_until = self.user_mutes[server_id][user_id]
            if mute_until > datetime.now():
                return True
            else:
                # Mute expired, remove it
                del self.user_mutes[server_id][user_id]

        # Check blacklist
        if server_id in self.blacklist:
            content_lower = message.content.lower()
            for blocked_word in self.blacklist[server_id]:
                if blocked_word.lower() in content_lower:
                    await message.delete()
                    await message.channel.send(
                        f"⚠️ Message from {message.author.mention} was removed for containing blacklisted content.",
                        delete_after=5
                    )
                    self._log_moderation_action(
                        server_id=server_id,
                        action="delete",
                        user_id=user_id,
                        moderator_id=self.user.id,
                        reason="Blacklisted word/phrase"
                    )
                    return True

        # Check spam
        if await self._check_spam(message):
            await message.delete()
            await message.channel.send(
                f"⚠️ Message from {message.author.mention} was removed for spam.",
                delete_after=5
            )
            self._log_moderation_action(
                server_id=server_id,
                action="delete",
                user_id=user_id,
                moderator_id=self.user.id,
                reason="Spam detected"
            )
            return True

        # Check NSFW content in SFW channels
        if message.channel.id not in self.nsfw_channels:
            if await self._check_nsfw_content(message):
                await message.delete()
                await message.channel.send(
                    f"⚠️ NSFW content from {message.author.mention} was removed. Please use NSFW channels for such content.",
                    delete_after=5
                )
                self._log_moderation_action(
                    server_id=server_id,
                    action="delete",
                    user_id=user_id,
                    moderator_id=self.user.id,
                    reason="NSFW content in SFW channel"
                )
                return True

        return False

    async def _check_spam(self, message: discord.Message) -> bool:
        """Check if message is spam"""
        if not message.guild:
            return False

        server_id = message.guild.id
        user_id = message.author.id

        if server_id not in self.spam_tracker:
            self.spam_tracker[server_id] = {}

        if user_id not in self.spam_tracker[server_id]:
            self.spam_tracker[server_id][user_id] = []

        now = datetime.now()
        timestamps = self.spam_tracker[server_id][user_id]

        # Remove timestamps older than 10 seconds
        timestamps[:] = [ts for ts in timestamps if (
            now - ts).total_seconds() < 10]

        # Add current timestamp
        timestamps.append(now)

        # Check if more than 5 messages in 10 seconds (spam)
        if len(timestamps) > 5:
            return True

        # Check for repeated messages
        if len(timestamps) >= 3:
            # Check if same message repeated
            recent_messages = getattr(self, '_recent_messages', {})
            if server_id not in recent_messages:
                recent_messages[server_id] = {}
            if user_id not in recent_messages[server_id]:
                recent_messages[server_id][user_id] = []

            recent_messages[server_id][user_id].append(message.content.lower())
            if len(recent_messages[server_id][user_id]) > 3:
                recent_messages[server_id][user_id].pop(0)

            # Check if last 3 messages are identical
            if len(recent_messages[server_id][user_id]) == 3:
                if len(set(recent_messages[server_id][user_id])) == 1:
                    return True

        return False

    async def _check_nsfw_content(self, message: discord.Message) -> bool:
        """Check if message contains NSFW content"""
        # Check if channel is marked as NSFW
        if hasattr(message.channel, 'nsfw') and message.channel.nsfw:
            return False

        # Check for NSFW keywords
        nsfw_keywords = [
            'nsfw', 'porn', 'xxx', 'sex', 'nude', 'naked',
            'explicit', 'adult', '18+', 'nsfl'
        ]

        content_lower = message.content.lower()
        for keyword in nsfw_keywords:
            if keyword in content_lower:
                return True

        # Check attachments for NSFW
        if message.attachments:
            for attachment in message.attachments:
                # Check file name
                filename_lower = attachment.filename.lower()
                if any(keyword in filename_lower for keyword in nsfw_keywords):
                    return True

                # Check if image and might be NSFW (basic check)
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    # Could use AI to check image, but for now just check filename
                    pass

        return False

    def _log_moderation_action(
        self,
        server_id: int,
        action: str,
        user_id: int,
        moderator_id: int,
        reason: str = None,
        duration: timedelta = None
    ):
        """Log a moderation action"""
        log_entry = {
            'timestamp': datetime.now(),
            'server_id': server_id,
            'action': action,
            'user_id': user_id,
            'moderator_id': moderator_id,
            'reason': reason,
            'duration': duration
        }
        self.moderation_logs.append(log_entry)

        # Keep only last 1000 logs
        if len(self.moderation_logs) > 1000:
            self.moderation_logs.pop(0)

    async def _auto_translate_message(self, message: discord.Message, detected_language: str):
        """
        Auto-translate a message when auto-translation is enabled

        Args:
            message: Discord message object
            detected_language: Detected language code
        """
        if not self.use_claude or not self.claude_handler:
            return

        try:
            # Don't translate if message is too short or is a command
            if len(message.content) < 5 or message.content.startswith(self.config.get("prefix", "!")):
                return

            # Detect Kurdish dialect
            kurdish_dialect = None
            if detected_language == 'ku' and KURDISH_DETECTOR_AVAILABLE:
                kurdish_result = KurdishDetector.detect_kurdish(
                    message.content)
                if kurdish_result:
                    kurdish_dialect, _ = kurdish_result

            # Build translation prompt
            lang_names = {
                'ku': 'Kurdish',
                'ar': 'Arabic',
                'tr': 'Turkish'
            }
            source_lang = lang_names.get(detected_language, detected_language)

            prompt = f"Translate the following text from {source_lang} to English. Provide only the translation:\n\n{message.content}"

            messages = [{
                "role": "user",
                "content": prompt
            }]

            result = await self.claude_handler.generate_response(
                messages=messages,
                user_name=message.author.display_name
            )

            if result["success"]:
                translation = result["response"].strip()

                # Send translation as a reply
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_info_embed(
                        title="🌐 Auto-Translation",
                        description=f"**Original ({source_lang}):** {message.content}\n\n**Translation:** {translation}",
                        color=EmbedColors.BLUE
                    )
                    embed.set_footer(
                        text=f"Auto-translated from {source_lang}")
                    await message.reply(embed=embed, mention_author=False)
                else:
                    await message.reply(f"🌐 **Auto-Translation**\n\n**Original ({source_lang}):** {message.content}\n**Translation:** {translation}", mention_author=False)
        except Exception as e:
            print(f"[ERROR] Auto-translation failed: {e}")
            # Silently fail for auto-translation

    def _get_cache_key(self, content: str, cache_type: str = 'general') -> str:
        """
        Generate cache key from content

        Args:
            content: Content to cache
            cache_type: Type of cache ('general', 'translation', 'image', 'static')

        Returns:
            Cache key string
        """
        import hashlib
        # Normalize content for caching (lowercase, strip whitespace)
        normalized = content.lower().strip()
        cache_string = f"{cache_type}:{normalized}"
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """
        Get cached response if available and not expired

        Args:
            cache_key: Cache key

        Returns:
            Cached response dict or None
        """
        if cache_key not in self.response_cache:
            self.cache_stats['misses'] += 1
            self.cache_stats['total_requests'] += 1
            return None

        cached = self.response_cache[cache_key]
        cache_time = cached['timestamp']

        # Check if cache is expired
        if datetime.now() - cache_time > self.cache_duration:
            del self.response_cache[cache_key]
            self.cache_stats['misses'] += 1
            self.cache_stats['total_requests'] += 1
            return None

        # Cache hit!
        cached['hits'] = cached.get('hits', 0) + 1
        self.cache_stats['hits'] += 1
        self.cache_stats['total_requests'] += 1
        return cached

    def _cache_response(self, cache_key: str, response: str, metadata: Optional[Dict] = None):
        """
        Cache a response

        Args:
            cache_key: Cache key
            response: Response to cache
            metadata: Optional metadata (tokens_used, etc.)
        """
        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now(),
            'hits': 0,
            'metadata': metadata or {}
        }

        # Limit cache size (keep last 500 entries)
        if len(self.response_cache) > 500:
            # Remove oldest entries
            sorted_cache = sorted(
                self.response_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            for key, _ in sorted_cache[:-500]:
                del self.response_cache[key]

    def _is_common_question(self, content: str) -> bool:
        """Check if content is a common question"""
        content_lower = content.lower().strip()
        for common in self.common_questions:
            if common in content_lower:
                return True
        return False

    def _extract_and_store_facts(self, user_id: str, channel_id: str, content: str):
        """
        Automatically extract and store facts from user messages

        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            content: Message content
        """
        if not self.memory_manager:
            return

        import re
        content_lower = content.lower().strip()

        # Patterns to extract facts
        patterns = [
            (r"my name is (.+)", "name", 0.9),
            (r"i am (.+)", "name", 0.8),
            (r"i'm (.+)", "name", 0.8),
            (r"call me (.+)", "name", 0.9),
            (r"i like (.+)", "likes", 0.7),
            (r"i love (.+)", "loves", 0.8),
            (r"i prefer (.+)", "preference", 0.7),
            (r"my favorite (.+) is (.+)", None, 0.7),
            (r"i'm from (.+)", "location", 0.8),
            (r"i live in (.+)", "location", 0.8),
            (r"i work as (.+)", "occupation", 0.8),
            (r"i'm a (.+)", "occupation", 0.8),
            (r"i'm allergic to (.+)", "allergy", 0.9),
        ]

        for pattern, key, importance in patterns:
            match = re.search(pattern, content_lower)
            if match:
                try:
                    if key is None:
                        # Special case for "my favorite X is Y"
                        groups = match.groups()
                        fact_key = f"favorite_{groups[0].replace(' ', '_')}"
                        fact_value = groups[1]
                    else:
                        fact_key = key
                        fact_value = match.group(1)

                    # Store fact
                    self.memory_manager.add_user_fact(
                        user_id=user_id,
                        channel_id=channel_id,
                        fact_key=fact_key,
                        fact_value=fact_value.strip(),
                        importance_score=importance
                    )
                    print(
                        f"[INFO] Auto-extracted fact: {fact_key} = {fact_value}")
                    break  # Only extract one fact per message
                except Exception as e:
                    print(f"[ERROR] Failed to store extracted fact: {e}")

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
            start_time = datetime.fromisoformat(
                messages_to_summarize[0]["timestamp"])
            end_time = datetime.fromisoformat(
                messages_to_summarize[-1]["timestamp"])

            # Extract preferences from messages (for importance scoring)
            from utils.importance_scorer import ImportanceScorer
            preferences = ImportanceScorer.extract_preferences(
                [{"role": m["role"], "content": m["content"]}
                    for m in messages_to_summarize]
            )

            # Create summary using Claude
            summary_result = await self.summarizer.summarize_messages(
                messages=[{"role": m["role"], "content": m["content"]}
                          for m in messages_to_summarize],
                user_name=None,
                extract_details=False  # Simple summary for automatic summarization
            )

            # Handle both dict and string return types (backwards compatibility)
            if isinstance(summary_result, dict):
                summary_text = summary_result.get(
                    "summary", "No summary available.")
            else:
                summary_text = summary_result

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

            print(
                f"[INFO] Summarized {len(messages_to_summarize)} messages for user {user_id}")

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
                timeout = timedelta(minutes=self.config.get(
                    "context_timeout_minutes", 30))

                # Find and remove old conversations from in-memory cache
                channels_to_remove = []
                for channel_id, conv_data in self.conversations.items():
                    if now - conv_data['last_activity'] > timeout:
                        channels_to_remove.append(channel_id)

                for channel_id in channels_to_remove:
                    del self.conversations[channel_id]
                    print(
                        f"Cleared conversation context for channel {channel_id} (inactive)")

                # Clean up old image requests (older than 24 hours)
                cutoff_time = now - timedelta(hours=24)
                users_to_clean = []
                for user_id, timestamps in self.image_requests.items():
                    # Remove old timestamps
                    self.image_requests[user_id] = [
                        ts for ts in timestamps if ts > cutoff_time]
                    # Remove user entry if no timestamps left
                    if not self.image_requests[user_id]:
                        users_to_clean.append(user_id)

                for user_id in users_to_clean:
                    del self.image_requests[user_id]

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
                            print(
                                f"[INFO] Memory decay: Processed {total_processed} old summaries")

                        # Clean up old messages (but keep important ones)
                        self.memory_manager.cleanup_old_messages(
                            days=60,  # Clean messages older than 60 days
                            min_importance=0.4  # Keep important messages
                        )
                    except Exception as e:
                        print(f"[ERROR] Error in memory decay cleanup: {e}")

            except Exception as e:
                print(f"Error in cleanup task: {e}")

    def _get_user_permission_level(self, user_id: int, guild: Optional[discord.Guild] = None) -> str:
        """
        Get user's permission level

        Returns:
            'owner', 'admin', 'premium', or 'regular'
        """
        # Owner check
        if hasattr(self, 'owner_id') and self.owner_id and user_id == self.owner_id:
            return 'owner'

        # Admin check (server admins)
        if guild:
            member = guild.get_member(user_id)
            if member and member.guild_permissions.administrator:
                return 'admin'

        # Premium check
        if user_id in self.premium_users:
            return 'premium'

        # Custom permission override
        if user_id in self.user_permissions:
            return self.user_permissions[user_id]

        # Default to regular
        return 'regular'

    def _get_rate_limit_for_level(self, level: str) -> int:
        """
        Get rate limit for permission level

        Returns:
            Messages per minute allowed
        """
        rate_limits = {
            'owner': 999999,  # Effectively unlimited
            'admin': 20,
            'premium': 15,
            'regular': 5
        }
        return rate_limits.get(level, 5)

    def _check_rate_limit(self, user_id: int, guild: Optional[discord.Guild] = None) -> bool:
        """
        Check if user is within rate limit based on permission level
        """
        # Get user's permission level
        level = self._get_user_permission_level(user_id, guild)
        rate_limit = self._get_rate_limit_for_level(level)

        now = datetime.now()
        # Remove timestamps older than 1 minute
        self.rate_limits[user_id] = [
            ts for ts in self.rate_limits[user_id]
            if now - ts < timedelta(minutes=1)
        ]

        # Check if limit exceeded
        if len(self.rate_limits[user_id]) >= rate_limit:
            return False

        # Add current timestamp
        self.rate_limits[user_id].append(now)
        return True

    def _has_permission(self, user_id: int, required_level: str, guild: Optional[discord.Guild] = None) -> bool:
        """
        Check if user has required permission level

        Args:
            user_id: User ID to check
            required_level: Required level ('owner', 'admin', 'premium', 'regular')
            guild: Optional guild for admin check

        Returns:
            True if user has permission
        """
        user_level = self._get_user_permission_level(user_id, guild)

        level_hierarchy = {
            'owner': 4,
            'admin': 3,
            'premium': 2,
            'regular': 1
        }

        user_rank = level_hierarchy.get(user_level, 0)
        required_rank = level_hierarchy.get(required_level, 999)

        return user_rank >= required_rank

    async def setup_hook(self):
        """Called when bot is starting up - setup owner info and reset monthly budget alerts"""
        # Get application info to find owner
        try:
            app_info = await self.application_info()
            if app_info and app_info.owner:
                self.owner_id = app_info.owner.id
                print(
                    f"[OK] Bot owner: {app_info.owner.name} (ID: {self.owner_id})")
        except Exception as e:
            print(f"[WARNING] Could not get application info: {e}")
            self.owner_id = None

        # Start webhook server (if method exists)
        if hasattr(self, '_start_webhook_server'):
            try:
                asyncio.create_task(self._start_webhook_server())
            except Exception as e:
                print(f"[WARNING] Could not start webhook server: {e}")
        else:
            print("[INFO] Webhook server method not available, skipping")

        # Start daily backup scheduler
        try:
            asyncio.create_task(self._backup_scheduler())
        except Exception as e:
            print(f"[WARNING] Could not start backup scheduler: {e}")

        # Reset monthly budget alerts if it's a new month
        if self.statistics_tracker:
            try:
                self.statistics_tracker.reset_monthly_alerts_if_needed()
                print("[OK] Monthly budget alerts checked/reset")
            except Exception as e:
                print(f"[WARNING] Could not reset monthly budget alerts: {e}")

    async def _test_apis_on_startup(self):
        """Test all APIs on startup"""
        if self.api_manager:
            try:
                await asyncio.sleep(2)  # Wait a bit for bot to be ready
                await self.api_manager.test_on_startup()
            except Exception as e:
                print(f"[WARNING] Failed to test APIs on startup: {e}")
        
        # Also test Claude handler if available
        if self.claude_handler:
            try:
                print("[INFO] Testing Claude handler API...")
                test_result = await self.claude_handler.test_api_key()
                if test_result.get("success"):
                    print("[OK] ✅ Claude handler API test: Success")
                else:
                    print(f"[ERROR] ❌ Claude handler API test: Failed - {test_result.get('error', 'Unknown')}")
                    # Try to reinitialize
                    print("[INFO] Attempting to reinitialize Claude handler...")
                    self.claude_handler = self._initialize_claude_handler_with_retry(max_retries=2)
                    self.use_claude = self.claude_handler is not None
            except Exception as e:
                print(f"[WARNING] Failed to test Claude handler: {e}")

    async def on_ready(self):
        """Called when bot is ready and connected"""
        # Wait for API initialization if not complete
        if not self.api_initialization_complete:
            print("[INFO] Waiting for API initialization to complete...")
            max_wait = 30  # Maximum wait time in seconds
            waited = 0
            while not self.api_initialization_complete and waited < max_wait:
                await asyncio.sleep(1)
                waited += 1
            
            if not self.api_initialization_complete:
                print("[WARNING] API initialization timed out, continuing anyway...")
        
        mode = "Multi-API" if self.api_manager else (
            "Claude AI" if self.use_claude else "Static Responses (Fallback)")

        print(f"\n{'='*50}")
        print(f"AI Boot is ready!")
        print(f"Logged in as: {self.user.name}#{self.user.discriminator}")
        print(f"Bot ID: {self.user.id}")
        print(f"Servers: {len(self.guilds)}")
        print(f"Mode: {mode}")
        if self.api_manager:
            providers = [p.value for p in self.api_manager.providers.keys()]
            print(
                f"Available APIs: {', '.join(providers) if providers else 'None'}")
            # Run additional startup tests
            asyncio.create_task(self._test_apis_on_startup())
        elif self.use_claude and self.claude_handler:
            print(f"Claude Model: {self.claude_handler.model}")
        print(f"{'='*50}\n")

        # Sync slash commands (backup sync in case setup_hook didn't work)
        try:
            synced = await self.tree.sync()
            if synced:
                print(
                    f"[OK] Synced {len(synced)} slash command(s) in on_ready")
        except Exception as e:
            print(f"[WARNING] Could not sync slash commands in on_ready: {e}")

        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{self.config.get('prefix', '!')}help or /help"
        )
        await self.change_presence(activity=activity)

    def _build_system_prompt(
        self,
        user_name: Optional[str] = None,
        summaries: Optional[List[str]] = None,
        detected_language: Optional[str] = None,
        kurdish_dialect: Optional[str] = None,
        user_facts: Optional[List[Dict[str, any]]] = None,
        follow_up_context: Optional[str] = None
    ) -> str:
        """Build system prompt for API manager (similar to Claude handler)"""
        base_prompt = (
            "You are AI Boot, a friendly and helpful Discord bot assistant. "
            "You have a professional yet warm personality - be knowledgeable and reliable, but also approachable and friendly. "
            "Use emojis occasionally (😊, 👍, ✨, 💡) to add friendliness, but don't overuse them. "
            "Answer questions directly and completely. Don't ask for clarification - provide helpful answers based on context. "
            "Be conversational but get to the point quickly. Keep responses concise (max 300 tokens) and Discord-friendly.\n\n"

            "📝 RESPONSE FORMATTING:\n"
            "- Use bullet points (•) for lists when helpful\n"
            "- Structure longer responses with clear sections\n"
            "- Use line breaks for readability\n"
            "- Keep paragraphs short (2-3 sentences max)\n"
            "- Format code/technical terms with backticks when appropriate\n\n"

            "💬 CONVERSATION FLOW GUIDELINES:\n"
            "- Maintain natural conversation flow across multiple messages\n"
            "- Reference previous answers when relevant: 'As I mentioned earlier...', 'Building on what we discussed...'\n"
            "- If the user asks a follow-up question within 2 minutes, treat it as related to the previous topic\n"
            "- Ask relevant follow-up questions when appropriate to keep conversation engaging\n"
            "- Connect current questions to previous context naturally\n"
            "- If the user asks about something you already explained, briefly reference it: 'Like I said before...'\n"
            "- Maintain topic continuity - don't abruptly change subjects unless the user does\n"
            "- Remember the last 10 messages in the conversation for context\n\n"

            "🌍 MULTILINGUAL SUPPORT:\n"
            "You support Kurdish (Sorani and Kurmanji dialects), English, and Arabic.\n"
            "ALWAYS respond in the SAME LANGUAGE the user uses. Auto-detect their language and match it exactly.\n"
            "When a user speaks Kurdish, respond FULLY in Kurdish using the same dialect.\n"
            "For mixed languages, match the user's primary language preference.\n"
            "For error messages, use the user's detected language.\n\n"

            "🟥⬜🟩☀️ KURDISH LANGUAGE GUIDELINES (Kurdistan Flag: Red-White-Green with Sun):\n"
            "• Sorani (Central Kurdish): Uses Arabic script (ئە, پ, ژ, گ, چ, ۆ, ش)\n"
            "  Example: 'سڵاو، چۆنی؟' → Respond: 'سڵاو! من باشم، سوپاس. تۆ چۆنی؟'\n"
            "• Kurmanji (Northern Kurdish): Uses Latin script (ç, ş, ê, î, û)\n"
            "  Example: 'Merheba, çawa yî?' → Respond: 'Merheba! Ez baş im, spas. Tu çawa yî?'\n"
            "• Use culturally appropriate greetings and expressions\n"
            "• Be respectful and warm in Kurdish conversations\n"
            "• Common Sorani greetings: سڵاو (hello), چۆنی (how are you), سوپاس (thanks)\n"
            "• Common Kurmanji greetings: Merheba (hello), Çawa yî (how are you), Spas (thanks)\n"
            "• IMPORTANT: When showing language flags in translations, use 🟥⬜🟩☀️ for Kurdish (both Sorani and Kurmanji) to represent the Kurdistan flag colors (red, white, green with sun)\n\n"

            "⚠️ ERROR HANDLING:\n"
            "If you encounter an error or can't provide an answer, respond in the user's language:\n"
            "- English: 'I'm having trouble connecting. Please try again in a moment.'\n"
            "- Kurdish (Sorani): 'ببورە، هەندێک کێشە هەیە. تکایە دواتر هەوڵ بدەوە.'\n"
            "- Kurdish (Kurmanji): 'Bibûre, hinek kêşe heye. Tika duar hewl bide.'\n"
            "- Arabic: 'أواجه مشكلة في الاتصال. يرجى المحاولة مرة أخرى في لحظة.'\n"
            "Never expose technical error details to users - keep messages friendly and simple."
        )

        # Add summaries (long-term memory) to system prompt
        if summaries:
            base_prompt += "\n\nPrevious conversation summaries (for context):\n"
            for summary in summaries[:5]:  # Limit to 5 summaries
                base_prompt += f"- {summary}\n"
            base_prompt += "\nUse these summaries to remember past conversations, but focus on the current conversation."

        # Add user name to system prompt if provided
        if user_name:
            base_prompt += f"\n\nThe user you're talking to is: {user_name}"

        # Add user facts for personalization
        if user_facts:
            facts_text = "\n\nThings I know about this user (use these to personalize responses):\n"
            for fact in user_facts[:15]:  # Limit to top 15 facts
                facts_text += f"- {fact.get('fact_key', 'unknown').title()}: {fact.get('fact_value', '')}\n"
            base_prompt += facts_text
            base_prompt += "\nUse these facts naturally in your responses when relevant. Don't mention that you're using stored facts - just incorporate them naturally."

        # Add follow-up context if this is a follow-up question
        if follow_up_context:
            base_prompt += f"\n\n{follow_up_context}"

        # Add language detection context
        if detected_language == 'ku':
            if kurdish_dialect:
                base_prompt += f"\n\nIMPORTANT: The user is speaking Kurdish ({kurdish_dialect} dialect). Respond FULLY in Kurdish using the {kurdish_dialect} dialect. Match their language exactly."
            else:
                base_prompt += "\n\nIMPORTANT: The user is speaking Kurdish. Respond FULLY in Kurdish. Match their dialect (Sorani or Kurmanji) based on their script and expressions."
        elif detected_language:
            base_prompt += f"\n\nNote: User language detected as {detected_language}. Respond in the same language if appropriate."

        return base_prompt

    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore messages from bots (including ourselves)
        if message.author.bot:
            return

        # Check moderation first (before processing message)
        if message.guild:
            if await self._check_message_moderation(message):
                return  # Message was blocked/deleted by moderation

        # Check for image attachments (even without text)
        has_images = False
        image_attachments = []
        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    has_images = True
                    image_attachments.append(attachment)

        # Ignore empty messages (unless they have images)
        if not message.content and not has_images:
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

        # Handle images if bot is mentioned or in DM
        if has_images and (bot_mentioned or is_dm):
            await self._handle_image_analysis(message, image_attachments)
            # Continue processing text if present
            if not message.content:
                return

        # Only respond to mentions or DMs (for text messages)
        if not (bot_mentioned or is_dm):
            # Check for auto-translation mode
            if message.guild and message.guild.id in self.auto_translate_servers:
                # Auto-translate non-English messages
                if KURDISH_DETECTOR_AVAILABLE:
                    lang_result = KurdishDetector.detect_language(
                        message.content)
                    detected_lang = lang_result[0]
                    if detected_lang != 'en':
                        await self._auto_translate_message(message, detected_lang)
            return

        # Check rate limit (based on permission level)
        if not self._check_rate_limit(message.author.id, message.guild):
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="⏱️ Rate Limited",
                    description="Whoa, slow down! Let's chat in a minute 😊",
                    footer="Rate limit: 5 messages per minute"
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send(
                    "Whoa, slow down! Let's chat in a minute 😊"
                )
            return

        # Show typing indicator while AI is thinking
        async with message.channel.typing():
            # Start timing the response
            start_time = None
            if self.response_tracker:
                start_time = self.response_tracker.start_timer()

            try:

                # Clean message content (remove mention)
                content = message.content
                if bot_mentioned:
                    content = content.replace(f"<@{self.user.id}>", "").strip()
                    content = content.replace(
                        f"<@!{self.user.id}>", "").strip()

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

                # Track message statistics (will be updated with language after detection)
                pass

                # Detect language (especially Kurdish)
                detected_language = 'en'
                kurdish_dialect = None

                # Check for stored language preference first
                if self.memory_manager:
                    stored_lang = self.memory_manager.get_user_preference(
                        user_id, channel_id, 'language')
                    stored_dialect = self.memory_manager.get_user_preference(
                        user_id, channel_id, 'kurdish_dialect')
                    if stored_lang:
                        detected_language = stored_lang
                    if stored_dialect:
                        kurdish_dialect = stored_dialect

                # Detect language if not stored or if user is speaking different language
                if KURDISH_DETECTOR_AVAILABLE:
                    lang_result = KurdishDetector.detect_language(content)
                    current_lang = lang_result[0]

                    # If Kurdish detected, determine dialect
                    if current_lang == 'ku':
                        kurdish_result = KurdishDetector.detect_kurdish(
                            content)
                        if kurdish_result:
                            current_dialect, confidence = kurdish_result
                            print(
                                f"[INFO] Kurdish detected: {current_dialect} (confidence: {confidence:.2f})")

                            # Update detected language and dialect
                            detected_language = 'ku'
                            kurdish_dialect = current_dialect

                            # Store language preference for future conversations
                            if self.memory_manager:
                                self.memory_manager.set_user_preference(
                                    user_id, channel_id, 'language', 'ku')
                                self.memory_manager.set_user_preference(
                                    user_id, channel_id, 'kurdish_dialect', current_dialect)

                            # Update statistics with language (will be tracked again below with correct language)
                            pass
                    elif current_lang != detected_language:
                        # Language changed, update preference
                        detected_language = current_lang
                        if self.memory_manager:
                            self.memory_manager.set_user_preference(
                                user_id, channel_id, 'language', current_lang)
                            if current_lang != 'ku':
                                # Clear Kurdish dialect if switching to another language
                                self.memory_manager.set_user_preference(
                                    user_id, channel_id, 'kurdish_dialect', '')

                # Track message statistics with detected language
                if self.statistics_tracker:
                    try:
                        server_id = str(
                            message.guild.id) if message.guild else None
                        self.statistics_tracker.track_message(
                            user_id=user_id,
                            channel_id=channel_id,
                            server_id=server_id,
                            language=detected_language,
                            is_command=False
                        )
                    except Exception as e:
                        print(f"[ERROR] Failed to track message stats: {e}")

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
                        importance_score = ImportanceScorer.score_message(
                            message_dict, is_user_message=True)
                        print(
                            f"[INFO] High importance message detected (score: {importance_score:.2f}): {content[:50]}...")

                    self.memory_manager.add_message(
                        user_id=user_id,
                        channel_id=channel_id,
                        role="user",
                        content=content,
                        importance_score=importance_score  # Will auto-calculate if None
                    )

                    # Try to extract facts from the message automatically
                    self._extract_and_store_facts(user_id, channel_id, content)

                # Get conversation context from database (summaries + recent messages)
                if self.memory_manager:
                    # Get context with increased limit (15 messages)
                    context_limit = self.config.get("max_context_messages", 15)
                    api_messages, summary_texts = self.memory_manager.get_conversation_context(
                        user_id=user_id,
                        channel_id=channel_id,
                        include_summaries=True,
                        limit=context_limit
                    )

                    # Check if this is a follow-up question (within 2 minutes)
                    # Initialize variables first to avoid UnboundLocalError
                    is_follow_up = False
                    follow_up_context = None

                    if api_messages and len(api_messages) > 0:
                        # Get last message timestamp
                        recent_messages = self.memory_manager.get_recent_messages(
                            user_id=user_id,
                            channel_id=channel_id,
                            limit=2
                        )
                        if len(recent_messages) >= 2:
                            last_message_time = datetime.fromisoformat(
                                recent_messages[0]["timestamp"])
                            current_time = datetime.now()
                            time_diff = (
                                # minutes
                                current_time - last_message_time).total_seconds() / 60

                            # If within 2 minutes, mark as follow-up
                            if time_diff <= self.config.get("follow_up_timeout_minutes", 2):
                                is_follow_up = True
                                # Get last assistant response for context
                                for msg in reversed(recent_messages):
                                    if msg["role"] == "assistant":
                                        follow_up_context = msg["content"]
                                        break

                    # Add current user message if not already in context
                    if not api_messages or api_messages[-1]["content"] != content:
                        api_messages.append(
                            {"role": "user", "content": content})

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
                            api_messages.append(
                                {"role": "user", "content": content})
                else:
                    # Fallback to in-memory storage
                    conv_data = self.conversations[message.channel.id]
                    api_messages = list(conv_data['messages'])
                    api_messages.append({"role": "user", "content": content})
                    summary_texts = []
                    conv_data['last_activity'] = datetime.now()
                    # Initialize follow-up variables for fallback path
                    is_follow_up = False
                    follow_up_context = None

                # Check cache first for common questions or identical questions
                cache_key = None
                cached_response = None

                # Check if this is a common question or identical to a previous question
                if self._is_common_question(content) or len(content) < 100:
                    cache_key = self._get_cache_key(content, 'general')
                    cached_response = self._get_cached_response(cache_key)

                # Try Claude API first, fallback to static responses if it fails
                response_text = None
                used_claude = False
                tokens_used = 0
                model_used = "unknown"
                is_cached = False

                # Use cached response if available
                if cached_response:
                    response_text = cached_response['response']
                    tokens_used = cached_response.get(
                        'metadata', {}).get('tokens_used', 0)
                    is_cached = True
                    used_claude = False  # Not using API
                    print(
                        f"[CACHE HIT] Using cached response for: {content[:50]}...")
                else:
                    # Get user facts for personalization
                    user_facts = []
                if self.memory_manager:
                    facts_list = self.memory_manager.get_all_user_facts(
                        user_id, channel_id)
                    user_facts = facts_list

                # Check budget before making API call
                if self.statistics_tracker:
                    budget_settings = self.statistics_tracker.get_budget_settings()
                    budget_amount = budget_settings.get("budget_amount", 0.0)
                    if budget_amount > 0:
                        current_month_cost = self.statistics_tracker.get_current_month_cost()
                        if current_month_cost >= budget_amount:
                            self.budget_exceeded = True
                            if EMBED_HELPER_AVAILABLE:
                                embed = EmbedHelper.create_error_embed(
                                    title="💰 Budget Exceeded",
                                    description=(
                                        "Monthly API budget has been exceeded.\n\n"
                                        "**Current Spending**: ${:.2f}\n"
                                        "**Budget**: ${:.2f}\n\n"
                                        "Please update your budget using `!budget [amount]` or wait until next month."
                                    ).format(current_month_cost, budget_amount)
                                )
                                await message.reply(embed=embed)
                            else:
                                await message.reply(
                                    f"💰 **Budget Exceeded**\n"
                                    f"Monthly API budget has been exceeded.\n"
                                    f"Current: ${current_month_cost:.2f} / Budget: ${budget_amount:.2f}\n"
                                    f"Use `!budget [amount]` to update."
                                )
                            return
                        else:
                            self.budget_exceeded = False

                # Use Multi-API Manager if available, otherwise fallback to Claude handler
                if self.api_manager:
                    print(
                        f"[DEBUG] Using Multi-API Manager for: {content[:50]}...")
                    if detected_language == 'ku':
                        print(
                            f"[DEBUG] Language: Kurdish ({kurdish_dialect or 'general'})")

                    # Add follow-up context to system prompt if this is a follow-up question
                    follow_up_note = None
                    if is_follow_up and follow_up_context:
                        follow_up_note = (
                            f"This appears to be a follow-up question related to the previous conversation. "
                            f"The user's last question was answered with: '{follow_up_context[:200]}...' "
                            f"Reference this context naturally in your response if relevant."
                        )

                    # Build system prompt
                    system_prompt = self._build_system_prompt(
                        user_name=message.author.display_name,
                        summaries=summary_texts if summary_texts else None,
                        detected_language=detected_language,
                        kurdish_dialect=kurdish_dialect,
                        user_facts=user_facts,
                        follow_up_context=follow_up_note
                    )

                    # Call API Manager with intelligent routing
                    result = await self.api_manager.generate_response(
                        messages=api_messages,
                        system_prompt=system_prompt,
                        user_name=message.author.display_name,
                        detected_language=detected_language,
                        has_image=False,
                        query=content,
                        max_tokens=300,
                        temperature=0.7
                    )

                    # Extract provider info for logging
                    provider_used = result.get("provider", "unknown")
                    print(
                        f"[DEBUG] {provider_used.capitalize()} API used for this query")

                elif self.use_claude and self.claude_handler:
                    print(
                        f"[DEBUG] ✅ Claude is available - calling API for: {content[:50]}...")
                    print(
                        f"[DEBUG] use_claude={self.use_claude}, claude_handler={self.claude_handler is not None}")
                    if detected_language == 'ku':
                        print(
                            f"[DEBUG] Language: Kurdish ({kurdish_dialect or 'general'})")
                    # Add follow-up context to system prompt if this is a follow-up question
                    follow_up_note = None
                    if is_follow_up and follow_up_context:
                        follow_up_note = (
                            f"This appears to be a follow-up question related to the previous conversation. "
                            f"The user's last question was answered with: '{follow_up_context[:200]}...' "
                            f"Reference this context naturally in your response if relevant."
                        )

                    # Call Claude API with conversation history, summaries, and user facts
                    result = await self.claude_handler.generate_response(
                        messages=api_messages,
                        user_name=message.author.display_name,
                        summaries=summary_texts if summary_texts else None,
                        detected_language=detected_language,
                        kurdish_dialect=kurdish_dialect,
                        user_facts=user_facts,
                        follow_up_context=follow_up_note
                    )
                    # Add provider info for consistency
                    result["provider"] = "claude"

                    if result["success"]:
                        response_text = result["response"]
                        used_claude = True
                        tokens_used = result.get(
                            "input_tokens", 0) + result.get("output_tokens", result.get("tokens_used", 0))
                        provider_used = result.get("provider", "claude")
                        model_used = f"{provider_used}-api"
                        if self.api_manager:
                            self.claude_responses += 1  # Track as API response
                        else:
                            self.claude_responses += 1
                        print(
                            f"[DEBUG] {provider_used.capitalize()} API success! Response length: {len(response_text)}")

                        # Track API usage with accurate cost calculation
                        if self.statistics_tracker:
                            try:
                                input_tokens = result.get(
                                    "input_tokens", int(tokens_used * 0.7))
                                output_tokens = result.get(
                                    "output_tokens", tokens_used - input_tokens)

                                # Use provider name as model if from API manager
                                if self.api_manager:
                                    model_used = f"{provider_used}-api"

                                self.statistics_tracker.track_api_usage(
                                    tokens_used=tokens_used,
                                    success=True,
                                    model_used=model_used,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    user_id=user_id,
                                    server_id=str(
                                        message.guild.id) if message.guild else None
                                )

                                # Check budget and send alerts if needed
                                await self._check_budget_alerts()
                            except Exception as e:
                                print(
                                    f"[ERROR] Failed to track API usage: {e}")

                        # Track question
                        if self.statistics_tracker:
                            try:
                                server_id = str(
                                    message.guild.id) if message.guild else None
                                self.statistics_tracker.track_question(
                                    user_id=user_id,
                                    question_text=content[:500],
                                    server_id=server_id,
                                    language=detected_language
                                )
                            except Exception as e:
                                print(f"[ERROR] Failed to track question: {e}")
                    else:
                        # API failed after retries
                        error_msg = result.get('error', 'Unknown error')
                        retry_attempts = result.get('retry_attempts', 0)
                        print(
                            f"[ERROR] Claude API failed after {retry_attempts} retries: {error_msg}")

                        # Track API failure
                        if self.statistics_tracker:
                            try:
                                provider_used = result.get(
                                    "provider", "unknown")
                                model_used = f"{provider_used}-api" if self.api_manager else (
                                    self.claude_handler.model if self.claude_handler else "unknown")
                                self.statistics_tracker.track_api_usage(
                                    tokens_used=0,
                                    success=False,
                                    model_used=model_used,
                                    input_tokens=0,
                                    output_tokens=0,
                                    user_id=user_id,
                                    server_id=str(
                                        message.guild.id) if message.guild else None
                                )
                                self.statistics_tracker.track_error(
                                    error_type="API_ERROR",
                                    error_message=f"Failed after {retry_attempts} retries: {error_msg[:150]}",
                                    user_id=user_id,
                                    server_id=str(
                                        message.guild.id) if message.guild else None
                                )
                            except Exception as e:
                                print(f"[ERROR] Failed to track error: {e}")

                        # Check for error alerting
                        self.error_count_recent += 1
                        await self._check_error_alerts()

                        # Use Claude's user-friendly error message if available, otherwise use static fallback
                        if result.get('response') and result.get('user_friendly'):
                            # Claude provided a user-friendly error message
                            response_text = result['response']
                            print(
                                f"[DEBUG] Using Claude's user-friendly error message: {response_text[:50]}...")
                        else:
                            # Fallback to static responses only if Claude didn't provide a message
                            response_text = find_response(
                                content, detected_language, kurdish_dialect)
                            if not response_text or len(response_text) < 10:
                                # Enhanced fallback message
                                if detected_language == 'ku':
                                    if kurdish_dialect == 'Sorani':
                                        response_text = "ببورە، هەندێک کێشە هەیە. تکایە دواتر هەوڵ بدەوە."
                                    else:
                                        response_text = "Bibûre, hinek kêşe heye. Tika duar hewl bide."
                                else:
                                    response_text = (
                                        "I'm having a bit of trouble right now, but I'm still here! "
                                        "Try asking again in a moment, or rephrase your question. "
                                        "I'll do my best to help! 😊"
                                    )
                            print(
                                f"[DEBUG] Using static fallback response: {response_text[:50]}...")

                        model_used = "static_fallback"
                        self.fallback_responses += 1
                else:
                    # Claude not available - this should NOT happen if API key is set correctly
                    print(
                        f"[ERROR] ❌ Claude not available! use_claude={self.use_claude}, handler={self.claude_handler is not None}")
                    print(
                        f"[ERROR] Claude API Key present in env: {bool(os.getenv('CLAUDE_API_KEY'))}")
                    print(f"[ERROR] CLAUDE_AVAILABLE: {CLAUDE_AVAILABLE}")
                    print(
                        f"[ERROR] This means Claude handler failed to initialize. Check Railway logs for initialization errors.")

                    # Try to reinitialize Claude handler if API key is present
                    claude_key = os.getenv("CLAUDE_API_KEY")
                    if claude_key and CLAUDE_AVAILABLE and not self.claude_handler:
                        print(
                            f"[INFO] Attempting to reinitialize Claude handler...")
                        self.claude_handler = self._initialize_claude_handler_with_retry(max_retries=2)
                        if self.claude_handler:
                            self.use_claude = True
                            print(
                                f"[OK] ✅ Claude handler reinitialized successfully!")
                            try:
                            follow_up_note_retry = None
                            if is_follow_up and follow_up_context:
                                follow_up_note_retry = (
                                    f"This appears to be a follow-up question related to the previous conversation. "
                                    f"The user's last question was answered with: '{follow_up_context[:200]}...' "
                                    f"Reference this context naturally in your response if relevant."
                                )
                            result = await self.claude_handler.generate_response(
                                messages=api_messages,
                                user_name=message.author.display_name,
                                summaries=summary_texts if summary_texts else None,
                                detected_language=detected_language,
                                kurdish_dialect=kurdish_dialect,
                                user_facts=user_facts,
                                follow_up_context=follow_up_note_retry
                            )
                            if result["success"]:
                                response_text = result["response"]
                                used_claude = True
                                tokens_used = result.get("tokens_used", 0)
                                model_used = self.claude_handler.model
                                self.claude_responses += 1
                                print(
                                    f"[DEBUG] ✅ Claude API success after reinit! Response length: {len(response_text)}")
                            else:
                                # Use Claude's user-friendly error message
                                if result.get('response') and result.get('user_friendly'):
                                    response_text = result['response']
                                else:
                                    response_text = "I'm having trouble connecting. Please try again in a moment. 😊"
                                model_used = "static_fallback"
                                self.fallback_responses += 1
                            except Exception as e:
                            print(
                                f"[ERROR] Failed to reinitialize Claude: {e}")
                            # Fall through to static response
                            if detected_language == 'ku':
                                response_text = "ببورە، هەندێک کێشە هەیە لە دەستگەیشتن بە AI. تکایە دواتر هەوڵ بدەوە یان بە زمانی ئینگلیزی بپرسە."
                            else:
                                response_text = (
                                    "I'm currently experiencing issues connecting to the AI service. "
                                    "Please try again in a moment, or use `!help` to see available commands. "
                                    "If this persists, the Claude API key may need to be configured."
                                )
                            model_used = "static_fallback"
                            self.fallback_responses += 1
                    else:
                        # No API key or module not available
                        if detected_language == 'ku':
                            response_text = "ببورە، هەندێک کێشە هەیە لە دەستگەیشتن بە AI. تکایە دواتر هەوڵ بدەوە یان بە زمانی ئینگلیزی بپرسە."
                        else:
                            response_text = (
                                "I'm currently experiencing issues connecting to the AI service. "
                                "Please try again in a moment, or use `!help` to see available commands. "
                                "If this persists, the Claude API key may need to be configured."
                            )
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
                    conv_data['messages'].append(
                        {"role": "assistant", "content": response_text})
                    # Keep last N messages
                    max_context = self.config.get("max_context_messages", 15)
                    if len(conv_data['messages']) > max_context:
                        conv_data['messages'] = deque(
                            list(conv_data['messages'])[-max_context:],
                            maxlen=max_context
                        )

                # Calculate response time and format it
                response_time = None
                response_time_text = None
                if start_time and self.response_tracker:
                    response_time = time.time() - start_time
                    response_time_text = f"⏱️ Responded in {self.response_tracker.format_response_time(response_time)}"

                    # Record response time
                    self.response_tracker.record_response_time(
                        response_time=response_time,
                        user_id=user_id,
                        channel_id=channel_id,
                        used_claude=used_claude,
                        model_used=model_used,
                        tokens_used=tokens_used
                    )

                # Add human-like delay for very short responses (< 50 chars)
                # This makes the bot feel more natural
                if len(response_text) < 50 and response_time and response_time < 0.5:
                    # Add random delay between 0.5-1.5 seconds for short responses
                    delay = random.uniform(0.5, 1.5)
                    await asyncio.sleep(delay)
                    # Update response time to include delay
                    if start_time and self.response_tracker:
                        response_time = time.time() - start_time
                        response_time_text = f"⏱️ Responded in {self.response_tracker.format_response_time(response_time)}"

                # Generate question suggestions (only for successful Claude responses)
                question_suggestions = []
                if used_claude and self.use_claude and self.claude_handler:
                    try:
                        # Get recent conversation history for context
                        recent_history = api_messages[-10:] if api_messages else []

                        question_suggestions = await self.claude_handler.generate_question_suggestions(
                            user_question=content,
                            bot_answer=response_text,
                            conversation_history=recent_history,
                            user_facts=user_facts,
                            detected_language=detected_language,
                            kurdish_dialect=kurdish_dialect
                        )
                    except Exception as e:
                        print(
                            f"[ERROR] Failed to generate question suggestions: {e}")
                        question_suggestions = []

                # Create embed for AI response
                if EMBED_HELPER_AVAILABLE:
                    # Split long content if needed
                    content_chunks = EmbedHelper.split_long_content(
                        response_text, max_length=4096)

                    # Create main embed
                    embed = EmbedHelper.create_ai_response_embed(
                        content=content_chunks[0],
                        user_name=message.author.display_name,
                        user_avatar=message.author.display_avatar.url if hasattr(
                            message.author, 'display_avatar') else None,
                        response_time=response_time_text
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
                        suggestions_text = "\n".join(
                            [f"❓ {q}" for q in question_suggestions])
                        embed.add_field(
                            name="💡 You might also want to know:",
                            value=suggestions_text[:1024],
                            inline=False
                        )

                    # Add API provider info to footer if using API manager
                    if self.api_manager and 'result' in locals() and result.get("provider"):
                        provider_raw = result.get("provider", "unknown").lower()
                        # Special attribution for DeepSeek and Gemini
                        if provider_raw == "deepseek":
                            provider_name = "🧮 DeepSeek R1"
                        elif provider_raw == "gemini":
                            provider_name = "⚡ Gemini 2.0 Flash"
                        else:
                            provider_name = result.get("provider", "unknown").capitalize() + " API"
                        current_footer = embed.footer.text if embed.footer else ""
                        if current_footer:
                            embed.set_footer(
                                text=f"{current_footer} | Powered by {provider_name}")
                        else:
                            embed.set_footer(
                                text=f"Powered by {provider_name}")

                    # Send embed response
                    response_sent = False
                    try:
                        await message.reply(embed=embed)
                        response_sent = True
                    except Exception as send_error:
                        print(
                            f"[ERROR] Failed to send embed response: {send_error}")
                        # Fallback to text
                        try:
                            response_text_with_time = response_text
                            if response_time_text:
                                if len(response_text) + len(response_time_text) + 2 > 2000:
                                    max_length = 2000 - \
                                        len(response_time_text) - 3
                                    response_text_with_time = response_text[:max_length] + "..."
                                response_text_with_time += f"\n\n{response_time_text}"

                            # Add suggestions to text response
                            if question_suggestions:
                                response_text_with_time += "\n\n💡 **You might also want to know:**\n"
                                for q in question_suggestions:
                                    response_text_with_time += f"❓ {q}\n"

                            # Add API provider info to footer if using API manager
                            if self.api_manager and result.get("provider"):
                                provider_raw = result.get("provider", "unknown").lower()
                                # Special attribution for DeepSeek and Gemini
                                if provider_raw == "deepseek":
                                    response_text_with_time += "\n\n🧮 *Powered by DeepSeek R1*"
                                elif provider_raw == "gemini":
                                    response_text_with_time += "\n\n⚡ *Powered by Gemini 2.0 Flash*"
                                else:
                                    provider_name = result.get("provider", "unknown").capitalize()
                                    response_text_with_time += f"\n\n*Powered by {provider_name} API*"

                            await message.reply(response_text_with_time)
                            response_sent = True
                        except:
                            try:
                                await message.channel.send(response_text_with_time if 'response_text_with_time' in locals() else response_text)
                                response_sent = True
                            except:
                                pass
                else:
                    # Fallback: append response time to text
                    if response_time_text:
                        if len(response_text) + len(response_time_text) + 2 > 2000:
                            max_length = 2000 - len(response_time_text) - 3
                            response_text = response_text[:max_length] + "..."
                        response_text += f"\n\n{response_time_text}"

                    # Add API provider info to footer if using API manager
                    if self.api_manager and 'result' in locals() and result.get("provider"):
                        provider_raw = result.get("provider", "unknown").lower()
                        # Special attribution for DeepSeek and Gemini
                        if provider_raw == "deepseek":
                            footer_text = "\n\n🧮 *Powered by DeepSeek R1*"
                        elif provider_raw == "gemini":
                            footer_text = "\n\n⚡ *Powered by Gemini 2.0 Flash*"
                        else:
                            provider_name = result.get("provider", "unknown").capitalize()
                            footer_text = f"\n\n*Powered by {provider_name} API*"
                        if len(response_text) + len(footer_text) <= 2000:
                            response_text += footer_text

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
                            print(
                                f"[OK] Conversation logged: User={message.author.display_name}, Tokens={tokens_used}, Model={model_used}")
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
                            self._log_message(
                                message, response_text, used_claude)
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
                    # Detect language for fallback
                    detected_lang = 'en'
                    kurdish_dial = None
                    if KURDISH_DETECTOR_AVAILABLE:
                        lang_result = KurdishDetector.detect_language(
                            message.content)
                        detected_lang = lang_result[0]
                        if detected_lang == 'ku':
                            kurdish_result = KurdishDetector.detect_kurdish(
                                message.content)
                            if kurdish_result:
                                kurdish_dial, _ = kurdish_result
                    fallback = find_response(
                        message.content, detected_lang, kurdish_dial)
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_ai_response_embed(
                            content=fallback,
                            user_name=message.author.display_name if hasattr(
                                message, 'author') else None
                        )
                        await message.channel.send(embed=embed)
                    else:
                        await message.channel.send(fallback)
                except Exception as fallback_error:
                    print(f"[ERROR] Fallback also failed: {fallback_error}")
                    # Last resort - only if nothing was sent
                    try:
                        if EMBED_HELPER_AVAILABLE:
                            embed = EmbedHelper.create_error_embed(
                                title="⚠️ Technical Difficulties",
                                description="I'm having some technical difficulties. Please try again in a moment!"
                            )
                            await message.channel.send(embed=embed)
                        else:
                            await message.channel.send("I'm having some technical difficulties. Please try again in a moment!")
                    except:
                        pass  # If even this fails, give up

    def _log_message(self, message: discord.Message, response: str, used_claude: bool):
        """Log conversation to file"""
        try:
            log_file = self.config.get("log_file", "bot.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            server = message.guild.name if message.guild else "DM"
            channel = message.channel.name if hasattr(
                message.channel, 'name') else "DM"
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
            color=EmbedColors.BLUE if EMBED_HELPER_AVAILABLE else discord.Color.blue()
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
                f"`{prefix}export summaries` - Export summaries to CSV\n"
                f"`{prefix}stats` - Show your personal statistics\n"
                f"`{prefix}serverstats` - Show server statistics (Admin)\n"
                f"`{prefix}globalstats` - Show global statistics (Owner)\n"
                f"`{prefix}errors` - Show recent errors (Owner)\n"
                f"`{prefix}retry` - Retry last failed request (Owner)\n"
                f"`{prefix}costs` - Show API spending breakdown\n"
                f"`{prefix}budget [amount]` - Set monthly budget (Owner)\n"
                f"\n**Image Analysis:**\n"
                f"Send an image with @mention to analyze it!\n"
                f"Examples: 'What's in this image?', 'Describe this picture', 'Read the text'\n"
                f"\n**🎮 Fun & Games:**\n"
                f"`{prefix}joke` - AI-generated jokes\n"
                f"`{prefix}story [topic]` - Generate creative stories\n"
                f"`{prefix}riddle` - Get a riddle (use `{prefix}answer` to guess)\n"
                f"`{prefix}fact` - Random interesting facts\n"
                f"`{prefix}quote` - Inspirational quotes\n"
                f"`{prefix}8ball [question]` - Magic 8-ball\n"
                f"`{prefix}trivia` - Trivia quiz (use `{prefix}guess` to answer)\n"
                f"`{prefix}wouldyourather` - Would you rather questions\n"
                f"`{prefix}dadjoke` - Dad jokes\n"
                f"`{prefix}roast [@user]` - Friendly roast\n"
                f"\n**🌐 Translation:**\n"
                f"`{prefix}translate [text]` - Auto-translate to English\n"
                f"`{prefix}translate [lang] [text]` - Translate to specific language\n"
                f"`{prefix}detect [text]` - Detect language\n"
                f"`{prefix}kurdish [text]` - Translate to Kurdish\n"
                f"`{prefix}english [text]` - Translate to English\n"
                f"`{prefix}autotranslate [on/off]` - Auto-translation mode (Admin)\n"
                f"\n**🛡️ Moderation (Admin):**\n"
                f"`{prefix}warn @user [reason]` - Warn a user\n"
                f"`{prefix}mute @user [time] [reason]` - Mute a user\n"
                f"`{prefix}ban @user [reason]` - Ban a user from bot\n"
                f"`{prefix}modlogs [limit]` - Show moderation history\n"
                f"`{prefix}blacklist [add/remove/list] [word]` - Manage blacklist\n"
                f"`{prefix}whitelist [add/remove/list] @user` - Manage whitelist\n"
                f"\n**🔐 Permissions:**\n"
                f"`{prefix}permissions` - Show your permission level\n"
                f"`{prefix}setpremium @user [add/remove]` - Grant premium (Owner)\n"
                f"`{prefix}cachestats` - Show cache statistics (Owner)\n"
                f"`{prefix}clearcache` - Clear response cache (Owner)\n"
                f"\n**🔗 Webhooks (Admin):**\n"
                f"`{prefix}webhook add [url] [channel]` - Add webhook integration\n"
                f"`{prefix}webhook list` - List webhooks\n"
                f"`{prefix}webhook remove [id]` - Remove webhook\n"
                f"\n**💾 Backup (Admin/Owner):**\n"
                f"`{prefix}backup now` - Create backup now\n"
                f"`{prefix}backups list` - List available backups\n"
                f"`{prefix}restore [id]` - Restore backup (Owner)\n"
                f"\n**Memory & History:**\n"
                f"`{prefix}history [user]` - Show conversation history\n"
                f"`{prefix}summarize [@user]` - Summarize conversation"
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
        if EMBED_HELPER_AVAILABLE:
            # Determine color based on latency
            if latency < 100:
                color = EmbedColors.GREEN
                status = "Excellent"
            elif latency < 200:
                color = EmbedColors.BLUE
                status = "Good"
            else:
                color = EmbedColors.YELLOW
                status = "Slow"

            embed = discord.Embed(
                title="🏓 Pong!",
                description=f"Latency: **{latency}ms**\nStatus: **{status}**",
                color=color
            )
            embed.set_footer(text="Discord API latency")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Pong! 🏓 Latency: {latency}ms")

    @commands.command(name="info")
    async def info_command(self, ctx: commands.Context):
        """Show bot information"""
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds

        embed = discord.Embed(
            title="🤖 AI Boot Information",
            color=EmbedColors.BLUE if EMBED_HELPER_AVAILABLE else discord.Color.green()
        )

        embed.add_field(name="Bot Name", value="AI Boot", inline=True)
        embed.add_field(name="Status", value="Online ✅", inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Messages Processed", value=str(
            self.message_count), inline=True)
        embed.add_field(
            name="Latency", value=f"{round(self.latency * 1000)}ms", inline=True)
        embed.add_field(name="Servers", value=str(
            len(self.guilds)), inline=True)

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

        embed.set_footer(
            text=f"Bot started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
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
            color=EmbedColors.BLUE if EMBED_HELPER_AVAILABLE else discord.Color.blue()
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
    async def export_command(self, ctx: commands.Context, export_type: Optional[str] = None):
        """
        Export conversations or summaries to CSV file

        Usage:
        !export - Export conversations
        !export summaries - Export summaries
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if export_type and export_type.lower() in ["summaries", "summary"]:
                # Export summaries
                if not self.memory_manager:
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_error_embed(
                            title="❌ Export Failed",
                            description="Memory manager not available!"
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("❌ Memory manager not available!")
                    return

                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_info_embed(
                        title="📊 Exporting Summaries",
                        description="Exporting conversation summaries to CSV... This may take a moment.",
                        footer="Please wait..."
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("📊 Exporting summaries to CSV... This may take a moment.")

                filename = f"summaries_export_{timestamp}.csv"
                filepath = self.memory_manager.export_summaries_to_csv(
                    output_path=filename)

                # Send file to Discord
                with open(filepath, 'rb') as f:
                    file = discord.File(f, filename=filename)
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_success_embed(
                            title="✅ Export Complete",
                            description=f"All summaries exported successfully!",
                            details=f"📁 File: `{filename}`"
                        )
                        await ctx.send(embed=embed, file=file)
                    else:
                        await ctx.send(
                            f"✅ **Export Complete!**\n"
                            f"📁 File: `{filename}`\n"
                            f"📊 All summaries exported successfully!",
                            file=file
                        )

                print(f"[OK] Exported summaries to {filepath}")
            else:
                # Export conversations (default)
                if not self.conversation_logger:
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_error_embed(
                            title="❌ Export Failed",
                            description="Conversation logger not available!"
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("❌ Conversation logger not available!")
                    return

                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_info_embed(
                        title="📊 Exporting Conversations",
                        description="Exporting conversations to CSV... This may take a moment.",
                        footer="Please wait..."
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("📊 Exporting conversations to CSV... This may take a moment.")

                filename = f"conversation_export_{timestamp}.csv"
                filepath = self.conversation_logger.export_to_csv(
                    output_path=filename)

                # Send file to Discord
                with open(filepath, 'rb') as f:
                    file = discord.File(f, filename=filename)
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_success_embed(
                            title="✅ Export Complete",
                            description=f"All conversations exported successfully!",
                            details=f"📁 File: `{filename}`"
                        )
                        await ctx.send(embed=embed, file=file)
                    else:
                        await ctx.send(
                            f"✅ **Export Complete!**\n"
                            f"📁 File: `{filename}`\n"
                            f"📊 All conversations exported successfully!",
                            file=file
                        )

                print(f"[OK] Exported conversations to {filepath}")
        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Export Failed",
                    description="Error exporting data",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error exporting: {str(e)}")
            print(f"[ERROR] Export failed: {e}")
            import traceback
            traceback.print_exc()

    @commands.command(name="stats")
    async def stats_command(self, ctx: commands.Context):
        """
        Show your personal statistics

        Usage:
        !stats - Show your personal stats (messages, activity, etc.)
        """
        if not self.statistics_tracker:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Stats Unavailable",
                    description="Statistics tracker not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Statistics tracker not available!")
            return

        try:
            user_id = str(ctx.author.id)
            stats = self.statistics_tracker.get_personal_stats(
                user_id, days=30)

            embed = discord.Embed(
                title=f"📊 Personal Statistics - {ctx.author.display_name}",
                color=EmbedColors.BLUE if EMBED_HELPER_AVAILABLE else discord.Color.blue()
            )

            # Total messages
            embed.add_field(
                name="💬 Total Messages (30 days)",
                value=f"{stats['total_messages']:,}",
                inline=True
            )

            # Retention info
            if stats.get('retention'):
                retention = stats['retention']
                embed.add_field(
                    name="📅 Account Info",
                    value=(
                        f"**First Seen**: {retention.get('first_seen', 'N/A')[:10]}\n"
                        f"**Last Seen**: {retention.get('last_seen', 'N/A')[:10]}\n"
                        f"**Days Active**: {retention.get('days_active', 0)}"
                    ),
                    inline=True
                )

            # Messages per day chart
            if stats['messages_per_day']:
                chart = self.statistics_tracker.create_time_chart(
                    stats['messages_per_day'], "Messages")
                embed.add_field(
                    name="📈 Activity (Last 7 Days)",
                    value=f"```\n{chart}\n```",
                    inline=False
                )

            # Most active hours
            if stats['active_hours']:
                hours_text = "\n".join([
                    f"**{hour:02d}:00**: {count:,} messages"
                    for hour, count in sorted(stats['active_hours'].items(), key=lambda x: x[1], reverse=True)[:5]
                ])
                embed.add_field(
                    name="🕐 Most Active Hours",
                    value=hours_text,
                    inline=False
                )

            # Language distribution
            if stats['language_distribution']:
                lang_text = "\n".join([
                    f"**{lang.upper()}**: {count:,} messages"
                    for lang, count in sorted(stats['language_distribution'].items(), key=lambda x: x[1], reverse=True)[:5]
                ])
                embed.add_field(
                    name="🌍 Language Distribution",
                    value=lang_text,
                    inline=False
                )

            # Commands used
            if stats['commands_used']:
                cmd_text = "\n".join([
                    f"`{cmd}`: {count:,} times"
                    for cmd, count in sorted(stats['commands_used'].items(), key=lambda x: x[1], reverse=True)[:5]
                ])
                embed.add_field(
                    name="⚙️ Commands Used",
                    value=cmd_text,
                    inline=False
                )

            # Response time stats
            if self.response_tracker:
                response_stats = self.response_tracker.get_stats()
                if response_stats.get('average_all_time') != "N/A":
                    embed.add_field(
                        name="⏱️ Response Times",
                        value=(
                            f"**Average**: {response_stats.get('average_all_time', 'N/A')}s\n"
                            f"**Fastest**: {response_stats.get('fastest', 'N/A')}s\n"
                            f"**Slowest**: {response_stats.get('slowest', 'N/A')}s"
                        ),
                        inline=False
                    )

            embed.set_footer(text="Statistics for last 30 days")
            await ctx.send(embed=embed)
        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Stats Error",
                    description="Error getting statistics",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error getting statistics: {str(e)}")
            print(f"[ERROR] Stats command failed: {e}")
            import traceback
            traceback.print_exc()

    @commands.command(name="serverstats")
    @commands.has_permissions(administrator=True)
    async def serverstats_command(self, ctx: commands.Context):
        """
        Show server-wide statistics (Admin only)

        Usage:
        !serverstats - Show statistics for this server
        """
        if not self.statistics_tracker:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Stats Unavailable",
                    description="Statistics tracker not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Statistics tracker not available!")
            return

        if not ctx.guild:
            await ctx.send("❌ This command can only be used in a server!")
            return

        try:
            server_id = str(ctx.guild.id)
            stats = self.statistics_tracker.get_server_stats(
                server_id, days=30)

            embed = discord.Embed(
                title=f"📊 Server Statistics - {ctx.guild.name}",
                color=EmbedColors.BLUE if EMBED_HELPER_AVAILABLE else discord.Color.blue()
            )

            # Overview
            embed.add_field(
                name="📊 Overview",
                value=(
                    f"**Total Messages**: {stats['total_messages']:,}\n"
                    f"**Unique Users**: {stats['unique_users']:,}\n"
                    f"**Returning Users**: {stats['returning_users']:,}"
                ),
                inline=False
            )

            # Messages per day chart
            if stats['messages_per_day']:
                chart = self.statistics_tracker.create_time_chart(
                    stats['messages_per_day'], "Messages")
                embed.add_field(
                    name="📈 Activity (Last 7 Days)",
                    value=f"```\n{chart}\n```",
                    inline=False
                )

            # Most active users
            if stats['active_users']:
                users_text = ""
                for user_id, count in list(stats['active_users'].items())[:10]:
                    try:
                        user = await self.fetch_user(int(user_id))
                        username = user.display_name if user else f"User {user_id}"
                    except:
                        username = f"User {user_id}"
                    users_text += f"**{username}**: {count:,} messages\n"

                embed.add_field(
                    name="👥 Most Active Users",
                    value=users_text[:1024],
                    inline=False
                )

            # Most active hours
            if stats['active_hours']:
                hours_text = "\n".join([
                    f"**{hour:02d}:00**: {count:,} messages"
                    for hour, count in sorted(stats['active_hours'].items(), key=lambda x: x[1], reverse=True)[:5]
                ])
                embed.add_field(
                    name="🕐 Most Active Hours",
                    value=hours_text,
                    inline=False
                )

            # Language distribution
            if stats['language_distribution']:
                lang_text = "\n".join([
                    f"**{lang.upper()}**: {count:,} messages ({count/stats['total_messages']*100:.1f}%)"
                    for lang, count in sorted(stats['language_distribution'].items(), key=lambda x: x[1], reverse=True)[:5]
                ])
                embed.add_field(
                    name="🌍 Language Distribution",
                    value=lang_text,
                    inline=False
                )

            # Popular questions
            if stats['popular_questions']:
                questions_text = "\n".join([
                    f"**{i+1}.** {q[:80]}... ({count}x)"
                    for i, (q, count) in enumerate(list(stats['popular_questions'].items())[:5])
                ])
                embed.add_field(
                    name="❓ Popular Questions",
                    value=questions_text[:1024],
                    inline=False
                )

            # Commands used
            if stats['commands_used']:
                cmd_text = "\n".join([
                    f"`{cmd}`: {count:,} times"
                    for cmd, count in sorted(stats['commands_used'].items(), key=lambda x: x[1], reverse=True)[:5]
                ])
                embed.add_field(
                    name="⚙️ Commands Used",
                    value=cmd_text,
                    inline=False
                )

            embed.set_footer(text="Statistics for last 30 days | Admin only")
            await ctx.send(embed=embed)
        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Stats Error",
                    description="Error getting server statistics",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error getting statistics: {str(e)}")
            print(f"[ERROR] Serverstats command failed: {e}")
            import traceback
            traceback.print_exc()

    @commands.command(name="globalstats")
    @commands.is_owner()
    async def globalstats_command(self, ctx: commands.Context):
        """
        Show global statistics across all servers (Owner only)

        Usage:
        !globalstats - Show statistics for all servers
        """
        if not self.statistics_tracker:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Stats Unavailable",
                    description="Statistics tracker not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Statistics tracker not available!")
            return

        try:
            stats = self.statistics_tracker.get_global_stats(days=30)

            embed = discord.Embed(
                title="📊 Global Statistics (All Servers)",
                color=EmbedColors.BLUE if EMBED_HELPER_AVAILABLE else discord.Color.blue()
            )

            # Overview
            embed.add_field(
                name="📊 Overview",
                value=(
                    f"**Total Messages**: {stats['total_messages']:,}\n"
                    f"**Unique Users**: {stats['unique_users']:,}\n"
                    f"**Total Servers**: {stats['total_servers']:,}\n"
                    f"**Returning Users**: {stats['returning_users']:,}"
                ),
                inline=False
            )

            # Messages per day chart
            if stats['messages_per_day']:
                chart = self.statistics_tracker.create_time_chart(
                    stats['messages_per_day'], "Messages")
                embed.add_field(
                    name="📈 Activity (Last 7 Days)",
                    value=f"```\n{chart}\n```",
                    inline=False
                )

            # API costs
            if stats.get('api_costs'):
                total_cost = stats.get('total_api_cost', 0.0)
                total_tokens = stats.get('total_tokens', 0)
                total_calls = stats.get('total_api_calls', 0)
                error_rate = stats.get('error_rate', 0.0)

                embed.add_field(
                    name="💰 API Usage & Costs",
                    value=(
                        f"**Total Cost**: ${total_cost:.2f}\n"
                        f"**Total Tokens**: {total_tokens:,}\n"
                        f"**API Calls**: {total_calls:,}\n"
                        f"**Error Rate**: {error_rate:.2f}%"
                    ),
                    inline=False
                )

                # Daily costs chart
                if len(stats['api_costs']) > 0:
                    daily_costs = {cost['date']: cost['cost']
                                   for cost in stats['api_costs'][-7:]}
                    cost_chart = self.statistics_tracker.create_time_chart(
                        daily_costs, "Cost")
                    embed.add_field(
                        name="💵 Daily API Costs (Last 7 Days)",
                        value=f"```\n{cost_chart}\n```",
                        inline=False
                    )

            # Language distribution
            if stats['language_distribution']:
                lang_text = "\n".join([
                    f"**{lang.upper()}**: {count:,} messages ({count/stats['total_messages']*100:.1f}%)"
                    for lang, count in sorted(stats['language_distribution'].items(), key=lambda x: x[1], reverse=True)[:5]
                ])
                embed.add_field(
                    name="🌍 Language Distribution",
                    value=lang_text,
                    inline=False
                )

            # Most active servers
            if stats['active_servers']:
                servers_text = ""
                for server_id, count in list(stats['active_servers'].items())[:5]:
                    try:
                        guild = self.get_guild(int(server_id))
                        server_name = guild.name if guild else f"Server {server_id}"
                    except:
                        server_name = f"Server {server_id}"
                    servers_text += f"**{server_name}**: {count:,} messages\n"

                embed.add_field(
                    name="🏆 Most Active Servers",
                    value=servers_text[:1024],
                    inline=False
                )

            # Commands used
            if stats['commands_used']:
                cmd_text = "\n".join([
                    f"`{cmd}`: {count:,} times"
                    for cmd, count in sorted(stats['commands_used'].items(), key=lambda x: x[1], reverse=True)[:5]
                ])
                embed.add_field(
                    name="⚙️ Commands Used",
                    value=cmd_text,
                    inline=False
                )

            # Error stats
            total_errors = stats.get('total_errors', 0)
            if total_errors > 0:
                embed.add_field(
                    name="⚠️ Errors",
                    value=f"**Total Errors**: {total_errors:,}\n**Error Rate**: {stats.get('error_rate', 0.0):.2f}%",
                    inline=False
                )

            embed.set_footer(text="Statistics for last 30 days | Owner only")
            await ctx.send(embed=embed)
        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Stats Error",
                    description="Error getting global statistics",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error getting statistics: {str(e)}")
            print(f"[ERROR] Globalstats command failed: {e}")
            import traceback
            traceback.print_exc()

    @commands.command(name="errors")
    @commands.is_owner()
    async def errors_command(self, ctx: commands.Context, limit: Optional[int] = 10):
        """
        Show recent errors (Owner only)

        Usage:
        !errors - Show last 10 errors
        !errors 20 - Show last 20 errors
        """
        if not self.statistics_tracker:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Errors Unavailable",
                    description="Statistics tracker not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Statistics tracker not available!")
            return

        try:
            import sqlite3
            conn = sqlite3.connect(self.statistics_tracker.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT error_type, error_message, user_id, server_id, timestamp
                FROM error_stats
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit or 10,))

            errors = cursor.fetchall()
            conn.close()

            if not errors:
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_info_embed(
                        title="✅ No Recent Errors",
                        description="No errors recorded in the last period!",
                        footer="Great job keeping the bot running smoothly!"
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("✅ No recent errors!")
                return

            embed = discord.Embed(
                title=f"⚠️ Recent Errors (Last {len(errors)})",
                color=EmbedColors.RED if EMBED_HELPER_AVAILABLE else discord.Color.red()
            )

            # Group errors by type
            error_types = {}
            for error_type, error_msg, user_id, server_id, timestamp in errors:
                if error_type not in error_types:
                    error_types[error_type] = []
                error_types[error_type].append({
                    "message": error_msg[:100],
                    "user_id": user_id,
                    "server_id": server_id,
                    "timestamp": timestamp
                })

            # Show error summary
            for error_type, error_list in list(error_types.items())[:5]:
                count = len(error_list)
                latest = error_list[0]
                embed.add_field(
                    name=f"🔴 {error_type} ({count}x)",
                    value=(
                        f"**Latest**: {latest['message']}\n"
                        f"**Time**: {latest['timestamp'][:19]}\n"
                        f"**User**: {latest['user_id'] or 'N/A'}"
                    ),
                    inline=False
                )

            embed.set_footer(
                text="Owner only | Use !retry to retry last failed request")
            await ctx.send(embed=embed)

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Error",
                    description="Error retrieving error logs",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error: {str(e)}")
            print(f"[ERROR] Errors command failed: {e}")
            import traceback
            traceback.print_exc()

    @commands.command(name="retry")
    @commands.is_owner()
    async def retry_command(self, ctx: commands.Context):
        """
        Manually retry the last failed Claude API request (Owner only)

        Usage:
        !retry - Retry last failed request
        """
        if not self.use_claude or not self.claude_handler:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Retry Unavailable",
                    description="Claude API handler not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Claude API handler not available!")
            return

        try:
            if not self.claude_handler.last_failed_request:
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_info_embed(
                        title="ℹ️ No Failed Request",
                        description="No failed request to retry. All requests are successful!",
                        footer="Great job!"
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("ℹ️ No failed request to retry!")
                return

            # Show processing message
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="🔄 Retrying Request",
                    description="Retrying last failed Claude API request...",
                    footer="Please wait..."
                )
                processing_msg = await ctx.send(embed=embed)
            else:
                processing_msg = await ctx.send("🔄 Retrying last failed request...")

            # Retry the request
            result = await self.claude_handler.retry_last_failed_request()

            if result["success"]:
                response_text = result["response"]
                cached_note = " (from cache)" if result.get("cached") else ""
                fallback_note = " (fallback)" if result.get("fallback") else ""

                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_success_embed(
                        title="✅ Retry Successful",
                        description=f"Request succeeded!{cached_note}{fallback_note}",
                        details=f"**Response**: {response_text[:500]}..."
                    )
                    await processing_msg.edit(embed=embed)
                else:
                    await processing_msg.edit(content=f"✅ **Retry Successful!**\n\n{response_text[:1000]}")
            else:
                error_msg = result.get("error", "Unknown error")
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_error_embed(
                        title="❌ Retry Failed",
                        description="Retry attempt failed",
                        error_details=error_msg
                    )
                    await processing_msg.edit(embed=embed)
                else:
                    await processing_msg.edit(content=f"❌ **Retry Failed**: {error_msg}")

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Retry Error",
                    description="Error during retry",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error: {str(e)}")
            print(f"[ERROR] Retry command failed: {e}")
            import traceback
            traceback.print_exc()

    @commands.command(name="costs")
    async def costs_command(self, ctx: commands.Context, period: Optional[str] = None):
        """
        Show API spending and cost breakdown

        Usage:
        !costs - Show current month costs
        !costs week - Show last 7 days
        !costs month - Show last 30 days
        """
        if not self.statistics_tracker:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Costs Unavailable",
                    description="Statistics tracker not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Statistics tracker not available!")
            return

        try:
            # Determine period
            if period and period.lower() in ["week", "7", "7d"]:
                days = 7
                period_name = "Last 7 Days"
            elif period and period.lower() in ["month", "30", "30d"]:
                days = 30
                period_name = "Last 30 Days"
            else:
                days = 30
                period_name = "Current Month"

            # Get cost breakdown
            breakdown = self.statistics_tracker.get_cost_breakdown(days=days)

            # Get budget info
            budget_settings = self.statistics_tracker.get_budget_settings()
            budget_amount = budget_settings.get("budget_amount", 0.0)
            current_month_cost = self.statistics_tracker.get_current_month_cost()

            embed = discord.Embed(
                title="💰 API Costs & Spending",
                color=EmbedColors.BLUE if EMBED_HELPER_AVAILABLE else discord.Color.blue()
            )

            # Overview
            overview_text = (
                f"**Total Cost**: ${breakdown['total_cost']:.2f}\n"
                f"**Total Tokens**: {breakdown['total_tokens']:,}\n"
                f"**Input Tokens**: {breakdown['total_input_tokens']:,}\n"
                f"**Output Tokens**: {breakdown['total_output_tokens']:,}\n"
                f"**API Calls**: {breakdown['total_calls']:,}\n"
                f"**Success Rate**: {(breakdown['successful_calls']/breakdown['total_calls']*100) if breakdown['total_calls'] > 0 else 0:.1f}%"
            )

            embed.add_field(
                name=f"📊 Overview ({period_name})",
                value=overview_text,
                inline=False
            )

            # Budget info
            if budget_amount > 0:
                usage_percent = (current_month_cost / budget_amount) * 100
                budget_text = (
                    f"**Monthly Budget**: ${budget_amount:.2f}\n"
                    f"**Current Month**: ${current_month_cost:.2f}\n"
                    f"**Usage**: {usage_percent:.1f}%\n"
                    f"**Remaining**: ${max(0, budget_amount - current_month_cost):.2f}"
                )

                # Color code based on usage
                if usage_percent >= 90:
                    budget_color = "🚨"
                elif usage_percent >= 75:
                    budget_color = "⚠️"
                elif usage_percent >= 50:
                    budget_color = "💛"
                else:
                    budget_color = "✅"

                embed.add_field(
                    name=f"{budget_color} Budget Status",
                    value=budget_text,
                    inline=False
                )

            # Daily costs chart
            if breakdown['daily_costs']:
                chart = self.statistics_tracker.create_time_chart(
                    breakdown['daily_costs'], "Cost")
                embed.add_field(
                    name="📈 Daily Costs (Last 7 Days)",
                    value=f"```\n{chart}\n```",
                    inline=False
                )

            # Top users
            if breakdown['top_users']:
                users_text = ""
                for user_id, cost in list(breakdown['top_users'].items())[:5]:
                    try:
                        user = await self.fetch_user(int(user_id))
                        username = user.display_name if user else f"User {user_id[:8]}"
                    except:
                        username = f"User {user_id[:8]}"
                    users_text += f"**{username}**: ${cost:.2f}\n"

                if users_text:
                    embed.add_field(
                        name="👥 Top Users by Cost",
                        value=users_text[:1024],
                        inline=False
                    )

            # Top servers
            if breakdown['top_servers']:
                servers_text = ""
                for server_id, cost in list(breakdown['top_servers'].items())[:5]:
                    try:
                        guild = self.get_guild(int(server_id))
                        server_name = guild.name if guild else f"Server {server_id[:8]}"
                    except:
                        server_name = f"Server {server_id[:8]}"
                    servers_text += f"**{server_name}**: ${cost:.2f}\n"

                if servers_text:
                    embed.add_field(
                        name="🏆 Top Servers by Cost",
                        value=servers_text[:1024],
                        inline=False
                    )

            embed.set_footer(
                text=f"Period: {period_name} | Use !budget to set monthly budget")
            await ctx.send(embed=embed)

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Error",
                    description="Error retrieving costs",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error: {str(e)}")
            print(f"[ERROR] Costs command failed: {e}")
            import traceback
            traceback.print_exc()

    @commands.command(name="budget")
    @commands.is_owner()
    async def budget_command(self, ctx: commands.Context, amount: Optional[float] = None):
        """
        Set or view monthly API budget (Owner only)

        Usage:
        !budget - Show current budget
        !budget 50 - Set monthly budget to $50
        """
        if not self.statistics_tracker:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Budget Unavailable",
                    description="Statistics tracker not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Statistics tracker not available!")
            return

        try:
            budget_settings = self.statistics_tracker.get_budget_settings()
            current_budget = budget_settings.get("budget_amount", 0.0)
            current_month_cost = self.statistics_tracker.get_current_month_cost()

            if amount is None:
                # Show current budget
                if current_budget <= 0:
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="💰 Budget Settings",
                            description="No monthly budget set.",
                            details="Use `!budget [amount]` to set a monthly budget.\nExample: `!budget 50` sets budget to $50/month"
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("💰 **No budget set.** Use `!budget [amount]` to set one.")
                else:
                    usage_percent = (
                        current_month_cost / current_budget) * 100 if current_budget > 0 else 0

                    if EMBED_HELPER_AVAILABLE:
                        embed = discord.Embed(
                            title="💰 Monthly Budget",
                            color=EmbedColors.BLUE if EMBED_HELPER_AVAILABLE else discord.Color.blue()
                        )
                        embed.add_field(
                            name="Budget Amount",
                            value=f"${current_budget:.2f}/month",
                            inline=True
                        )
                        embed.add_field(
                            name="Current Spending",
                            value=f"${current_month_cost:.2f}",
                            inline=True
                        )
                        embed.add_field(
                            name="Usage",
                            value=f"{usage_percent:.1f}%",
                            inline=True
                        )
                        embed.add_field(
                            name="Remaining",
                            value=f"${max(0, current_budget - current_month_cost):.2f}",
                            inline=False
                        )
                        embed.set_footer(
                            text="Owner only | Alerts at 50%, 75%, and 90%")
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(
                            f"💰 **Monthly Budget**: ${current_budget:.2f}\n"
                            f"**Current Spending**: ${current_month_cost:.2f}\n"
                            f"**Usage**: {usage_percent:.1f}%\n"
                            f"**Remaining**: ${max(0, current_budget - current_month_cost):.2f}"
                        )
            else:
                # Set new budget
                if amount < 0:
                    await ctx.send("❌ Budget amount must be positive!")
                    return

                self.statistics_tracker.set_budget(amount)

                # Reset alerts for new budget
                self.statistics_tracker.reset_budget_alerts()

                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_success_embed(
                        title="✅ Budget Updated",
                        description=f"Monthly budget set to ${amount:.2f}",
                        details=(
                            f"**Current Month Spending**: ${current_month_cost:.2f}\n"
                            f"**Usage**: {(current_month_cost/amount*100) if amount > 0 else 0:.1f}%\n\n"
                            f"You'll receive alerts at 50%, 75%, and 90% usage."
                        )
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(
                        f"✅ **Budget Updated!**\n"
                        f"Monthly budget set to ${amount:.2f}\n"
                        f"Current spending: ${current_month_cost:.2f}"
                    )

                print(f"[OK] Budget set to ${amount:.2f} by {ctx.author.name}")

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Error",
                    description="Error managing budget",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error: {str(e)}")
            print(f"[ERROR] Budget command failed: {e}")
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
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ History Unavailable",
                    description="Conversation logger not available!"
                )
                await ctx.send(embed=embed)
            else:
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
                    user_id = user.replace(
                        "<@", "").replace("!", "").replace(">", "")
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
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_info_embed(
                        title="📭 No History Found",
                        description="No conversation history found!",
                        footer="Start chatting to build history"
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("📭 No conversation history found!")
                return

            # Create embed with history
            display_name = history[0]['user_name'] if history else "Unknown"
            embed = discord.Embed(
                title=f"💬 Conversation History - {display_name}",
                description=f"Showing last {len(history)} conversations",
                color=EmbedColors.BLUE if EMBED_HELPER_AVAILABLE else discord.Color.blue()
            )

            # Show conversations (limit to fit Discord embed limits)
            for i, conv in enumerate(history[:5], 1):  # Show max 5 in embed
                timestamp = conv['timestamp'][:19] if len(
                    conv['timestamp']) > 19 else conv['timestamp']
                user_msg = conv['user_message'][:200] + "..." if len(
                    conv['user_message']) > 200 else conv['user_message']
                bot_msg = conv['bot_response'][:200] + \
                    "..." if len(conv['bot_response']
                                 ) > 200 else conv['bot_response']

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
                embed.set_footer(
                    text=f"Showing 5 of {len(history)} conversations. Use !export for full history.")

            await ctx.send(embed=embed)
        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ History Error",
                    description="Error getting conversation history",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
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
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Missing Argument",
                    description=f"Missing required argument! Use `{prefix}help` for usage."
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Missing required argument! Use `{prefix}help` for usage.")
            return

        # Handle other command errors
        print(f"[ERROR] Command error: {error}")
        import traceback
        traceback.print_exc()

        # Send user-friendly error message
        try:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Command Error",
                    description="An error occurred while processing that command. Please try again!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ An error occurred while processing that command. Please try again!")
        except:
            pass  # If we can't send message, ignore

    @commands.command(name="summarize")
    async def summarize_command(self, ctx: commands.Context, user: Optional[str] = None):
        """
        Summarize conversation history

        Usage:
        !summarize - Summarize current conversation
        !summarize @user - Summarize specific user's conversation
        """
        if not self.memory_manager:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Summarization Unavailable",
                    description="Memory manager not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Memory manager not available!")
            return

        if not self.summarizer:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Summarization Unavailable",
                    description="Summarizer not available! Claude API is required for summarization."
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Summarizer not available! Claude API is required.")
            return

        # Determine which user to summarize
        target_user_id = str(user.id) if user else str(ctx.author.id)
        target_user_name = user.display_name if user else ctx.author.display_name
        channel_id = str(ctx.channel.id)

        # Show processing message
        if EMBED_HELPER_AVAILABLE:
            processing_embed = EmbedHelper.create_info_embed(
                title="📝 Summarizing Conversation",
                description=f"Analyzing last 20 messages for {target_user_name}...",
                footer="This may take a few seconds"
            )
            processing_msg = await ctx.send(embed=processing_embed)
        else:
            processing_msg = await ctx.send(f"📝 Summarizing conversation for {target_user_name}... This may take a few seconds.")

        try:
            # Get recent messages (last 20)
            recent_messages = self.memory_manager.get_recent_messages(
                user_id=target_user_id,
                channel_id=channel_id,
                limit=20
            )

            if len(recent_messages) < 2:
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_info_embed(
                        title="📭 Not Enough Messages",
                        description=f"Need at least 2 messages to create a summary. Found {len(recent_messages)} message(s).",
                        footer="Start chatting to build conversation history"
                    )
                    await processing_msg.edit(embed=embed)
                else:
                    await processing_msg.edit(content=f"📭 Not enough messages to summarize. Found {len(recent_messages)} message(s).")
                return

            # Convert to API format
            api_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in recent_messages
            ]

            # Get timestamps
            start_time = datetime.fromisoformat(
                recent_messages[0]["timestamp"])
            end_time = datetime.fromisoformat(recent_messages[-1]["timestamp"])

            # Create summary with details extraction
            summary_result = await self.summarizer.summarize_messages(
                messages=api_messages,
                user_name=target_user_name,
                extract_details=True
            )

            # Extract components
            summary_text = summary_result.get(
                "summary", "No summary available.")
            key_topics = summary_result.get("key_topics", [])
            important_info = summary_result.get("important_info", [])

            # Create summary embed
            if EMBED_HELPER_AVAILABLE:
                embed = discord.Embed(
                    title=f"📝 Conversation Summary - {target_user_name}",
                    description=summary_text[:2000],  # Discord limit
                    color=EmbedColors.BLUE
                )

                # Add key topics
                if key_topics:
                    topics_text = "\n".join(
                        [f"• {topic}" for topic in key_topics[:5]])
                    embed.add_field(
                        name="🔑 Key Topics",
                        value=topics_text[:1024],
                        inline=False
                    )

                # Add important information
                if important_info:
                    info_text = "\n".join(
                        [f"• {info}" for info in important_info[:5]])
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

                await processing_msg.edit(embed=embed)
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
                await processing_msg.edit(content=result_text)

            # Save summary to database
            try:
                summary_id = self.memory_manager.create_summary(
                    user_id=target_user_id,
                    channel_id=channel_id,
                    summary_text=summary_text,
                    message_count=len(recent_messages),
                    start_timestamp=start_time,
                    end_timestamp=end_time,
                    importance_score=0.7  # Manual summaries are important
                )
                print(
                    f"[OK] Summary created: ID={summary_id}, User={target_user_id}, Messages={len(recent_messages)}")
            except Exception as e:
                print(f"[ERROR] Failed to save summary to database: {e}")

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Summarization Failed",
                    description="Error creating summary",
                    error_details=str(e)
                )
                await processing_msg.edit(embed=embed)
            else:
                await processing_msg.edit(content=f"❌ Error creating summary: {str(e)}")
            print(f"[ERROR] Summarize command failed: {e}")
            import traceback
            traceback.print_exc()

    @commands.command(name="remember")
    async def remember_command(self, ctx: commands.Context):
        """
        Show what the bot remembers about you

        Usage:
        !remember - Show all facts, preferences, and conversation history
        """
        if not self.memory_manager:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Memory Unavailable",
                    description="Memory manager not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Memory manager not available!")
            return

        try:
            user_id = str(ctx.author.id)
            channel_id = str(ctx.channel.id)

            # Get memory summary
            memory = self.memory_manager.get_user_memory_summary(
                user_id, channel_id)

            # Create embed
            if EMBED_HELPER_AVAILABLE:
                embed = discord.Embed(
                    title=f"🧠 What I Remember About {ctx.author.display_name}",
                    color=EmbedColors.BLUE
                )

                # Show facts
                if memory['facts']:
                    facts_text = ""
                    for fact in memory['facts'][:10]:  # Show top 10
                        importance_emoji = "⭐" if fact['importance_score'] > 0.7 else "📝"
                        facts_text += f"{importance_emoji} **{fact['fact_key'].title()}**: {fact['fact_value']}\n"

                    if len(memory['facts']) > 10:
                        facts_text += f"\n*...and {len(memory['facts']) - 10} more facts*"

                    embed.add_field(
                        name="📚 Facts I Know",
                        value=facts_text[:1024] if len(
                            facts_text) > 1024 else facts_text,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="📚 Facts I Know",
                        value="I don't remember any specific facts yet. Use `!teach` to teach me something!",
                        inline=False
                    )

                # Show preferences
                if memory['preferences']:
                    prefs_text = ""
                    for pref in memory['preferences'][:10]:  # Show top 10
                        prefs_text += f"• **{pref['key'].title()}**: {pref['value']}\n"

                    if len(memory['preferences']) > 10:
                        prefs_text += f"\n*...and {len(memory['preferences']) - 10} more preferences*"

                    embed.add_field(
                        name="⚙️ Preferences",
                        value=prefs_text[:1024] if len(
                            prefs_text) > 1024 else prefs_text,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="⚙️ Preferences",
                        value="No preferences stored yet.",
                        inline=False
                    )

                # Show conversation stats
                embed.add_field(
                    name="💬 Conversation History",
                    value=f"I've had {memory['conversation_count']} conversation(s) with you in this channel.",
                    inline=False
                )

                embed.set_footer(
                    text="Use !teach to add more facts, !forget to clear memory")

                await ctx.send(embed=embed)
            else:
                # Fallback text format
                result_text = f"**🧠 What I Remember About {ctx.author.display_name}**\n\n"

                if memory['facts']:
                    result_text += "**📚 Facts:**\n"
                    for fact in memory['facts'][:10]:
                        result_text += f"• {fact['fact_key'].title()}: {fact['fact_value']}\n"
                    result_text += "\n"

                if memory['preferences']:
                    result_text += "**⚙️ Preferences:**\n"
                    for pref in memory['preferences'][:10]:
                        result_text += f"• {pref['key'].title()}: {pref['value']}\n"
                    result_text += "\n"

                result_text += f"**💬 Conversations:** {memory['conversation_count']}"
                await ctx.send(result_text)

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Error",
                    description="Error retrieving memory",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error: {str(e)}")
            print(f"[ERROR] Remember command failed: {e}")
            import traceback
            traceback.print_exc()

    @commands.command(name="forget")
    async def forget_command(self, ctx: commands.Context, confirm: Optional[str] = None):
        """
        Clear your memory

        Usage:
        !forget - Clear your memory (requires confirmation)
        !forget confirm - Confirm and clear memory
        """
        if not self.memory_manager:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Memory Unavailable",
                    description="Memory manager not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Memory manager not available!")
            return

        try:
            user_id = str(ctx.author.id)
            channel_id = str(ctx.channel.id)

            # Require confirmation
            if confirm != "confirm":
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_info_embed(
                        title="⚠️ Confirm Memory Clear",
                        description=(
                            "This will delete all facts, preferences, and conversation history!\n\n"
                            "**To confirm, type:** `!forget confirm`\n\n"
                            "⚠️ **This action cannot be undone!**"
                        )
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(
                        "⚠️ **Warning:** This will delete all your memory!\n"
                        "Type `!forget confirm` to confirm."
                    )
                return

            # Clear memory
            counts = self.memory_manager.clear_user_memory(user_id, channel_id)

            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_success_embed(
                    title="✅ Memory Cleared",
                    description="All your memory has been cleared!",
                    details=(
                        f"**Deleted:**\n"
                        f"• {counts.get('facts', 0)} facts\n"
                        f"• {counts.get('preferences', 0)} preferences\n"
                        f"• {counts.get('conversations', 0)} conversations\n"
                        f"• {counts.get('summaries', 0)} summaries"
                    )
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(
                    f"✅ **Memory Cleared!**\n"
                    f"Deleted {counts.get('facts', 0)} facts, "
                    f"{counts.get('preferences', 0)} preferences, "
                    f"{counts.get('conversations', 0)} conversations, "
                    f"and {counts.get('summaries', 0)} summaries."
                )

            print(
                f"[OK] Memory cleared for user {user_id} in channel {channel_id}")

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Error",
                    description="Error clearing memory",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error: {str(e)}")
            print(f"[ERROR] Forget command failed: {e}")
            import traceback
            traceback.print_exc()

    # ========== FUN & GAMES COMMANDS ==========

    @commands.command(name="joke")
    async def joke_command(self, ctx: commands.Context):
        # Tell an AI-generated joke
        if not self.use_claude or not self.claude_handler:
            # Fallback to static jokes
            static_jokes = [
                "Why don't scientists trust atoms? Because they make up everything!",
                "Why did the scarecrow win an award? He was outstanding in his field!",
                "Why don't eggs tell jokes? They'd crack each other up!",
                "What do you call a fake noodle? An impasta!",
                "Why did the math book look so sad? Because it had too many problems!"
            ]
            joke = random.choice(static_jokes)
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="😄 Joke",
                    description=joke,
                    color=EmbedColors.PURPLE
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"😄 **Joke:**\n{joke}")
            return

        try:
            async with ctx.channel.typing():
                # Generate AI joke
                messages = [{
                    "role": "user",
                    "content": "Tell me a funny, clean joke. Make it creative and entertaining!"
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    joke = result["response"]
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="😄 AI-Generated Joke",
                            description=joke,
                            color=EmbedColors.PURPLE
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"😄 **Joke:**\n{joke}")
                else:
                    await ctx.send("😅 Couldn't generate a joke right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Joke command failed: {e}")
            await ctx.send("😅 Oops! Couldn't tell a joke right now.")

    @commands.command(name="story")
    async def story_command(self, ctx: commands.Context, *, topic: Optional[str] = None):
        # Generate a creative story (Premium feature for longer stories). Usage: !story [topic]
        if not self.use_claude or not self.claude_handler:
            await ctx.send("❌ Story generation requires Claude API!")
            return

        try:
            async with ctx.channel.typing():
                story_topic = topic if topic else "a random creative and engaging story"

                # Premium users get longer stories
                is_premium = self._check_premium_feature(ctx.author.id)
                if is_premium:
                    prompt = f"Write a creative story (4-5 paragraphs) about {story_topic}. Make it engaging, imaginative, and fun to read!"
                else:
                    prompt = f"Write a short creative story (2-3 paragraphs) about {story_topic}. Make it engaging, imaginative, and fun to read!"

                messages = [{
                    "role": "user",
                    "content": prompt
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    story = result["response"]
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_ai_response_embed(
                            content=story,
                            user_name=ctx.author.display_name
                        )
                        embed.title = "📖 Creative Story"
                        if topic:
                            embed.add_field(
                                name="Topic", value=topic, inline=False)
                        await ctx.send(embed=embed)
                    else:
                        response = f"📖 **Story{' about ' + topic if topic else ''}:**\n\n{story}"
                        await ctx.send(response)
                else:
                    await ctx.send("❌ Couldn't generate a story right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Story command failed: {e}")
            await ctx.send("❌ Oops! Couldn't generate a story right now.")

    @commands.command(name="riddle")
    async def riddle_command(self, ctx: commands.Context):
        # Share a riddle - use !answer to check your guess
        if not self.use_claude or not self.claude_handler:
            # Fallback riddles
            fallback_riddles = [
                ("What has keys but no locks, space but no room, and you can enter but not go inside?", "A keyboard"),
                ("I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "An echo"),
                ("The more you take, the more you leave behind. What am I?", "Footsteps")
            ]
            riddle, answer = random.choice(fallback_riddles)
            self.riddle_answers[str(ctx.channel.id)] = answer.lower()

            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="🤔 Riddle",
                    description=f"{riddle}\n\nUse `!answer [your guess]` to check your answer!",
                    color=EmbedColors.BLUE
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"🤔 **Riddle:**\n{riddle}\n\nUse `!answer [your guess]` to check your answer!")
            return

        try:
            async with ctx.channel.typing():
                messages = [{
                    "role": "user",
                    "content": "Give me a fun riddle with a clear answer. Format it as:\nRIDDLE: [the riddle]\nANSWER: [the answer]"
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    response = result["response"]
                    # Parse riddle and answer
                    if "RIDDLE:" in response and "ANSWER:" in response:
                        parts = response.split("ANSWER:")
                        riddle = parts[0].replace("RIDDLE:", "").strip()
                        answer = parts[1].strip().lower()
                    else:
                        # Fallback parsing
                        lines = response.split("\n")
                        riddle = response
                        answer = "unknown"

                    # Store answer for this channel
                    if not hasattr(self, 'riddle_answers'):
                        self.riddle_answers = {}
                    self.riddle_answers[str(ctx.channel.id)] = answer

                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="🤔 Riddle",
                            description=f"{riddle}\n\nUse `!answer [your guess]` to check your answer!",
                            color=EmbedColors.BLUE
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"🤔 **Riddle:**\n{riddle}\n\nUse `!answer [your guess]` to check your answer!")
                else:
                    await ctx.send("❌ Couldn't generate a riddle right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Riddle command failed: {e}")
            await ctx.send("❌ Oops! Couldn't generate a riddle right now.")

    @commands.command(name="answer")
    async def answer_command(self, ctx: commands.Context, *, guess: str):
        # Check your riddle answer. Usage: !answer [guess]
        if not hasattr(self, 'riddle_answers') or str(ctx.channel.id) not in self.riddle_answers:
            await ctx.send("❌ No active riddle! Use `!riddle` first.")
            return

        correct_answer = self.riddle_answers[str(ctx.channel.id)]
        guess_lower = guess.lower().strip()

        # Check if answer is correct (fuzzy matching)
        is_correct = (
            guess_lower == correct_answer or
            guess_lower in correct_answer or
            correct_answer in guess_lower
        )

        if is_correct:
            del self.riddle_answers[str(ctx.channel.id)]
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_success_embed(
                    title="✅ Correct!",
                    description=f"🎉 Well done, {ctx.author.display_name}! You got it right!",
                    footer="The answer was: " + correct_answer.title()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"✅ **Correct!** 🎉 Well done! The answer was: {correct_answer.title()}")
        else:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="❌ Not Quite",
                    description=f"Try again! 💭",
                    color=EmbedColors.YELLOW
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Not quite right. Try again! 💭")

    @commands.command(name="fact")
    async def fact_command(self, ctx: commands.Context):
        # Get a random interesting fact
        if not self.use_claude or not self.claude_handler:
            # Fallback facts
            static_facts = [
                "Octopuses have three hearts!",
                "Honey never spoils - archaeologists have found 3000-year-old honey that's still edible!",
                "Bananas are berries, but strawberries aren't!",
                "A day on Venus is longer than its year!",
                "Sharks have been around longer than trees!"
            ]
            fact = random.choice(static_facts)
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="💡 Did You Know?",
                    description=fact,
                    color=EmbedColors.BLUE
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"💡 **Did You Know?**\n{fact}")
            return

        try:
            async with ctx.channel.typing():
                messages = [{
                    "role": "user",
                    "content": "Tell me a random interesting fact that's true and fascinating. Make it fun and educational!"
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    fact = result["response"]
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="💡 Did You Know?",
                            description=fact,
                            color=EmbedColors.BLUE
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"💡 **Did You Know?**\n{fact}")
                else:
                    await ctx.send("❌ Couldn't get a fact right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Fact command failed: {e}")
            await ctx.send("❌ Oops! Couldn't get a fact right now.")

    @commands.command(name="quote")
    async def quote_command(self, ctx: commands.Context):
        # Get an inspirational quote
        if not self.use_claude or not self.claude_handler:
            # Fallback quotes
            static_quotes = [
                "The only way to do great work is to love what you do. - Steve Jobs",
                "Innovation distinguishes between a leader and a follower. - Steve Jobs",
                "Life is what happens to you while you're busy making other plans. - John Lennon",
                "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
                "It is during our darkest moments that we must focus to see the light. - Aristotle"
            ]
            quote = random.choice(static_quotes)
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="💭 Inspirational Quote",
                    description=quote,
                    color=EmbedColors.BLUE
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"💭 **Inspirational Quote:**\n{quote}")
            return

        try:
            async with ctx.channel.typing():
                messages = [{
                    "role": "user",
                    "content": "Give me an inspirational quote with the author's name. Make it meaningful and motivating!"
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    quote = result["response"]
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="💭 Inspirational Quote",
                            description=quote,
                            color=EmbedColors.BLUE
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"💭 **Inspirational Quote:**\n{quote}")
                else:
                    await ctx.send("❌ Couldn't get a quote right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Quote command failed: {e}")
            await ctx.send("❌ Oops! Couldn't get a quote right now.")

    @commands.command(name="eightball", aliases=["8ball", "magic8ball"])
    async def eightball_command(self, ctx: commands.Context, *, question: str):
        # Ask the Magic 8-Ball a question. Usage: !eightball [question]
        responses = [
            "🎱 It is certain.",
            "🎱 Without a doubt.",
            "🎱 Yes, definitely.",
            "🎱 You may rely on it.",
            "🎱 As I see it, yes.",
            "🎱 Most likely.",
            "🎱 Outlook good.",
            "🎱 Yes.",
            "🎱 Signs point to yes.",
            "🎱 Reply hazy, try again.",
            "🎱 Ask again later.",
            "🎱 Better not tell you now.",
            "🎱 Cannot predict now.",
            "🎱 Concentrate and ask again.",
            "🎱 Don't count on it.",
            "🎱 My reply is no.",
            "🎱 My sources say no.",
            "🎱 Outlook not so good.",
            "🎱 Very doubtful.",
            "🎱 No."
        ]

        answer = random.choice(responses)

        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="🎱 Magic 8-Ball",
                description=f"**Question:** {question}\n\n**Answer:** {answer}",
                color=EmbedColors.PURPLE
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"🎱 **Magic 8-Ball**\n\n**Question:** {question}\n**Answer:** {answer}")

    @commands.command(name="trivia")
    async def trivia_command(self, ctx: commands.Context):
        # Start a trivia quiz game
        if not self.use_claude or not self.claude_handler:
            await ctx.send("❌ Trivia requires Claude API!")
            return

        try:
            async with ctx.channel.typing():
                messages = [{
                    "role": "user",
                    "content": "Give me a trivia question with 4 multiple choice answers (A, B, C, D). Format it as:\nQUESTION: [the question]\nA) [option A]\nB) [option B]\nC) [option C]\nD) [option D]\nANSWER: [the correct letter]"
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    response = result["response"]
                    # Parse question and answer
                    if "ANSWER:" in response:
                        parts = response.split("ANSWER:")
                        question_part = parts[0].replace(
                            "QUESTION:", "").strip()
                        answer = parts[1].strip().upper()[
                            0]  # Get first letter
                    else:
                        question_part = response
                        answer = "A"  # Default

                    # Store answer for this channel
                    if not hasattr(self, 'trivia_answers'):
                        self.trivia_answers = {}
                    self.trivia_answers[str(ctx.channel.id)] = answer

                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="🧠 Trivia Question",
                            description=f"{question_part}\n\nUse `!guess [A/B/C/D]` to answer!",
                            color=EmbedColors.BLUE
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"🧠 **Trivia Question:**\n{question_part}\n\nUse `!guess [A/B/C/D]` to answer!")
                else:
                    await ctx.send("❌ Couldn't generate trivia right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Trivia command failed: {e}")
            await ctx.send("❌ Oops! Couldn't generate trivia right now.")

    @commands.command(name="guess")
    async def guess_command(self, ctx: commands.Context, answer: str):
        # Guess the trivia answer. Usage: !guess [answer]
        if not hasattr(self, 'trivia_answers') or str(ctx.channel.id) not in self.trivia_answers:
            await ctx.send("❌ No active trivia question! Use `!trivia` first.")
            return

        correct_answer = self.trivia_answers[str(ctx.channel.id)]
        guess = answer.upper().strip()[0] if answer else ""

        if guess == correct_answer:
            del self.trivia_answers[str(ctx.channel.id)]
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_success_embed(
                    title="✅ Correct!",
                    description=f"🎉 Well done, {ctx.author.display_name}! You got it right!",
                    footer="The answer was: " + correct_answer
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"✅ **Correct!** 🎉 Well done! The answer was: {correct_answer}")
        else:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="❌ Incorrect",
                    description=f"Sorry, that's not right. The correct answer was **{correct_answer}**.",
                    color=EmbedColors.RED
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Incorrect! The correct answer was **{correct_answer}**.")
            del self.trivia_answers[str(ctx.channel.id)]

    @commands.command(name="wouldyourather", aliases=["wyr", "would_you_rather"])
    async def wouldyourather_command(self, ctx: commands.Context):
        # Get a "Would You Rather" question
        if not self.use_claude or not self.claude_handler:
            # Fallback questions
            fallback_wyr = [
                "Would you rather have the ability to fly or be invisible?",
                "Would you rather have super strength or super speed?",
                "Would you rather be able to speak all languages or play all instruments?",
                "Would you rather have unlimited money or unlimited time?",
                "Would you rather live in the past or the future?"
            ]
            question = random.choice(fallback_wyr)
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="🤔 Would You Rather?",
                    description=question,
                    color=EmbedColors.PURPLE
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"🤔 **Would You Rather?**\n{question}")
            return

        try:
            async with ctx.channel.typing():
                messages = [{
                    "role": "user",
                    "content": "Give me a fun 'Would You Rather' question with two interesting options. Make it creative and thought-provoking!"
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    question = result["response"]
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="🤔 Would You Rather?",
                            description=question,
                            color=EmbedColors.PURPLE
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"🤔 **Would You Rather?**\n{question}")
                else:
                    await ctx.send("❌ Couldn't generate a question right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Would You Rather command failed: {e}")
            await ctx.send("❌ Oops! Couldn't generate a question right now.")

    @commands.command(name="dadjoke")
    async def dadjoke_command(self, ctx: commands.Context):
        # Get a dad joke
        if not self.use_claude or not self.claude_handler:
            # Fallback dad jokes
            dad_jokes = [
                "Why don't scientists trust atoms? Because they make up everything!",
                "I told my wife she was drawing her eyebrows too high. She looked surprised.",
                "Why don't eggs tell jokes? They'd crack each other up!",
                "What do you call a fake noodle? An impasta!",
                "Why did the scarecrow win an award? He was outstanding in his field!",
                "I'm reading a book about anti-gravity. It's impossible to put down!",
                "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them!",
                "Why don't programmers like nature? It has too many bugs!"
            ]
            joke = random.choice(dad_jokes)
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="👨 Dad Joke",
                    description=joke,
                    color=EmbedColors.PURPLE
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"👨 **Dad Joke:**\n{joke}")
            return

        try:
            async with ctx.channel.typing():
                messages = [{
                    "role": "user",
                    "content": "Tell me a classic dad joke - the kind that makes people groan! Make it punny and cheesy."
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    joke = result["response"]
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="👨 Dad Joke",
                            description=joke,
                            color=EmbedColors.PURPLE
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"👨 **Dad Joke:**\n{joke}")
                else:
                    await ctx.send("❌ Couldn't tell a dad joke right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Dad joke command failed: {e}")
            await ctx.send("❌ Oops! Couldn't tell a dad joke right now.")

    @commands.command(name="roast")
    async def roast_command(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        # Friendly roast someone (all in good fun!). Usage: !roast @user or !roast
        target = member if member else ctx.author

        # Don't roast the bot
        if target == self.user:
            await ctx.send("😅 Nice try, but I'm too cool to roast!")
            return

        if not self.use_claude or not self.claude_handler:
            # Fallback roasts
            fallback_roasts = [
                f"{target.display_name}, you're so funny... not! 😂",
                f"{target.display_name}, you're like a cloud. When you disappear, it's a beautiful day! ☁️",
                f"{target.display_name}, you're proof that evolution can go in reverse! 🦕",
                f"{target.display_name}, you're not stupid, you just have bad luck thinking! 🤔",
                f"{target.display_name}, if I had a dollar for every smart thing you said, I'd be broke! 💰"
            ]
            roast = random.choice(fallback_roasts)
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="🔥 Friendly Roast",
                    description=roast,
                    color=EmbedColors.RED
                )
                embed.set_footer(text="All in good fun! 😄")
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"🔥 **Friendly Roast:**\n{roast}\n\n*All in good fun! 😄*")
            return

        try:
            async with ctx.channel.typing():
                messages = [{
                    "role": "user",
                    "content": f"Give me a friendly, lighthearted roast for someone named {target.display_name}. Keep it fun and playful - no mean-spirited insults. Make it creative and funny!"
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    roast = result["response"]
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="🔥 Friendly Roast",
                            description=f"{roast}",
                            color=EmbedColors.RED
                        )
                        embed.set_footer(
                            text=f"Roasting {target.display_name} • All in good fun! 😄")
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"🔥 **Friendly Roast:**\n{roast}\n\n*Roasting {target.display_name} - All in good fun! 😄*")
                else:
                    await ctx.send("❌ Couldn't generate a roast right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Roast command failed: {e}")
            await ctx.send("❌ Oops! Couldn't generate a roast right now.")

    # ========== TRANSLATION COMMANDS ==========

    @commands.command(name="translate", aliases=["tr", "trans"])
    async def translate_command(self, ctx: commands.Context, *, text: Optional[str] = None):
        # Translate text to English or specified language. Usage: !translate [text] or !translate [lang] [text]
        if not text:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Missing Text",
                    description="Please provide text to translate!\n\n**Usage:**\n`!translate [text]` - Auto-translate to English\n`!translate [lang] [text]` - Translate to specific language"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Please provide text to translate!\n\n**Usage:**\n`!translate [text]` - Auto-translate to English\n`!translate [lang] [text]` - Translate to specific language")
            return

        if not self.use_claude or not self.claude_handler:
            await ctx.send("❌ Translation requires Claude API!")
            return

        try:
            async with ctx.channel.typing():
                # Parse language and text
                parts = text.split(' ', 1)
                target_lang = None
                text_to_translate = text

                # Check if first word is a language code
                lang_codes = {
                    'english': 'en', 'en': 'en',
                    'kurdish': 'ku', 'ku': 'ku', 'kurdi': 'ku',
                    'sorani': 'ku-sorani', 'kurmanji': 'ku-kurmanji',
                    'arabic': 'ar', 'ar': 'ar',
                    'turkish': 'tr', 'tr': 'tr'
                }

                if len(parts) > 1 and parts[0].lower() in lang_codes:
                    target_lang = lang_codes[parts[0].lower()]
                    text_to_translate = parts[1]

                # Detect source language
                detected_language = 'en'
                kurdish_dialect = None
                if KURDISH_DETECTOR_AVAILABLE:
                    lang_result = KurdishDetector.detect_language(
                        text_to_translate)
                    detected_language = lang_result[0]
                    if detected_language == 'ku':
                        kurdish_result = KurdishDetector.detect_kurdish(
                            text_to_translate)
                        if kurdish_result:
                            kurdish_dialect, _ = kurdish_result

                # Default to English if no target specified
                if not target_lang:
                    target_lang = 'en'

                # Build translation prompt
                lang_names = {
                    'en': 'English',
                    'ku': 'Kurdish',
                    'ku-sorani': 'Kurdish (Sorani dialect)',
                    'ku-kurmanji': 'Kurdish (Kurmanji dialect)',
                    'ar': 'Arabic',
                    'tr': 'Turkish'
                }

                source_lang_name = lang_names.get(
                    detected_language, 'the detected language')
                target_lang_name = lang_names.get(target_lang, 'English')

                # Special handling for Kurdish dialects
                if target_lang == 'ku' and kurdish_dialect:
                    # If translating to Kurdish and we know the dialect preference
                    if kurdish_dialect.lower() == 'sorani':
                        target_lang = 'ku-sorani'
                        target_lang_name = 'Kurdish (Sorani)'
                    elif kurdish_dialect.lower() == 'kurmanji':
                        target_lang = 'ku-kurmanji'
                        target_lang_name = 'Kurdish (Kurmanji)'

                prompt = f"Translate the following text from {source_lang_name} to {target_lang_name}. Provide only the translation, no explanations:\n\n{text_to_translate}"

                messages = [{
                    "role": "user",
                    "content": prompt
                }]

                result = await self.claude_handler.generate_response(
                    messages=messages,
                    user_name=ctx.author.display_name
                )

                if result["success"]:
                    translation = result["response"].strip()

                    # Check cache for translation
                    trans_cache_key = self._get_cache_key(
                        f"{text_to_translate}:{target_lang}", 'translation')
                    trans_cached = self._get_cached_response(trans_cache_key)

                    if trans_cached:
                        translation = trans_cached['response']
                        is_cached = True
                    else:
                        is_cached = False
                        # Cache translation
                        self._cache_response(trans_cache_key, translation, {
                            'source_lang': source_lang_name,
                            'target_lang': target_lang_name
                        })

                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="🌐 Translation",
                            description=f"**Original ({source_lang_name}):**\n{text_to_translate}\n\n**Translation ({target_lang_name}):**\n{translation}",
                            color=EmbedColors.BLUE
                        )
                        if is_cached:
                            embed.set_footer(text="⚡ Cached response")
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"🌐 **Translation**\n\n**Original ({source_lang_name}):** {text_to_translate}\n**Translation ({target_lang_name}):** {translation}")
                else:
                    await ctx.send("❌ Couldn't translate right now. Try again!")
        except Exception as e:
            print(f"[ERROR] Translate command failed: {e}")
            await ctx.send("❌ Oops! Couldn't translate right now.")

    @commands.command(name="detect", aliases=["detectlang", "langdetect"])
    async def detect_command(self, ctx: commands.Context, *, text: Optional[str] = None):
        # Detect the language of text. Usage: !detect [text]
        if not text:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Missing Text",
                    description="Please provide text to detect!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Please provide text to detect!")
            return

        try:
            # Detect language
            detected_language = 'en'
            kurdish_dialect = None
            confidence = 0.5

            if KURDISH_DETECTOR_AVAILABLE:
                lang_result = KurdishDetector.detect_language(text)
                detected_language = lang_result[0]
                confidence = lang_result[1] if len(lang_result) > 1 else 0.5

                if detected_language == 'ku':
                    kurdish_result = KurdishDetector.detect_kurdish(text)
                    if kurdish_result:
                        kurdish_dialect, dialect_confidence = kurdish_result
                        confidence = dialect_confidence

            # Language names
            lang_names = {
                'en': 'English 🇬🇧',
                'ku': 'Kurdish 🟥⬜🟩☀️',  # Kurdistan flag colors: red, white, green, sun
                'ar': 'Arabic 🇸🇦',
                'tr': 'Turkish 🇹🇷'
            }

            lang_name = lang_names.get(
                detected_language, detected_language.upper())

            if detected_language == 'ku' and kurdish_dialect:
                # Kurdistan flag colors
                lang_name = f"Kurdish ({kurdish_dialect.title()}) 🟥⬜🟩☀️"

            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="🔍 Language Detection",
                    description=f"**Text:** {text}\n\n**Detected Language:** {lang_name}\n**Confidence:** {confidence:.0%}",
                    color=EmbedColors.BLUE
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"🔍 **Language Detection**\n\n**Text:** {text}\n**Language:** {lang_name}\n**Confidence:** {confidence:.0%}")
        except Exception as e:
            print(f"[ERROR] Detect command failed: {e}")
            await ctx.send("❌ Oops! Couldn't detect language right now.")

    @commands.command(name="kurdish", aliases=["ku", "kurdi"])
    async def kurdish_command(self, ctx: commands.Context, *, text: Optional[str] = None):
        # Translate text to Kurdish. Usage: !kurdish [text]
        if not text:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Missing Text",
                    description="Please provide text to translate to Kurdish!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Please provide text to translate to Kurdish!")
            return

        # Use translate command with Kurdish target
        await self.translate_command(ctx, text=f"kurdish {text}")

    @commands.command(name="english", aliases=["en"])
    async def english_command(self, ctx: commands.Context, *, text: Optional[str] = None):
        # Translate text to English. Usage: !english [text]
        if not text:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Missing Text",
                    description="Please provide text to translate to English!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Please provide text to translate to English!")
            return

        # Use translate command with English target
        await self.translate_command(ctx, text=f"english {text}")

    @commands.command(name="autotranslate", aliases=["autotr", "auto-translate"])
    @commands.has_permissions(manage_messages=True)
    async def autotranslate_command(self, ctx: commands.Context, enable: Optional[str] = None):
        # Enable/disable auto-translation mode for this server (Admin only). Usage: !autotranslate on/off
        if not ctx.guild:
            await ctx.send("❌ This command only works in servers!")
            return

        server_id = ctx.guild.id

        if enable is None:
            # Show status
            is_enabled = server_id in self.auto_translate_servers
            status = "enabled" if is_enabled else "disabled"
            status_emoji = "✅" if is_enabled else "❌"

            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="🌐 Auto-Translation Status",
                    description=f"{status_emoji} Auto-translation is **{status}** for this server.\n\nUse `!autotranslate on` to enable or `!autotranslate off` to disable.",
                    color=EmbedColors.GREEN if is_enabled else EmbedColors.RED
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"🌐 **Auto-Translation Status:** {status_emoji} {status.capitalize()}")
            return

        enable_lower = enable.lower()
        if enable_lower in ['on', 'enable', 'true', '1', 'yes']:
            self.auto_translate_servers.add(server_id)
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_success_embed(
                    title="✅ Auto-Translation Enabled",
                    description="Auto-translation is now enabled for this server. Messages in non-English languages will be automatically translated to English."
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("✅ Auto-translation enabled for this server!")
        elif enable_lower in ['off', 'disable', 'false', '0', 'no']:
            self.auto_translate_servers.discard(server_id)
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="❌ Auto-Translation Disabled",
                    description="Auto-translation is now disabled for this server.",
                    color=EmbedColors.RED
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Auto-translation disabled for this server.")
        else:
            await ctx.send("❌ Invalid option! Use `on` or `off`.")

    # ========== MODERATION COMMANDS ==========

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn_command(self, ctx: commands.Context, member: discord.Member = None, *, reason: Optional[str] = None):
        # Warn a user (Admin only). Usage: !warn @user [reason]
        if not member:
            await ctx.send("❌ Please mention a user to warn!")
            return

        if member == ctx.author:
            await ctx.send("❌ You can't warn yourself!")
            return

        if member == self.user:
            await ctx.send("❌ You can't warn me!")
            return

        if not ctx.guild:
            await ctx.send("❌ This command only works in servers!")
            return

        server_id = ctx.guild.id
        user_id = member.id

        # Initialize warnings dict
        if server_id not in self.user_warnings:
            self.user_warnings[server_id] = {}
        if user_id not in self.user_warnings[server_id]:
            self.user_warnings[server_id][user_id] = []

        # Add warning
        warning = {
            'timestamp': datetime.now(),
            'moderator': ctx.author.id,
            'reason': reason or "No reason provided"
        }
        self.user_warnings[server_id][user_id].append(warning)

        # Log action
        self._log_moderation_action(
            server_id=server_id,
            action="warn",
            user_id=user_id,
            moderator_id=ctx.author.id,
            reason=reason
        )

        warning_count = len(self.user_warnings[server_id][user_id])

        # Send warning to user
        try:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="⚠️ Warning",
                    description=f"You have been warned in {ctx.guild.name}",
                    error_details=f"Reason: {reason or 'No reason provided'}\n\nTotal warnings: {warning_count}"
                )
                await member.send(embed=embed)
            else:
                await member.send(f"⚠️ **Warning**\n\nYou have been warned in {ctx.guild.name}\nReason: {reason or 'No reason provided'}\nTotal warnings: {warning_count}")
        except:
            pass  # User has DMs disabled

        # Confirm in channel
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_success_embed(
                title="✅ User Warned",
                description=f"{member.mention} has been warned.\nReason: {reason or 'No reason provided'}\nTotal warnings: {warning_count}"
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"✅ {member.mention} has been warned. Reason: {reason or 'No reason provided'} (Total: {warning_count})")

    @commands.command(name="mute")
    @commands.has_permissions(manage_messages=True)
    async def mute_command(self, ctx: commands.Context, member: discord.Member = None, duration: Optional[str] = None, *, reason: Optional[str] = None):
        # Mute a user for a specified time (Admin only). Usage: !mute @user [duration] [reason]. Duration: m/h/d
        if not member:
            await ctx.send("❌ Please mention a user to mute!")
            return

        if member == ctx.author:
            await ctx.send("❌ You can't mute yourself!")
            return

        if member == self.user:
            await ctx.send("❌ You can't mute me!")
            return

        if not ctx.guild:
            await ctx.send("❌ This command only works in servers!")
            return

        # Parse duration
        mute_duration = timedelta(minutes=10)  # Default 10 minutes
        if duration:
            duration_lower = duration.lower()
            if duration_lower.endswith('m'):
                try:
                    minutes = int(duration_lower[:-1])
                    mute_duration = timedelta(minutes=minutes)
                except:
                    pass
            elif duration_lower.endswith('h'):
                try:
                    hours = int(duration_lower[:-1])
                    mute_duration = timedelta(hours=hours)
                except:
                    pass
            elif duration_lower.endswith('d'):
                try:
                    days = int(duration_lower[:-1])
                    mute_duration = timedelta(days=days)
                except:
                    pass

        server_id = ctx.guild.id
        user_id = member.id

        # Initialize mutes dict
        if server_id not in self.user_mutes:
            self.user_mutes[server_id] = {}

        # Set mute until time
        mute_until = datetime.now() + mute_duration
        self.user_mutes[server_id][user_id] = mute_until

        # Log action
        self._log_moderation_action(
            server_id=server_id,
            action="mute",
            user_id=user_id,
            moderator_id=ctx.author.id,
            reason=reason,
            duration=mute_duration
        )

        # Send notification to user
        try:
            duration_str = f"{mute_duration.total_seconds() / 60:.0f} minutes" if mute_duration.total_seconds(
            ) < 3600 else f"{mute_duration.total_seconds() / 3600:.1f} hours"
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="🔇 Muted",
                    description=f"You have been muted in {ctx.guild.name}",
                    error_details=f"Duration: {duration_str}\nReason: {reason or 'No reason provided'}"
                )
                await member.send(embed=embed)
            else:
                await member.send(f"🔇 **Muted**\n\nYou have been muted in {ctx.guild.name}\nDuration: {duration_str}\nReason: {reason or 'No reason provided'}")
        except:
            pass

        # Confirm in channel
        duration_str = f"{mute_duration.total_seconds() / 60:.0f} minutes" if mute_duration.total_seconds(
        ) < 3600 else f"{mute_duration.total_seconds() / 3600:.1f} hours"
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_success_embed(
                title="✅ User Muted",
                description=f"{member.mention} has been muted for {duration_str}.\nReason: {reason or 'No reason provided'}"
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"✅ {member.mention} has been muted for {duration_str}. Reason: {reason or 'No reason provided'}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_command(self, ctx: commands.Context, member: discord.Member = None, *, reason: Optional[str] = None):
        # Ban a user from using the bot (Admin only). Usage: !ban @user [reason]
        if not member:
            await ctx.send("❌ Please mention a user to ban!")
            return

        if member == ctx.author:
            await ctx.send("❌ You can't ban yourself!")
            return

        if member == self.user:
            await ctx.send("❌ You can't ban me!")
            return

        if not ctx.guild:
            await ctx.send("❌ This command only works in servers!")
            return

        server_id = ctx.guild.id
        user_id = member.id

        # Initialize bans dict
        if server_id not in self.user_bans:
            self.user_bans[server_id] = {}

        # Add ban (permanent by default)
        self.user_bans[server_id][user_id] = {
            'timestamp': datetime.now(),
            'moderator': ctx.author.id,
            'reason': reason or "No reason provided",
            'permanent': True
        }

        # Log action
        self._log_moderation_action(
            server_id=server_id,
            action="ban",
            user_id=user_id,
            moderator_id=ctx.author.id,
            reason=reason
        )

        # Send notification to user
        try:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="🚫 Banned",
                    description=f"You have been banned from using the bot in {ctx.guild.name}",
                    error_details=f"Reason: {reason or 'No reason provided'}"
                )
                await member.send(embed=embed)
            else:
                await member.send(f"🚫 **Banned**\n\nYou have been banned from using the bot in {ctx.guild.name}\nReason: {reason or 'No reason provided'}")
        except:
            pass

        # Confirm in channel
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_success_embed(
                title="✅ User Banned",
                description=f"{member.mention} has been banned from using the bot.\nReason: {reason or 'No reason provided'}"
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"✅ {member.mention} has been banned from using the bot. Reason: {reason or 'No reason provided'}")

    @commands.command(name="modlogs")
    @commands.has_permissions(manage_messages=True)
    async def modlogs_command(self, ctx: commands.Context, limit: Optional[int] = 10):
        # Show moderation logs (Admin only). Usage: !modlogs [limit]
        if not ctx.guild:
            await ctx.send("❌ This command only works in servers!")
            return

        server_id = ctx.guild.id

        # Filter logs for this server
        server_logs = [
            log for log in self.moderation_logs if log['server_id'] == server_id]
        server_logs.sort(key=lambda x: x['timestamp'], reverse=True)

        # Limit results
        logs_to_show = server_logs[:limit or 10]

        if not logs_to_show:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="📋 Moderation Logs",
                    description="No moderation actions recorded yet.",
                    color=EmbedColors.BLUE
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("📋 **Moderation Logs:**\nNo actions recorded yet.")
            return

        # Format logs
        log_text = ""
        for log in logs_to_show:
            timestamp = log['timestamp'].strftime("%Y-%m-%d %H:%M")
            action = log['action'].upper()
            user_id = log['user_id']
            reason = log.get('reason', 'No reason')

            try:
                user = await self.fetch_user(user_id)
                user_name = user.display_name
            except:
                user_name = f"User {user_id}"

            log_text += f"**{timestamp}** - {action} | {user_name} | {reason}\n"

        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="📋 Moderation Logs",
                description=log_text[:2000],  # Discord embed limit
                color=EmbedColors.BLUE
            )
            embed.set_footer(
                text=f"Showing {len(logs_to_show)} of {len(server_logs)} total actions")
            await ctx.send(embed=embed)
        else:
            response = f"📋 **Moderation Logs** ({len(logs_to_show)}/{len(server_logs)}):\n\n{log_text}"
            await ctx.send(response[:2000])

    @commands.command(name="blacklist")
    @commands.has_permissions(manage_messages=True)
    async def blacklist_command(self, ctx: commands.Context, action: Optional[str] = None, *, word: Optional[str] = None):
        # Manage blacklist (Admin only). Usage: !blacklist add/remove [word] or !blacklist list
        if not ctx.guild:
            await ctx.send("❌ This command only works in servers!")
            return

        server_id = ctx.guild.id

        if server_id not in self.blacklist:
            self.blacklist[server_id] = set()

        if not action:
            # Show blacklist
            if not self.blacklist[server_id]:
                await ctx.send("📋 **Blacklist:** Empty")
            else:
                words = ", ".join(list(self.blacklist[server_id])[:20])
                await ctx.send(f"📋 **Blacklist:** {words}")
            return

        action_lower = action.lower()

        if action_lower == 'add' and word:
            self.blacklist[server_id].add(word.lower())
            await ctx.send(f"✅ Added '{word}' to blacklist")
        elif action_lower == 'remove' and word:
            if word.lower() in self.blacklist[server_id]:
                self.blacklist[server_id].remove(word.lower())
                await ctx.send(f"✅ Removed '{word}' from blacklist")
            else:
                await ctx.send(f"❌ '{word}' not in blacklist")
        elif action_lower == 'list':
            if not self.blacklist[server_id]:
                await ctx.send("📋 **Blacklist:** Empty")
            else:
                words = ", ".join(list(self.blacklist[server_id])[:20])
                await ctx.send(f"📋 **Blacklist:** {words}")
        else:
            await ctx.send("❌ Usage: `!blacklist add [word]` or `!blacklist remove [word]` or `!blacklist list`")

    @commands.command(name="whitelist")
    @commands.has_permissions(manage_messages=True)
    async def whitelist_command(self, ctx: commands.Context, action: Optional[str] = None, member: discord.Member = None):
        # Manage whitelist (Admin only). Usage: !whitelist add/remove @user or !whitelist list
        if not ctx.guild:
            await ctx.send("❌ This command only works in servers!")
            return

        server_id = ctx.guild.id

        if server_id not in self.whitelist:
            self.whitelist[server_id] = set()

        if not action:
            # Show whitelist
            if not self.whitelist[server_id]:
                await ctx.send("📋 **Whitelist:** Empty")
            else:
                user_list = []
                for user_id in list(self.whitelist[server_id])[:20]:
                    try:
                        user = await self.fetch_user(user_id)
                        user_list.append(user.display_name)
                    except:
                        user_list.append(f"User {user_id}")
                await ctx.send(f"📋 **Whitelist:** {', '.join(user_list)}")
            return

        action_lower = action.lower()

        if action_lower == 'add' and member:
            self.whitelist[server_id].add(member.id)
            await ctx.send(f"✅ Added {member.mention} to whitelist")
        elif action_lower == 'remove' and member:
            if member.id in self.whitelist[server_id]:
                self.whitelist[server_id].remove(member.id)
                await ctx.send(f"✅ Removed {member.mention} from whitelist")
            else:
                await ctx.send(f"❌ {member.mention} not in whitelist")
        elif action_lower == 'list':
            if not self.whitelist[server_id]:
                await ctx.send("📋 **Whitelist:** Empty")
            else:
                user_list = []
                for user_id in list(self.whitelist[server_id])[:20]:
                    try:
                        user = await self.fetch_user(user_id)
                        user_list.append(user.display_name)
                    except:
                        user_list.append(f"User {user_id}")
                await ctx.send(f"📋 **Whitelist:** {', '.join(user_list)}")
        else:
            await ctx.send("❌ Usage: `!whitelist add @user` or `!whitelist remove @user` or `!whitelist list`")

    # ========== PERMISSION COMMANDS ==========

    @commands.command(name="permissions", aliases=["perms", "perm"])
    async def permissions_command(self, ctx: commands.Context):
        # Show your permission level and rate limits
        user_id = ctx.author.id
        level = self._get_user_permission_level(user_id, ctx.guild)
        rate_limit = self._get_rate_limit_for_level(level)

        # Get level info
        level_info = {
            'owner': {
                'name': '👑 Owner',
                'description': 'Full access to all features',
                'rate_limit': 'Unlimited',
                'features': ['All commands', 'Unlimited rate limit', 'Premium features', 'Admin features']
            },
            'admin': {
                'name': '🛡️ Admin',
                'description': 'Server administrator',
                'rate_limit': f'{rate_limit} messages/minute',
                'features': ['Moderation commands', 'Server management', 'Higher rate limit']
            },
            'premium': {
                'name': '⭐ Premium',
                'description': 'Premium supporter',
                'rate_limit': f'{rate_limit} messages/minute',
                'features': ['Premium features', 'Higher rate limit', 'Priority support']
            },
            'regular': {
                'name': '👤 Regular',
                'description': 'Standard user',
                'rate_limit': f'{rate_limit} messages/minute',
                'features': ['Standard features', 'Basic rate limit']
            }
        }

        info = level_info.get(level, level_info['regular'])

        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="🔐 Your Permissions",
                description=f"**Level:** {info['name']}\n**Description:** {info['description']}\n**Rate Limit:** {info['rate_limit']}",
                color=EmbedColors.BLUE
            )

            # Add features
            features_text = "\n".join(
                [f"• {feature}" for feature in info['features']])
            embed.add_field(
                name="✨ Features",
                value=features_text,
                inline=False
            )

            # Add premium info if not premium
            if level != 'premium' and level != 'owner':
                embed.set_footer(
                    text="Contact server owner for premium access")

            await ctx.send(embed=embed)
        else:
            response = f"🔐 **Your Permissions**\n\n"
            response += f"**Level:** {info['name']}\n"
            response += f"**Description:** {info['description']}\n"
            response += f"**Rate Limit:** {info['rate_limit']}\n\n"
            response += f"**Features:**\n" + \
                "\n".join([f"• {feature}" for feature in info['features']])
            await ctx.send(response)

    @commands.command(name="setpremium")
    @commands.is_owner()
    async def setpremium_command(self, ctx: commands.Context, member: Optional[discord.Member] = None, action: Optional[str] = None):
        # Grant or revoke premium access (Owner only). Usage: !setpremium @user add/remove or !setpremium list
        if not member and action != 'list':
            await ctx.send("❌ Please mention a user or use `!setpremium list`!")
            return

        if action == 'list':
            # List premium users
            if not self.premium_users:
                await ctx.send("📋 **Premium Users:** None")
                return

            premium_list = []
            for user_id in list(self.premium_users)[:20]:  # Limit to 20
                try:
                    user = await self.fetch_user(user_id)
                    premium_list.append(user.display_name)
                except:
                    premium_list.append(f"User {user_id}")

            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="⭐ Premium Users",
                    description="\n".join(
                        premium_list) if premium_list else "None",
                    color=EmbedColors.PURPLE
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"⭐ **Premium Users:**\n" + "\n".join(premium_list) if premium_list else "None")
            return

        if not member:
            await ctx.send("❌ Please mention a user!")
            return

        action_lower = (action or 'add').lower()

        if action_lower == 'add':
            self.premium_users.add(member.id)
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_success_embed(
                    title="✅ Premium Granted",
                    description=f"{member.mention} has been granted premium access!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"✅ {member.mention} has been granted premium access!")
        elif action_lower == 'remove':
            if member.id in self.premium_users:
                self.premium_users.remove(member.id)
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_info_embed(
                        title="❌ Premium Removed",
                        description=f"{member.mention} no longer has premium access.",
                        color=EmbedColors.RED
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"❌ {member.mention} no longer has premium access.")
            else:
                await ctx.send(f"❌ {member.mention} is not a premium user.")
        else:
            await ctx.send("❌ Usage: `!setpremium @user add` or `!setpremium @user remove` or `!setpremium list`")

    def _check_premium_feature(self, user_id: int) -> bool:
        # Check if user has access to premium features. Returns True if user has premium access
        level = self._get_user_permission_level(user_id)
        return level in ['owner', 'premium']

    @commands.command(name="teach")
    async def teach_command(self, ctx: commands.Context, *, fact: str):
        # Teach the bot something about you. Usage: !teach [fact]
        if not self.memory_manager:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Memory Unavailable",
                    description="Memory manager not available!"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Memory manager not available!")
            return

        if not fact or len(fact.strip()) < 3:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Invalid Input",
                    description="Please provide a fact to teach me! Example: `!teach My name is John`"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Please provide a fact! Example: `!teach My name is John`")
            return

        try:
            user_id = str(ctx.author.id)
            channel_id = str(ctx.channel.id)

            # Parse fact (simple extraction)
            fact_lower = fact.lower().strip()

            # Extract fact key and value
            fact_key = None
            fact_value = None
            importance_score = 0.6

            # Common patterns
            patterns = [
                (r"my name is (.+)", "name", 0.9),
                (r"i am (.+)", "name", 0.8),
                (r"i'm (.+)", "name", 0.8),
                (r"call me (.+)", "name", 0.9),
                (r"i like (.+)", "likes", 0.7),
                (r"i love (.+)", "loves", 0.8),
                (r"i prefer (.+)", "preference", 0.7),
                (r"my favorite (.+) is (.+)", None, 0.7),  # Special case
                (r"i'm from (.+)", "location", 0.8),
                (r"i live in (.+)", "location", 0.8),
                (r"i work as (.+)", "occupation", 0.8),
                (r"i'm a (.+)", "occupation", 0.8),
                (r"i have (.+)", "has", 0.6),
                (r"i'm allergic to (.+)", "allergy", 0.9),
            ]

            import re
            matched = False

            for pattern, key, importance in patterns:
                match = re.search(pattern, fact_lower)
                if match:
                    matched = True
                    if key is None:
                        # Special case for "my favorite X is Y"
                        groups = match.groups()
                        fact_key = f"favorite_{groups[0].replace(' ', '_')}"
                        fact_value = groups[1]
                    else:
                        fact_key = key
                        fact_value = match.group(1)
                    importance_score = importance
                    break

            # If no pattern matched, use first few words as key
            if not matched:
                words = fact.split()
                if len(words) >= 2:
                    fact_key = words[0].lower()
                    fact_value = " ".join(words[1:])
                else:
                    fact_key = "fact"
                    fact_value = fact

            # Store fact
            fact_id = self.memory_manager.add_user_fact(
                user_id=user_id,
                channel_id=channel_id,
                fact_key=fact_key,
                fact_value=fact_value.strip(),
                importance_score=importance_score
            )

            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_success_embed(
                    title="✅ Learned!",
                    description=f"I'll remember that!",
                    details=(
                        f"**Fact:** {fact_key.title()}\n"
                        f"**Value:** {fact_value}\n\n"
                        f"I'll use this information in future conversations!"
                    )
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(
                    f"✅ **Learned!**\n"
                    f"I'll remember: **{fact_key.title()}** = {fact_value}\n"
                    f"I'll use this in future conversations!"
                )

            print(
                f"[OK] Fact stored: {fact_key} = {fact_value} for user {user_id}")

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Error",
                    description="Error storing fact",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Error: {str(e)}")
            print(f"[ERROR] Teach command failed: {e}")
            import traceback
            traceback.print_exc()

    # ========== BACKUP COMMANDS ==========

    async def _backup_scheduler(self):
        # Daily backup scheduler
        while True:
            try:
                # Wait until next backup time (daily at 2 AM)
                now = datetime.now()
                next_backup = now.replace(
                    hour=2, minute=0, second=0, microsecond=0)
                if next_backup <= now:
                    next_backup += timedelta(days=1)

                wait_seconds = (next_backup - now).total_seconds()
                print(
                    f"[BACKUP] Next automatic backup scheduled for {next_backup.strftime('%Y-%m-%d %H:%M:%S')}")
                await asyncio.sleep(wait_seconds)

                # Perform backup
                await self._perform_backup(automatic=True)

                # Cleanup old backups
                await self._cleanup_old_backups()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] Backup scheduler error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retrying

    async def _perform_backup(self, automatic: bool = False) -> Dict:
        # Perform database backup. Args: automatic (bool). Returns: Backup result dictionary
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_info = {
                'timestamp': timestamp,
                'date': datetime.now().strftime("%Y-%m-%d"),
                'time': datetime.now().strftime("%H:%M:%S"),
                'automatic': automatic,
                'files': [],
                'success': False,
                'error': None
            }

            # List of databases to backup
            databases = []

            # Add databases from various components
            if self.memory_manager:
                databases.append(
                    ('bot_memory.db', self.memory_manager.db_path))
            if self.conversation_logger:
                databases.append(
                    ('conversation_logs.db', self.conversation_logger.db_path))
            if self.statistics_tracker:
                databases.append(
                    ('bot_statistics.db', self.statistics_tracker.db_path))
            if self.response_tracker and hasattr(self.response_tracker, 'db_path'):
                databases.append(
                    ('response_times.db', self.response_tracker.db_path))

            # Also check for common database files
            common_dbs = ['bot_memory.db', 'conversation_logs.db',
                          'bot_statistics.db', 'response_times.db']
            for db_name in common_dbs:
                if os.path.exists(db_name) and db_name not in [d[0] for d in databases]:
                    databases.append((db_name, db_name))

            if not databases:
                backup_info['error'] = "No databases found to backup"
                return backup_info

            # Create backup directory for this timestamp
            backup_folder = os.path.join(self.backup_dir, timestamp)
            os.makedirs(backup_folder, exist_ok=True)

            # Backup each database
            for db_name, db_path in databases:
                if os.path.exists(db_path):
                    backup_file = os.path.join(backup_folder, db_name)
                    shutil.copy2(db_path, backup_file)
                    backup_info['files'].append({
                        'name': db_name,
                        'path': backup_file,
                        'size': os.path.getsize(backup_file)
                    })
                    print(f"[BACKUP] Backed up {db_name} to {backup_file}")

            if backup_info['files']:
                backup_info['success'] = True
                self.backups.append(backup_info)

                # Keep only metadata for last 30 backups
                if len(self.backups) > 30:
                    self.backups.pop(0)

                # Send notification
                await self._send_backup_notification(backup_info, success=True)

                print(
                    f"[BACKUP] Backup completed successfully: {len(backup_info['files'])} files")
            else:
                backup_info['error'] = "No files were backed up"
                await self._send_backup_notification(backup_info, success=False)

            return backup_info

        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Backup failed: {error_msg}")
            import traceback
            traceback.print_exc()

            backup_info = {
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'date': datetime.now().strftime("%Y-%m-%d"),
                'time': datetime.now().strftime("%H:%M:%S"),
                'automatic': automatic,
                'success': False,
                'error': error_msg
            }
            await self._send_backup_notification(backup_info, success=False)
            return backup_info

    async def _cleanup_old_backups(self):
        # Remove backups older than retention period
        try:
            cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)

            # Get all backup folders
            if not os.path.exists(self.backup_dir):
                return

            removed_count = 0
            for folder_name in os.listdir(self.backup_dir):
                folder_path = os.path.join(self.backup_dir, folder_name)
                if os.path.isdir(folder_path):
                    # Parse timestamp from folder name
                    try:
                        folder_date = datetime.strptime(
                            folder_name.split('_')[0], "%Y%m%d")
                        if folder_date < cutoff_date:
                            shutil.rmtree(folder_path)
                            removed_count += 1
                            print(
                                f"[BACKUP] Removed old backup: {folder_name}")
                    except:
                        pass

            if removed_count > 0:
                print(f"[BACKUP] Cleaned up {removed_count} old backup(s)")

        except Exception as e:
            print(f"[ERROR] Backup cleanup failed: {e}")

    async def _send_backup_notification(self, backup_info: Dict, success: bool):
        # Send backup notification to owner
        try:
            owner_id = self.owner_id if hasattr(self, 'owner_id') else None
            if not owner_id:
                return

            owner = await self.fetch_user(owner_id)
            if not owner:
                return

            if success:
                backup_type = "Automatic" if backup_info.get(
                    'automatic') else "Manual"
                total_size = sum(f['size']
                                 for f in backup_info.get('files', []))
                size_mb = total_size / (1024 * 1024)

                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_success_embed(
                        title="✅ Backup Successful",
                        description=f"{backup_type} backup completed successfully!",
                        details=(
                            f"**Date:** {backup_info['date']} {backup_info['time']}\n"
                            f"**Files:** {len(backup_info['files'])} database(s)\n"
                            f"**Size:** {size_mb:.2f} MB\n"
                            f"**Backup ID:** {backup_info['timestamp']}"
                        )
                    )
                    await owner.send(embed=embed)
                else:
                    await owner.send(
                        f"✅ **Backup Successful**\n\n"
                        f"{backup_type} backup completed!\n"
                        f"Date: {backup_info['date']} {backup_info['time']}\n"
                        f"Files: {len(backup_info['files'])} database(s)\n"
                        f"Size: {size_mb:.2f} MB"
                    )
            else:
                error_msg = backup_info.get('error', 'Unknown error')
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_error_embed(
                        title="❌ Backup Failed",
                        description="Backup operation failed!",
                        error_details=error_msg
                    )
                    await owner.send(embed=embed)
                else:
                    await owner.send(f"❌ **Backup Failed**\n\nError: {error_msg}")

        except Exception as e:
            print(f"[ERROR] Failed to send backup notification: {e}")

    @commands.command(name="backup")
    async def backup_command(self, ctx: commands.Context, action: Optional[str] = None):
        # Perform manual backup or show backup info. Usage: !backup now or !backup
        if action and action.lower() == 'now':
            # Check permissions (owner or admin)
            if not ctx.author.guild_permissions.administrator and ctx.author.id != self.owner_id:
                await ctx.send("❌ You need administrator permissions to create backups!")
                return

            await ctx.send("🔄 Creating backup... This may take a moment.")

            backup_info = await self._perform_backup(automatic=False)

            if backup_info['success']:
                total_size = sum(f['size']
                                 for f in backup_info.get('files', []))
                size_mb = total_size / (1024 * 1024)

                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_success_embed(
                        title="✅ Backup Created",
                        description=f"Backup completed successfully!\n\n"
                        f"**Files:** {len(backup_info['files'])} database(s)\n"
                        f"**Size:** {size_mb:.2f} MB\n"
                        f"**Backup ID:** {backup_info['timestamp']}",
                        details="Backup saved to backups folder"
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"✅ **Backup Created**\n\n"
                                   f"Files: {len(backup_info['files'])} database(s)\n"
                                   f"Size: {size_mb:.2f} MB\n"
                                   f"Backup ID: {backup_info['timestamp']}")
            else:
                error_msg = backup_info.get('error', 'Unknown error')
                if EMBED_HELPER_AVAILABLE:
                    embed = EmbedHelper.create_error_embed(
                        title="❌ Backup Failed",
                        description="Failed to create backup",
                        error_details=error_msg
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"❌ Backup failed: {error_msg}")
        else:
            # Show backup info
            if not os.path.exists(self.backup_dir):
                await ctx.send("📦 **Backups:** No backups folder found.")
                return

            # Count backups
            backup_count = 0
            total_size = 0
            for folder_name in os.listdir(self.backup_dir):
                folder_path = os.path.join(self.backup_dir, folder_name)
                if os.path.isdir(folder_path):
                    backup_count += 1
                    for file_name in os.listdir(folder_path):
                        file_path = os.path.join(folder_path, file_name)
                        if os.path.isfile(file_path):
                            total_size += os.path.getsize(file_path)

            size_mb = total_size / (1024 * 1024)

            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_info_embed(
                    title="📦 Backup Information",
                    description=f"**Total Backups:** {backup_count}\n**Total Size:** {size_mb:.2f} MB\n**Retention:** {self.backup_retention_days} days",
                    color=EmbedColors.BLUE
                )
                embed.add_field(
                    name="Commands",
                    value="`!backup now` - Create backup now\n`!backups list` - List all backups\n`!restore [date]` - Restore backup (Owner)",
                    inline=False
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"📦 **Backup Information**\n\n"
                               f"Total Backups: {backup_count}\n"
                               f"Total Size: {size_mb:.2f} MB\n"
                               f"Retention: {self.backup_retention_days} days\n\n"
                               f"Commands:\n"
                               f"`!backup now` - Create backup now\n"
                               f"`!backups list` - List all backups\n"
                               f"`!restore [date]` - Restore backup (Owner)")

    @commands.command(name="backups")
    async def backups_command(self, ctx: commands.Context, action: Optional[str] = None):
        # List available backups. Usage: !backups list
        if not ctx.author.guild_permissions.administrator and ctx.author.id != self.owner_id:
            await ctx.send("❌ You need administrator permissions to list backups!")
            return

        if not os.path.exists(self.backup_dir):
            await ctx.send("📦 **Backups:** No backups found.")
            return

        # Get all backups
        backup_list = []
        # Last 20
        for folder_name in sorted(os.listdir(self.backup_dir), reverse=True)[:20]:
            folder_path = os.path.join(self.backup_dir, folder_name)
            if os.path.isdir(folder_path):
                try:
                    # Parse timestamp
                    date_str = folder_name.split('_')[0]
                    time_str = folder_name.split(
                        '_')[1] if '_' in folder_name else "000000"
                    backup_date = datetime.strptime(
                        date_str, "%Y%m%d").strftime("%Y-%m-%d")
                    backup_time = f"{time_str[:2]}:{time_str[2:4]}" if len(
                        time_str) >= 4 else "00:00"

                    # Calculate size
                    folder_size = 0
                    file_count = 0
                    for file_name in os.listdir(folder_path):
                        file_path = os.path.join(folder_path, file_name)
                        if os.path.isfile(file_path):
                            folder_size += os.path.getsize(file_path)
                            file_count += 1

                    size_mb = folder_size / (1024 * 1024)
                    backup_list.append({
                        'id': folder_name,
                        'date': backup_date,
                        'time': backup_time,
                        'size': size_mb,
                        'files': file_count
                    })
                except:
                    pass

        if not backup_list:
            await ctx.send("📦 **Backups:** No backups found.")
            return

        # Format list
        backup_text = ""
        for backup in backup_list[:10]:  # Show last 10
            backup_text += f"**{backup['date']} {backup['time']}** - {backup['files']} file(s), {backup['size']:.2f} MB\n"

        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="📦 Available Backups",
                description=backup_text,
                color=EmbedColors.BLUE
            )
            embed.set_footer(
                text=f"Showing {len(backup_list[:10])} of {len(backup_list)} backups")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"📦 **Available Backups** ({len(backup_list)} total):\n\n{backup_text}")

    @commands.command(name="restore")
    @commands.is_owner()
    async def restore_command(self, ctx: commands.Context, backup_id: Optional[str] = None):
        # Restore database from backup (Owner only). Usage: !restore [backup_id] or !restore latest
        if not backup_id:
            await ctx.send("❌ Usage: `!restore [backup_id]` or `!restore latest`\nUse `!backups list` to see available backups.")
            return

        try:
            # Find backup folder
            backup_folder = None

            if backup_id.lower() == 'latest':
                # Find latest backup
                if not os.path.exists(self.backup_dir):
                    await ctx.send("❌ No backups found!")
                    return

                folders = [f for f in os.listdir(self.backup_dir) if os.path.isdir(
                    os.path.join(self.backup_dir, f))]
                if not folders:
                    await ctx.send("❌ No backups found!")
                    return

                folders.sort(reverse=True)
                backup_folder = os.path.join(self.backup_dir, folders[0])
            else:
                # Find specific backup
                backup_folder = os.path.join(self.backup_dir, backup_id)
                if not os.path.exists(backup_folder):
                    await ctx.send(f"❌ Backup **{backup_id}** not found!")
                    return

            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="⚠️ WARNING",
                    description="This will overwrite current databases!",
                    error_details="Reply with 'confirm' in the next 30 seconds to proceed."
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("⚠️ **WARNING:** This will overwrite current databases! Reply with 'confirm' to proceed.")

            # Wait for confirmation
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'confirm'

            try:
                confirmation = await ctx.bot.wait_for('message', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("❌ Restore cancelled - no confirmation received.")
                return

            # Restore databases
            restored_files = []
            for file_name in os.listdir(backup_folder):
                file_path = os.path.join(backup_folder, file_name)
                if os.path.isfile(file_path) and file_name.endswith('.db'):
                    # Copy backup file to current location
                    shutil.copy2(file_path, file_name)
                    restored_files.append(file_name)
                    print(f"[RESTORE] Restored {file_name}")

            if restored_files:
                if EMBED_HELPER_AVAILABLE:
                    files_list = "\n".join([f"• {f}" for f in restored_files])
                    embed = EmbedHelper.create_success_embed(
                        title="✅ Restore Complete",
                        description=f"Restored {len(restored_files)} database(s):\n{files_list}",
                        details="Bot restart recommended to load restored data"
                    )
                    await ctx.send(embed=embed)
                else:
                    files_list = "\n".join([f"• {f}" for f in restored_files])
                    await ctx.send(f"✅ **Restore Complete**\n\nRestored {len(restored_files)} database(s):\n{files_list}")
            else:
                await ctx.send("❌ No database files found in backup!")

        except Exception as e:
            if EMBED_HELPER_AVAILABLE:
                embed = EmbedHelper.create_error_embed(
                    title="❌ Restore Failed",
                    description="Failed to restore backup",
                    error_details=str(e)
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Restore failed: {str(e)}")
            print(f"[ERROR] Restore failed: {e}")
            import traceback
            traceback.print_exc()

    async def close(self):
        # Called when bot is shutting down
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()

        # Stop webhook server
        if self.webhook_server:
            try:
                await self.webhook_server.cleanup()
                print("[WEBHOOK] Webhook server stopped")
            except Exception as e:
                print(f"[ERROR] Error stopping webhook server: {e}")

        await super().close()


# End of AIBootBot class

async def main():
    # Main function to run the bot
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
