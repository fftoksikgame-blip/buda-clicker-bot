from flask import Flask, send_file, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Главная страница - игра
@app.route('/')
def index():
    return send_file('templates/index.html')

# Сохранение клика
@app.route('/api/click', methods=['POST'])
def save_click():
    data = request.json
    user_id = data.get('user_id')
    earned = data.get('earned')
    
    if user_id:
        conn = sqlite3.connect('buda.db')
        cur = conn.cursor()
        cur.execute('''
            UPDATE users 
            SET balance = balance + ?, total_clicks = total_clicks + 1 
            WHERE user_id = ?
        ''', (earned, user_id))
        conn.commit()
        conn.close()
    
    return jsonify({'status': 'ok'})

# Получение топа
@app.route('/api/top')
def get_top():
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT first_name, total_clicks 
        FROM users 
        ORDER BY total_clicks DESC 
        LIMIT 10
    ''')
    top = cur.fetchall()
    conn.close()
    
    return jsonify(top)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)