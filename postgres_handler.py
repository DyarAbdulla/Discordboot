"""
PostgreSQL Database Handler for Railway
Handles PostgreSQL connections with Railway's DATABASE_URL
"""

import os
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
from contextlib import contextmanager
import time


class PostgresHandler:
    """
    PostgreSQL database handler for Railway PostgreSQL service
    Uses connection pooling for better performance
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize PostgreSQL handler
        
        Args:
            database_url: PostgreSQL connection URL (from Railway DATABASE_URL env var)
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        # Parse DATABASE_URL to extract components
        # Format: postgresql://user:password@host:port/database
        self._parse_database_url()
        
        # Connection pool (min 1, max 10 connections)
        self.connection_pool = None
        self._initialize_pool()
        
        # Ensure tables exist
        self._ensure_tables_exist()
    
    def _parse_database_url(self):
        """Parse DATABASE_URL into components"""
        # Remove postgresql:// or postgres:// prefix
        url = self.database_url.replace("postgresql://", "").replace("postgres://", "")
        
        # Split into parts
        if "@" in url:
            auth_part, host_part = url.split("@", 1)
            if ":" in auth_part:
                self.db_user, self.db_password = auth_part.split(":", 1)
            else:
                self.db_user = auth_part
                self.db_password = ""
        else:
            self.db_user = ""
            self.db_password = ""
            host_part = url
        
        if "/" in host_part:
            host_port, self.db_name = host_part.split("/", 1)
        else:
            host_port = host_part
            self.db_name = "postgres"
        
        if ":" in host_port:
            self.db_host, self.db_port = host_port.split(":", 1)
        else:
            self.db_host = host_port
            self.db_port = "5432"
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                sslmode='require'  # Railway requires SSL
            )
            print(f"[OK] PostgreSQL connection pool initialized: {self.db_host}:{self.db_port}/{self.db_name}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize PostgreSQL pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def _ensure_tables_exist(self):
        """Create tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    user_name VARCHAR(100) NOT NULL,
                    channel_id VARCHAR(50) NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tokens_used INTEGER DEFAULT 0,
                    model_used VARCHAR(50) DEFAULT 'unknown',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
                ON conversations(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_channel_id 
                ON conversations(channel_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp 
                ON conversations(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user_name 
                ON conversations(user_name)
            """)
            
            conn.commit()
            print("[OK] PostgreSQL tables and indexes created")
    
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
        Log a conversation to PostgreSQL
        
        Returns:
            Conversation ID
        """
        # Validate inputs
        if not user_id or not user_name or not channel_id:
            raise ValueError("user_id, user_name, and channel_id are required")
        
        if not user_message or not bot_response:
            raise ValueError("user_message and bot_response cannot be empty")
        
        # Limit string lengths
        user_name = str(user_name)[:100]
        model_used = str(model_used)[:50]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conversations 
                (user_id, user_name, channel_id, user_message, bot_response, tokens_used, model_used)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (str(user_id), user_name, str(channel_id), user_message, bot_response, tokens_used, model_used))
            
            conversation_id = cursor.fetchone()[0]
            return conversation_id
    
    def get_stats(self) -> Dict:
        """Get conversation statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Total conversations
            cursor.execute("SELECT COUNT(*) as count FROM conversations")
            total_conversations = cursor.fetchone()['count']
            
            # Total unique users
            cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM conversations")
            total_users = cursor.fetchone()['count']
            
            # Total tokens used
            cursor.execute("SELECT COALESCE(SUM(tokens_used), 0) as total FROM conversations")
            total_tokens = cursor.fetchone()['total']
            
            # Models used
            cursor.execute("""
                SELECT model_used, COUNT(*) as count 
                FROM conversations 
                GROUP BY model_used
            """)
            models_used = {row['model_used']: row['count'] for row in cursor.fetchall()}
            
            # Recent activity (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) as count FROM conversations 
                WHERE timestamp > NOW() - INTERVAL '1 day'
            """)
            recent_24h = cursor.fetchone()['count']
            
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
        """Get conversation history for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if user_id:
                cursor.execute("""
                    SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                           timestamp, tokens_used, model_used
                    FROM conversations
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (str(user_id), limit))
            elif user_name:
                cursor.execute("""
                    SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                           timestamp, tokens_used, model_used
                    FROM conversations
                    WHERE user_name ILIKE %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (f"%{user_name}%", limit))
            else:
                cursor.execute("""
                    SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                           timestamp, tokens_used, model_used
                    FROM conversations
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
            
            rows = cursor.fetchall()
            
            conversations = []
            for row in rows:
                conversations.append({
                    "id": row['id'],
                    "user_id": row['user_id'],
                    "user_name": row['user_name'],
                    "channel_id": row['channel_id'],
                    "user_message": row['user_message'],
                    "bot_response": row['bot_response'],
                    "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                    "tokens_used": row['tokens_used'],
                    "model_used": row['model_used']
                })
            
            return conversations
    
    def get_all_conversations(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all conversations"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if limit:
                cursor.execute("""
                    SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                           timestamp, tokens_used, model_used
                    FROM conversations
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                           timestamp, tokens_used, model_used
                    FROM conversations
                    ORDER BY timestamp DESC
                """)
            
            rows = cursor.fetchall()
            
            conversations = []
            for row in rows:
                conversations.append({
                    "id": row['id'],
                    "user_id": row['user_id'],
                    "user_name": row['user_name'],
                    "channel_id": row['channel_id'],
                    "user_message": row['user_message'],
                    "bot_response": row['bot_response'],
                    "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                    "tokens_used": row['tokens_used'],
                    "model_used": row['model_used']
                })
            
            return conversations
    
    def close(self):
        """Close connection pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            print("[OK] PostgreSQL connection pool closed")



