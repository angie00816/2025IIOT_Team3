## Firmware (Arduino) — Dual-Slot Smart Tool Shelf Logic

This Arduino firmware controls a **two-slot smart tool shelf** using:
- 2× RC522 RFID readers (MFRC522 library, shared SPI bus)
- 2× Load Cells + HX711 (weight sensing)
- 2× Red/Green LED pairs (status indication)

**Main rule:**
- **Green LED = Authorized AND Tool Present (weight > threshold)**
- Otherwise, the LED stays **Red**

---

### Key Features
- Two independent slots (System 1 / System 2)
- RFID authorization with UID whitelist
  - Slot 1: accepts **two allowed UIDs**
  - Slot 2: accepts **one allowed UID**
- Authorization toggle on valid card scan (`toggle = !toggle`)
- Weight threshold detection using HX711 readings
- Serial debug output printed once per second

---

### Hardware Pin Mapping

**Slot 1**
- HX711: DOUT = D3, SCK = D2  
- LEDs: RED = D8, GREEN = D9  
- RFID SS (SDA): D5  

**Slot 2**
- HX711: DOUT = D4, SCK = D13  
- LEDs: RED = D10, GREEN = D11  
- RFID SS (SDA): D6  

**Shared**
- RFID RST: D7  
- SPI bus: shared by both RC522 modules (different SS pins)

---

### RFID Authorization Rules (UID Whitelist)
- Slot 1: matches either `UID_1` or `UID_2`
- Slot 2: matches `UID_2_SINGLE` only  
If UID is not in the whitelist, it is ignored and does not change authorization state.

---

### LED Logic (Per Slot)
1. Check RFID: if a new card is present, read UID
2. If UID is valid → toggle authorization state
3. Read weight from HX711 (`fabs(scale.get_units())`)
4. Compare to threshold (`weight > 0.5`)
5. LED output:
   - Green if `authorized == true` AND `weightOK == true`
   - Red otherwise

---

### Serial Output
Every 1 second, the firmware prints:
- Authorization state (TRUE/FALSE)
- Current weight
- LED state (Green/Red)

---

### Notes
- Threshold is `0.5` (see `TARGET_WEIGHT_G`) — adjust based on your setup.
- Calibration factor is `100000.0f` (see `CALIBRATION_FACTOR`) — tune if needed.

## 🌐 ESP8266 Wi-Fi Bridge (Serial ➜ JSON ➜ HTTP POST)

This sketch turns an **ESP8266** into a small **Wi-Fi bridge / gateway** for our project.

✅ It **listens to JSON messages** coming from the Arduino via **Serial**  
✅ It prints the **RAW JSON** for debugging  
✅ It **validates** the JSON format (so bad data won’t be sent)  
✅ It then forwards the data to our backend server using **HTTP POST**  
✅ Plus, it has **auto Wi-Fi reconnect** to stay online as much as possible 🔁

---

### ✨ What this bridge does (in one sentence)
📥 **Serial input** (JSON) → 🧠 **Validate** → 📡 **Wi-Fi** → 🚀 **POST to Backend**

---

### 🧩 Key Features

#### 1) 📶 Auto Wi-Fi Connect + Reconnect
- Connects to the specified SSID/password on boot
- Checks Wi-Fi status **every 5 seconds**
- If disconnected, it will **retry automatically** and print connection info (IP / RSSI)

#### 2) 🕵️ RAW Serial Monitor Output
- Every message received from Arduino is printed as:
  - `[RAW] { ...json... }`
- This makes debugging super easy: you can confirm **what data is actually arriving**

#### 3) ✅ JSON Validation (Before Sending)
- Uses `ArduinoJson` to parse the incoming string  
- If parsing fails, it prints the error and **stops that upload**
- Prevents sending broken or incomplete data to the server

#### 4) 🚀 HTTP POST to Backend API
- When Wi-Fi is connected, it sends the JSON to:
  - `serverURL = "http://172.20.10.3:5000/api/data"`
- Uses:
  - `Content-Type: application/json`
- Prints the HTTP response code + server reply for confirmation

#### 5) 🧾 Periodic Status Report
- Every **30 seconds**, it prints a small status report:
  - Connected / Not connected
  - Current IP and RSSI (signal strength)

---

### 🔧 How to Use
1. Upload this sketch to the ESP8266  
2. Connect ESP8266 to Arduino via Serial (TX/RX + GND)  
3. Make sure Arduino sends **one JSON per line** (ends with `\n`)  
4. Start Serial Monitor at **115200 baud**
5. When Wi-Fi is up, you should see:
   - `✓ WiFi 連接成功！`
   - Then `[RAW] ...`
   - Then `HTTP 回應碼: ...`

---

### ⚙️ Configuration
Update these fields before uploading:

- Wi-Fi:
  - `ssid`
  - `password`
- Backend endpoint:
  - `serverURL`

---

### 📝 Notes
- The bridge only sends data **when Wi-Fi is connected**
- If Wi-Fi is down, it will keep waiting and reconnecting (data will not be posted during disconnect)
- JSON size is limited by:
  - `StaticJsonDocument<512>`
  (Keep messages small and clean)

## 🧠 Backend Server (Flask) + 🗄️ SQLite Database

This is the **backend brain** of our Smart Tool Shelf system.  
It receives data from the hardware, stores it in SQLite, and provides clean API endpoints for the web dashboard.

---

### 🚀 What this backend does (quick overview)

📥 **Receive** tool status from firmware (POST)  
🗄️ **Store** current state + history logs in SQLite  
🧮 **Apply rules** like *Overdue* and *Maintenance*  
🌐 **Serve APIs** for the web dashboard (real-time + history + export)

---

### ⚙️ Smart Rules (Important!)

These two parameters control the main “smart” features:

- 🔧 **Maintenance Reminder**  
  `MAINTENANCE_THRESHOLD = 5`  
  → If a tool is borrowed **5 times**, the system triggers a maintenance alert.

- ⏱️ **Overdue Detection**  
  `OVERDUE_SECONDS = 15`  
  → If a tool is borrowed for more than **15 seconds**, it becomes **Overdue**.

---

### 🗄️ Database Design (SQLite)

This backend creates and maintains two tables:

#### 1) `tools` — Current status for each slot
Stores:
- slot id, tool name
- status (`-1 = Waiting`, `0 = Borrowed`, `1 = Available`)
- current authorized value (stored as string)
- weight
- borrow time
- usage count (how many times borrowed)

#### 2) `logs` — History records
Every borrow/return event is saved with:
- slot id
- action (`Borrowed` / `Returned`)
- user_name (stored value from authorization)
- timestamp

---

### 🔌 API Endpoints

#### `POST /api/update`
✅ Receives JSON payload from hardware (two systems: `system1`, `system2`)  
✅ Updates the database (status, weight, borrow time, usage count)  
✅ Writes logs on every status change (Borrowed / Returned)  
✅ Prints a **one-time success message** when the first real hardware data arrives

---

#### `GET /api/dashboard`
📊 Returns real-time dashboard data per slot, including:
- `slot_id`, `name`, `weight`, `usage_count`
- `display_status`:
  - `Waiting...`
  - `Available`
  - `Borrowed`
  - `Overdue`
- `led_color`: `green / red / grey`
- Alerts:
  - `alert_overdue`
  - `alert_maintenance`

This endpoint is what the web page polls to display the live dashboard.

---

#### `GET /api/history`
📜 Returns the latest 50 activity logs (most recent first), including:
- timestamp, slot id, action, user_name

---

#### `GET /api/export`
📥 Exports all logs as a **CSV file** (with BOM for Excel compatibility), so users can download a report easily.

---

### 🟢 System Startup Behavior
When the server starts:
- It initializes the database (`init_db()`)
- Creates two default tool slots if the database is empty
- Otherwise resets all slots to:
  - `Waiting` status
  - weight = 0.0
  - borrow_time = NULL

Then it runs on:
- `host = 0.0.0.0`
- `port = 5000`

---

### ✅ Why this backend matters
Without this backend:
- No history tracking
- No Overdue/Maintenance logic
- No centralized data storage
- The dashboard would have nothing reliable to display

With this backend:
- The system becomes **trackable, scalable, and management-friendly** ✅
