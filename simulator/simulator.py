import json
import os
import signal
import time

from multiprocessing import Process
from pathlib import Path

import paho.mqtt.client as mqtt

# --------------------------------------------------
# Configuration
# --------------------------------------------------

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")


MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))


EVENTS_PATH = Path(os.getenv("EVENTS_PATH", "/app/data/events.jsonl"))


ROBOTS_PATH = Path(os.getenv("ROBOTS_PATH", "/app/data/robots.json"))


PLAYBACK_SPEED = float(os.getenv("PLAYBACK_SPEED", "10"))


LOOP_PLAYBACK = os.getenv("LOOP_PLAYBACK", "true").lower() == "true"


# --------------------------------------------------
# Load events
# --------------------------------------------------


def load_events():

    events_by_robot = {}

    with open(EVENTS_PATH, "r") as file:

        for line in file:

            line = line.strip()

            if not line:

                continue

            event = json.loads(line)

            robot_id = event["robot_id"]

            if robot_id not in events_by_robot:

                events_by_robot[robot_id] = []

            events_by_robot[robot_id].append(event)

    # Sort events

    for robot_id in events_by_robot:

        events_by_robot[robot_id].sort(key=lambda event: event["t"])

    return events_by_robot


# --------------------------------------------------
# Robot publisher
# --------------------------------------------------


def run_robot(robot_id, events):

    connected = False

    # ----------------------------------------------
    # MQTT callbacks
    # ----------------------------------------------

    def on_connect(client, userdata, flags, reason_code, properties=None):

        nonlocal connected

        connected = True

        print(f"[{robot_id}] Connected to MQTT broker", flush=True)

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):

        nonlocal connected

        connected = False

        print(f"[{robot_id}] Disconnected from broker", flush=True)

    # ----------------------------------------------
    # Create MQTT client
    # ----------------------------------------------

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, client_id=f"robot-{robot_id}"
    )

    client.reconnect_delay_set(min_delay=1, max_delay=10)

    client.on_connect = on_connect

    client.on_disconnect = on_disconnect

    # ----------------------------------------------
    # Connect with retry
    # ----------------------------------------------

    while True:

        try:

            client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)

            break

        except Exception as error:

            print(f"[{robot_id}] " f"Broker unavailable: {error}", flush=True)

            time.sleep(2)

    # Start network loop

    client.loop_start()

    # Wait for connection

    while not connected:

        time.sleep(0.1)

    # ----------------------------------------------
    # Replay events
    # ----------------------------------------------

    try:

        while True:

            previous_time = events[0]["t"]

            for event in events:

                current_time = event["t"]

                # Maintain relative timing

                delay = (current_time - previous_time) / PLAYBACK_SPEED

                if delay > 0:

                    time.sleep(delay)

                # Publish event

                topic = f"robots/" f"{robot_id}/" f"telemetry"

                payload = json.dumps(event)

                client.publish(topic, payload, qos=1)

                print(
                    f"[{robot_id}] "
                    f"Published t={event['t']} "
                    f"status={event['status']}",
                    flush=True,
                )

                previous_time = current_time

            # --------------------------------------
            # Loop replay
            # --------------------------------------

            if not LOOP_PLAYBACK:

                break

            print(f"[{robot_id}] " f"Restarting replay", flush=True)

            time.sleep(1)

    finally:

        client.loop_stop()

        client.disconnect()


# --------------------------------------------------
# Main process
# --------------------------------------------------


def main():

    events_by_robot = load_events()

    with open(ROBOTS_PATH, "r") as file:

        robots = json.load(file)

    processes = []

    # ----------------------------------------------
    # Create one process per robot
    # ----------------------------------------------

    for robot in robots:

        robot_id = robot["robot_id"]

        robot_events = events_by_robot.get(robot_id, [])

        if not robot_events:

            raise RuntimeError(f"No events found " f"for robot {robot_id}")

        process = Process(
            target=run_robot, args=(robot_id, robot_events), name=f"robot-{robot_id}"
        )

        process.start()

        processes.append(process)

    print("Started " f"{len(processes)} " "robot processes", flush=True)

    # ----------------------------------------------
    # Graceful shutdown
    # ----------------------------------------------

    def shutdown(signal_number, frame):

        print("Stopping robot simulation...", flush=True)

        for process in processes:

            if process.is_alive():

                process.terminate()

        for process in processes:

            process.join(timeout=5)

        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)

    signal.signal(signal.SIGINT, shutdown)

    # Wait for robot processes

    for process in processes:

        process.join()


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":

    main()
