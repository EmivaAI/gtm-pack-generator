import sqlite3
import json
from config import config

def view_data():
    try:
        # Extract file path from sqlite:/// URL
        db_path = config.DATABASE_URL.replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Check if table exists first
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='source_event'")
        if not cur.fetchone():
            print("Table 'source_event' does not exist yet. Send some webhooks first!")
            return

        cur.execute("SELECT * FROM source_event ORDER BY created_at DESC LIMIT 20")
        rows = cur.fetchall()
        
        if not rows:
            print("No data found in source_event table.")
            return

        print(f"{'ID':<38} | {'Source':<10} | {'Workspace':<20} | {'Created At':<25}")
        print("-" * 105)
        
        for row in rows:
            created_at = str(row['created_at'])
            print(f"{row['id']:<38} | {row['source_type']:<10} | {row['workspace_id']:<20} | {created_at:<25}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    view_data()
