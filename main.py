import asyncio
import logging
import struct
import sqlite3
import datetime
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Heart Rate Measurement UUID
HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# Database setup
DB_FILE = "heart_rate.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS measurements
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                  value INTEGER, 
                  device_address TEXT)''')
    conn.commit()
    conn.close()

init_db()

def save_heart_rate(value: int, device_address: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO measurements (value, device_address) VALUES (?, ?)", (value, device_address))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database error: {e}")

try:
    from bleak import BleakScanner, BleakClient
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    class BleakScanner:
        @staticmethod
        async def discover(**kwargs):
            await asyncio.sleep(1)
            # Return mock devices
            class MockDevice:
                def __init__(self, name, address):
                    self.name = name
                    self.address = address
            
            class MockAdv:
                def __init__(self, rssi):
                    self.rssi = rssi

            d1 = MockDevice("Mock HR Monitor", "00:11:22:33:44:55")
            d2 = MockDevice("Another Device", "AA:BB:CC:DD:EE:FF")
            
            # Return dict format to match return_adv=True
            return {
                d1.address: (d1, MockAdv(-60)),
                d2.address: (d2, MockAdv(-80))
            }

    class BleakClient:
        def __init__(self, address, **kwargs):
            self.address = address
            self.is_connected = False
            self._notify_callbacks = {}

        async def connect(self):
            await asyncio.sleep(1)
            self.is_connected = True
            # Start a background task to simulate notifications
            asyncio.create_task(self._simulate_notifications())

        async def disconnect(self):
            self.is_connected = False
        
        async def start_notify(self, char_specifier, callback):
            self._notify_callbacks[char_specifier] = callback

        async def _simulate_notifications(self):
            import random
            while self.is_connected:
                await asyncio.sleep(1)
                if HR_UUID in self._notify_callbacks:
                    # Simulate HR data format (flags + value)
                    # flags = 0 (uint8 format)
                    hr = random.randint(60, 100)
                    data = bytearray([0, hr])
                    await self._notify_callbacks[HR_UUID](0, data)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()
current_client: Optional[BleakClient] = None
current_hr: int = 0

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scan")
async def scan_devices():
    logger.info("Scanning for devices...")
    if not BLEAK_AVAILABLE:
        logger.warning("Bleak not installed, using Mock data.")
    
    try:
        devices = await BleakScanner.discover(timeout=5.0, return_adv=True)
        device_list = []
        for d, adv in devices.values():
            # Include all devices, fallback to "Unknown" if name is missing
            name = d.name if d.name else "Unknown"
            device_list.append({"name": name, "address": d.address, "rssi": adv.rssi})
        
        # Sort by RSSI (signal strength) descending
        device_list.sort(key=lambda x: x["rssi"], reverse=True)
        
        logger.info(f"Found {len(device_list)} devices.")
        return device_list
    except Exception as e:
        logger.error(f"Scan error: {e}")
        return []

@app.get("/api/history")
async def get_history(period: str = "minute", limit: int = 100):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # SQLite datetime format: YYYY-MM-DD HH:MM:SS
    if period == "minute":
        # Group by minute
        query = '''
            SELECT strftime('%Y-%m-%d %H:%M', timestamp) as time_bucket, AVG(value)
            FROM measurements
            GROUP BY time_bucket
            ORDER BY time_bucket DESC
            LIMIT ?
        '''
    elif period == "hour":
        # Group by hour
        query = '''
            SELECT strftime('%Y-%m-%d %H:00', timestamp) as time_bucket, AVG(value)
            FROM measurements
            GROUP BY time_bucket
            ORDER BY time_bucket DESC
            LIMIT ?
        '''
    elif period == "day":
        # Group by day
        query = '''
            SELECT strftime('%Y-%m-%d', timestamp) as time_bucket, AVG(value)
            FROM measurements
            GROUP BY time_bucket
            ORDER BY time_bucket DESC
            LIMIT ?
        '''
    else:
        # Raw data (recent)
        query = '''
            SELECT timestamp, value
            FROM measurements
            ORDER BY timestamp DESC
            LIMIT ?
        '''
        
    c.execute(query, (limit,))
    rows = c.fetchall()
    conn.close()
    
    # Reverse to show oldest to newest in chart
    return [{"timestamp": row[0], "value": round(row[1])} for row in reversed(rows)]

async def heart_rate_notification_handler(sender, data):
    global current_hr
    flag = data[0]
    hr_format = flag & 0x01
    
    if hr_format == 0:
        hr_val = data[1]
    else:
        hr_val = struct.unpack_from("<H", data, 1)[0]
    
    current_hr = hr_val
    logger.info(f"Heart Rate: {hr_val}")
    
    # Save to database
    if current_client:
        save_heart_rate(hr_val, str(current_client.address))

    await manager.broadcast({
        "type": "heart_rate",
        "value": hr_val
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "connect":
                device_address = data.get("address")
                await connect_ble(device_address)
            elif data.get("action") == "disconnect":
                await disconnect_ble()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def connect_ble(address: str):
    global current_client
    if current_client and current_client.is_connected:
        await current_client.disconnect()
    
    await manager.broadcast({"type": "status", "message": f"Connecting to {address}..."})
    try:
        current_client = BleakClient(address)
        await current_client.connect()
        await manager.broadcast({"type": "status", "message": f"Connected to {address}"})
        await current_client.start_notify(HR_UUID, heart_rate_notification_handler)
    except Exception as e:
        logger.error(f"Connection error: {e}")
        await manager.broadcast({"type": "error", "message": str(e)})
        current_client = None

async def disconnect_ble():
    global current_client
    if current_client and current_client.is_connected:
        await current_client.disconnect()
        await manager.broadcast({"type": "status", "message": "Disconnected"})
    current_client = None
