"""
Advanced Analytics and Tracking System
Tracks detailed statistics for users, servers, APIs, and interactions
"""

import sqlite3
import aiosqlite
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json


class AnalyticsTracker:
    """Tracks comprehensive analytics for the bot"""
    
    def __init__(self, db_path: str = "analytics.db"):
        """
        Initialize analytics tracker
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self):
        """Initialize database tables"""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Interactions table - tracks every interaction
            await db.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    username TEXT,
                    server_id TEXT,
                    channel_id TEXT NOT NULL,
                    query_text TEXT,
                    bot_response TEXT,
                    api_provider TEXT,
                    response_time REAL,
                    tokens_used INTEGER,
                    cost REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    language_detected TEXT,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT
                )
            """)
            
            # User statistics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    total_messages INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0.0,
                    preferred_language TEXT,
                    preferred_api TEXT,
                    first_seen DATETIME,
                    last_seen DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Server statistics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_stats (
                    server_id TEXT PRIMARY KEY,
                    server_name TEXT,
                    total_messages INTEGER DEFAULT 0,
                    total_users INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0.0,
                    first_seen DATETIME,
                    last_seen DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # API usage table - tracks API performance
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_provider TEXT NOT NULL,
                    date DATE NOT NULL,
                    calls INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0.0,
                    avg_response_time REAL DEFAULT 0.0,
                    UNIQUE(api_provider, date)
                )
            """)
            
            # Command usage table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS command_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_name TEXT NOT NULL,
                    user_id TEXT,
                    server_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Language distribution table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS language_usage (
                    language_code TEXT PRIMARY KEY,
                    usage_count INTEGER DEFAULT 0,
                    last_used DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_interactions_server ON interactions(server_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_interactions_api ON interactions(api_provider)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_command_usage_command ON command_usage(command_name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_command_usage_timestamp ON command_usage(timestamp)")
            
            await db.commit()
        
        self._initialized = True
    
    async def log_interaction(
        self,
        user_id: str,
        username: str,
        server_id: Optional[str],
        channel_id: str,
        query_text: str,
        bot_response: str,
        api_provider: Optional[str],
        response_time: float,
        tokens_used: int,
        cost: float,
        language_detected: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Log an interaction
        
        Args:
            user_id: User ID
            username: Username
            server_id: Server ID (None for DMs)
            channel_id: Channel ID
            query_text: User query
            bot_response: Bot response
            api_provider: API provider used
            response_time: Response time in seconds
            tokens_used: Tokens used
            cost: Cost in USD
            language_detected: Detected language
            success: Whether interaction was successful
            error_message: Error message if failed
        """
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO interactions 
                (user_id, username, server_id, channel_id, query_text, bot_response,
                 api_provider, response_time, tokens_used, cost, language_detected,
                 success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, username, server_id, channel_id, query_text, bot_response,
                api_provider, response_time, tokens_used, cost, language_detected,
                success, error_message
            ))
            
            # Update user stats
            await db.execute("""
                INSERT INTO user_stats 
                (user_id, username, total_messages, total_tokens, total_cost, 
                 first_seen, last_seen)
                VALUES (?, ?, 1, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    total_messages = total_messages + 1,
                    total_tokens = total_tokens + excluded.total_tokens,
                    total_cost = total_cost + excluded.total_cost,
                    last_seen = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, username, tokens_used, cost))
            
            # Update server stats if server_id provided
            if server_id:
                await db.execute("""
                    INSERT INTO server_stats 
                    (server_id, total_messages, total_tokens, total_cost,
                     first_seen, last_seen)
                    VALUES (?, 1, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(server_id) DO UPDATE SET
                        total_messages = total_messages + 1,
                        total_tokens = total_tokens + excluded.total_tokens,
                        total_cost = total_cost + excluded.total_cost,
                        last_seen = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """, (server_id, tokens_used, cost))
            
            # Update API usage
            if api_provider:
                today = datetime.now().date().isoformat()
                await db.execute("""
                    INSERT INTO api_usage 
                    (api_provider, date, calls, errors, total_tokens, total_cost, avg_response_time)
                    VALUES (?, ?, 1, ?, ?, ?, ?)
                    ON CONFLICT(api_provider, date) DO UPDATE SET
                        calls = calls + 1,
                        errors = errors + excluded.errors,
                        total_tokens = total_tokens + excluded.total_tokens,
                        total_cost = total_cost + excluded.total_cost,
                        avg_response_time = (avg_response_time * calls + excluded.avg_response_time) / (calls + 1)
                """, (api_provider, today, 0 if success else 1, tokens_used, cost, response_time))
            
            # Update language usage
            if language_detected:
                await db.execute("""
                    INSERT INTO language_usage 
                    (language_code, usage_count, last_used)
                    VALUES (?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(language_code) DO UPDATE SET
                        usage_count = usage_count + 1,
                        last_used = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """, (language_detected,))
            
            await db.commit()
    
    async def log_command(self, command_name: str, user_id: str, server_id: Optional[str]):
        """Log command usage"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO command_usage (command_name, user_id, server_id)
                VALUES (?, ?, ?)
            """, (command_name, user_id, server_id))
            await db.commit()
    
    async def get_user_stats(self, user_id: str) -> Dict:
        """Get statistics for a user"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM user_stats WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return {}
                
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "total_messages": row[2],
                    "total_tokens": row[3],
                    "total_cost": row[4],
                    "preferred_language": row[5],
                    "preferred_api": row[6],
                    "first_seen": row[7],
                    "last_seen": row[8]
                }
    
    async def get_server_stats(self, server_id: str) -> Dict:
        """Get statistics for a server"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM server_stats WHERE server_id = ?
            """, (server_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return {}
                
                # Get unique users count
                async with db.execute("""
                    SELECT COUNT(DISTINCT user_id) FROM interactions 
                    WHERE server_id = ?
                """, (server_id,)) as user_cursor:
                    user_count = (await user_cursor.fetchone())[0]
                
                return {
                    "server_id": row[0],
                    "server_name": row[1],
                    "total_messages": row[2],
                    "total_users": user_count,
                    "total_tokens": row[4],
                    "total_cost": row[5],
                    "first_seen": row[6],
                    "last_seen": row[7]
                }
    
    async def get_global_stats(self, days: int = 30) -> Dict:
        """Get global statistics"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Total interactions
            async with db.execute("""
                SELECT COUNT(*), SUM(tokens_used), SUM(cost), AVG(response_time)
                FROM interactions WHERE timestamp >= ?
            """, (cutoff_date,)) as cursor:
                row = await cursor.fetchone()
                total_interactions = row[0] or 0
                total_tokens = row[1] or 0
                total_cost = row[2] or 0.0
                avg_response_time = row[3] or 0.0
            
            # Unique users
            async with db.execute("""
                SELECT COUNT(DISTINCT user_id) FROM interactions WHERE timestamp >= ?
            """, (cutoff_date,)) as cursor:
                unique_users = (await cursor.fetchone())[0] or 0
            
            # Unique servers
            async with db.execute("""
                SELECT COUNT(DISTINCT server_id) FROM interactions 
                WHERE server_id IS NOT NULL AND timestamp >= ?
            """, (cutoff_date,)) as cursor:
                unique_servers = (await cursor.fetchone())[0] or 0
            
            # API breakdown
            async with db.execute("""
                SELECT api_provider, COUNT(*), SUM(cost), AVG(response_time)
                FROM interactions 
                WHERE timestamp >= ? AND api_provider IS NOT NULL
                GROUP BY api_provider
            """, (cutoff_date,)) as cursor:
                api_breakdown = {}
                async for row in cursor:
                    api_breakdown[row[0]] = {
                        "calls": row[1],
                        "total_cost": row[2] or 0.0,
                        "avg_response_time": row[3] or 0.0
                    }
            
            # Language distribution
            async with db.execute("""
                SELECT language_detected, COUNT(*) 
                FROM interactions 
                WHERE timestamp >= ? AND language_detected IS NOT NULL
                GROUP BY language_detected
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, (cutoff_date,)) as cursor:
                language_dist = {}
                async for row in cursor:
                    language_dist[row[0]] = row[1]
            
            # Most used commands
            async with db.execute("""
                SELECT command_name, COUNT(*) 
                FROM command_usage 
                WHERE timestamp >= ?
                GROUP BY command_name
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, (cutoff_date,)) as cursor:
                top_commands = {}
                async for row in cursor:
                    top_commands[row[0]] = row[1]
            
            return {
                "period_days": days,
                "total_interactions": total_interactions,
                "unique_users": unique_users,
                "unique_servers": unique_servers,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "avg_response_time": avg_response_time,
                "api_breakdown": api_breakdown,
                "language_distribution": language_dist,
                "top_commands": top_commands
            }
    
    async def get_leaderboard(self, category: str = "messages", limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get leaderboard
        
        Args:
            category: 'messages', 'tokens', 'cost'
            limit: Number of results
            
        Returns:
            List of (user_id, value) tuples
        """
        await self.initialize()
        
        column_map = {
            "messages": "total_messages",
            "tokens": "total_tokens",
            "cost": "total_cost"
        }
        
        column = column_map.get(category, "total_messages")
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f"""
                SELECT user_id, {column} 
                FROM user_stats 
                ORDER BY {column} DESC 
                LIMIT ?
            """, (limit,)) as cursor:
                results = []
                async for row in cursor:
                    results.append((row[0], row[1]))
                return results
    
    async def get_cost_analytics(self, days: int = 30) -> Dict:
        """Get cost analytics"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Daily costs
            async with db.execute("""
                SELECT DATE(timestamp) as date, SUM(cost) as daily_cost
                FROM interactions
                WHERE timestamp >= ? AND cost > 0
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (cutoff_date,)) as cursor:
                daily_costs = {}
                async for row in cursor:
                    daily_costs[row[0]] = row[1] or 0.0
            
            # API costs
            async with db.execute("""
                SELECT api_provider, SUM(cost) as total_cost
                FROM interactions
                WHERE timestamp >= ? AND api_provider IS NOT NULL AND cost > 0
                GROUP BY api_provider
            """, (cutoff_date,)) as cursor:
                api_costs = {}
                async for row in cursor:
                    api_costs[row[0]] = row[1] or 0.0
            
            # Projected monthly cost
            total_cost = sum(daily_costs.values())
            days_so_far = len(daily_costs)
            if days_so_far > 0:
                daily_avg = total_cost / days_so_far
                projected_monthly = daily_avg * 30
            else:
                projected_monthly = 0.0
            
            return {
                "total_cost": total_cost,
                "daily_costs": daily_costs,
                "api_costs": api_costs,
                "projected_monthly": projected_monthly,
                "days_analyzed": days_so_far
            }

