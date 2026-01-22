import asyncio
import json
import logging
import random
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MapServer")

# Global State - Zero-Sync Compatible Data Structure
devices: Dict[str, "Device"] = {}
connected_clients: Set[str] = set()

# Distributed State with versioning for zero-sync compatibility
traffic_state: Dict[str, Dict] = {
    f"Signal {i}": {
        "id": f"signal-{i}",
        "mode": "SIM",
        "name": f"Sim-Node-{i}",
        "ip": "10.10.0.0",
        "signal": "RED",
        "count": random.randint(5, 15),
        "last_switch": time.time(),
        "client_id": None,
        "version": 0,  # Version for sync tracking
        "timestamp": time.time(),
    }
    for i in range(1, 5)
}

# Ensure init has one Green to start simulation
traffic_state["Signal 2"]["signal"] = "GREEN"


async def traffic_simulation_loop():
    """
    Simulates traffic for 'SIM' mode nodes.
    'REAL' nodes are updated via WebSocket messages.
    """
    while True:
        await asyncio.sleep(1)
        for pos, state in traffic_state.items():
            if state["mode"] == "SIM":
                state["count"] = random.randint(30, 100)
                state["version"] += 1
                state["timestamp"] = time.time()


async def broadcast_to_others(sender_client_id: str, updated_state: Dict):
    """
    Broadcast state update to all clients EXCEPT the sender.
    Zero-sync compatible: each update has version and timestamp.
    """
    for client_id, device in devices.items():
        if device.socket and client_id != sender_client_id:
            try:
                await device.socket.send_json(
                    {
                        "type": "state_update",
                        "data": updated_state,
                        "timestamp": time.time(),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting background tasks...")
    task1 = asyncio.create_task(traffic_simulation_loop())
    yield
    task1.cancel()
    logger.info("Background tasks stopped.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.mount("/static", StaticFiles(directory=".", html=True), name="static")


# Data Models
class RegistrationRequest(BaseModel):
    name: str
    intersection_type: str
    position: str = "Signal 1"


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
    client_id = str(uuid.uuid4())[:12]

    device = Device(
        client_id=client_id,
        name=req.name,
        intersection_type=req.intersection_type,
        position=req.position,
        last_seen=time.time(),
    )
    devices[client_id] = device

    if req.position in traffic_state:
        traffic_state[req.position]["mode"] = "REAL"
        traffic_state[req.position]["name"] = req.name
        traffic_state[req.position]["client_id"] = client_id
        traffic_state[req.position]["version"] = 0
        traffic_state[req.position]["timestamp"] = time.time()

    logger.info(
        f"Registered: {req.name} ({client_id}) | Type: {req.intersection_type} | Pos: {req.position}"
    )

    return {
        "client_id": client_id,
        "position": req.position,
        "initial_state": traffic_state,
        "message": "Registration successful",
    }


@app.get("/state")
async def get_state():
    """Get current distributed state - zero-sync compatible."""
    return {
        "state": traffic_state,
        "connected_clients": len(connected_clients),
        "timestamp": time.time(),
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    if client_id not in devices:
        await websocket.close(code=1008)
        return

    devices[client_id].socket = websocket
    connected_clients.add(client_id)
    logger.info(f"WebSocket connected for {client_id} ({devices[client_id].name})")

    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                msg = json.loads(data_str)

                if msg.get("type") == "status":
                    pos = devices[client_id].position
                    if pos in traffic_state:
                        # Update state with versioning
                        traffic_state[pos]["signal"] = msg.get("signal", "RED")
                        traffic_state[pos]["count"] = msg.get("count", 0)
                        traffic_state[pos]["version"] += 1
                        traffic_state[pos]["timestamp"] = time.time()

                        logger.info(
                            f"State update from {devices[client_id].name}: "
                            f"Signal={traffic_state[pos]['signal']}, "
                            f"Count={traffic_state[pos]['count']}, "
                            f"Version={traffic_state[pos]['version']}"
                        )

                        # Broadcast to others (zero-sync: idempotent state update)
                        await broadcast_to_others(client_id, traffic_state[pos])

            except json.JSONDecodeError:
                pass

            devices[client_id].last_seen = time.time()

    except WebSocketDisconnect:
        connected_clients.discard(client_id)
        devices[client_id].socket = None

        pos = devices[client_id].position
        if pos in traffic_state and traffic_state[pos]["client_id"] == client_id:
            traffic_state[pos]["mode"] = "SIM"
            traffic_state[pos]["name"] = f"Sim-Node-{pos.split()[-1]}"
            traffic_state[pos]["client_id"] = None
            traffic_state[pos]["version"] += 1

        logger.info(f"WebSocket disconnected for {client_id}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
