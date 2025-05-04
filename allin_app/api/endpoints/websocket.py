# WebSocket endpoint logic (Phase 2)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...core.interaction import InteractionManager # Adjusted import path
from google.genai import types # Import types for config
from ...core.logging_config import logger # Adjusted import path

router = APIRouter()

# Instantiate the InteractionManager (global for now, consider DI later)
# Ensure this runs *after* logging and config are set up if they have side effects on import
try:
    interaction_manager = InteractionManager()
except Exception as e:
    logger.critical(f"Failed to initialize InteractionManager: {e}")
    interaction_manager = None # Set to None to prevent usage

@router.websocket("/ws") # Remove chat_id from path, session is tied to connection
async def websocket_endpoint(websocket: WebSocket):
    client_host = websocket.client.host
    client_port = websocket.client.port
    logger.info(f"WebSocket connection accepted from {client_host}:{client_port}")
    await websocket.accept()

    if not interaction_manager or not interaction_manager.client:
        logger.error(f"InteractionManager or GenAI client not available. Closing WebSocket from {client_host}:{client_port}.")
        await websocket.close(code=1011, reason="AI Service Unavailable")
        return

    # --- Prepare Live API Config ---
    system_prompt_text = interaction_manager.get_system_prompt()
    initial_handle = interaction_manager.last_session_handle # Get the handle
    logger.info(f"Attempting connection with session handle: {initial_handle}")

    # Use LiveConnectConfig class
    live_config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        # Add Session Resumption config
        session_resumption=types.SessionResumptionConfig(
            handle=initial_handle
        ),
        # Add Context Window Compression config
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(), # Use default sliding window
        )
    )

    # Add system instruction if available
    if system_prompt_text:
        live_config.system_instruction = types.Content(
            parts=[types.Part(text=system_prompt_text)])
        logger.info("System instruction included in Live API config.")
    else:
        logger.warning("No system prompt loaded, proceeding without system instruction.")
    # -----------------------------

    try:
        # --- Establish Live API Session --- 
        logger.info(f"Connecting to Live API model: {interaction_manager.live_model_name}")
        async with interaction_manager.client.aio.live.connect(
            model=interaction_manager.live_model_name, 
            config=live_config # Pass the LiveConnectConfig object
        ) as session:
            logger.info(f"Live API session established for {client_host}:{client_port}")
            
            # --- Interaction Loop --- 
            # Listen for messages from the WebSocket client
            async for message in websocket.iter_text():
                logger.debug(f"Received via WebSocket from {client_host}:{client_port}: {message}")
                # Process the message using the live session
                await interaction_manager.process_live_message(session, message, websocket)
            # -----------------------

        logger.info(f"Live API session closed for {client_host}:{client_port}")
        # -------------------------------

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from {client_host}:{client_port}")
        # TODO: Handle client disconnection (e.g., cleanup resources associated with chat_id)
    except Exception as e:
        logger.error(f"Error during WebSocket/Live API interaction for {client_host}:{client_port}: {e}", exc_info=True)
        # Attempt to close gracefully, but connection might already be dead
        try:
            await websocket.close(code=1011, reason=f"Server error: {e}")
        except RuntimeError:
            pass # Connection likely already closed
