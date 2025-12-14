"""
Memory Manager - Persistent Conversation History
Handles short-term and long-term memory for the Discord bot

ARCHITECTURE:
- Short-term memory: Last N messages (e.g., 30) sent directly to API
- Long-term memory: Summarized older conversations stored separately
- Database: SQLite for persistence across restarts
"""

import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class MemoryManager:
    """
    Manages persistent conversation memory using SQLite database
    
    Database Schema:
    - conversations: Stores individual messages
    - summaries: Stores conversation summaries for long-term memory
    """
    
    def __init__(self, db_path: str = "bot_memory.db", short_term_limit: int = 30):
        """
        Initialize memory manager
        
        Args:
            db_path: Path to SQLite database file
            short_term_limit: Maximum number of recent messages to keep in short-term memory
        """
        self.db_path = db_path
        self.short_term_limit = short_term_limit
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for individual messages (short-term memory)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_channel (user_id, channel_id),
                INDEX idx_timestamp (timestamp)
            )
        """)
        
        # Table for conversation summaries (long-term memory)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                message_count INTEGER NOT NULL,
                start_timestamp DATETIME NOT NULL,
                end_timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_channel (user_id, channel_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print(f"[OK] Memory database initialized: {self.db_path}")
    
    def add_message(
        self,
        user_id: str,
        channel_id: str,
        role: str,
        content: str
    ) -> int:
        """
        Add a message to the conversation history
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID (or DM channel ID)
            role: 'user' or 'assistant'
            content: Message content
            
        Returns:
            Message ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations (user_id, channel_id, role, content)
            VALUES (?, ?, ?, ?)
        """, (str(user_id), str(channel_id), role, content))
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return message_id
    
    def get_recent_messages(
        self,
        user_id: str,
        channel_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, any]]:
        """
        Get recent messages for short-term memory
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            limit: Maximum number of messages (defaults to short_term_limit)
            
        Returns:
            List of message dicts with 'role' and 'content'
        """
        if limit is None:
            limit = self.short_term_limit
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, timestamp
            FROM conversations
            WHERE user_id = ? AND channel_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (str(user_id), str(channel_id), limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Reverse to get chronological order (oldest first)
        messages = [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in reversed(rows)
        ]
        
        return messages
    
    def get_summaries(
        self,
        user_id: str,
        channel_id: str
    ) -> List[Dict[str, any]]:
        """
        Get conversation summaries for long-term memory
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            
        Returns:
            List of summary dicts ordered by end_timestamp (oldest first)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT summary_text, message_count, start_timestamp, end_timestamp
            FROM summaries
            WHERE user_id = ? AND channel_id = ?
            ORDER BY end_timestamp ASC
        """, (str(user_id), str(channel_id)))
        
        rows = cursor.fetchall()
        conn.close()
        
        summaries = [
            {
                "summary": row[0],
                "message_count": row[1],
                "start_timestamp": row[2],
                "end_timestamp": row[3]
            }
            for row in rows
        ]
        
        return summaries
    
    def create_summary(
        self,
        user_id: str,
        channel_id: str,
        summary_text: str,
        message_count: int,
        start_timestamp: datetime,
        end_timestamp: datetime
    ) -> int:
        """
        Create a conversation summary for long-term memory
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            summary_text: Summary of the conversation
            message_count: Number of messages summarized
            start_timestamp: Start time of summarized period
            end_timestamp: End time of summarized period
            
        Returns:
            Summary ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO summaries (user_id, channel_id, summary_text, message_count, start_timestamp, end_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(user_id),
            str(channel_id),
            summary_text,
            message_count,
            start_timestamp.isoformat(),
            end_timestamp.isoformat()
        ))
        
        summary_id = cursor.lastrowid
        
        # Delete the messages that were summarized (keep only recent ones)
        cursor.execute("""
            DELETE FROM conversations
            WHERE user_id = ? AND channel_id = ?
            AND timestamp >= ? AND timestamp <= ?
        """, (
            str(user_id),
            str(channel_id),
            start_timestamp.isoformat(),
            end_timestamp.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return summary_id
    
    def get_conversation_context(
        self,
        user_id: str,
        channel_id: str,
        include_summaries: bool = True
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Get full conversation context (summaries + recent messages)
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            include_summaries: Whether to include long-term memory summaries
            
        Returns:
            Tuple of (messages_list, summary_texts)
            - messages_list: List of recent messages for API
            - summary_texts: List of summary strings for system context
        """
        # Get recent messages (short-term memory)
        messages = self.get_recent_messages(user_id, channel_id)
        
        # Get summaries (long-term memory)
        summaries = []
        if include_summaries:
            summaries = self.get_summaries(user_id, channel_id)
        
        # Format summaries as text
        summary_texts = [
            f"Previous conversation summary ({s['message_count']} messages, {s['start_timestamp']} to {s['end_timestamp']}): {s['summary']}"
            for s in summaries
        ]
        
        # Convert messages to API format
        api_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
        
        return api_messages, summary_texts
    
    def cleanup_old_messages(self, days: int = 30):
        """
        Delete messages older than specified days
        (Summaries are kept indefinitely)
        
        Args:
            days: Delete messages older than this many days
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            DELETE FROM conversations
            WHERE timestamp < ?
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"[INFO] Cleaned up {deleted_count} old messages (older than {days} days)")
        return deleted_count
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count messages
        cursor.execute("SELECT COUNT(*) FROM conversations")
        message_count = cursor.fetchone()[0]
        
        # Count summaries
        cursor.execute("SELECT COUNT(*) FROM summaries")
        summary_count = cursor.fetchone()[0]
        
        # Count unique users
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM conversations")
        user_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_messages": message_count,
            "total_summaries": summary_count,
            "unique_users": user_count
        }

