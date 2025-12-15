"""
Response Time Tracker
Tracks bot response times for performance monitoring
"""

import time
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from collections import deque
import json


class ResponseTracker:
    """Tracks response times for bot performance monitoring"""
    
    def __init__(self, db_path: str = "bot_memory.db", slow_threshold: float = 5.0):
        """
        Initialize response tracker
        
        Args:
            db_path: Path to SQLite database
            slow_threshold: Threshold in seconds for slow responses (default: 5.0)
        """
        self.db_path = db_path
        self.slow_threshold = slow_threshold
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times in memory
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create response_times table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS response_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                channel_id TEXT,
                response_time REAL NOT NULL,
                used_claude BOOLEAN DEFAULT 1,
                model_used TEXT,
                tokens_used INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_timestamp (timestamp),
                INDEX idx_response_time (response_time)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def start_timer(self) -> float:
        """
        Start timing a response
        
        Returns:
            Start timestamp
        """
        return time.time()
    
    def record_response_time(
        self,
        response_time: float,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        used_claude: bool = True,
        model_used: Optional[str] = None,
        tokens_used: int = 0
    ):
        """
        Record a response time
        
        Args:
            response_time: Response time in seconds
            user_id: Optional user ID
            channel_id: Optional channel ID
            used_claude: Whether Claude API was used
            model_used: Model used (e.g., 'claude-3-5-haiku-20241022')
            tokens_used: Number of tokens used
        """
        # Store in memory
        self.response_times.append(response_time)
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO response_times 
            (user_id, channel_id, response_time, used_claude, model_used, tokens_used)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, channel_id, response_time, used_claude, model_used, tokens_used))
        
        conn.commit()
        conn.close()
        
        # Log slow responses
        if response_time > self.slow_threshold:
            self._log_slow_response(response_time, user_id, channel_id, used_claude, model_used)
        
        # Alert on unusually slow responses (>10 seconds)
        if response_time > 10.0:
            self._alert_slow_response(response_time, user_id, channel_id)
    
    def _log_slow_response(
        self,
        response_time: float,
        user_id: Optional[str],
        channel_id: Optional[str],
        used_claude: bool,
        model_used: Optional[str]
    ):
        """Log slow response to file"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "response_time": response_time,
                "user_id": user_id,
                "channel_id": channel_id,
                "used_claude": used_claude,
                "model_used": model_used,
                "threshold": self.slow_threshold
            }
            
            with open("slow_responses.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
            
            print(f"[WARNING] Slow response detected: {response_time:.2f}s (threshold: {self.slow_threshold}s)")
        except Exception as e:
            print(f"[ERROR] Failed to log slow response: {e}")
    
    def _alert_slow_response(
        self,
        response_time: float,
        user_id: Optional[str],
        channel_id: Optional[str]
    ):
        """Alert on unusually slow response"""
        print(f"[ALERT] ⚠️ UNUSUALLY SLOW RESPONSE: {response_time:.2f}s")
        print(f"[ALERT] User: {user_id}, Channel: {channel_id}")
        print(f"[ALERT] This may indicate API issues or network problems")
    
    def get_average_response_time(
        self,
        hours: Optional[int] = None,
        used_claude: Optional[bool] = None
    ) -> float:
        """
        Get average response time
        
        Args:
            hours: Optional number of hours to look back (None = all time)
            used_claude: Optional filter by Claude usage (None = all)
            
        Returns:
            Average response time in seconds
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT AVG(response_time) FROM response_times WHERE 1=1"
        params = []
        
        if hours:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            query += " AND timestamp >= ?"
            params.append(cutoff_time.isoformat())
        
        if used_claude is not None:
            query += " AND used_claude = ?"
            params.append(used_claude)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] is not None:
            return round(result[0], 2)
        return 0.0
    
    def get_stats(self) -> Dict:
        """
        Get response time statistics
        
        Returns:
            Dictionary with stats
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total responses
        cursor.execute("SELECT COUNT(*) FROM response_times")
        total_responses = cursor.fetchone()[0]
        
        # Average response time (all time)
        cursor.execute("SELECT AVG(response_time) FROM response_times")
        avg_all = cursor.fetchone()[0] or 0.0
        
        # Average response time (last 24 hours)
        cutoff_24h = datetime.now() - timedelta(hours=24)
        cursor.execute("""
            SELECT AVG(response_time) FROM response_times 
            WHERE timestamp >= ?
        """, (cutoff_24h.isoformat(),))
        avg_24h = cursor.fetchone()[0] or 0.0
        
        # Average response time (last hour)
        cutoff_1h = datetime.now() - timedelta(hours=1)
        cursor.execute("""
            SELECT AVG(response_time) FROM response_times 
            WHERE timestamp >= ?
        """, (cutoff_1h.isoformat(),))
        avg_1h = cursor.fetchone()[0] or 0.0
        
        # Slow responses (>5s)
        cursor.execute("""
            SELECT COUNT(*) FROM response_times 
            WHERE response_time > ?
        """, (self.slow_threshold,))
        slow_count = cursor.fetchone()[0]
        
        # Very slow responses (>10s)
        cursor.execute("""
            SELECT COUNT(*) FROM response_times 
            WHERE response_time > 10.0
        """)
        very_slow_count = cursor.fetchone()[0]
        
        # Fastest response
        cursor.execute("SELECT MIN(response_time) FROM response_times")
        fastest = cursor.fetchone()[0] or 0.0
        
        # Slowest response
        cursor.execute("SELECT MAX(response_time) FROM response_times")
        slowest = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            "total_responses": total_responses,
            "average_all_time": round(avg_all, 2) if avg_all else 0.0,
            "average_24h": round(avg_24h, 2) if avg_24h else 0.0,
            "average_1h": round(avg_1h, 2) if avg_1h else 0.0,
            "slow_responses": slow_count,
            "very_slow_responses": very_slow_count,
            "fastest": round(fastest, 2) if fastest else 0.0,
            "slowest": round(slowest, 2) if slowest else 0.0,
            "slow_threshold": self.slow_threshold
        }
    
    def format_response_time(self, response_time: float) -> str:
        """
        Format response time for display
        
        Args:
            response_time: Response time in seconds
            
        Returns:
            Formatted string (e.g., "1.2s", "0.5s")
        """
        if response_time < 1.0:
            return f"{response_time * 1000:.0f}ms"
        return f"{response_time:.1f}s"


