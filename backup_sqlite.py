"""
SQLite Backup Script
Creates backups of SQLite conversation database

Usage:
python backup_sqlite.py
"""

import os
import shutil
import sqlite3
import csv
from datetime import datetime
from pathlib import Path

def backup_database_file():
    """Backup SQLite database file directly"""
    
    db_path = "conversation_logs.db"
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file not found: {db_path}")
        return False
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"conversation_logs_backup_{timestamp}.db"
    
    try:
        # Copy database file
        shutil.copy2(db_path, backup_path)
        
        # Get file size
        file_size = os.path.getsize(backup_path)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"[OK] Database backed up: {backup_path}")
        print(f"[INFO] Backup size: {file_size_mb:.2f} MB")
        
        return backup_path
    
    except Exception as e:
        print(f"[ERROR] Backup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def backup_to_csv():
    """Backup SQLite database to CSV file"""
    
    db_path = "conversation_logs.db"
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file not found: {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all conversations
        cursor.execute("""
            SELECT id, user_id, user_name, channel_id, user_message, bot_response, 
                   timestamp, tokens_used, model_used
            FROM conversations
            ORDER BY timestamp ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"conversation_backup_{timestamp}.csv"
        
        # Write to CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                'id', 'user_id', 'user_name', 'channel_id', 
                'user_message', 'bot_response', 'timestamp', 
                'tokens_used', 'model_used'
            ])
            
            # Write data
            for row in rows:
                writer.writerow(row)
        
        # Get file size
        file_size = os.path.getsize(csv_path)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"[OK] CSV backup created: {csv_path}")
        print(f"[INFO] Conversations exported: {len(rows)}")
        print(f"[INFO] Backup size: {file_size_mb:.2f} MB")
        
        return csv_path
    
    except Exception as e:
        print(f"[ERROR] CSV backup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_stats():
    """Show database statistics"""
    
    db_path = "conversation_logs.db"
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
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
        
        # Database file size
        file_size = os.path.getsize(db_path)
        file_size_mb = file_size / (1024 * 1024)
        
        conn.close()
        
        print("=" * 70)
        print("SQLite Database Statistics")
        print("=" * 70)
        print(f"Database File: {db_path}")
        print(f"File Size: {file_size_mb:.2f} MB")
        print(f"\nTotal Conversations: {total_conversations:,}")
        print(f"Total Users: {total_users:,}")
        print(f"Total Tokens: {total_tokens:,}")
        print(f"Recent (24h): {recent_24h:,}")
        print("\nModels Used:")
        for model, count in models_used.items():
            print(f"  - {model}: {count:,}")
        print("=" * 70)
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Failed to get stats: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    
    print("SQLite Backup Tool")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "csv":
            backup_to_csv()
        elif command == "db" or command == "database":
            backup_database_file()
        elif command == "stats":
            show_stats()
        elif command == "all":
            print("[INFO] Creating both database and CSV backups...")
            backup_database_file()
            backup_to_csv()
        else:
            print(f"[ERROR] Unknown command: {command}")
            print("\nUsage:")
            print("  python backup_sqlite.py          # CSV backup")
            print("  python backup_sqlite.py csv     # CSV backup")
            print("  python backup_sqlite.py db      # Database file backup")
            print("  python backup_sqlite.py all     # Both backups")
            print("  python backup_sqlite.py stats   # Show statistics")
    else:
        # Default: CSV backup
        backup_to_csv()




