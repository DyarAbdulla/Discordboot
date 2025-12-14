"""
Web Dashboard - Simple Flask dashboard to monitor bot stats
"""

from flask import Flask, render_template_string, jsonify
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Dashboard HTML template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Discord Bot Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 {
            color: #667eea;
            margin-bottom: 30px;
            text-align: center;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card h3 {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 36px;
            font-weight: bold;
        }
        .section {
            margin-top: 30px;
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 15px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #667eea;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-bottom: 20px;
        }
        .refresh-btn:hover {
            background: #764ba2;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Discord Bot Dashboard</h1>
        
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Messages</h3>
                <div class="value">{{ stats.total_messages }}</div>
            </div>
            <div class="stat-card">
                <h3>Total Commands</h3>
                <div class="value">{{ stats.total_commands }}</div>
            </div>
            <div class="stat-card">
                <h3>Active Servers</h3>
                <div class="value">{{ stats.servers }}</div>
            </div>
            <div class="stat-card">
                <h3>Uptime</h3>
                <div class="value">{{ stats.uptime }}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Recent Activity (Last 7 Days)</h2>
            <p>Statistics are automatically updated as the bot processes messages.</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""


def get_db_connection():
    """Get database connection"""
    db_path = os.getenv("DATABASE_PATH", "bot.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def dashboard():
    """Main dashboard page"""
    conn = get_db_connection()
    
    try:
        # Get stats from last 7 days
        cursor = conn.execute("""
            SELECT SUM(message_count) as total_messages,
                   SUM(command_count) as total_commands,
                   COUNT(DISTINCT server_id) as servers
            FROM bot_stats
            WHERE date >= date('now', '-7 days')
        """)
        
        row = cursor.fetchone()
        stats = {
            "total_messages": row["total_messages"] or 0,
            "total_commands": row["total_commands"] or 0,
            "servers": row["servers"] or 0,
            "uptime": "Active"
        }
    except Exception as e:
        stats = {
            "total_messages": 0,
            "total_commands": 0,
            "servers": 0,
            "uptime": "Unknown"
        }
    finally:
        conn.close()
    
    return render_template_string(DASHBOARD_HTML, stats=stats)


@app.route('/api/stats')
def api_stats():
    """API endpoint for stats"""
    conn = get_db_connection()
    
    try:
        cursor = conn.execute("""
            SELECT SUM(message_count) as total_messages,
                   SUM(command_count) as total_commands,
                   COUNT(DISTINCT server_id) as servers
            FROM bot_stats
            WHERE date >= date('now', '-7 days')
        """)
        
        row = cursor.fetchone()
        return jsonify({
            "total_messages": row["total_messages"] or 0,
            "total_commands": row["total_commands"] or 0,
            "servers": row["servers"] or 0
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

