# WebSocket endpoint logic (Phase 2)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from ...core.interaction import InteractionManager # Adjusted import path
from google.genai import types # Import types for config
from ...core.logging_config import logger # Adjusted import path
from ...core.dependencies import get_interaction_manager # Import the dependency getter
import json # Import json for parsing incoming data

router = APIRouter()

@router.websocket("/ws") # Remove chat_id from path, session is tied to connection
async def websocket_endpoint(websocket: WebSocket, manager: InteractionManager = Depends(get_interaction_manager)):
    client_host = websocket.client.host
    client_port = websocket.client.port
    logger.info(f"WebSocket connection accepted from {client_host}:{client_port}")
    await websocket.accept()

    # Use the injected InteractionManager instance ('manager')
    try:
        # Check the injected manager's client
        if not manager.client: # Check if google client init failed within manager
            raise ValueError("InteractionManager failed to initialize Google GenAI client.")
        logger.info(f"Using shared InteractionManager for connection {client_host}:{client_port}")
    except Exception as e:
        logger.critical(f"Failed to initialize InteractionManager for connection {client_host}:{client_port}: {e}", exc_info=True)
        # Close connection if manager fails to init
        await websocket.close(code=1011, reason="AI Service Initialization Error")
        return

    if not manager.client:
        logger.error(f"InteractionManager or GenAI client not available. Closing WebSocket from {client_host}:{client_port}.")
        await websocket.close(code=1011, reason="AI Service Unavailable")
        return

    # --- Prepare Live API Config ---
    system_prompt_text = manager.get_system_prompt()
    initial_handle = manager.last_session_handle # Get the handle
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
        # --- Configure tools for the Live API session --- 
        tools = [types.Tool(code_execution=types.ToolCodeExecution())]
        # Add the tools to the existing live_config object
        live_config.tools = tools
        logger.info(f"Live API config now includes tools: {live_config.tools}")
        # ---------------------------------------

        # --- Establish Live API Session --- 
        logger.info(f"Connecting to Live API model: {manager.live_model_name}")

        async with manager.client.aio.live.connect(
            model=manager.live_model_name, 
            config=live_config # Pass the updated LiveConnectConfig object with tools
        ) as session:
            logger.info(f"Live API session established for connection from {client_host}:{client_port}")
            
            # --- Interaction Loop --- 
            # Listen for messages from the WebSocket client
            async for raw_data in websocket.iter_text(): # Changed variable name
                logger.debug(f"Received raw data via WebSocket from {client_host}:{client_port}: {raw_data}")

                # --- Parse Incoming JSON ---
                try:
                    data = json.loads(raw_data)
                    user_id = data.get("user_id")
                    message = data.get("message")

                    if user_id is None or message is None:
                        logger.warning(f"Received invalid message structure: {raw_data}")
                        await websocket.send_text(json.dumps({"type": "error", "content": "Invalid message format. 'user_id' and 'message' are required."}))
                        continue # Skip processing this message

                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from {client_host}:{client_port}: {raw_data}")
                    await websocket.send_text("Error: Invalid JSON format.")
                    continue # Skip processing this message
                # --------------------------

                # Process the message using the live session
                # Pass user_id and message extracted from JSON
                try:
                    async for response_part in manager.process_live_message(
                        live_session=session,
                        user_id=user_id, # Pass user_id
                        message=message, # Pass message content
                        websocket=websocket
                    ):
                        # Send the structured response part as a JSON string
                        await websocket.send_text(json.dumps(response_part))

                    # Indicate the end of the response stream (optional, depends on client needs)
                    await websocket.send_text(json.dumps({"type": "end_of_response"}))
                except Exception as e:
                    logger.error(f"Error during message processing for {client_host}:{client_port}: {e}", exc_info=True)
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
