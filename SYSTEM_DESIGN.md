# System Design

## 1. What happens if we ask you to add a new feature to this later? Does your current design accommodate that, or does it need a rework? Walk through a specific feature and where it would plug in.

The current design can accommodate additional fleet features without a major rework because the responsibilities are already separated between robot publishing, MQTT ingestion, current state management, and client delivery. For example, if I added a low-battery alert feature, the robot telemetry would continue to arrive through the existing MQTT path. The feature could be added inside `FleetStore.update_robot()` in `backend/app/main.py`, or preferably extracted into a separate alert service that receives the same state updates.

The simulator in `simulator/simulator.py` would not need to change because battery data is already part of the telemetry event. After updating the state, the backend could check whether the battery crossed a configured threshold and publish an alert through a separate WebSocket message or REST endpoint. As the application grows, I would extract state handling, MQTT consumption, and WebSocket management from `main.py` into separate modules, but the current flow would remain the same.

---

## 2. What happens if the number of robots grows a lot, say from eight to five hundred? What is the first thing that breaks, and why that specifically?

The first limitation would be the current in-memory backend combined with broadcasting a complete fleet snapshot after every telemetry update. In `FleetStore.broadcast()`, every incoming MQTT message triggers `get_snapshot()` and sends the entire fleet state to every connected WebSocket client. With eight robots this is acceptable, but with five hundred robots and frequent updates, the backend would repeatedly serialize and transmit large snapshots.

The MQTT broker itself can handle a larger number of publishers better than the current WebSocket fanout approach, but the backend would become inefficient because one robot update causes every client to receive all five hundred robots. I would change the WebSocket protocol to send only the changed robot after the initial snapshot. I would also move the state from process memory to Redis if multiple backend instances were needed, and consider batching or throttling high-frequency updates.

---

## 3. What happens if bandwidth is limited and robots and the backend can only exchange a small amount of data per second? What would you change about what you send, how often, or how much detail it carries?

The current simulator sends the full telemetry payload for every recorded update, including robot ID, position, battery, status, timestamp, and sometimes task information. If bandwidth became limited, I would first reduce unnecessary update frequency. For example, a robot could send immediately when its status changes but send position updates less frequently when it is moving normally.

I would also send only changed fields when possible. Robot ID can remain part of the MQTT topic, so it may not need to be repeated in every payload. Battery updates could be sent less frequently because they usually change slowly. For the dashboard, the backend could also send delta updates over WebSocket instead of the full fleet snapshot currently sent by `FleetStore.broadcast()`. Compression or a more compact serialization format could be considered later, but reducing unnecessary messages would be the first improvement.

---

## 4. What happens if a robot goes down mid task and stops responding? What should the rest of the system do about it, and how would it even find out?

The current implementation records `last_seen_at` whenever `FleetStore.update_robot()` receives telemetry. The backend could use this timestamp to detect that a robot has stopped reporting. A background monitoring task could periodically compare the current time against each robot's `last_seen_at`. If the difference exceeds a configured timeout, the robot could be marked as `offline` or `unresponsive`.

For a robot that was previously `on_mission`, I would also mark its task as needing attention instead of assuming the task was completed. The backend could broadcast an alert to connected dashboard clients and expose the updated status through the existing REST endpoint. In a production system, I would add an explicit heartbeat message or MQTT Last Will and Testament configuration so the broker can help detect unexpected disconnects more quickly.

---

## 5. What happens if the connection between a robot and the backend is slow or unreliable, and updates arrive late, out of order, or not at all for a while? What does the rest of the system see during that time, and how does it recover once the connection is healthy again?

The current backend keeps the last known state for each robot. If updates stop arriving temporarily, REST and WebSocket consumers continue to see that last known position, status, and battery together with `last_seen_at`. A client can therefore determine that the data may be stale based on how long ago the robot was last seen.

For out-of-order events, `FleetStore.update_robot()` compares the incoming event timestamp (`t`) with `last_event_t` and ignores events older than the latest accepted event. This prevents an older delayed event from overwriting newer current state. The MQTT consumer in `mqtt_consumer()` reconnects with exponential backoff if its connection to the broker fails, while each robot publisher in `simulator.py` retries and uses MQTT reconnect handling.

Once the connection becomes healthy again, new events are accepted normally and the latest state is broadcast to WebSocket clients. A WebSocket client that reconnects receives a complete current snapshot from `fleet_websocket()` before receiving future live updates.
