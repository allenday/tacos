import sqlite3
import logging
import datetime
from . import config

logger = logging.getLogger(__name__)

DATABASE = config.DATABASE_FILE

def get_db():
    """Opens a new database connection."""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def close_db(conn):
    """Closes the database connection."""
    if conn is not None:
        conn.close()

def init_db():
    """Initializes the database schema if it doesn't exist."""
    schema = """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giver_id TEXT NOT NULL,
        recipient_id TEXT NOT NULL,
        amount INTEGER NOT NULL,
        note TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        source_channel_id TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_giver_timestamp ON transactions (giver_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_recipient_timestamp ON transactions (recipient_id, timestamp);
    """
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.executescript(schema)
        conn.commit()
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        close_db(conn)

def get_tacos_given_last_24h(giver_id):
    """Calculates the total number of tacos given by a user in the last 24 hours."""
    # Calculate the timestamp for 24 hours ago
    time_24_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=24)
    query = """
    SELECT SUM(amount) FROM transactions
    WHERE giver_id = ? AND timestamp >= ?
    """
    conn = None
    total = 0
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Convert datetime object to ISO 8601 string format suitable for SQLite comparison
        cursor.execute(query, (giver_id, time_24_hours_ago.isoformat()))
        result = cursor.fetchone()
        if result and result[0] is not None:
            total = result[0]
    except sqlite3.Error as e:
        logger.error(f"Error fetching tacos given in last 24h for {giver_id}: {e}")
    finally:
        close_db(conn)
    return total

# --- Placeholder functions for command logic --- #

def add_transaction(giver_id, recipient_id, amount, note, source_channel_id):
    """Adds a new taco transaction to the database, including the source channel."""
    query = """
    INSERT INTO transactions (giver_id, recipient_id, amount, note, source_channel_id)
    VALUES (?, ?, ?, ?, ?)
    """
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(query, (giver_id, recipient_id, amount, note, source_channel_id))
        conn.commit()
        logger.info(f"Transaction added: {giver_id} -> {recipient_id} ({amount} {config.UNIT_NAME_PLURAL}) from channel {source_channel_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error adding transaction: {e}")
        conn.rollback() # Rollback changes on error
        return False
    finally:
        close_db(conn)

def get_leaderboard(limit=config.LEADERBOARD_LIMIT, time_range=None):
    """Gets the leaderboard based on received tacos, optionally filtered by time range."""
    query = """
    SELECT recipient_id, SUM(amount) as total_received
    FROM transactions
    """
    
    params = []
    
    if time_range:
        query += " WHERE timestamp >= ? "
        params.append(_get_time_range_start(time_range))
    
    query += """
    GROUP BY recipient_id
    ORDER BY total_received DESC
    LIMIT ?
    """
    params.append(limit)
    
    conn = None
    leaders = []
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        leaders = cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Error fetching leaderboard: {e}")
    finally:
        close_db(conn)
    return leaders

def get_history(lines=config.DEFAULT_HISTORY_LINES, giver_id=None, recipient_id=None):
    """Gets recent transaction history, filtering by giver or recipient."""
    base_query = "SELECT giver_id, recipient_id, amount, note, timestamp, source_channel_id FROM transactions"
    filters = []
    params = []

    # Ensure only one filter type is active if both are provided,
    # prioritizing recipient_id if that happens (matches history @user behavior)
    if recipient_id:
        filters.append("recipient_id = ?")
        params.append(recipient_id)
    elif giver_id:
        filters.append("giver_id = ?")
        params.append(giver_id)
    # If neither is specified, no WHERE clause is added initially.

    if filters:
        base_query += " WHERE " + " AND ".join(filters) # 'AND' is okay even for one filter

    base_query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(lines)

    conn = None
    history = []
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(base_query, tuple(params))
        history = cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Error fetching history: {e}")
    finally:
        close_db(conn)
    return history  

def _get_time_range_start(time_range):
    """
    Returns the start datetime for the specified time range.
    
    Args:
        time_range (str): One of: 'last7days', 'lastweek', 'lastmonth', 'lastquarter', 
                          'thismonth', 'thisquarter', 'alltime'
    
    Returns:
        str: ISO formatted datetime string for the start of the time range
    """
    now = datetime.datetime.now()
    
    if time_range == 'last7days':
        start_date = now - datetime.timedelta(days=7)
    elif time_range == 'lastweek':
        days_since_monday = now.weekday()
        start_of_this_week = now - datetime.timedelta(days=days_since_monday)
        start_date = start_of_this_week - datetime.timedelta(days=7)
    elif time_range == 'lastmonth':
        if now.month == 1:
            start_date = datetime.datetime(now.year - 1, 12, 1)
        else:
            start_date = datetime.datetime(now.year, now.month - 1, 1)
    elif time_range == 'lastquarter':
        current_quarter = (now.month - 1) // 3 + 1
        if current_quarter == 1:
            start_date = datetime.datetime(now.year - 1, 10, 1)
        else:
            start_date = datetime.datetime(now.year, (current_quarter - 1) * 3 - 2, 1)
    elif time_range == 'thismonth':
        start_date = datetime.datetime(now.year, now.month, 1)
    elif time_range == 'thisquarter':
        current_quarter = (now.month - 1) // 3 + 1
        start_date = datetime.datetime(now.year, (current_quarter - 1) * 3 + 1, 1)
    else:
        start_date = datetime.datetime(1970, 1, 1)
        
    return start_date.isoformat()        