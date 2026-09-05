import asyncio
import json
import logging
import os

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiomqtt

from fastapi import FastAPI
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

# --------------------------------------------------
# Configuration
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

ROSTER_PATH = Path(os.getenv("ROSTER_PATH", "/app/data/robots.json"))

MQTT_TOPIC = "robots/+/telemetry"


# --------------------------------------------------
# Fleet Store
# --------------------------------------------------


class FleetStore:
    """
    Single source of truth.

    Both REST and WebSocket use this same state.
    """

    def __init__(self, robots: list[dict[str, Any]]):

        self.lock = asyncio.Lock()

        self.robots: dict[str, dict] = {}

        self.websocket_clients: set[WebSocket] = set()

        # Initialize fleet from robots.json
        for robot in robots:

            robot_id = robot["robot_id"]

            self.robots[robot_id] = {
                "robot_id": robot_id,
                "robot_type": robot["robot_type"],
                "x": robot["start"]["x"],
                "y": robot["start"]["y"],
                # Before receiving telemetry
                "status": "offline",
                "battery": None,
                "last_event_t": None,
                "last_seen_at": None,
            }

    # --------------------------------------------------
    # Update robot
    # --------------------------------------------------

    async def update_robot(self, event: dict):

        async with self.lock:

            robot_id = event["robot_id"]

            robot = self.robots.get(robot_id)

            if robot is None:

                # Future-proofing:
                # unknown robot can still be added

                robot = {"robot_id": robot_id, "robot_type": "unknown"}

                self.robots[robot_id] = robot

            # Ignore old events

            previous_time = robot.get("last_event_t")

            if previous_time is not None and event["t"] < previous_time:
                return

            # Update current state

            robot["x"] = event["x"]

            robot["y"] = event["y"]

            robot["status"] = event["status"]

            robot["battery"] = event["battery"]

            robot["last_event_t"] = event["t"]

            robot["last_seen_at"] = datetime.now(timezone.utc).isoformat()

            # Optional task event

            if "task_event" in event:

                robot["task_event"] = event["task_event"]

    # --------------------------------------------------
    # Get current snapshot
    # --------------------------------------------------

    async def get_snapshot(self):

        async with self.lock:

            robots = sorted(
                [robot.copy() for robot in self.robots.values()],
                key=lambda robot: robot["robot_id"],
            )

            return {
                "generated_at": (datetime.now(timezone.utc).isoformat()),
                "count": len(robots),
                "robots": robots,
            }

    # --------------------------------------------------
    # WebSocket client management
    # --------------------------------------------------

    async def add_client(self, websocket: WebSocket):

        async with self.lock:

            self.websocket_clients.add(websocket)

    async def remove_client(self, websocket: WebSocket):

        async with self.lock:

            self.websocket_clients.discard(websocket)

    # --------------------------------------------------
    # Broadcast
    # --------------------------------------------------

    async def broadcast(self):

        snapshot = await self.get_snapshot()

        message = {"type": "fleet_update", "data": snapshot}

        # Copy clients

        async with self.lock:

            clients = list(self.websocket_clients)

        disconnected_clients = []

        for client in clients:

            try:

                await client.send_json(message)

            except Exception:

                disconnected_clients.append(client)

        # Remove disconnected clients

        for client in disconnected_clients:

            await self.remove_client(client)


# --------------------------------------------------
# Load robots
# --------------------------------------------------


def load_robots():

    with open(ROSTER_PATH, "r") as file:

        return json.load(file)


# --------------------------------------------------
# MQTT Consumer
# --------------------------------------------------


async def mqtt_consumer(store: FleetStore):

    reconnect_delay = 1

    while True:

        try:

            logger.info("Connecting to MQTT broker: %s:%s", MQTT_HOST, MQTT_PORT)

            async with aiomqtt.Client(
                hostname=MQTT_HOST, port=MQTT_PORT, identifier="fleet-backend"
            ) as client:

                logger.info("Connected to MQTT broker")

                await client.subscribe(MQTT_TOPIC, qos=1)

                logger.info("Subscribed to: %s", MQTT_TOPIC)

                # Reset reconnect delay

                reconnect_delay = 1

                async for message in client.messages:

                    try:

                        payload = message.payload.decode("utf-8")

                        event = json.loads(payload)

                        # Update state

                        await store.update_robot(event)

                        # Push update

                        await store.broadcast()

                    except Exception as error:

                        logger.exception("Failed to process event: %s", error)

        except asyncio.CancelledError:

            raise

        except Exception as error:

            logger.warning("MQTT connection failed: %s", error)

            logger.info("Retrying in %s seconds", reconnect_delay)

            await asyncio.sleep(reconnect_delay)

            reconnect_delay = min(reconnect_delay * 2, 15)


# --------------------------------------------------
# FastAPI lifespan
# --------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):

    robots = load_robots()

    store = FleetStore(robots)

    app.state.store = store

    mqtt_task = asyncio.create_task(mqtt_consumer(store))

    try:

        yield

    finally:

        mqtt_task.cancel()

        try:

            await mqtt_task

        except asyncio.CancelledError:

            pass


# --------------------------------------------------
# FastAPI app
# --------------------------------------------------

app = FastAPI(title="Fleet Management Backend", version="1.0.0", lifespan=lifespan)


# --------------------------------------------------
# Root
# --------------------------------------------------


@app.get("/")
async def root():

    return {
        "service": "Fleet Management Backend",
        "rest": "/fleet/current",
        "websocket": "/ws/fleet",
        "health": "/health",
    }


# --------------------------------------------------
# Health
# --------------------------------------------------


@app.get("/health")
async def health():

    return {"status": "ok"}


# --------------------------------------------------
# REST API
# --------------------------------------------------


@app.get("/fleet/current")
async def get_current_fleet():

    store = app.state.store

    return await store.get_snapshot()


# --------------------------------------------------
# WebSocket
# --------------------------------------------------


@app.websocket("/ws/fleet")
async def fleet_websocket(websocket: WebSocket):

    store = app.state.store

    await websocket.accept()

    await store.add_client(websocket)

    try:

        # Immediately send current state

        snapshot = await store.get_snapshot()

        await websocket.send_json({"type": "snapshot", "data": snapshot})

        # Keep connection alive

        while True:

            await websocket.receive_text()

    except WebSocketDisconnect:

        logger.info("WebSocket client disconnected")

    except Exception:

        logger.info("WebSocket connection closed")

    finally:

        await store.remove_client(websocket)
