""" # test_client.py

import socketio
import app

# TODO: Create a Socket.IO client object here
sio = socketio.Client()

# TODO: Create an event handler for 'connect' that prints a message
# and sends a "start_game" event to the backend
@sio.event
def connect():
    pass

# TODO: Create an event handler for 'update' that prints the game state
@sio.event
def update(data):
    pass

# TODO: Create an event handler for 'disconnect' that prints something like "Disconnected"
@sio.event
def disconnect():
    pass

# Main function to run the client
def main():
    pass

if __name__ == "__main__":
    main() """

import time
import socketio

# TODO: Create a Socket.IO client object here
sio = socketio.Client()

# We'll capture grid size from the server's initial payload
_grid_w = None
_grid_h = None

def _normalize_and_print_update(payload):
    global _grid_w, _grid_h

    # snake can be a list (your Game.send) or a dict (if using to_dict)
    snake_val = payload.get("snake")
    if isinstance(snake_val, dict) and "body" in snake_val:
        snake_val = snake_val["body"]

    # food can be a list (your Game.send) or a dict (if using to_dict)
    food_val = payload.get("food")
    if isinstance(food_val, dict) and "position" in food_val:
        food_val = food_val["position"]

    out = {
        "grid_width": payload.get("grid_width", _grid_w),
        "grid_height": payload.get("grid_height", _grid_h),
        "snake": snake_val,
        "food": food_val,
        "score": payload.get("score"),
    }
    print(f"Update: {out}")

# TODO: Create an event handler for 'connect' that prints a message
# and sends a "start_game" event to the backend
@sio.event
def connect():
    print("[client] Connected to server.")
    # Start a game (you can tweak these or omit to use server defaults)
    sio.emit("start_game", {
        "grid_width": 29,
        "grid_height": 19,
        "starting_tick": 0.03,
    })

# The server emits 'game_state' -> we handle it and print formatted updates
@sio.on("game_state")
def on_game_state(data):
    global _grid_w, _grid_h
    event = data.get("event")
    payload = data.get("payload", {})

    if event == "init":
        # capture grid size from initial snapshot
        _grid_w = payload.get("grid_width", _grid_w)
        _grid_h = payload.get("grid_height", _grid_h)
        # also print an initial update in the requested shape
        _normalize_and_print_update(payload)

    elif event == "tick":
        _normalize_and_print_update(payload)

    elif event == "game_over":
        # some servers may send game_over in the same channel
        _normalize_and_print_update(payload)
        print("[client] Game over. Disconnecting...")
        sio.disconnect()

# TODO: Create an event handler for 'update' that prints the game state
# If your backend ever emits a plain 'update' event, print it the same way.
@sio.event
def update(data):
    _normalize_and_print_update(data)

# Also listen for explicit game_over events (if emitted separately)
@sio.on("game_over")
def on_game_over(data):
    _normalize_and_print_update(data.get("payload", data))
    print("[client] Game over. Disconnecting...")
    sio.disconnect()

# TODO: Create an event handler for 'disconnect' that prints something like "Disconnected"
@sio.event
def disconnect():
    print("[client] Disconnected from server.")

# Main function to run the client
def main():
    try:
        sio.connect("http://localhost:8765")
        print("[client] Waiting for live updates...")
        while sio.connected:
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("[client] Interrupted by user.")
    finally:
        if sio.connected:
            sio.disconnect()
        print("[client] Client stopped.")

if __name__ == "__main__":
    main()