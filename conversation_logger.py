"""
Conversation Logger - Permanent Conversation Storage
Saves all conversations with user info, tokens, and model used for training data collection
Supports both PostgreSQL (Railway) and SQLite (fallback)
"""

import sqlite3
import csv
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Try to import PostgreSQL handler
try:
    from postgres_handler import PostgresHandler
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("[INFO] PostgreSQL handler not available, using SQLite")


class ConversationLogger:
    """
    Logs all conversations permanently for training data collection
    
    Supports:
    - PostgreSQL (Railway) - if DATABASE_URL is set
    - SQLite (fallback) - local file storage
    
    Database Schema:
    - conversations: Stores conversation pairs (user_message + bot_response)
    """
    
    def __init__(self, db_path: str = "conversation_logs.db", database_url: Optional[str] = None):
        """
        Initialize conversation logger
        
        Args:
            db_path: Path to SQLite database file (fallback)
            database_url: PostgreSQL connection URL (from Railway DATABASE_URL)
        """
        self.db_path = db_path
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.use_postgres = False
        self.postgres_handler = None
        
        # Try PostgreSQL first (Railway)
        if self.database_url and POSTGRES_AVAILABLE:
            try:
                self.postgres_handler = PostgresHandler(database_url=self.database_url)
                self.use_postgres = True
                print("[OK] Using PostgreSQL database (Railway)")
            except Exception as e:
                print(f"[WARNING] Failed to connect to PostgreSQL: {e}")
                print("[INFO] Falling back to SQLite")
                self.use_postgres = False
                self._ensure_db_exists()  # Initialize SQLite
        else:
            # Use SQLite
            if not self.database_url:
                print("[INFO] DATABASE_URL not set, using SQLite")
            self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database and table if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for conversation logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                tokens_used INTEGER DEFAULT 0,
                model_used TEXT DEFAULT 'unknown'
            )
        """)
        
        # Create indexes separately (SQLite doesn't support inline INDEX)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel_id ON conversations(channel_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_name ON conversations(user_name)")
        
        conn.commit()
        conn.close()
        print(f"[OK] Conversation logger database initialized: {self.db_path}")
    
    def log_conversation(
        self,
        user_id: str,
        user_name: str,
        channel_id: str,
        user_message: str,
        bot_response: str,
        tokens_used: int = 0,
        model_used: str = "unknown"
    ) -> int:
        """
        Log a conversation (user message + bot response)
        
        Args:
            user_id: Discord user ID
            user_name: Discord username/display name
            channel_id: Channel ID where conversation happened
            user_message: What the user said
            bot_response: What the bot replied
            tokens_used: Number of tokens used (if available)
            model_used: Model name (e.g., 'claude-3-5-haiku-20241022', 'gemini-pro', etc.)
            
        Returns:
            Conversation ID
        """
        if self.use_postgres and self.postgres_handler:
            return self.postgres_handler.log_conversation(
                user_id, user_name, channel_id, user_message, bot_response, tokens_used, model_used
            )
        
        # SQLite fallback
        # Validate inputs
        if not user_id or not user_name or not channel_id:
            raise ValueError("user_id, user_name, and channel_id are required")
        
        if not user_message or not bot_response:
            raise ValueError("user_message and bot_response cannot be empty")
        
        # Ensure values are strings (prevent SQL injection)
        user_id = str(user_id)
        user_name = str(user_name)[:100]  # Limit length
        channel_id = str(channel_id)
        model_used = str(model_used)[:50]  # Limit length
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use parameterized query to prevent SQL injection
        cursor.execute("""
            INSERT INTO conversations 
            (user_id, user_name, channel_id, user_message, bot_response, tokens_used, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, user_name, channel_id, user_message, bot_response, tokens_used, model_used))
        
        conversation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return conversation_id
    
    def get_stats(self) -> Dict:
        """
        Get conversation statistics
        
        Returns:
            Dictionary with stats: total_conversations, total_users, total_tokens, models_used
        """
        if self.use_postgres and self.postgres_handler:
            return self.postgres_handler.get_stats()
        
        # SQLite fallback
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total conversations
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_conversations = cursor.fetchone()[0]
        
        # Total unique users
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM conversations")
        total_users = cursor.fetchone()[0]
        
        # Total tokens used
        cursor.execute("SELECT SUM(tokens_used) FROM conversations")
        result = cursor.fetchone()[0]
        total_tokens = result if result else 0
        
        # Models used
        cursor.execute("SELECT DISTINCT model_used, COUNT(*) FROM conversations GROUP BY model_used")
        models_used = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Recent activity (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM conversations 
            WHERE timestamp > datetime('now', '-1 day')
        """)
        recent_24h = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_conversations": total_conversations,
            "total_users": total_users,
            "total_tokens": total_tokens,
            "models_used": models_used,
            "recent_24h": recent_24h
        }
    
    def get_user_history(
        self,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get conversation history for a user
        
        Args:
            user_id: Discord user ID (optional)
            user_name: Username to search (optional)
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation dictionaries
        """
        if self.use_postgres and self.postgres_handler:
            return self.postgres_handler.get_user_history(user_id, user_name, limit)
        
        # SQLite fallback
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                       timestamp, tokens_used, model_used
                FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (str(user_id), limit))
        elif user_name:
            cursor.execute("""
                SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                       timestamp, tokens_used, model_used
                FROM conversations
                WHERE user_name LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{user_name}%", limit))
        else:
            cursor.execute("""
                SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                       timestamp, tokens_used, model_used
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        conversations = []
        for row in rows:
            conversations.append({
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "channel_id": row[3],
                "user_message": row[4],
                "bot_response": row[5],
                "timestamp": row[6],
                "tokens_used": row[7],
                "model_used": row[8]
            })
        
        return conversations
    
    def export_to_csv(self, output_path: str = "conversation_export.csv") -> str:
        """
        Export all conversations to CSV file
        
        Args:
            output_path: Path to output CSV file
            
        Returns:
            Path to exported file
        """
        # Get all conversations (works with both PostgreSQL and SQLite)
        conversations = self.get_all_conversations(limit=None)
        
        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                'id', 'user_id', 'user_name', 'channel_id', 
                'user_message', 'bot_response', 'timestamp', 
                'tokens_used', 'model_used'
            ])
            
            # Write data
            for conv in conversations:
                writer.writerow([
                    conv['id'],
                    conv['user_id'],
                    conv['user_name'],
                    conv['channel_id'],
                    conv['user_message'],
                    conv['bot_response'],
                    conv['timestamp'],
                    conv['tokens_used'],
                    conv['model_used']
                ])
        
        print(f"[OK] Exported {len(conversations)} conversations to {output_path}")
        return output_path
    
    def get_all_conversations(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get all conversations (for export or analysis)
        
        Args:
            limit: Maximum number to return (None for all)
            
        Returns:
            List of all conversations
        """
        if self.use_postgres and self.postgres_handler:
            return self.postgres_handler.get_all_conversations(limit)
        
        # SQLite fallback
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if limit:
            cursor.execute("""
                SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                       timestamp, tokens_used, model_used
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        else:
            cursor.execute("""
                SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                       timestamp, tokens_used, model_used
                FROM conversations
                ORDER BY timestamp DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        conversations = []
        for row in rows:
            conversations.append({
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "channel_id": row[3],
                "user_message": row[4],
                "bot_response": row[5],
                "timestamp": row[6],
                "tokens_used": row[7],
                "model_used": row[8]
            })
        
        return conversations

