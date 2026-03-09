import sqlite3
from datetime import datetime, timedelta

def init_db():
    """Создаёт все таблицы при первом запуске"""
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            total_clicks INTEGER DEFAULT 0,
            click_power INTEGER DEFAULT 1,
            energy INTEGER DEFAULT 100,
            max_energy INTEGER DEFAULT 100,
            energy_regen INTEGER DEFAULT 1,
            crit_chance INTEGER DEFAULT 0,
            premium BOOLEAN DEFAULT FALSE,
            premium_expire TIMESTAMP,
            current_skin TEXT DEFAULT 'normal',
            referrals INTEGER DEFAULT 0,
            referrer_id INTEGER,
            last_energy_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица покупок
    cur.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item TEXT,
            stars INTEGER,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица рефералов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referral_id INTEGER,
            bonus_claimed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных создана")

def get_user(user_id, username=None, first_name=None, referrer_id=None):
    """Получает пользователя из БД или создаёт нового"""
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    
    # Пробуем найти пользователя
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cur.fetchone()
    
    # Если нет - создаём
    if not user:
        cur.execute('''
            INSERT INTO users (user_id, username, first_name, referrer_id)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, referrer_id))
        conn.commit()
        
        # Если есть реферер, начисляем бонус
        if referrer_id and referrer_id != user_id:
            cur.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (referrer_id,))
            cur.execute('UPDATE users SET balance = balance + 100 WHERE user_id = ?', (referrer_id,))
            conn.commit()
    
    # Получаем данные
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cur.fetchone()
    conn.close()
    
    # Преобразуем кортеж в словарь для удобства
    columns = ['user_id', 'username', 'first_name', 'balance', 'total_clicks', 
               'click_power', 'energy', 'max_energy', 'energy_regen', 'crit_chance',
               'premium', 'premium_expire', 'current_skin', 'referrals', 'referrer_id',
               'last_energy_update', 'created_at']
    
    return dict(zip(columns, user))

def update_user(user_id, **kwargs):
    """Обновляет данные пользователя"""
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    
    for key, value in kwargs.items():
        cur.execute(f'UPDATE users SET {key} = ? WHERE user_id = ?', (value, user_id))
    
    conn.commit()
    conn.close()

def add_purchase(user_id, item, stars):
    """Записывает покупку"""
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO purchases (user_id, item, stars) VALUES (?, ?, ?)',
                (user_id, item, stars))
    conn.commit()
    conn.close()

def get_top_users(limit=10):
    """Топ игроков по кликам"""
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT first_name, total_clicks, balance 
        FROM users 
        ORDER BY total_clicks DESC 
        LIMIT ?
    ''', (limit,))
    top = cur.fetchall()
    conn.close()
    return top