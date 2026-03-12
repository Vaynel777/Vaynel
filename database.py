"""
Database initialization and schema for Mission Control Master
Uses SQLite for simplicity and single-machine deployment
"""
import sqlite3
from pathlib import Path
from datetime import datetime
import json

DB_PATH = Path.home() / ".openclaw" / "workspace" / "mission_control_master" / "data.db"


def init_db():
    """Initialize database schema"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Deployments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deployments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            host TEXT NOT NULL,
            metrics_port INTEGER NOT NULL,
            admin_port INTEGER NOT NULL,
            region TEXT,
            model_tiers TEXT,  -- JSON array
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Metrics history (time series)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            uptime_percent REAL,
            health_status TEXT,
            rate_limit_current INTEGER,
            rate_limit_max INTEGER,
            rate_limit_percent REAL,
            tokens_used_today INTEGER,
            cost_usd_today REAL,
            cost_usd_month REAL,
            error_count_hour INTEGER,
            error_count_day INTEGER,
            active_models INTEGER,
            total_requests_hour INTEGER,
            guardrails_json TEXT,  -- JSON for all guardrail metrics
            FOREIGN KEY (deployment_id) REFERENCES deployments(id),
            UNIQUE(deployment_id, timestamp)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_deployment_time ON metrics_history(deployment_id, timestamp DESC)")

    # Critical events (push from subset)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT,
            metadata_json TEXT,  -- JSON metadata
            acknowledged BOOLEAN DEFAULT 0,
            FOREIGN KEY (deployment_id) REFERENCES deployments(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_deployment_time ON events(deployment_id, timestamp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")

    # Sync status (last successful pull from each instance)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_status (
            deployment_id TEXT PRIMARY KEY,
            last_sync_time TEXT,
            last_sync_status TEXT,  -- "success", "timeout", "error"
            last_sync_error TEXT,
            consecutive_failures INTEGER DEFAULT 0,
            FOREIGN KEY (deployment_id) REFERENCES deployments(id)
        )
    """)

    conn.commit()
    conn.close()


def get_connection():
    """Get database connection"""
    return sqlite3.connect(str(DB_PATH))


def store_metrics(deployment_id: str, metrics: dict):
    """Store metrics snapshot"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO metrics_history (
                deployment_id, timestamp, uptime_percent, health_status,
                rate_limit_current, rate_limit_max, rate_limit_percent,
                tokens_used_today, cost_usd_today, cost_usd_month,
                error_count_hour, error_count_day, active_models,
                total_requests_hour, guardrails_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deployment_id,
            metrics.get("timestamp", datetime.utcnow().isoformat()),
            metrics.get("uptime_percent"),
            metrics.get("health_status"),
            metrics.get("rate_limit_current"),
            metrics.get("rate_limit_max"),
            metrics.get("rate_limit_percent"),
            metrics.get("tokens_used_today"),
            metrics.get("cost_usd_today"),
            metrics.get("cost_usd_month"),
            metrics.get("error_count_hour"),
            metrics.get("error_count_day"),
            metrics.get("active_models"),
            metrics.get("total_requests_hour"),
            json.dumps(metrics.get("guardrails", {}))
        ))
        conn.commit()
    finally:
        conn.close()


def store_event(deployment_id: str, event: dict):
    """Store critical event"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO events (
                deployment_id, timestamp, event_type, severity, message, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            deployment_id,
            event.get("timestamp", datetime.utcnow().isoformat()),
            event.get("event_type"),
            event.get("severity"),
            event.get("message"),
            json.dumps(event.get("metadata", {}))
        ))
        conn.commit()
    finally:
        conn.close()


def get_latest_metrics(deployment_id: str) -> dict:
    """Get latest metrics for a deployment"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM metrics_history
            WHERE deployment_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (deployment_id,))

        row = cursor.fetchone()
        if not row:
            return None

        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))
    finally:
        conn.close()


def get_metrics_history(deployment_id: str, hours: int = 24) -> list:
    """Get metrics history for a deployment"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"""
            SELECT * FROM metrics_history
            WHERE deployment_id = ?
            AND timestamp >= datetime('now', '-{hours} hours')
            ORDER BY timestamp DESC
        """, (deployment_id,))

        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def get_recent_events(deployment_id: str = None, limit: int = 50) -> list:
    """Get recent critical events"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if deployment_id:
            cursor.execute("""
                SELECT * FROM events
                WHERE deployment_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (deployment_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM events
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def register_deployment(deployment_id: str, config: dict):
    """Register a deployment instance"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO deployments (
                id, name, host, metrics_port, admin_port, region, model_tiers
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            deployment_id,
            config.get("name"),
            config.get("host"),
            config.get("metrics_port"),
            config.get("admin_port"),
            config.get("region"),
            json.dumps(config.get("model_tiers", []))
        ))
        conn.commit()
    finally:
        conn.close()


def get_deployments() -> list:
    """Get all registered deployments"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM deployments")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


# Initialize DB on import
if not DB_PATH.exists():
    init_db()
