import sqlite3
from datetime import datetime

DB_PATH = "./devices.db"

#   TABLE devices:
#   identity_mac    passkey     last_paired
#   2E:FC:F8...     

def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            identity_mac TEXT PRIMARY KEY,
            passkey TEXT NOT NULL,
            last_paired TEXT NOT NULL
        )
    """)
    return conn

def store_device(mac_address: str, passkey: str):
    conn = _get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO devices (identity_mac, passkey, last_paired) VALUES (?, ?, ?) "
        "ON CONFLICT(identity_mac) DO UPDATE SET passkey = ?, last_paired = ?",
        (mac_address, passkey, now, passkey, now)
    )
    conn.commit()
    conn.close()

def load_mac_addresses():
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT identity_mac FROM devices")
    macs = [row[0].upper() for row in cursor.fetchall()]
    conn.close()
    return macs