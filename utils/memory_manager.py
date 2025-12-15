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
    
    def __init__(self, db_path: str = "bot_memory.db", short_term_limit: int = 15):
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
                importance_score REAL DEFAULT 0.5,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_channel (user_id, channel_id),
                INDEX idx_timestamp (timestamp),
                INDEX idx_importance (importance_score)
            )
        """)
        
        # Add importance_score column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN importance_score REAL DEFAULT 0.5")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Add last_accessed column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Table for conversation summaries (long-term memory)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                message_count INTEGER NOT NULL,
                importance_score REAL DEFAULT 0.5,
                start_timestamp DATETIME NOT NULL,
                end_timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_channel (user_id, channel_id),
                INDEX idx_importance (importance_score),
                INDEX idx_created_at (created_at)
            )
        """)
        
        # Table for user preferences (language, personality, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, channel_id, preference_key),
                INDEX idx_user_channel (user_id, channel_id)
            )
        """)
        
        # Table for user facts (name, interests, important information)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                importance_score REAL DEFAULT 0.5,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, channel_id, fact_key),
                INDEX idx_user_channel (user_id, channel_id),
                INDEX idx_fact_key (fact_key),
                INDEX idx_importance (importance_score)
            )
        """)
        
        # Add importance_score column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE summaries ADD COLUMN importance_score REAL DEFAULT 0.5")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Add last_accessed column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE summaries ADD COLUMN last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()
        print(f"[OK] Memory database initialized: {self.db_path}")
    
    def add_message(
        self,
        user_id: str,
        channel_id: str,
        role: str,
        content: str,
        importance_score: Optional[float] = None
    ) -> int:
        """
        Add a message to the conversation history
        
        PER-USER ISOLATION: Messages are stored with user_id and channel_id,
        ensuring complete isolation between users.
        
        Args:
            user_id: Discord user ID (required for isolation)
            channel_id: Discord channel ID (or DM channel ID)
            role: 'user' or 'assistant'
            content: Message content
            
        Returns:
            Message ID
        """
        # Validate inputs for security
        if not user_id or not channel_id:
            raise ValueError("user_id and channel_id are required for memory isolation")
        
        if role not in ['user', 'assistant']:
            raise ValueError("role must be 'user' or 'assistant'")
        
        # Ensure user_id and channel_id are strings (prevent SQL injection)
        user_id = str(user_id)
        channel_id = str(channel_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate importance score if not provided
        if importance_score is None:
            from utils.importance_scorer import ImportanceScorer
            message_dict = {"role": role, "content": content}
            importance_score = ImportanceScorer.score_message(message_dict, is_user_message=(role == "user"))
        
        # Use parameterized query to prevent SQL injection
        cursor.execute("""
            INSERT INTO conversations (user_id, channel_id, role, content, importance_score)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, channel_id, role, content, importance_score))
        
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
            SELECT role, content, timestamp, importance_score, last_accessed
            FROM conversations
            WHERE user_id = ? AND channel_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (str(user_id), str(channel_id), limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Reverse to get chronological order (oldest first)
        messages = [
            {
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
                "importance_score": row[3] if len(row) > 3 else 0.5,
                "last_accessed": row[4] if len(row) > 4 else row[2]
            }
            for row in reversed(rows)
        ]
        
        # Update last_accessed timestamp
        self._update_last_accessed(user_id, channel_id, "conversations")
        
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
            SELECT summary_text, message_count, start_timestamp, end_timestamp, 
                   importance_score, created_at, last_accessed
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
                "end_timestamp": row[3],
                "importance_score": row[4] if len(row) > 4 else 0.5,
                "created_at": row[5] if len(row) > 5 else row[2],
                "last_accessed": row[6] if len(row) > 6 else row[5] if len(row) > 5 else row[2]
            }
            for row in rows
        ]
        
        # Update last_accessed timestamp
        self._update_last_accessed(user_id, channel_id, "summaries")
        
        return summaries
    
    def create_summary(
        self,
        user_id: str,
        channel_id: str,
        summary_text: str,
        message_count: int,
        start_timestamp: datetime,
        end_timestamp: datetime,
        importance_score: Optional[float] = None
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
        
        # Calculate importance score if not provided
        if importance_score is None:
            from utils.importance_scorer import ImportanceScorer
            age_days = (datetime.now() - start_timestamp).total_seconds() / 86400
            importance_score = ImportanceScorer.score_summary(summary_text, message_count, age_days)
        
        cursor.execute("""
            INSERT INTO summaries (user_id, channel_id, summary_text, message_count, 
                                 start_timestamp, end_timestamp, importance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(user_id),
            str(channel_id),
            summary_text,
            message_count,
            start_timestamp.isoformat(),
            end_timestamp.isoformat(),
            importance_score
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
    
    def _update_last_accessed(self, user_id: str, channel_id: str, table: str):
        """Update last_accessed timestamp for records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if table == "conversations":
                cursor.execute("""
                    UPDATE conversations
                    SET last_accessed = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND channel_id = ?
                """, (str(user_id), str(channel_id)))
            elif table == "summaries":
                cursor.execute("""
                    UPDATE summaries
                    SET last_accessed = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND channel_id = ?
                """, (str(user_id), str(channel_id)))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[WARNING] Failed to update last_accessed: {e}")
    
    def _calculate_decay_score(self, importance_score: float, age_days: float, last_accessed_days: float) -> float:
        """
        Calculate decay-adjusted importance score
        
        Args:
            importance_score: Base importance score (0.0-1.0)
            age_days: Age in days since creation
            last_accessed_days: Days since last access
            
        Returns:
            Decay-adjusted score (0.0-1.0)
        """
        # Critical info (score > 0.8) decays much slower
        if importance_score > 0.8:
            # Critical info: 1% decay per day, but only if not accessed recently
            if last_accessed_days > 30:  # Not accessed in 30 days
                decay = min(0.3, age_days * 0.01)
            else:
                decay = min(0.1, age_days * 0.005)  # Very slow decay if recently accessed
        elif importance_score > 0.6:
            # Important info: 2% decay per day
            decay = min(0.4, age_days * 0.02)
        else:
            # Normal info: 3% decay per day
            decay = min(0.5, age_days * 0.03)
        
        # Apply decay
        decayed_score = importance_score - decay
        
        # Ensure minimum score
        return max(0.1, decayed_score)
    
    def get_conversation_context(
        self,
        user_id: str,
        channel_id: str,
        include_summaries: bool = True,
        min_importance: float = 0.2,
        limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Get full conversation context (summaries + recent messages)
        
        PER-USER ISOLATION: Only returns data for the specified user_id and channel_id.
        This ensures complete memory isolation between users.
        
        Args:
            user_id: Discord user ID (required for isolation)
            channel_id: Discord channel ID (required for isolation)
            include_summaries: Whether to include long-term memory summaries
            
        Returns:
            Tuple of (messages_list, summary_texts)
            - messages_list: List of recent messages for API
            - summary_texts: List of summary strings for system context
        """
        # Validate inputs for security
        if not user_id or not channel_id:
            raise ValueError("user_id and channel_id are required for memory isolation")
        
        # Ensure user_id and channel_id are strings (prevent SQL injection)
        user_id = str(user_id)
        channel_id = str(channel_id)
        
        # Get recent messages (short-term memory) - ISOLATED BY USER+CHANNEL
        if limit is None:
            limit = self.short_term_limit
        messages = self.get_recent_messages(user_id, channel_id, limit=limit)
        
        # Get summaries (long-term memory) - ISOLATED BY USER+CHANNEL
        summaries = []
        if include_summaries:
            summaries = self.get_summaries(user_id, channel_id)
            
            # Apply decay and filter by importance
            now = datetime.now()
            filtered_summaries = []
            
            for s in summaries:
                # Calculate age and last accessed
                created_at = datetime.fromisoformat(s['created_at']) if isinstance(s['created_at'], str) else s['created_at']
                last_accessed = datetime.fromisoformat(s['last_accessed']) if isinstance(s['last_accessed'], str) else s['last_accessed']
                
                age_days = (now - created_at).total_seconds() / 86400
                last_accessed_days = (now - last_accessed).total_seconds() / 86400
                
                # Calculate decay-adjusted score
                decayed_score = self._calculate_decay_score(
                    s['importance_score'],
                    age_days,
                    last_accessed_days
                )
                
                # Only include summaries above minimum importance threshold
                if decayed_score >= min_importance:
                    s['decayed_score'] = decayed_score
                    filtered_summaries.append(s)
            
            # Sort by decayed score (highest first) and limit to top summaries
            filtered_summaries.sort(key=lambda x: x['decayed_score'], reverse=True)
            summaries = filtered_summaries[:10]  # Limit to top 10 summaries
        
        # Format summaries as text (prioritize important ones)
        summary_texts = [
            f"Previous conversation summary ({s['message_count']} messages, {s['start_timestamp']} to {s['end_timestamp']}, importance: {s.get('decayed_score', s['importance_score']):.2f}): {s['summary']}"
            for s in summaries
        ]
        
        # Convert messages to API format
        api_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
        
        return api_messages, summary_texts
    
    def merge_old_summaries(
        self,
        user_id: str,
        channel_id: str,
        max_age_days: int = 90,
        min_importance: float = 0.3
    ) -> int:
        """
        Merge or drop old summaries based on importance and age
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            max_age_days: Summaries older than this will be considered for merging
            min_importance: Minimum importance score to keep (after decay)
            
        Returns:
            Number of summaries merged/dropped
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get old summaries
        cutoff_date = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        cursor.execute("""
            SELECT id, summary_text, message_count, start_timestamp, end_timestamp,
                   importance_score, created_at, last_accessed
            FROM summaries
            WHERE user_id = ? AND channel_id = ? AND created_at < ?
            ORDER BY created_at ASC
        """, (str(user_id), str(channel_id), cutoff_date))
        
        old_summaries = cursor.fetchall()
        
        if len(old_summaries) < 2:
            conn.close()
            return 0  # Need at least 2 summaries to merge
        
        # Calculate decay scores and filter
        now = datetime.now()
        summaries_to_keep = []
        summaries_to_merge = []
        summaries_to_drop = []
        
        for row in old_summaries:
            summary_id, summary_text, msg_count, start_ts, end_ts, importance, created_at, last_accessed = row
            
            created_dt = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
            last_acc_dt = datetime.fromisoformat(last_accessed) if isinstance(last_accessed, str) else last_accessed
            
            age_days = (now - created_dt).total_seconds() / 86400
            last_acc_days = (now - last_acc_dt).total_seconds() / 86400
            
            decayed_score = self._calculate_decay_score(importance, age_days, last_acc_days)
            
            if decayed_score >= min_importance:
                # Keep important summaries
                summaries_to_keep.append(row)
            elif decayed_score >= 0.2:
                # Merge less important summaries
                summaries_to_merge.append(row)
            else:
                # Drop very low importance summaries
                summaries_to_drop.append(row)
        
        # Drop low-importance summaries
        dropped_count = 0
        if summaries_to_drop:
            ids_to_drop = [row[0] for row in summaries_to_drop]
            placeholders = ','.join(['?'] * len(ids_to_drop))
            cursor.execute(f"""
                DELETE FROM summaries
                WHERE id IN ({placeholders})
            """, ids_to_drop)
            dropped_count = cursor.rowcount
        
        # Merge similar summaries (if we have multiple to merge)
        merged_count = 0
        if len(summaries_to_merge) >= 2:
            # Group summaries by time period (merge adjacent summaries)
            merged_texts = []
            total_messages = 0
            earliest_start = None
            latest_end = None
            
            for row in summaries_to_merge:
                _, summary_text, msg_count, start_ts, end_ts, _, _, _ = row
                merged_texts.append(summary_text)
                total_messages += msg_count
                
                start_dt = datetime.fromisoformat(start_ts) if isinstance(start_ts, str) else start_ts
                end_dt = datetime.fromisoformat(end_ts) if isinstance(end_ts, str) else end_ts
                
                if earliest_start is None or start_dt < earliest_start:
                    earliest_start = start_dt
                if latest_end is None or end_dt > latest_end:
                    latest_end = end_dt
            
            # Create merged summary text
            merged_summary = f"Merged summary of {len(summaries_to_merge)} previous conversations ({total_messages} total messages): " + " | ".join(merged_texts[:3])  # Limit to 3 summaries
            
            # Calculate average importance
            avg_importance = sum(row[5] for row in summaries_to_merge) / len(summaries_to_merge)
            
            # Delete old summaries
            ids_to_merge = [row[0] for row in summaries_to_merge]
            placeholders = ','.join(['?'] * len(ids_to_merge))
            cursor.execute(f"""
                DELETE FROM summaries
                WHERE id IN ({placeholders})
            """, ids_to_merge)
            
            # Insert merged summary
            cursor.execute("""
                INSERT INTO summaries (user_id, channel_id, summary_text, message_count,
                                     start_timestamp, end_timestamp, importance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(user_id),
                str(channel_id),
                merged_summary,
                total_messages,
                earliest_start.isoformat(),
                latest_end.isoformat(),
                avg_importance * 0.8  # Slightly reduce importance when merging
            ))
            
            merged_count = len(summaries_to_merge)
        
        conn.commit()
        conn.close()
        
        total_processed = dropped_count + merged_count
        if total_processed > 0:
            print(f"[INFO] Processed {total_processed} old summaries for user {user_id}: dropped {dropped_count}, merged {merged_count}")
        
        return total_processed
    
    def cleanup_old_messages(self, days: int = 30, min_importance: float = 0.3):
        """
        Delete messages older than specified days, but keep important ones
        
        Args:
            days: Delete messages older than this many days
            min_importance: Keep messages above this importance score regardless of age
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Delete old messages, but keep important ones
        cursor.execute("""
            DELETE FROM conversations
            WHERE timestamp < ? AND importance_score < ?
        """, (cutoff_date, min_importance))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"[INFO] Cleaned up {deleted_count} old messages (older than {days} days, importance < {min_importance})")
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
    
    def set_user_preference(
        self,
        user_id: str,
        channel_id: str,
        preference_key: str,
        preference_value: str
    ):
        """
        Set a user preference (language, personality, etc.)
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            preference_key: Preference key (e.g., 'language', 'kurdish_dialect', 'personality')
            preference_value: Preference value (e.g., 'ku', 'sorani', 'friendly')
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_preferences 
            (user_id, channel_id, preference_key, preference_value, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (str(user_id), str(channel_id), preference_key, preference_value))
        
        conn.commit()
        conn.close()
    
    def get_user_preference(
        self,
        user_id: str,
        channel_id: str,
        preference_key: str,
        default_value: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a user preference
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            preference_key: Preference key
            default_value: Default value if preference not found
            
        Returns:
            Preference value or default_value
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT preference_value FROM user_preferences
            WHERE user_id = ? AND channel_id = ? AND preference_key = ?
        """, (str(user_id), str(channel_id), preference_key))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return default_value
    
    def export_summaries_to_csv(
        self,
        output_path: str = "summaries_export.csv",
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None
    ) -> str:
        """
        Export summaries to CSV file
        
        Args:
            output_path: Path to output CSV file
            user_id: Optional filter by user ID
            channel_id: Optional filter by channel ID
            
        Returns:
            Path to exported file
        """
        import csv
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT id, user_id, channel_id, summary_text, message_count,
                   start_timestamp, end_timestamp, importance_score, created_at
            FROM summaries
            WHERE 1=1
        """
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(str(user_id))
        
        if channel_id:
            query += " AND channel_id = ?"
            params.append(str(channel_id))
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                'id', 'user_id', 'channel_id', 'summary_text', 'message_count',
                'start_timestamp', 'end_timestamp', 'importance_score', 'created_at'
            ])
            
            # Write data
            for row in rows:
                writer.writerow([
                    row[0],  # id
                    row[1],  # user_id
                    row[2],  # channel_id
                    row[3],  # summary_text
                    row[4],  # message_count
                    row[5],  # start_timestamp
                    row[6],  # end_timestamp
                    row[7] if len(row) > 7 else 0.5,  # importance_score
                    row[8] if len(row) > 8 else row[5]  # created_at
                ])
        
        print(f"[OK] Exported {len(rows)} summaries to {output_path}")
        return output_path
    
    def get_all_summaries(
        self,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, any]]:
        """
        Get all summaries
        
        Args:
            user_id: Optional filter by user ID
            channel_id: Optional filter by channel ID
            limit: Optional limit number of results
            
        Returns:
            List of summary dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT id, user_id, channel_id, summary_text, message_count,
                   start_timestamp, end_timestamp, importance_score, created_at
            FROM summaries
            WHERE 1=1
        """
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(str(user_id))
        
        if channel_id:
            query += " AND channel_id = ?"
            params.append(str(channel_id))
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        summaries = []
        for row in rows:
            summaries.append({
                "id": row[0],
                "user_id": row[1],
                "channel_id": row[2],
                "summary_text": row[3],
                "message_count": row[4],
                "start_timestamp": row[5],
                "end_timestamp": row[6],
                "importance_score": row[7] if len(row) > 7 else 0.5,
                "created_at": row[8] if len(row) > 8 else row[5]
            })
        
        return summaries

