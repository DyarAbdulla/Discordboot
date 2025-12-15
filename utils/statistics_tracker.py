"""
Comprehensive Statistics Tracker
Tracks detailed statistics for users, servers, and global metrics
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import json


class StatisticsTracker:
    """
    Tracks comprehensive statistics for the Discord bot
    Stores data in SQLite database for persistence
    """
    
    def __init__(self, db_path: str = "bot_statistics.db"):
        """
        Initialize statistics tracker
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for message statistics (per user, per server, per day)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                server_id TEXT,
                channel_id TEXT NOT NULL,
                date DATE NOT NULL,
                hour INTEGER NOT NULL,
                message_count INTEGER DEFAULT 1,
                language TEXT,
                is_command BOOLEAN DEFAULT 0,
                command_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, server_id, channel_id, date, hour),
                INDEX idx_user_date (user_id, date),
                INDEX idx_server_date (server_id, date),
                INDEX idx_date (date),
                INDEX idx_hour (hour)
            )
        """)
        
        # Table for question/topic tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                server_id TEXT,
                question_text TEXT NOT NULL,
                topic TEXT,
                language TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user (user_id),
                INDEX idx_server (server_id),
                INDEX idx_topic (topic),
                INDEX idx_timestamp (timestamp)
            )
        """)
        
        # Table for API usage and costs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                user_id TEXT,
                server_id TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                api_calls INTEGER DEFAULT 0,
                successful_calls INTEGER DEFAULT 0,
                failed_calls INTEGER DEFAULT 0,
                estimated_cost REAL DEFAULT 0.0,
                model_used TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_date (date),
                INDEX idx_user (user_id),
                INDEX idx_server (server_id)
            )
        """)
        
        # Table for budget settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                budget_type TEXT NOT NULL DEFAULT 'monthly',
                budget_amount REAL NOT NULL DEFAULT 0.0,
                alert_50_sent BOOLEAN DEFAULT 0,
                alert_75_sent BOOLEAN DEFAULT 0,
                alert_90_sent BOOLEAN DEFAULT 0,
                last_alert_date DATE,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(budget_type)
            )
        """)
        
        # Add new columns to api_stats if they don't exist (migration)
        try:
            cursor.execute("ALTER TABLE api_stats ADD COLUMN user_id TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE api_stats ADD COLUMN server_id TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE api_stats ADD COLUMN input_tokens INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE api_stats ADD COLUMN output_tokens INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        
        # Table for error tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT,
                user_id TEXT,
                server_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_error_type (error_type),
                INDEX idx_timestamp (timestamp)
            )
        """)
        
        # Table for user retention (first seen, last seen)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_retention (
                user_id TEXT PRIMARY KEY,
                server_id TEXT,
                first_seen DATETIME NOT NULL,
                last_seen DATETIME NOT NULL,
                total_messages INTEGER DEFAULT 1,
                days_active INTEGER DEFAULT 1,
                INDEX idx_server (server_id),
                INDEX idx_last_seen (last_seen)
            )
        """)
        
        conn.commit()
        conn.close()
        print(f"[OK] Statistics database initialized: {self.db_path}")
    
    def track_message(
        self,
        user_id: str,
        channel_id: str,
        server_id: Optional[str] = None,
        language: Optional[str] = None,
        is_command: bool = False,
        command_name: Optional[str] = None
    ):
        """
        Track a message event
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            server_id: Optional Discord server ID
            language: Optional detected language
            is_command: Whether this is a command
            command_name: Command name if is_command is True
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        date = now.date()
        hour = now.hour
        
        # Update message stats
        cursor.execute("""
            INSERT INTO message_stats 
            (user_id, server_id, channel_id, date, hour, language, is_command, command_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, server_id, channel_id, date, hour) 
            DO UPDATE SET message_count = message_count + 1
        """, (
            str(user_id), 
            str(server_id) if server_id else None,
            str(channel_id),
            date.isoformat(),
            hour,
            language,
            1 if is_command else 0,
            command_name
        ))
        
        # Update user retention
        cursor.execute("""
            INSERT INTO user_retention (user_id, server_id, first_seen, last_seen, total_messages)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                last_seen = ?,
                total_messages = total_messages + 1,
                days_active = CASE 
                    WHEN date(last_seen) != date(?) THEN days_active + 1
                    ELSE days_active
                END
        """, (
            str(user_id),
            str(server_id) if server_id else None,
            now.isoformat(),
            now.isoformat(),
            now.isoformat(),
            now.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def track_question(
        self,
        user_id: str,
        question_text: str,
        server_id: Optional[str] = None,
        topic: Optional[str] = None,
        language: Optional[str] = None
    ):
        """
        Track a question asked by user
        
        Args:
            user_id: Discord user ID
            question_text: The question text
            server_id: Optional Discord server ID
            topic: Optional topic/category
            language: Optional detected language
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO question_stats (user_id, server_id, question_text, topic, language)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(user_id),
            str(server_id) if server_id else None,
            question_text[:500],  # Limit length
            topic,
            language
        ))
        
        conn.commit()
        conn.close()
    
    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str = "claude-3-5-haiku-20241022") -> float:
        """
        Calculate accurate API cost based on input/output tokens
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
            
        Returns:
            Cost in USD
        """
        # Claude 3.5 Haiku pricing (as of 2024):
        # Input: $0.25 per 1M tokens
        # Output: $1.25 per 1M tokens
        input_cost_per_million = 0.25
        output_cost_per_million = 1.25
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * output_cost_per_million
        
        return input_cost + output_cost
    
    def track_api_usage(
        self,
        tokens_used: int,
        success: bool,
        model_used: str = "claude-3-5-haiku-20241022",
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
        server_id: Optional[str] = None
    ):
        """
        Track API usage and costs
        
        Args:
            tokens_used: Total number of tokens used
            success: Whether the API call was successful
            model_used: Model name
            input_tokens: Number of input tokens (if available)
            output_tokens: Number of output tokens (if available)
            user_id: Optional user ID
            server_id: Optional server ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date = datetime.now().date()
        
        # Estimate input/output tokens if not provided (assume 70% input, 30% output)
        if input_tokens is None or output_tokens is None:
            if input_tokens is None:
                input_tokens = int(tokens_used * 0.7)
            if output_tokens is None:
                output_tokens = tokens_used - input_tokens
        
        # Calculate accurate cost
        estimated_cost = self.calculate_cost(input_tokens, output_tokens, model_used)
        
        # Insert or update daily stats
        cursor.execute("""
            INSERT INTO api_stats 
            (date, user_id, server_id, input_tokens, output_tokens, tokens_used, api_calls, 
             successful_calls, failed_calls, estimated_cost, model_used)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        """, (
            date.isoformat(),
            str(user_id) if user_id else None,
            str(server_id) if server_id else None,
            input_tokens,
            output_tokens,
            tokens_used,
            1 if success else 0,
            0 if success else 1,
            estimated_cost,
            model_used
        ))
        
        conn.commit()
        conn.close()
    
    def get_current_month_cost(self) -> float:
        """
        Get total cost for current month
        
        Returns:
            Total cost in USD
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get first day of current month
        now = datetime.now()
        first_day = datetime(now.year, now.month, 1).date()
        
        cursor.execute("""
            SELECT COALESCE(SUM(estimated_cost), 0.0) FROM api_stats
            WHERE date >= ?
        """, (first_day.isoformat(),))
        
        total_cost = cursor.fetchone()[0] or 0.0
        conn.close()
        
        return float(total_cost)
    
    def get_budget_settings(self) -> Dict:
        """
        Get budget settings
        
        Returns:
            Dictionary with budget settings
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT budget_type, budget_amount, alert_50_sent, alert_75_sent, alert_90_sent, last_alert_date
            FROM budget_settings
            WHERE budget_type = 'monthly'
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "budget_type": row[0],
                "budget_amount": row[1],
                "alert_50_sent": bool(row[2]),
                "alert_75_sent": bool(row[3]),
                "alert_90_sent": bool(row[4]),
                "last_alert_date": row[5]
            }
        
        return {
            "budget_type": "monthly",
            "budget_amount": 0.0,
            "alert_50_sent": False,
            "alert_75_sent": False,
            "alert_90_sent": False,
            "last_alert_date": None
        }
    
    def set_budget(self, amount: float, budget_type: str = "monthly"):
        """
        Set monthly budget
        
        Args:
            amount: Budget amount in USD
            budget_type: Budget type (default: monthly)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO budget_settings 
            (budget_type, budget_amount, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (budget_type, amount))
        
        conn.commit()
        conn.close()
    
    def reset_budget_alerts(self):
        """
        Reset budget alerts (call at start of new month)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE budget_settings
            SET alert_50_sent = 0, alert_75_sent = 0, alert_90_sent = 0,
                last_alert_date = NULL
            WHERE budget_type = 'monthly'
        """)
        
        conn.commit()
        conn.close()
    
    def mark_budget_alert_sent(self, threshold: int):
        """
        Mark budget alert as sent
        
        Args:
            threshold: Alert threshold (50, 75, or 90)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        field = f"alert_{threshold}_sent"
        cursor.execute(f"""
            UPDATE budget_settings
            SET {field} = 1, last_alert_date = CURRENT_DATE
            WHERE budget_type = 'monthly'
        """)
        
        conn.commit()
        conn.close()
    
    def get_cost_breakdown(
        self,
        days: int = 30,
        user_id: Optional[str] = None,
        server_id: Optional[str] = None
    ) -> Dict:
        """
        Get cost breakdown by user/server/time period
        
        Args:
            days: Number of days to look back
            user_id: Optional filter by user
            server_id: Optional filter by server
            
        Returns:
            Dictionary with cost breakdown
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        # Build query
        query = """
            SELECT 
                COALESCE(SUM(estimated_cost), 0.0) as total_cost,
                COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                COALESCE(SUM(tokens_used), 0) as total_tokens,
                COALESCE(SUM(api_calls), 0) as total_calls,
                COALESCE(SUM(successful_calls), 0) as successful_calls
            FROM api_stats
            WHERE date >= ?
        """
        params = [cutoff_date.isoformat()]
        
        if user_id:
            query += " AND user_id = ?"
            params.append(str(user_id))
        
        if server_id:
            query += " AND server_id = ?"
            params.append(str(server_id))
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        # Get daily costs
        daily_query = """
            SELECT date, SUM(estimated_cost) as cost
            FROM api_stats
            WHERE date >= ?
        """
        daily_params = [cutoff_date.isoformat()]
        
        if user_id:
            daily_query += " AND user_id = ?"
            daily_params.append(str(user_id))
        
        if server_id:
            daily_query += " AND server_id = ?"
            daily_params.append(str(server_id))
        
        daily_query += " GROUP BY date ORDER BY date DESC LIMIT 30"
        
        cursor.execute(daily_query, daily_params)
        daily_costs = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get top users by cost
        if not user_id:
            user_query = """
                SELECT user_id, SUM(estimated_cost) as cost
                FROM api_stats
                WHERE date >= ? AND user_id IS NOT NULL
            """
            user_params = [cutoff_date.isoformat()]
            
            if server_id:
                user_query += " AND server_id = ?"
                user_params.append(str(server_id))
            
            user_query += " GROUP BY user_id ORDER BY cost DESC LIMIT 10"
            
            cursor.execute(user_query, user_params)
            top_users = {row[0]: row[1] for row in cursor.fetchall()}
        else:
            top_users = {}
        
        # Get top servers by cost
        if not server_id:
            server_query = """
                SELECT server_id, SUM(estimated_cost) as cost
                FROM api_stats
                WHERE date >= ? AND server_id IS NOT NULL
                GROUP BY server_id
                ORDER BY cost DESC
                LIMIT 10
            """
            cursor.execute(server_query, [cutoff_date.isoformat()])
            top_servers = {row[0]: row[1] for row in cursor.fetchall()}
        else:
            top_servers = {}
        
        conn.close()
        
        return {
            "total_cost": float(row[0]) if row else 0.0,
            "total_input_tokens": row[1] if row else 0,
            "total_output_tokens": row[2] if row else 0,
            "total_tokens": row[3] if row else 0,
            "total_calls": row[4] if row else 0,
            "successful_calls": row[5] if row else 0,
            "daily_costs": daily_costs,
            "top_users": top_users,
            "top_servers": top_servers
        }
    
    def track_error(
        self,
        error_type: str,
        error_message: str,
        user_id: Optional[str] = None,
        server_id: Optional[str] = None
    ):
        """
        Track an error
        
        Args:
            error_type: Type of error
            error_message: Error message
            user_id: Optional user ID
            server_id: Optional server ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO error_stats (error_type, error_message, user_id, server_id)
            VALUES (?, ?, ?, ?)
        """, (
            error_type,
            error_message[:500],  # Limit length
            str(user_id) if user_id else None,
            str(server_id) if server_id else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_personal_stats(self, user_id: str, days: int = 30) -> Dict:
        """
        Get personal statistics for a user
        
        Args:
            user_id: Discord user ID
            days: Number of days to look back
            
        Returns:
            Dictionary with personal statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        # Total messages
        cursor.execute("""
            SELECT COALESCE(SUM(message_count), 0) FROM message_stats
            WHERE user_id = ? AND date >= ?
        """, (str(user_id), cutoff_date.isoformat()))
        total_messages = cursor.fetchone()[0] or 0
        
        # Messages per day
        cursor.execute("""
            SELECT date, SUM(message_count) as count
            FROM message_stats
            WHERE user_id = ? AND date >= ?
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """, (str(user_id), cutoff_date.isoformat()))
        messages_per_day = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Most active hours
        cursor.execute("""
            SELECT hour, SUM(message_count) as count
            FROM message_stats
            WHERE user_id = ? AND date >= ?
            GROUP BY hour
            ORDER BY count DESC
            LIMIT 5
        """, (str(user_id), cutoff_date.isoformat()))
        active_hours = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Language distribution
        cursor.execute("""
            SELECT language, SUM(message_count) as count
            FROM message_stats
            WHERE user_id = ? AND date >= ? AND language IS NOT NULL
            GROUP BY language
            ORDER BY count DESC
        """, (str(user_id), cutoff_date.isoformat()))
        language_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Commands used
        cursor.execute("""
            SELECT command_name, SUM(message_count) as count
            FROM message_stats
            WHERE user_id = ? AND date >= ? AND is_command = 1 AND command_name IS NOT NULL
            GROUP BY command_name
            ORDER BY count DESC
            LIMIT 10
        """, (str(user_id), cutoff_date.isoformat()))
        commands_used = {row[0]: row[1] for row in cursor.fetchall()}
        
        # User retention info
        cursor.execute("""
            SELECT first_seen, last_seen, total_messages, days_active
            FROM user_retention
            WHERE user_id = ?
        """, (str(user_id),))
        retention_row = cursor.fetchone()
        retention = {}
        if retention_row:
            retention = {
                "first_seen": retention_row[0],
                "last_seen": retention_row[1],
                "total_messages": retention_row[2],
                "days_active": retention_row[3]
            }
        
        conn.close()
        
        return {
            "total_messages": total_messages,
            "messages_per_day": messages_per_day,
            "active_hours": active_hours,
            "language_distribution": language_dist,
            "commands_used": commands_used,
            "retention": retention
        }
    
    def get_server_stats(self, server_id: str, days: int = 30) -> Dict:
        """
        Get server-wide statistics
        
        Args:
            server_id: Discord server ID
            days: Number of days to look back
            
        Returns:
            Dictionary with server statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        # Total messages
        cursor.execute("""
            SELECT COALESCE(SUM(message_count), 0) FROM message_stats
            WHERE server_id = ? AND date >= ?
        """, (str(server_id), cutoff_date.isoformat()))
        total_messages = cursor.fetchone()[0] or 0
        
        # Most active users
        cursor.execute("""
            SELECT user_id, SUM(message_count) as count
            FROM message_stats
            WHERE server_id = ? AND date >= ?
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 10
        """, (str(server_id), cutoff_date.isoformat()))
        active_users = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Messages per day
        cursor.execute("""
            SELECT date, SUM(message_count) as count
            FROM message_stats
            WHERE server_id = ? AND date >= ?
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """, (str(server_id), cutoff_date.isoformat()))
        messages_per_day = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Most active hours
        cursor.execute("""
            SELECT hour, SUM(message_count) as count
            FROM message_stats
            WHERE server_id = ? AND date >= ?
            GROUP BY hour
            ORDER BY count DESC
            LIMIT 5
        """, (str(server_id), cutoff_date.isoformat()))
        active_hours = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Language distribution
        cursor.execute("""
            SELECT language, SUM(message_count) as count
            FROM message_stats
            WHERE server_id = ? AND date >= ? AND language IS NOT NULL
            GROUP BY language
            ORDER BY count DESC
        """, (str(server_id), cutoff_date.isoformat()))
        language_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Popular questions/topics
        cursor.execute("""
            SELECT question_text, COUNT(*) as count
            FROM question_stats
            WHERE server_id = ? AND timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY question_text
            ORDER BY count DESC
            LIMIT 10
        """, (str(server_id), days))
        popular_questions = {row[0][:100]: row[1] for row in cursor.fetchall()}
        
        # Commands used
        cursor.execute("""
            SELECT command_name, SUM(message_count) as count
            FROM message_stats
            WHERE server_id = ? AND date >= ? AND is_command = 1 AND command_name IS NOT NULL
            GROUP BY command_name
            ORDER BY count DESC
            LIMIT 10
        """, (str(server_id), cutoff_date.isoformat()))
        commands_used = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Unique users
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM message_stats
            WHERE server_id = ? AND date >= ?
        """, (str(server_id), cutoff_date.isoformat()))
        unique_users = cursor.fetchone()[0] or 0
        
        # Returning users (retention)
        cursor.execute("""
            SELECT COUNT(*) FROM user_retention
            WHERE server_id = ? AND days_active > 1
        """, (str(server_id),))
        returning_users = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_messages": total_messages,
            "unique_users": unique_users,
            "returning_users": returning_users,
            "active_users": active_users,
            "messages_per_day": messages_per_day,
            "active_hours": active_hours,
            "language_distribution": language_dist,
            "popular_questions": popular_questions,
            "commands_used": commands_used
        }
    
    def get_global_stats(self, days: int = 30) -> Dict:
        """
        Get global statistics across all servers
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with global statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        # Total messages
        cursor.execute("""
            SELECT COALESCE(SUM(message_count), 0) FROM message_stats
            WHERE date >= ?
        """, (cutoff_date.isoformat(),))
        total_messages = cursor.fetchone()[0] or 0
        
        # Total unique users
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM message_stats
            WHERE date >= ?
        """, (cutoff_date.isoformat(),))
        unique_users = cursor.fetchone()[0] or 0
        
        # Total servers
        cursor.execute("""
            SELECT COUNT(DISTINCT server_id) FROM message_stats
            WHERE server_id IS NOT NULL AND date >= ?
        """, (cutoff_date.isoformat(),))
        total_servers = cursor.fetchone()[0] or 0
        
        # Messages per day
        cursor.execute("""
            SELECT date, SUM(message_count) as count
            FROM message_stats
            WHERE date >= ?
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """, (cutoff_date.isoformat(),))
        messages_per_day = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Most active servers
        cursor.execute("""
            SELECT server_id, SUM(message_count) as count
            FROM message_stats
            WHERE server_id IS NOT NULL AND date >= ?
            GROUP BY server_id
            ORDER BY count DESC
            LIMIT 10
        """, (cutoff_date.isoformat(),))
        active_servers = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Language distribution
        cursor.execute("""
            SELECT language, SUM(message_count) as count
            FROM message_stats
            WHERE date >= ? AND language IS NOT NULL
            GROUP BY language
            ORDER BY count DESC
        """, (cutoff_date.isoformat(),))
        language_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        # API costs
        cursor.execute("""
            SELECT date, SUM(estimated_cost) as cost, SUM(tokens_used) as tokens,
                   SUM(api_calls) as calls, SUM(failed_calls) as failed
            FROM api_stats
            WHERE date >= ?
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """, (cutoff_date.isoformat(),))
        api_costs = []
        total_cost = 0.0
        total_tokens = 0
        total_calls = 0
        total_failed = 0
        for row in cursor.fetchall():
            api_costs.append({
                "date": row[0],
                "cost": row[1] or 0.0,
                "tokens": row[2] or 0,
                "calls": row[3] or 0,
                "failed": row[4] or 0
            })
            total_cost += row[1] or 0.0
            total_tokens += row[2] or 0
            total_calls += row[3] or 0
            total_failed += row[4] or 0
        
        # Error rate
        cursor.execute("""
            SELECT COUNT(*) FROM error_stats
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        """, (days,))
        total_errors = cursor.fetchone()[0] or 0
        
        error_rate = (total_failed / total_calls * 100) if total_calls > 0 else 0.0
        
        # Commands used
        cursor.execute("""
            SELECT command_name, SUM(message_count) as count
            FROM message_stats
            WHERE date >= ? AND is_command = 1 AND command_name IS NOT NULL
            GROUP BY command_name
            ORDER BY count DESC
            LIMIT 10
        """, (cutoff_date.isoformat(),))
        commands_used = {row[0]: row[1] for row in cursor.fetchall()}
        
        # User retention
        cursor.execute("""
            SELECT COUNT(*) FROM user_retention WHERE days_active > 1
        """)
        returning_users = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_messages": total_messages,
            "unique_users": unique_users,
            "total_servers": total_servers,
            "returning_users": returning_users,
            "messages_per_day": messages_per_day,
            "active_servers": active_servers,
            "language_distribution": language_dist,
            "api_costs": api_costs,
            "total_api_cost": total_cost,
            "total_tokens": total_tokens,
            "total_api_calls": total_calls,
            "total_errors": total_errors,
            "error_rate": error_rate,
            "commands_used": commands_used
        }
    
    def create_chart(self, data: Dict, max_width: int = 20) -> str:
        """
        Create a simple text-based bar chart
        
        Args:
            data: Dictionary with labels and values
            max_width: Maximum width of chart bars
            
        Returns:
            String representation of chart
        """
        if not data:
            return "No data available"
        
        # Find max value for scaling
        max_value = max(data.values()) if data.values() else 1
        
        chart_lines = []
        for label, value in sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]:
            # Scale bar width
            bar_width = int((value / max_value) * max_width) if max_value > 0 else 0
            bar = "█" * bar_width
            chart_lines.append(f"{label[:15]:<15} {bar} {value:,}")
        
        return "\n".join(chart_lines)
    
    def create_time_chart(self, data: Dict, label: str = "Messages") -> str:
        """
        Create a time-based chart
        
        Args:
            data: Dictionary with dates as keys and values
            label: Label for the chart
            
        Returns:
            String representation of chart
        """
        if not data:
            return "No data available"
        
        # Sort by date
        sorted_data = sorted(data.items())[-7:]  # Last 7 days
        
        max_value = max([v for _, v in sorted_data]) if sorted_data else 1
        
        chart_lines = []
        for date_str, value in sorted_data:
            date_obj = datetime.fromisoformat(date_str) if isinstance(date_str, str) else date_str
            date_label = date_obj.strftime("%m/%d") if hasattr(date_obj, 'strftime') else str(date_str)
            bar_width = int((value / max_value) * 15) if max_value > 0 else 0
            bar = "█" * bar_width
            chart_lines.append(f"{date_label:<6} {bar} {value:,}")
        
        return "\n".join(chart_lines)

