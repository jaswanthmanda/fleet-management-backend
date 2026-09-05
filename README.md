# Fleet Management Backend

Backend implementation for the Peppermint Robotics Fleet Management Dashboard hiring challenge.

---

## Tech Stack

- Python 3.12
- FastAPI
- WebSockets
- MQTT
- Eclipse Mosquitto
- Docker
- Docker Compose

---

# Architecture

```text
Robot r1 ─────┐
Robot r2 ─────┤
Robot r3 ─────┤
Robot r4 ─────┤
Robot r5 ─────┼──── MQTT ──── Mosquitto
Robot r6 ─────┤                      │
Robot r7 ─────┤                      │
Robot r8 ─────┘                      ▼
                              FastAPI Backend
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                        REST                   WebSocket
                         │                         │
                    Polling Client          Live Client
```
