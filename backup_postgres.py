"""
PostgreSQL Backup Script for Railway
Creates backups of PostgreSQL database

Usage:
1. Set DATABASE_URL environment variable
2. Run: python backup_postgres.py
"""

import os
import csv
from datetime import datetime
from conversation_logger import ConversationLogger

def backup_to_csv():
    """Backup PostgreSQL database to CSV file"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL not set!")
        print("[INFO] Get DATABASE_URL from Railway PostgreSQL service")
        return False
    
    try:
        # Initialize logger
        logger = ConversationLogger(database_url=database_url)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"postgres_backup_{timestamp}.csv"
        
        print(f"[INFO] Creating backup: {filename}")
        
        # Export to CSV
        filepath = logger.export_to_csv(output_path=filename)
        
        print(f"[OK] Backup created: {filepath}")
        
        # Get file size
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        print(f"[INFO] Backup size: {file_size_mb:.2f} MB")
        
        return filepath
    
    except Exception as e:
        print(f"[ERROR] Backup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def backup_stats():
    """Show backup statistics"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL not set!")
        return False
    
    try:
        logger = ConversationLogger(database_url=database_url)
        stats = logger.get_stats()
        
        print("=" * 70)
        print("Database Statistics")
        print("=" * 70)
        print(f"Total Conversations: {stats['total_conversations']:,}")
        print(f"Total Users: {stats['total_users']:,}")
        print(f"Total Tokens: {stats['total_tokens']:,}")
        print(f"Recent (24h): {stats['recent_24h']:,}")
        print("\nModels Used:")
        for model, count in stats['models_used'].items():
            print(f"  - {model}: {count:,}")
        print("=" * 70)
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Failed to get stats: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    print("PostgreSQL Backup Tool")
    print("=" * 70)
    
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        backup_stats()
    else:
        backup_to_csv()





