import json
import websocket


WS_URL = "ws://localhost:8000/ws/fleet"


def on_open(ws):
    print("=" * 70)
    print("WEBSOCKET CONNECTED")
    print(f"URL: {WS_URL}")
    print("Waiting for fleet updates...")
    print("=" * 70)


def on_message(ws, message):
    print("\n" + "=" * 70)
    print("FLEET UPDATE RECEIVED")
    print("=" * 70)

    try:
        data = json.loads(message)
        print(json.dumps(data, indent=2))

        print("\nRESULT: MESSAGE RECEIVED ✓")

    except json.JSONDecodeError:
        print(message)


def on_error(ws, error):
    print("\nWEBSOCKET ERROR:")
    print(error)


def on_close(ws, close_status_code, close_msg):
    print("\n" + "=" * 70)
    print("WEBSOCKET CLOSED")
    print(f"Status Code: {close_status_code}")
    print(f"Message: {close_msg}")
    print("=" * 70)


if __name__ == "__main__":
    print("\nFLEET MANAGEMENT BACKEND - WEBSOCKET TEST")
    print(f"Connecting to: {WS_URL}\n")

    websocket.enableTrace(False)

    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n\nTest stopped by user.")
