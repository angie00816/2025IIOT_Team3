"""
檔案名稱：simulate_manual.py (後台遙控器)
用途：手動觸發資料發送，配合演員動作。
操作說明：
    輸入 's' -> 啟動 (Start/Connect)，所有燈變綠。
    輸入 '1' -> 切換 Slot 1 狀態 (借出 <-> 歸還)。
    輸入 '2' -> 切換 Slot 2 狀態 (借出 <-> 歸還)。
    輸入 'h' -> 發送心跳 (Heartbeat)，維持現狀發送一次。
"""
import requests
import time
import os

URL = "http://127.0.0.1:5000/api/update"

# === 設定預設重量 ===
WEIGHT_S1_FULL = 0.85
WEIGHT_S2_FULL = 0.53
WEIGHT_EMPTY = 0.00

# === 內部狀態紀錄 ===
state = {
    "s1": {"status": "green", "auth": False, "weight": WEIGHT_S1_FULL},
    "s2": {"status": "green", "auth": False, "weight": WEIGHT_S2_FULL}
}

def send_current_state():
    """ 發送當前的 state 給後端 """
    payload = {
        "timestamp": int(time.time()),
        "system1": {
            "weight": state["s1"]["weight"],
            "authorized": state["s1"]["auth"],
            "led_status": state["s1"]["status"]
        },
        "system2": {
            "weight": state["s2"]["weight"],
            "authorized": state["s2"]["auth"],
            "led_status": state["s2"]["status"]
        }
    }
    try:
        res = requests.post(URL, json=payload)
        print(f" -> 發送成功! HTTP {res.status_code}")
    except Exception as e:
        print(f" -> 發送失敗: {e}")

def toggle_slot(slot_key, full_weight):
    """ 切換指定 Slot 的借還狀態 """
    current = state[slot_key]
    if current["status"] == "green":
        # 變成借出 (Red)
        current["status"] = "red"
        current["auth"] = True
        current["weight"] = WEIGHT_EMPTY
        print(f"🔴 切換 {slot_key} 為 [借出] (Red)")
    else:
        # 變成歸還 (Green)
        current["status"] = "green"
        current["auth"] = False
        current["weight"] = full_weight
        print(f"🟢 切換 {slot_key} 為 [歸還] (Green)")

def main():
    print("==========================================")
    print("   後台遙控模擬器 (HIDDEN CONTROLLER)     ")
    print("   [s] 啟動連線 (Start) - 變綠燈")
    print("   [1] 切換 Slot 1 (借/還)")
    print("   [2] 切換 Slot 2 (借/還)")
    print("   [h] 心跳 (Heartbeat) - 僅發送資料")
    print("   [q] 離開程式")
    print("==========================================")
    print("等待指令中...")

    while True:
        cmd = input("指令 > ").strip().lower()
        
        if cmd == 'q':
            break
        
        elif cmd == 's':
            # 確保狀態是初始綠色
            state["s1"] = {"status": "green", "auth": False, "weight": WEIGHT_S1_FULL}
            state["s2"] = {"status": "green", "auth": False, "weight": WEIGHT_S2_FULL}
            print("🚀 發送啟動連線訊號...")
            send_current_state()

        elif cmd == '1':
            toggle_slot("s1", WEIGHT_S1_FULL)
            send_current_state()

        elif cmd == '2':
            toggle_slot("s2", WEIGHT_S2_FULL)
            send_current_state()

        elif cmd == 'h':
            print("💓 發送心跳訊號...")
            send_current_state()
            
        else:
            print("無效指令，請輸入 s, 1, 2, h")

if __name__ == "__main__":
    main()