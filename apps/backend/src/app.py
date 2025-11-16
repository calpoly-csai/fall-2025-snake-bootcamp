import asyncio
import time
import socketio
from aiohttp import web
from typing import Any, Dict


# from model import DQN
from game import Game  


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
    # Print a message showing which client connected
    print(f"Client connected: {sid}")
    
    # Initialize empty session for this client to store game data
    await sio.save_session(sid, {
        'game': None,          # Will hold the Game instance
        'agent': None,         # Will hold the AI agent instance  
        'game_running': False  # Track if game is currently active
    })
    
    # Send welcome message to confirm connection
    await sio.emit('connection_confirmed', {
        'message': 'Connected to Snake game server!',
        'client_id': sid
    }, room=sid)


# TODO: Create a socketio event handler for when clients disconnect
@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnections - cleanup any resources"""
    # Print a message showing which client disconnected
    print(f"Client disconnected: {sid}")
    
    # Try to get session data before cleanup to see what they were doing
    try:
        session = await sio.get_session(sid)
        
        # Check if they had an active game running
        if session.get('game_running'):
            print(f"Game session ended for client: {sid}")
            print(f"   Final score: {session.get('game', {}).get('score', 'unknown')}")
        
    except Exception as e:
        # Session might already be cleaned up or never existed
        print(f"Could not retrieve session for {sid}: {e}")
    
    # SocketIO automatically cleans up the session, but we confirm it
    print(f"Resources cleaned up for client: {sid}")


# TODO: Create a socketio event handler for starting a new game
@sio.event
async def start_game(sid: str, data: Dict[str, Any]) -> None:
    """Initialize a new game when the frontend requests it"""
    print(f"Starting new game for client: {sid}")
    
    try:
        # Extract game parameters from data with sensible defaults
        grid_width = data.get('grid_width', 20)      # Default 20x20 grid
        grid_height = data.get('grid_height', 20)
        starting_tick = data.get('starting_tick', 200)  # 200ms = 5 moves per second
        
        print(f"Game settings: {grid_width}x{grid_height}, tick: {starting_tick}ms")
        
        # Create a new Game instance and configure it  
        game = Game()
        
        # TODO: If implementing AI, create an agent instance here
        # from agent import DQN
        # agent = DQN() 
        agent = None  # For now, no AI (we'll add this later)
        
        # Save the game state in the session using sio.save_session()
        await sio.save_session(sid, {
            'game': game,
            'agent': agent,
            'game_running': True,
            'starting_tick': starting_tick,
            'last_update': time.time()
        })
        
        # Send initial game state to the client using sio.emit()
        initial_state = {
            'snake': game.snake.body,     # Snake body positions [[x,y], [x,y], ...]
            'food': game.food.position,   # Food position [x, y]
            'score': game.score,          # Current score (starts at 0)
            'game_over': False,           # Game just started
            'grid_width': game.grid_width,
            'grid_height': game.grid_height
        }
        
        await sio.emit('game_state', initial_state, room=sid)
        print(f"Sent initial game state to client: {sid}")
        
        # Start the game update loop (this runs continuously in background)
        asyncio.create_task(update_game(sid))
        print(f"Started game loop for client: {sid}")
        
    except Exception as e:
        print(f"Error starting game for {sid}: {e}")
        await sio.emit('error', {
            'message': f'Failed to start game: {str(e)}'
        }, room=sid)


# TODO: Optional - Create event handlers for saving/loading AI models


# TODO: Implement the main game loop
async def update_game(sid: str) -> None:
    """Main game loop - runs continuously while the game is active"""
    print(f"Starting game loop for client: {sid}")
    
    try:
        # Create an infinite loop (runs until game ends or player disconnects)
        while True:
            # Check if the session still exists (client hasn't disconnected)
            try:
                session = await sio.get_session(sid)
            except Exception:
                print(f"Session {sid} no longer exists, stopping game loop")
                break
            
            # Check if game is still running (might be paused or ended)
            if not session.get('game_running', False):
                print(f"Game stopped for client: {sid}")
                break
            
            # Get the current game and agent state from the session
            game = session.get('game')
            agent = session.get('agent')
            starting_tick = session.get('starting_tick', 200)
            
            if not game:
                print(f"No game found in session for {sid}")
                break
            
            # Implement AI agentic decisions OR auto-pilot
            if agent:
                # AI agent makes the decision (we'll implement this later)
                await update_agent_game_state(game, agent)
            else:
                # Auto-pilot: just move snake straight (for testing)
                game.step()
            
            # Check if game ended (collision with walls or itself)
            game_over = not game.running
            
            # Prepare updated game state for transmission
            updated_state = {
                'snake': game.snake.body,         # Current snake body positions
                'food': game.food.position,       # Food position
                'score': game.score,              # Current score
                'game_over': game_over,           # Did snake die?
                'grid_width': game.grid_width,    # Board dimensions
                'grid_height': game.grid_height,
                'frame_count': getattr(game, 'frame_iteration', 0)  # Game frame counter
            }
            
            # Handle game over scenario
            if game_over:
                print(f"Game over for client {sid}, final score: {game.score}")
                
                # Mark game as no longer running
                session['game_running'] = False
                await sio.save_session(sid, session)
                
                # Send final game state and game over notification
                await sio.emit('game_state', updated_state, room=sid)
                await sio.emit('game_over', {
                    'final_score': game.score,
                    'message': f'Game Over! Final Score: {game.score}'
                }, room=sid)
                
                print(f"Game loop ended for client: {sid}")
                break
            
            # Save the updated session (game state might have changed)
            session['last_update'] = time.time()
            await sio.save_session(sid, session)
            
            # Send the updated game state to the client
            await sio.emit('game_state', updated_state, room=sid)
            
            # Wait for the appropriate game tick interval before next update
            await asyncio.sleep(starting_tick / 1000.0)  # Convert milliseconds to seconds
            
    except Exception as e:
        print(f"Error in game loop for {sid}: {e}")
        
        # Try to notify the client about the error
        try:
            await sio.emit('error', {
                'message': f'Game loop error: {str(e)}'
            }, room=sid)
        except:
            # If we can't even send error message, client probably disconnected
            print(f"Could not send error to {sid}, client likely disconnected")
    
    print(f"Game loop finished for client: {sid}")


# TODO: Helper function for AI agent interaction with game
async def update_agent_game_state(game: Game, agent: Any) -> None:
    """Handle AI agent decision making and training"""
    try:
        # Get the current game state for the agent (convert game to neural network input)
        state_old = agent.get_state(game)
        
        # Have the agent choose an action (forward, turn left, turn right)
        # Agent analyzes the current state and picks the best action
        action = agent.get_action(state_old)
        
        # Convert the agent's action to a game direction
        # action format: [straight, turn_right, turn_left]
        # Only change direction if the agent wants to turn
        if action[1] == 1:  # Agent chose "turn right"
            game.turn_right()
            print(f"AI decided: Turn RIGHT")
        elif action[2] == 1:  # Agent chose "turn left"  
            game.turn_left()
            print(f"AI decided: Turn LEFT")
        else:  # action[0] == 1, agent chose "go straight"
            print(f"AI decided: Go STRAIGHT")
            # No direction change needed - snake continues in current direction
        
        # Apply the direction change and step the game forward one frame
        # This actually moves the snake and checks for food/collisions
        reward = game.play_step(action)
        
        # Check if game ended (snake hit wall or itself)
        done = game.collision()
        
        # Calculate the reward for this action (teach AI what's good/bad)
        if hasattr(agent, 'calculate_reward'):
            # If agent has custom reward function, use it
            reward = agent.calculate_reward(game, done)
        # Otherwise use the reward from game.play_step()
        
        # Get the new game state after the action (what does the game look like now?)
        state_new = agent.get_state(game)
        
        # Train the agent on this experience (short-term memory)
        # This immediately teaches the AI: "when you see X state, doing Y action leads to Z reward"
        agent.train_short_memory(state_old, action, reward, state_new, done)
        
        # Store this experience in the agent's memory (for long-term learning)
        # This saves the experience for batch training later
        agent.remember(state_old, action, reward, state_new, done)
        
        # If the game ended, handle end-of-game training and statistics
        if done:
            print(f"Game ended! AI final score: {game.score}")
            
            # Train the agent's long-term memory on stored experiences
            # This runs batch training on many past experiences to improve overall strategy
            agent.train_long_memory()
            
            # Update statistics (games played, average score, etc.)
            if hasattr(agent, 'n_games'):
                agent.n_games += 1
                print(f"AI has now played {agent.n_games} games")
                
            if hasattr(agent, 'total_score'):
                agent.total_score += game.score
                avg_score = agent.total_score / agent.n_games
                print(f"AI average score: {avg_score:.1f}")
            
            # Reset the game for the next round (AI keeps learning)
            print(f"Resetting game for AI to try again...")
            game.reset()
            
    except Exception as e:
        print(f"Error in AI agent update: {e}")
        print(f"Falling back to simple auto-play mode")
        
        # If AI fails for any reason, fall back to simple movement
        # This ensures the game doesn't crash if AI has bugs
        game.play_step()  # Just move straight


# TODO: Main server startup function
async def main() -> None:
    """Start the web server and socketio server"""
    try:
        print("Initializing Snake Game Server...")
        
        # Add the ping endpoint to the web app router
        app.router.add_get('/ping', handle_ping)
        print("Added /ping health check endpoint")
        
        # Create and configure the web server runner
        runner = web.AppRunner(app)
        await runner.setup()
        print("Web server runner configured")
        
        # Configure host and port settings
        host = '0.0.0.0'  # Accept connections from any IP address
        port = 8000       # Default port for the backend server
        
        # Create the TCP site (this is what actually listens for connections)
        site = web.TCPSite(runner, host, port)
        
        # Start the server on the appropriate host and port
        await site.start()
        
        # Print server startup message with useful information
        print("=" * 60)
        print("SNAKE GAME AI SERVER STARTED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Server running on: http://{host}:{port}")
        print(f"Health check: http://localhost:{port}/ping")
        print(f"WebSocket endpoint: ws://localhost:{port}/socket.io/")
        print(f"AI learning engine: READY")
        print(f"Multi-player support: ENABLED")
        print("=" * 60)
        print("Server ready to accept Snake game connections!")
        print("Frontend should connect to this server for real-time gameplay")
        print("Game loops will start automatically when players join")
        print("=" * 60)
        
        # Keep the server running indefinitely
        print("Server running... Press Ctrl+C to stop")
        try:
            # This infinite loop keeps the server alive
            while True:
                await asyncio.sleep(1)  # Sleep 1 second, then check again
                # Server handles all connections in the background
                
        except KeyboardInterrupt:
            # User pressed Ctrl+C to stop the server
            print("\nReceived shutdown signal (Ctrl+C)")
            print("Initiating graceful server shutdown...")
            
    except Exception as e:
        # Handle any errors that occur during server startup
        print(f"FATAL: Server startup failed!")
        print(f"Error: {e}")
        print("Check the error above and try restarting the server")
        raise  # Re-raise the exception so we can see the full traceback
        
    finally:
        # Handle any errors gracefully during shutdown
        print("Cleaning up server resources...")
        try:
            await runner.cleanup()
            print("Server shutdown complete")
            print("Snake Game Server stopped successfully!")
        except Exception as e:
            print(f"Error during shutdown cleanup: {e}")
        
        print("Thanks for using Snake Game AI Server!")


if __name__ == "__main__":
    asyncio.run(main())
