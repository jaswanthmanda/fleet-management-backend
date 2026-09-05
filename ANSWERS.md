# Written Answers

## 1. What holds the fleet's current state in your backend, and why that shape, given it has to serve both the WebSocket stream and the polling endpoint consistently?

The fleet's current state is held in the `FleetStore` class in `backend/app/main.py`. The state is stored as a dictionary keyed by `robot_id` (`self.robots`), which makes updates efficient because an incoming telemetry event can directly update the current state for one robot. The initial entries are created from `robots.json`, and `update_robot()` replaces the robot's current position, battery, status, and timestamps whenever a newer event arrives.

Both the REST endpoint (`get_current_fleet()`) and WebSocket fanout (`broadcast()`) read from the same `FleetStore` through `get_snapshot()`. This makes the store the single source of truth instead of maintaining separate REST and WebSocket state. An `asyncio.Lock` protects updates and snapshot creation so that a snapshot is not read while the state is being modified. For this small local deployment, an in-memory store keeps the design simple, although I would move this state to Redis or another shared store if the backend needed to run multiple replicas.

---

## 2. Name one real tradeoff you made: the mechanism you chose for robots to reach your backend, its delivery guarantees, and how you reconcile that mechanism's semantics with your WebSocket fanout. Argue for the decision, including its cost.

I chose MQTT as the communication mechanism between the simulated robots and the backend. Each robot process in `simulator/simulator.py` publishes telemetry to `robots/{robot_id}/telemetry`, while `mqtt_consumer()` in `backend/app/main.py` subscribes to `robots/+/telemetry`. MQTT fits the producer-consumer model well because robots and the backend are loosely coupled and can reconnect independently.

The simulator publishes with QoS 1, which gives at-least-once delivery semantics rather than exactly-once delivery. This means duplicates are possible, so the backend treats each event as an update to current state rather than as an event that must be processed exactly once. In `FleetStore.update_robot()`, older events are ignored using `last_event_t`, which also helps prevent stale out-of-order events from replacing newer state.

The WebSocket layer has different semantics: it is a live fanout of the current state and does not guarantee delivery while a client is disconnected. I reconcile this by sending a full current snapshot immediately when a client connects in `fleet_websocket()`. After that, the client receives live `fleet_update` messages. The tradeoff is that this design is simple and suitable for a dashboard, but MQTT QoS 1 can produce duplicates and the WebSocket layer does not replay missed historical updates.

---

## 3. What did you leave out, and what would you build next given more time?

I intentionally kept the current implementation focused on the assignment requirements. The biggest omission is persistent storage: `FleetStore` is in memory, so the current state is lost if the backend restarts. I also did not implement authentication, authorization, telemetry history, metrics, or a production-grade deployment configuration.

Given more time, I would first add automated tests around `FleetStore.update_robot()` and snapshot consistency, followed by persistence for the current fleet state. For production scaling, I would move the current state to Redis and store historical telemetry in a database such as PostgreSQL or TimescaleDB. I would also add explicit robot heartbeat monitoring, stale/offline detection, Prometheus metrics, structured logging, and authentication for the REST and WebSocket APIs.
