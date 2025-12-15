"""
Migration Script: SQLite to PostgreSQL
Migrates conversation data from SQLite to PostgreSQL (Railway)

Usage:
1. Set DATABASE_URL environment variable (from Railway PostgreSQL)
2. Run: python migrate_sqlite_to_postgres.py
"""

import os
import sqlite3
import sys
from conversation_logger import ConversationLogger

def migrate_conversations():
    """Migrate conversations from SQLite to PostgreSQL"""
    
    # Check DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL not set!")
        print("[INFO] Get DATABASE_URL from Railway PostgreSQL service")
        print("[INFO] Set it: export DATABASE_URL='postgresql://...'")
        return False
    
    # SQLite database paths
    sqlite_conversations_db = "conversation_logs.db"
    sqlite_memory_db = "bot_memory.db"
    
    # Check if SQLite databases exist
    conversations_exist = os.path.exists(sqlite_conversations_db)
    memory_exist = os.path.exists(sqlite_memory_db)
    
    if not conversations_exist and not memory_exist:
        print("[ERROR] No SQLite databases found!")
        print(f"[INFO] Looking for: {sqlite_conversations_db} or {sqlite_memory_db}")
        return False
    
    print("=" * 70)
    print("SQLite to PostgreSQL Migration")
    print("=" * 70)
    
    # Initialize PostgreSQL logger
    try:
        print("\n[INFO] Connecting to PostgreSQL...")
        postgres_logger = ConversationLogger(database_url=database_url)
        print("[OK] Connected to PostgreSQL!")
    except Exception as e:
        print(f"[ERROR] Failed to connect to PostgreSQL: {e}")
        return False
    
    # Migrate conversations
    if conversations_exist:
        print(f"\n[INFO] Migrating conversations from {sqlite_conversations_db}...")
        try:
            sqlite_conn = sqlite3.connect(sqlite_conversations_db)
            cursor = sqlite_conn.cursor()
            
            # Get all conversations
            cursor.execute("""
                SELECT user_id, user_name, channel_id, user_message, bot_response, 
                       timestamp, tokens_used, model_used
                FROM conversations
                ORDER BY timestamp ASC
            """)
            
            rows = cursor.fetchall()
            total = len(rows)
            print(f"[INFO] Found {total} conversations to migrate")
            
            if total > 0:
                migrated = 0
                skipped = 0
                
                for row in rows:
                    user_id, user_name, channel_id, user_message, bot_response, timestamp, tokens_used, model_used = row
                    
                    try:
                        # Log to PostgreSQL
                        postgres_logger.log_conversation(
                            user_id=str(user_id),
                            user_name=str(user_name),
                            channel_id=str(channel_id),
                            user_message=str(user_message),
                            bot_response=str(bot_response),
                            tokens_used=tokens_used or 0,
                            model_used=str(model_used) if model_used else "unknown"
                        )
                        migrated += 1
                        
                        if migrated % 100 == 0:
                            print(f"[INFO] Migrated {migrated}/{total} conversations...")
                    
                    except Exception as e:
                        print(f"[WARNING] Failed to migrate conversation {row[0]}: {e}")
                        skipped += 1
                        continue
                
                print(f"\n[OK] Migration complete!")
                print(f"  - Migrated: {migrated}")
                print(f"  - Skipped: {skipped}")
                print(f"  - Total: {total}")
            
            sqlite_conn.close()
        
        except Exception as e:
            print(f"[ERROR] Failed to migrate conversations: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Note about memory database
    if memory_exist:
        print(f"\n[INFO] Found {sqlite_memory_db}")
        print("[INFO] Memory database contains conversation context (not conversations)")
        print("[INFO] This is used for AI context, not permanent storage")
        print("[INFO] Memory will rebuild automatically as bot runs")
        print("[INFO] No migration needed for memory database")
    
    # Verify migration
    print("\n[INFO] Verifying migration...")
    try:
        stats = postgres_logger.get_stats()
        print(f"[OK] PostgreSQL now has:")
        print(f"  - Total conversations: {stats['total_conversations']}")
        print(f"  - Total users: {stats['total_users']}")
        print(f"  - Total tokens: {stats['total_tokens']:,}")
    except Exception as e:
        print(f"[WARNING] Could not verify: {e}")
    
    print("\n" + "=" * 70)
    print("Migration Complete!")
    print("=" * 70)
    print("\n[INFO] Your bot is now using PostgreSQL")
    print("[INFO] Old SQLite files are preserved as backup")
    print("[INFO] You can delete SQLite files after verifying PostgreSQL works")
    
    return True

if __name__ == "__main__":
    print("SQLite to PostgreSQL Migration Tool")
    print("=" * 70)
    
    # Confirm migration
    response = input("\nThis will migrate data from SQLite to PostgreSQL. Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        sys.exit(0)
    
    # Run migration
    success = migrate_conversations()
    
    if success:
        print("\n✅ Migration successful!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)



