import asyncio
import hashlib
import json
import logging
import random
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MapServer")

# Global State
devices: Dict[str, "Device"] = {}
# Simulate a model with 100 weights (randomly initialized)
global_weights: List[float] = [random.uniform(-1, 1) for _ in range(100)]

# Constants
UPDATE_INTERVAL = 30  # seconds

# Traffic State: 4 Slots fixed.
# keys: "Signal 1", "Signal 2", "Signal 3", "Signal 4"
traffic_state = {
    f"Signal {i}": {
        "mode": "SIM", # SIM or REAL
        "name": f"Sim-Node-{i}", 
        "ip": "10.10.0.0",
        "signal": "RED",
        "count": random.randint(5, 15),
        "last_switch": time.time(),
        "client_id": None
    } for i in range(1, 5)
}

# Ensure init has one Green to start simulation
traffic_state["Signal 2"]["signal"] = "GREEN"

async def traffic_simulation_loop():
    """
    Simulates traffic ONLY for 'SIM' mode nodes.
    'REAL' nodes are updated via WebSocket status messages.
    """
    while True:
        await asyncio.sleep(1)
        now = time.time()
        
        # 1. Update Counts for SIM nodes
        for pos, state in traffic_state.items():
            if state["mode"] == "SIM":
                # User Request: Sample in realistic range instead of increasing
                state["count"] = random.randint(30, 100)

        # 2. Logic: Who should switch?
        # Note: Real clients control their OWN state locally.
        # But for the simulation to respect real clients, we simply observe the *aggregated* state.
        
        # In this hybrid model:
        # - Real clients send us their Red/Green status.
        # - We simulate the rest.
        # - Ideally, real clients run the SAME distributed logic (Wait 3s, Check Max, Switch).
        
        # For 'SIM' nodes, we should probably just let them run a similar logic?
        # Or, to keep it simple as requested:
        # "randomly generated" for sim nodes.
        
        # We will just let the SIM nodes fluctuate counts. 
        # The logic for switching *simulated* signals could be:
        # If a Sim node is Green, hold for X then Red.
        # If a Sim node is Red and has max traffic, turn Green? 
        
        # User request implementation: "once real user select a signal that signal data will be given my them"
        # So we just passively hold the data in `traffic_state` and let `broadcast_status_loop` send it.
        # The SIM nodes will just randomly vary counts for now to provide "competition".
        # We won't auto-switch SIM signals here to avoid conflicting with the distributed logic 
        # that the REAL clients are running (since real clients decide who goes green).
        # Actually, if real clients decide, they need to see *simulated* neighbors also green/red.
        
        # Let's simple toggle SIM nodes if they are "active" in the users eyes.
        # But wait, if Client A says "I am Green", Client B (simulated) should be Red.
        pass # Logic handled by distributed agents (real) or just random noise (sim)

async def broadcast_status_loop():
    while True:
        await asyncio.sleep(0.5) # Fast updates
        
        neighbor_data = []
        for pos, data in traffic_state.items():
            neighbor_data.append({
                "pos": pos,
                "name": data["name"],
                "ip": data["ip"],
                "signal": data["signal"],
                "count": data["count"]
            })
            
        active_count = sum(1 for d in devices.values() if d.socket is not None)
        
        # DEBUG: Log state occasionally
        # logger.info(f"Traffic State: {[ (k, v['mode'], v['name']) for k,v in traffic_state.items()]}")

        for client_id, device in devices.items():
            if device.socket:
                try:
                    # Filter out MY OWN data from "neighbors" list.
                    # If I am "Signal 1", neighbors are S2, S3, S4.
                    
                    my_pos = device.position
                    others = [n for n in neighbor_data if n["pos"] != my_pos]
                    
                    # Sort others by position to be deterministic? 
                    # Neighbors list in Dashboard might rely on order? 
                    # Dashboard just maps `neighbors`. If order varies, it might be confusing.
                    # Let's sort by position string.
                    others.sort(key=lambda x: x["pos"])

                    await device.socket.send_json({
                        "type": "neighbor_update",
                        "neighbors": others,
                        "active_devices": active_count
                    })
                except Exception:
                    pass

async def trigger_update_loop():
    while True:
        await asyncio.sleep(UPDATE_INTERVAL)
        logger.info("Triggering Federated Learning Update Round...")
        
        for client_id, device in devices.items():
            if device.socket:
                try:
                    await device.socket.send_json({"type": "request_update"})
                    logger.info(f"Sent update request to {device.name}")
                except Exception as e:
                    logger.error(f"Failed to send to {device.name}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting background tasks...")
    task1 = asyncio.create_task(trigger_update_loop())
    task2 = asyncio.create_task(broadcast_status_loop())
    task3 = asyncio.create_task(traffic_simulation_loop())
    yield
    # Shutdown
    task1.cancel()
    task2.cancel()
    task3.cancel()
    logger.info("Background tasks stopped.")

app = FastAPI(lifespan=lifespan)

# Data Models
class RegistrationRequest(BaseModel):
    name: str
    intersection_type: str  # "3-way" or "4-way"
    position: str = "Signal 1"

class UpdateRequest(BaseModel):
    client_id: str
    updated_weights: List[float]
    metadata: Dict
    signature: str

class Device(BaseModel):
    client_id: str
    name: str
    intersection_type: str
    position: str
    socket: Optional[WebSocket] = None
    last_seen: float

    model_config = ConfigDict(arbitrary_types_allowed=True)

@app.post("/register")
async def register(req: RegistrationRequest):
    client_id = hashlib.sha256(f"{req.name}-{time.time()}".encode()).hexdigest()[:12]
    
    device = Device(
        client_id=client_id,
        name=req.name,
        intersection_type=req.intersection_type,
        position=req.position,
        last_seen=time.time()
    )
    devices[client_id] = device
    
    # Update Traffic State to mark this position as REAL
    if req.position in traffic_state:
        traffic_state[req.position] = {
            "mode": "REAL", 
            "name": req.name,
            "ip": "10.10.X.X", # In real env, get from req
            "signal": "RED",
            "count": 0,
            "last_switch": time.time(),
            "client_id": client_id
        }
    
    logger.info(f"Registered: {req.name} ({client_id}) | Type: {req.intersection_type} | Pos: {req.position}")
    
    return {
        "client_id": client_id,
        "initial_weights": global_weights,
        "message": "Registration successful"
    }

@app.post("/fl-update")
async def receive_update(req: UpdateRequest):
    if req.client_id not in devices:
        return {"error": "Device not registered"}
    
    # Verify Signature
    # Force separators to match JavaScript's JSON.stringify behavior
    local_hash = hashlib.sha256(
        json.dumps(req.updated_weights, separators=(',', ':')).encode()
    ).hexdigest()
    
    verified = local_hash == req.signature
    
    logger.info(f"Update received from {devices[req.client_id].name} ({req.client_id})")
    logger.info(f"Metadata: {req.metadata}")
    logger.info(f"Size: {len(json.dumps(req.updated_weights))} bytes")
    logger.info(f"Signature Verification: {'PASSED' if verified else 'FAILED'}")
    if not verified:
        logger.info(f"Server Hash: {local_hash}")
        logger.info(f"Client Hash: {req.signature}")
    
    if verified:
        # Simplistic Aggregation: Just Average (Federated Averaging)
        # Here we just take 10% of the weights and update them
        # In a real FL system, we would aggregate all updates
        # Requirement: "randomly updated 10 percent of weights and return again"
        update_indices = random.sample(range(len(global_weights)), int(len(global_weights) * 0.1))
        for idx in update_indices:
            global_weights[idx] = random.uniform(-1, 1)

    return {
        "status": "accepted", 
        "verified": verified,
        "server_hash": local_hash,
        "current_global_weights_sample": global_weights[:5] # Just to show change
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    if client_id not in devices:
        await websocket.close(code=1008)
        return
        
    devices[client_id].socket = websocket
    logger.info(f"WebSocket connected for {client_id}")
    
    try:
        while True:
            # Receive message (Status Update)
            data_str = await websocket.receive_text()
            try:
                msg = json.loads(data_str)
                if msg.get("type") == "status":
                    # Update Global State from Real Client
                    pos = devices[client_id].position
                    if pos in traffic_state:
                         traffic_state[pos]["signal"] = msg.get("signal", "RED")
                         traffic_state[pos]["count"] = msg.get("count", 0)
            except Exception:
                pass # Ignore malformed
                
            devices[client_id].last_seen = time.time()
    except WebSocketDisconnect:
        devices[client_id].socket = None
        # Should we revert traffic_state to SIM? 
        # For this demo, let's leave it or maybe revert if needed.
        # Ideally, we flip back to SIM mode.
        pos = devices[client_id].position
        if pos in traffic_state and traffic_state[pos]["client_id"] == client_id:
             traffic_state[pos]["mode"] = "SIM"
             traffic_state[pos]["name"] = f"Sim-Node-{pos.split()[-1]}"
        logger.info(f"WebSocket disconnected for {client_id}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
