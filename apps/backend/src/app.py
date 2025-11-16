import asyncio
import os
import random
import time
import socketio
from aiohttp import web
from typing import Any, Dict, Optional
from game import Game
# from model import DQN


sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

# Basic health check endpoint - keep this for server monitoring
async def handle_ping(request: Any) -> Any:
    """Simple ping endpoint to keep server alive and check if it's running"""
    return web.json_response({"message": "pong"})


# TODO: Create a socketio event handler for when clients connect
@sio.event
async def connect(sid: str, environ: Dict[str, Any]) -> None:
    """Handle client connections - called when a frontend connects to the server"""
    # TODO: Print a message showing which client connected
    print(f"[connect] client connected: {sid}")
    # TODO: You might want to initialize game state here
    await sio.save_session(sid, {"active": False, "game": None, "agent": None})


# TODO: Create a socketio event handler for when clients disconnect
@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnections - cleanup any resources"""
    # TODO: Print a message showing which client disconnected
    print(f"[disconnect] client disconnected: {sid}")
    # TODO: Clean up any game sessions or resources for this client
    session = await sio.get_session(sid)
    if session:
        session["active"] = False
        session["game"] = None
        session["agent"] = None
        await sio.save_session(sid, session)


# TODO: Create a socketio event handler for starting a new game
@sio.event
async def start_game(sid: str, data: Dict[str, Any]) -> None:
    """Initialize a new game when the frontend requests it"""

    # TODO: Extract game parameters from data (grid_width, grid_height, starting_tick)
    grid_width: Optional[int] = data.get("grid_width")
    grid_height: Optional[int] = data.get("grid_height")
    starting_tick: Optional[float] = data.get("starting_tick")

    # TODO: Create a new Game instance and configure it
    game = Game()
    if isinstance(grid_width, int):
        game.grid_width = grid_width
    if isinstance(grid_height, int):
        game.grid_height = grid_height
    if isinstance(starting_tick, (int, float)):
        game.game_tick = float(starting_tick)

    # TODO: If implementing AI, create an agent instance here
    # agent = DQN(...)
    agent = None  # placeholder; set to your model instance when ready

    # TODO: Save the game state in the session using sio.save_session()
    session = await sio.get_session(sid) or {}
    session.update({"active": True, "game": game, "agent": agent})
    await sio.save_session(sid, session)

    # TODO: Send initial game state to the client using sio.emit()
    await sio.emit("game_state", {"event": "init", "payload": game.to_dict()}, to=sid)

    """Initialize a new game when the frontend requests it"""

    # Start the update loop in the background
    sio.start_background_task(update_game, sid)


# TODO: Optional - Create event handlers for saving/loading AI models
# (intentionally omitted as optional)


# TODO: Implement the main game loop
async def update_game(sid: str) -> None:
    """Main game loop - runs continuously while the game is active"""
    # TODO: Create an infinite loop
    try:
        while True:
            # TODO: Check if the session still exists (client hasn't disconnected)
            session = await sio.get_session(sid)
            if not session:
                break

            # TODO: Get the current game and agent state from the session
            game: Optional[Game] = session.get("game")
            agent = session.get("agent")
            active: bool = session.get("active", False)

            if not active or not game:
                break

            # TODO: Implement AI agentic decisions
            if agent is not None:
                await update_agent_game_state(game, agent)
            else:
                # TODO: Update the game state (move snake, check collisions, etc.)
                game.step()

            # TODO: Save the updated session
            await sio.save_session(sid, session)

            # TODO: Send the updated game state to the client
            await sio.emit("game_state", {"event": "tick", "payload": game.send()}, to=sid)

            # If the game ended, stop the loop
            if not game.running:
                await sio.emit("game_over", {"event": "game_over", "payload": game.send()}, to=sid)
                session["active"] = False
                await sio.save_session(sid, session)
                break

            # TODO: Wait for the appropriate game tick interval before next update
            await asyncio.sleep(max(0.005, float(game.game_tick)))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[update_game] error for {sid}: {e}")
        try:
            await sio.emit("server_error", {"message": str(e)}, to=sid)
        except Exception:
            pass


# TODO: Helper function for AI agent interaction with game
async def update_agent_game_state(game: Game, agent: Any) -> None:
    """Handle AI agent decision making and training"""
    # TODO: Get the current game state for the agent
    state = game.to_vector() if hasattr(game, "to_vector") else None
    prev_score = game.score

    # TODO: Have the agent choose an action (forward, turn left, turn right)
    # For now, use a simple random policy placeholder until a real agent is plugged in.
    # Replace with: action = agent.act(state)
    action = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])

    # TODO: Convert the agent's action to a game direction
    direction = action  # already absolute in this placeholder

    # TODO: Apply the direction change to the game
    game.queue_change(direction)

    # TODO: Step the game forward one frame
    game.step()

    # TODO: Calculate the reward for this action
    # Basic reward: +1 if score increased, -1 if game ended, small step penalty
    reward = -0.01
    if game.score > prev_score:
        reward += 1.0
    if not game.running:
        reward -= 1.0

    # TODO: Get the new game state after the action
    next_state = game.to_vector() if hasattr(game, "to_vector") else None

    # TODO: Train the agent on this experience (short-term memory)
    # if hasattr(agent, "train_short_memory"):
    #     agent.train_short_memory(state, action, reward, next_state, not game.running)

    # TODO: Store this experience in the agent's memory
    # if hasattr(agent, "remember"):
    #     agent.remember(state, action, reward, next_state, not game.running)

    # TODO: If the game ended:
    #   - Train the agent's long-term memory
    #   - Update statistics (games played, average score)
    #   - Reset the game for the next round
    if not game.running:
        # if hasattr(agent, "train_long_memory"):
        #     agent.train_long_memory()
        game.reset()


# TODO: Main server startup function
async def main() -> None:
    """Start the web server and socketio server"""
    # TODO: Add the ping endpoint to the web app router
    app.router.add_get("/ping", handle_ping)
    # TODO: Create and configure the web server runner
    runner = web.AppRunner(app)
    await runner.setup()
    # TODO: Start the server on the appropriate host and port
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8765"))
    site = web.TCPSite(runner, host=host, port=port)
    # TODO: Print server startup message
    try:
        await site.start()
        print(f"[server] listening on http://{host}:{port}")
        # TODO: Keep the server running indefinitely
        stop_event = asyncio.Event()
        await stop_event.wait()
    # TODO: Handle any errors gracefully
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("[server] shutting down...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
