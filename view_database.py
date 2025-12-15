"""
Simple script to view the bot's SQLite database
Run: python view_database.py
"""

import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = "bot_memory.db"

def view_database():
    """View database contents"""
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database '{DB_PATH}' not found!")
        print("[INFO] Run the bot first to create the database: python bot.py")
        return
    
    # Connect to database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=" * 70)
        print("🤖 AI Boot Database Viewer")
        print("=" * 70)
        
        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n📊 Tables found: {[t[0] for t in tables]}\n")
        
        # View conversations
        print("=" * 70)
        print("💬 CONVERSATIONS (Recent Messages)")
        print("=" * 70)
        
        cursor.execute("""
            SELECT COUNT(*) FROM conversations
        """)
        total_messages = cursor.fetchone()[0]
        print(f"Total messages: {total_messages}\n")
        
        if total_messages > 0:
            cursor.execute("""
                SELECT id, user_id, channel_id, role, content, timestamp, importance_score
                FROM conversations 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            
            messages = cursor.fetchall()
            for msg in messages:
                msg_id, user_id, channel_id, role, content, timestamp, importance = msg
                content_preview = content[:80] + "..." if len(content) > 80 else content
                print(f"ID: {msg_id} | User: {user_id} | Role: {role}")
                print(f"Content: {content_preview}")
                print(f"Time: {timestamp} | Importance: {importance:.2f}")
                print("-" * 70)
        else:
            print("No messages yet.")
        
        # View summaries
        print("\n" + "=" * 70)
        print("📝 SUMMARIES (Long-term Memory)")
        print("=" * 70)
        
        cursor.execute("""
            SELECT COUNT(*) FROM summaries
        """)
        total_summaries = cursor.fetchone()[0]
        print(f"Total summaries: {total_summaries}\n")
        
        if total_summaries > 0:
            cursor.execute("""
                SELECT id, user_id, channel_id, summary_text, message_count, 
                       start_timestamp, end_timestamp, importance_score, created_at
                FROM summaries 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            summaries = cursor.fetchall()
            for summary in summaries:
                (sum_id, user_id, channel_id, summary_text, msg_count, 
                 start_time, end_time, importance, created_at) = summary
                summary_preview = summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
                print(f"ID: {sum_id} | User: {user_id} | Channel: {channel_id}")
                print(f"Summary: {summary_preview}")
                print(f"Messages: {msg_count} | Importance: {importance:.2f}")
                print(f"Period: {start_time} to {end_time}")
                print(f"Created: {created_at}")
                print("-" * 70)
        else:
            print("No summaries yet.")
        
        # Statistics
        print("\n" + "=" * 70)
        print("📈 STATISTICS")
        print("=" * 70)
        
        # Messages per user
        cursor.execute("""
            SELECT user_id, COUNT(*) as count 
            FROM conversations 
            GROUP BY user_id 
            ORDER BY count DESC
        """)
        user_stats = cursor.fetchall()
        if user_stats:
            print("\nMessages per user:")
            for user_id, count in user_stats:
                print(f"  User {user_id}: {count} messages")
        
        # Average importance
        cursor.execute("SELECT AVG(importance_score) FROM conversations")
        avg_importance = cursor.fetchone()[0]
        if avg_importance:
            print(f"\nAverage message importance: {avg_importance:.2f}")
        
        conn.close()
        print("\n" + "=" * 70)
        print("✅ Database view complete!")
        print("=" * 70)
        
    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    view_database()


