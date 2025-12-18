import sqlite3
import csv
import io
import logging
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from datetime import datetime

# --- 1. 設定 Flask 與 Log 過濾 ---
app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False

# 隱藏 Dashboard 的 GET 請求 Log
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

DB_NAME = "smart_factory.db"

# === [關鍵參數修改] ===
MAINTENANCE_THRESHOLD = 5   # 使用 5 次即顯示維護
OVERDUE_SECONDS = 15        # 借出 15 秒即逾期
# ======================

HAS_RECEIVED_FIRST_DATA = False

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS tools (
                    slot_id INTEGER PRIMARY KEY,
                    name TEXT,
                    status INTEGER,
                    current_user_rfid TEXT,
                    weight REAL DEFAULT 0.0,
                    borrow_time TIMESTAMP,
                    usage_count INTEGER DEFAULT 0
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_id INTEGER,
                    action TEXT,
                    user_name TEXT,
                    timestamp TIMESTAMP
                )''')

    c.execute("SELECT count(*) FROM tools")
    if c.fetchone()[0] == 0:
        print(">> [System] Creating New Database Slots...")
        c.execute("INSERT INTO tools VALUES (1, 'Precision Screwdriver Set', -1, '', 0.0, NULL, 0)")
        c.execute("INSERT INTO tools VALUES (2, 'Digital Torque Wrench', -1, '', 0.0, NULL, 0)")
    else:
        print(">> [System] Resetting status to 'Waiting' (0.0kg)...")
        c.execute("UPDATE tools SET status=-1, weight=0.0, current_user_rfid='', borrow_time=NULL")

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return "<h1>🏭 Smart Tool Shelf System is Running...</h1>"

@app.route('/api/update', methods=['POST'])
def update_data():
    global HAS_RECEIVED_FIRST_DATA
    
    try:
        payload = request.json
        if not payload:
            return jsonify({"status": "error", "msg": "Empty payload"}), 400

        # --- 真實資料檢測提示 (只顯示一次) ---
        if not HAS_RECEIVED_FIRST_DATA:
            print("\n" + "="*60)
            print("✅✅✅  SUCCESS: 收到第一筆硬體真實數據！連線成功！  ✅✅✅")
            print("      (System connected to Arduino/ESP32)      ")
            print("="*60 + "\n")
            HAS_RECEIVED_FIRST_DATA = True
        # -----------------------

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response_msg = []

        systems_map = [
            {"slot_id": 1, "json_key": "system1"},
            {"slot_id": 2, "json_key": "system2"}
        ]

        for sys in systems_map:
            s_id = sys['slot_id']
            key = sys['json_key']
            sys_data = payload.get(key)

            if sys_data:
                # 解析數據
                raw_led = sys_data.get('led_status', 'green')
                raw_auth = sys_data.get('authorized', False)
                raw_weight = sys_data.get('weight', 0.0)
                
                new_status = 0 if raw_led == 'red' else 1
                auth_str = "True" if raw_auth else "False"

                # 更新重量
                c.execute("UPDATE tools SET weight=? WHERE slot_id=?", (raw_weight, s_id))

                # 狀態處理
                c.execute("SELECT status, usage_count FROM tools WHERE slot_id=?", (s_id,))
                row = c.fetchone()
                
                if row:
                    old_status = row[0]
                    current_usage = row[1]
                    
                    # 初始化狀態 (-1 -> 正常)
                    if old_status == -1:
                         c.execute("UPDATE tools SET status=?, current_user_rfid=? WHERE slot_id=?", (new_status, auth_str, s_id))
                         print(f"📡 [Init] Slot {s_id} Connected | Status: {'Available' if new_status==1 else 'Borrowed'} | Weight: {raw_weight}kg")

                    # 狀態切換
                    elif old_status != new_status:
                        if new_status == 0: # 借出
                            new_usage = current_usage + 1
                            c.execute("UPDATE tools SET status=0, current_user_rfid=?, borrow_time=?, usage_count=? WHERE slot_id=?", 
                                      (auth_str, now_str, new_usage, s_id))
                            c.execute("INSERT INTO logs (slot_id, action, user_name, timestamp) VALUES (?, ?, ?, ?)",
                                      (s_id, "Borrowed", auth_str, now_str))
                            
                            log_msg = f"Slot {s_id} [TAKEN] (Real) | Auth: {auth_str} | LED: {raw_led}"
                            print(f"🔴 {log_msg}")
                            response_msg.append(log_msg)

                        elif new_status == 1: # 歸還
                            c.execute("UPDATE tools SET status=1, current_user_rfid='', borrow_time=NULL WHERE slot_id=?", (s_id,))
                            c.execute("INSERT INTO logs (slot_id, action, user_name, timestamp) VALUES (?, ?, ?, ?)",
                                      (s_id, "Returned", "", now_str))
                            
                            log_msg = f"Slot {s_id} [RETURNED] (Real) | Weight: {raw_weight} | LED: {raw_led}"
                            print(f"🟢 {log_msg}")
                            response_msg.append(log_msg)

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "processed": response_msg})

    except Exception as e:
        print(f"!! [Error] Processing Real Data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tools")
    tools = c.fetchall()
    
    dashboard_data = []
    now = datetime.now()
    
    for t in tools:
        slot_info = {
            "slot_id": t["slot_id"],
            "name": t["name"],
            "usage_count": t["usage_count"],
            "weight": t["weight"],
            "display_status": "Available",
            "led_color": "green",
            "authorized_status": "-",
            "alert_overdue": False,
            "alert_maintenance": False
        }

        if t["status"] == -1:
            slot_info["display_status"] = "Waiting..."
            slot_info["led_color"] = "grey"
            slot_info["authorized_status"] = "Connecting"
            slot_info["weight"] = 0.0
        else:
            if t["usage_count"] >= MAINTENANCE_THRESHOLD:
                slot_info["alert_maintenance"] = True
            
            if t["status"] == 0:
                slot_info["display_status"] = "Borrowed"
                slot_info["led_color"] = "red"
                slot_info["authorized_status"] = t["current_user_rfid"]
                
                if t["borrow_time"]:
                    try:
                        borrow_dt = datetime.strptime(t["borrow_time"], "%Y-%m-%d %H:%M:%S")
                        if (now - borrow_dt).total_seconds() > OVERDUE_SECONDS:
                            slot_info["display_status"] = "Overdue"
                            slot_info["alert_overdue"] = True
                    except:
                        pass

        dashboard_data.append(slot_info)
    conn.close()
    return jsonify(dashboard_data)

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/export', methods=['GET'])
def export_csv():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, slot_id, action, user_name, timestamp FROM logs ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Log ID', 'Slot ID', 'Action', 'Authorized', 'Timestamp'])
    cw.writerows(rows)
    output = make_response('\ufeff' + si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=tools_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    init_db()
    print("\n")
    print("================================================================")
    print("      SMART TOOL SHELF SERVER (Final System V10.1)             ")
    print("      狀態: 等待 Arduino 連線中... (Status: Waiting)            ")
    print("      請連接硬體，當收到真實數據時，下方將會顯示綠色提示。        ")
    print("================================================================")
    app.run(host='0.0.0.0', port=5000, debug=True)