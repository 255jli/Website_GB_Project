import os
import sqlite3
import time
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')


def get_conn():
    # increase timeout and allow cross-thread access for the simple dev server
    return sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)


def _write_with_retry(fn, *args, **kwargs):
    # retry a few times on SQLITE_BUSY / database is locked
    for attempt in range(5):
        try:
            return fn(*args, **kwargs)
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if ('locked' in msg or 'busy' in msg) and attempt < 4:
                time.sleep(0.1 * (attempt + 1))
                continue
            raise

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # Use WAL journal mode to reduce contention
    try:
        cur.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    # If users table does not exist, create new one. If an old table exists with
    # column `email`, migrate it to the new schema (email -> login).
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute('''
        CREATE TABLE users (
            login TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        ''')
    else:
        # inspect columns
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if 'login' not in cols:
            # old schema detected (likely has 'email' column). Migrate safely.
            # Rename old table, create new, copy data, drop old.
            cur.execute('ALTER TABLE users RENAME TO users_old')
            cur.execute('''
            CREATE TABLE users (
                login TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            ''')
            # Prepare copy depending on available columns in old table
            old_cols = cols
            # If created_at exists, copy it; otherwise use current time
            if 'email' in old_cols and 'password_hash' in old_cols and 'created_at' in old_cols:
                cur.execute('INSERT INTO users (login, password_hash, created_at) SELECT email, password_hash, created_at FROM users_old')
            elif 'email' in old_cols and 'password_hash' in old_cols:
                cur.execute('INSERT INTO users (login, password_hash, created_at) SELECT email, password_hash, ? FROM users_old', (time.time(),))
            else:
                # fallback: nothing sensible to copy, just leave empty new table
                pass
            cur.execute('DROP TABLE IF EXISTS users_old')

    # cleanup: remove verification_codes table if present (no longer used)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='verification_codes'")
    if cur.fetchone() is not None:
        cur.execute('DROP TABLE IF EXISTS verification_codes')
    conn.commit()
    conn.close()

def create_user(login: str, password_hash: str) -> None:
    def _create():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO users (login, password_hash, created_at) VALUES (?, ?, ?)',
                    (login, password_hash, time.time()))
        conn.commit()
        conn.close()

    return _write_with_retry(_create)

def get_user(login: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT login, password_hash, created_at FROM users WHERE login = ?', (login,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {'login': row[0], 'password_hash': row[1], 'created_at': row[2]}

def set_verification_code(email: str, code: str, expires: float) -> None:
    def _set():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('REPLACE INTO verification_codes (email, code, expires) VALUES (?, ?, ?)', (email, code, expires))
        conn.commit()
        conn.close()

    return _write_with_retry(_set)

def verify_code(email: str, code: str) -> bool:
    def _verify():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT code, expires FROM verification_codes WHERE email = ?', (email,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        stored_code, expires = row[0], row[1]
        now = time.time()
        if now > expires or stored_code != code:
            # expired or mismatch
            cur.execute('DELETE FROM verification_codes WHERE email = ?', (email,))
            conn.commit()
            conn.close()
            return False

        # mark user verified and remove code
        cur.execute('UPDATE users SET verified = 1 WHERE email = ?', (email,))
        cur.execute('DELETE FROM verification_codes WHERE email = ?', (email,))
        conn.commit()
        conn.close()
        return True

    return _write_with_retry(_verify)

def delete_verification_code(email: str) -> None:
    def _del():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM verification_codes WHERE email = ?', (email,))
        conn.commit()
        conn.close()

    return _write_with_retry(_del)

# Note: verification_codes and related helpers removed — simplified auth uses only login+password
