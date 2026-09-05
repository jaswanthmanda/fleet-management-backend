# Fleet Management Backend

A real-time Fleet Management Backend built with FastAPI, MQTT, WebSockets, Docker, and Docker Compose.

The application simulates robot fleet events, processes them through MQTT, maintains the latest fleet state, and exposes the data through REST APIs and WebSockets.

---

## Tech Stack

- Python 3.12
- FastAPI
- MQTT
- Eclipse Mosquitto
- WebSockets
- Docker
- Docker Compose

---

## Architecture

```text
Simulator
    │
    │ MQTT Events
    ▼
Mosquitto MQTT Broker
    │
    │ MQTT Messages
    ▼
FastAPI Backend
    │
    ├──────────────► REST API
    │
    └──────────────► WebSocket
```

---

## Services

| Service     | Description                          | Port   |
| ----------- | ------------------------------------ | ------ |
| `broker`    | Eclipse Mosquitto MQTT broker        | `1883` |
| `backend`   | FastAPI backend                      | `8000` |
| `simulator` | Simulates and publishes robot events | -      |

---

## Project Structure

```text
fleet-management-backend/
├── backend/
├── simulator/
├── mosquitto/
│   └── mosquitto.conf
├── data/
│   ├── robots.json
│   └── events.jsonl
├── docker-compose.yml
├── test_http.py
├── test_ws.py
└── README.md
```

---

## Prerequisites

Install:

- Docker
- Docker Compose

Verify installation:

```bash
docker --version
docker compose version
```

---

## Running the Application

Clone the repository:

```bash
git clone <repository-url>
cd fleet-management-backend
```

Start all services:

```bash
docker compose up --build
```

Or run in the background:

```bash
docker compose up -d --build
```

Check running services:

```bash
docker compose ps
```

The backend will be available at:

```text
http://localhost:8000
```

---

## API Endpoints

### Root

```http
GET /
```

### Health Check

```http
GET /health
```

### Current Fleet

```http
GET /fleet/current
```

Returns the latest state of all robots in the fleet.

---

## WebSocket

Connect to:

```text
ws://localhost:8000/ws/fleet
```

The WebSocket broadcasts real-time fleet updates.

---

## API Documentation

FastAPI Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI specification:

```text
http://localhost:8000/openapi.json
```

---

## Testing

### HTTP Testing

Install dependencies if required:

```bash
pip install requests
```

Run:

```bash
python3 test_http.py
```

This tests:

```text
GET /
GET /health
GET /fleet/current
```

### WebSocket Testing

Install:

```bash
pip install websocket-client
```

Run:

```bash
python3 test_ws.py
```

This connects to:

```text
ws://localhost:8000/ws/fleet
```

and receives live fleet updates.

---

## Data Flow

```text
Simulator
    ↓
MQTT Broker
    ↓
FastAPI Backend
    ↓
Fleet State Updated
    ↓
REST API + WebSocket
```

---

## Stopping the Application

```bash
docker compose down
```

To rebuild after changes:

```bash
docker compose up --build
```

---

## Status

The application has been successfully tested locally:

- Docker services running
- MQTT communication working
- Simulator publishing robot events
- Backend processing events
- REST API working
- WebSocket updates working
- End-to-end data flow verified
