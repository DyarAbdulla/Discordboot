"""
Database Handler - SQLite database for storing user preferences and history
"""

import sqlite3
import aiosqlite
import json
from typing import Optional, Dict, List
from datetime import datetime
import os


class Database:
    """Handles SQLite database operations"""
    
    def __init__(self, db_path: str = "bot.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self):
        """Initialize database tables"""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # User preferences table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    server_id INTEGER,
                    user_id INTEGER,
                    preference_key TEXT,
                    preference_value TEXT,
                    PRIMARY KEY (server_id, user_id, preference_key)
                )
            """)
            
            # Conversation history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER,
                    channel_id INTEGER,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Server settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_settings (
                    server_id INTEGER PRIMARY KEY,
                    settings_json TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Bot statistics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER,
                    channel_id INTEGER,
                    message_count INTEGER DEFAULT 0,
                    command_count INTEGER DEFAULT 0,
                    date DATE DEFAULT CURRENT_DATE,
                    UNIQUE(server_id, channel_id, date)
                )
            """)
            
            await db.commit()
        
        self._initialized = True
    
    async def get_user_preference(
        self,
        server_id: int,
        user_id: int,
        key: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get user preference
        
        Args:
            server_id: Discord server ID
            user_id: Discord user ID
            key: Preference key
            default: Default value if not found
            
        Returns:
            Preference value or default
        """
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT preference_value FROM user_preferences WHERE server_id = ? AND user_id = ? AND preference_key = ?",
                (server_id, user_id, key)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default
    
    async def set_user_preference(
        self,
        server_id: int,
        user_id: int,
        key: str,
        value: str
    ):
        """
        Set user preference
        
        Args:
            server_id: Discord server ID
            user_id: Discord user ID
            key: Preference key
            value: Preference value
        """
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO user_preferences 
                   (server_id, user_id, preference_key, preference_value) 
                   VALUES (?, ?, ?, ?)""",
                (server_id, user_id, key, value)
            )
            await db.commit()
    
    async def add_conversation_message(
        self,
        server_id: Optional[int],
        channel_id: int,
        user_id: int,
        role: str,
        content: str
    ):
        """
        Add conversation message to history
        
        Args:
            server_id: Discord server ID (None for DMs)
            channel_id: Discord channel ID
            user_id: Discord user ID
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO conversation_history 
                   (server_id, channel_id, user_id, role, content) 
                   VALUES (?, ?, ?, ?, ?)""",
                (server_id, channel_id, user_id, role, content)
            )
            await db.commit()
    
    async def get_conversation_history(
        self,
        channel_id: int,
        limit: int = 15
    ) -> List[Dict]:
        """
        Get conversation history for a channel
        
        Args:
            channel_id: Discord channel ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries
        """
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT role, content FROM conversation_history 
                   WHERE channel_id = ? 
                   ORDER BY timestamp DESC LIMIT ?""",
                (channel_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                # Reverse to get chronological order
                return [{"role": row[0], "content": row[1]} for row in reversed(rows)]
    
    async def clear_conversation_history(self, channel_id: int):
        """
        Clear conversation history for a channel
        
        Args:
            channel_id: Discord channel ID
        """
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM conversation_history WHERE channel_id = ?",
                (channel_id,)
            )
            await db.commit()
    
    async def get_server_settings(self, server_id: int) -> Dict:
        """
        Get server settings
        
        Args:
            server_id: Discord server ID
            
        Returns:
            Server settings dictionary
        """
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT settings_json FROM server_settings WHERE server_id = ?",
                (server_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return {}
    
    async def set_server_settings(self, server_id: int, settings: Dict):
        """
        Set server settings
        
        Args:
            server_id: Discord server ID
            settings: Settings dictionary
        """
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO server_settings 
                   (server_id, settings_json, updated_at) 
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (server_id, json.dumps(settings))
            )
            await db.commit()
    
    async def increment_stat(self, server_id: Optional[int], channel_id: int, stat_type: str = "message"):
        """
        Increment bot statistics
        
        Args:
            server_id: Discord server ID (None for DMs)
            channel_id: Discord channel ID
            stat_type: Type of stat ('message' or 'command')
        """
        await self.initialize()
        
        column = "message_count" if stat_type == "message" else "command_count"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""INSERT INTO bot_stats (server_id, channel_id, {column}, date)
                   VALUES (?, ?, 1, CURRENT_DATE)
                   ON CONFLICT(server_id, channel_id, date) 
                   DO UPDATE SET {column} = {column} + 1""",
                (server_id, channel_id)
            )
            await db.commit()
    
    async def get_stats(self, days: int = 7) -> Dict:
        """
        Get bot statistics
        
        Args:
            days: Number of days to look back
            
        Returns:
            Statistics dictionary
        """
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT SUM(message_count), SUM(command_count), COUNT(DISTINCT server_id)
                   FROM bot_stats 
                   WHERE date >= date('now', '-' || ? || ' days')""",
                (days,)
            ) as cursor:
                row = await cursor.fetchone()
                return {
                    "total_messages": row[0] or 0,
                    "total_commands": row[1] or 0,
                    "servers": row[2] or 0
                }

