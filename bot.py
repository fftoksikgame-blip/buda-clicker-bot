import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    
    # Пользователи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            total_clicks INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            pph INTEGER DEFAULT 0,
            daily_cipher BOOLEAN DEFAULT FALSE,
            daily_combo BOOLEAN DEFAULT FALSE,
            last_daily TIMESTAMP,
            referrals INTEGER DEFAULT 0,
            referrer_id INTEGER,
            premium BOOLEAN DEFAULT FALSE,
            premium_expire TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Покупки
    cur.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item TEXT,
            stars INTEGER,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных готова")

def get_user(user_id, username=None, first_name=None, referrer_id=None):
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cur.fetchone()
    
    if not user and username:
        cur.execute('''
            INSERT INTO users (user_id, username, first_name, referrer_id)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, referrer_id))
        conn.commit()
        
        cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cur.fetchone()
    
    conn.close()
    return user

def update_user(user_id, **kwargs):
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    
    for key, value in kwargs.items():
        cur.execute(f'UPDATE users SET {key} = ? WHERE user_id = ?', (value, user_id))
    
    conn.commit()
    conn.close()

def get_top_users(limit=10):
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT first_name, total_clicks, pph, balance 
        FROM users 
        WHERE total_clicks > 0 
        ORDER BY total_clicks DESC 
        LIMIT ?
    ''', (limit,))
    top = cur.fetchall()
    conn.close()
    return top
