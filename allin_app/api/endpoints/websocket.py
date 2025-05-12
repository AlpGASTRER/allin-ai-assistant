# WebSocket endpoint logic (Phase 2)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from ...core.interaction import InteractionManager # Adjusted import path
from google.genai import types # Import types for config
from ...core.logging_config import logger # Adjusted import path
from ...core.dependencies import get_interaction_manager # Import the dependency getter
import json # Import json for parsing incoming data

router = APIRouter()

# Add user_id and chat_id to the path for immediate identification and handle retrieval
@router.websocket("/ws/{user_id}/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, chat_id: str, manager: InteractionManager = Depends(get_interaction_manager)):
    client_host = websocket.client.host
    client_port = websocket.client.port
    logger.info(f"WebSocket connection accepted from {client_host}:{client_port} for user '{user_id}', chat '{chat_id}'")
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
    # Retrieve the handle for this specific user
    initial_handle = manager.get_session_handle(user_id)
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
                    # user_id is now obtained from the path parameter
                    message = data.get("message")

                    if message is None:
                        logger.warning(f"Received invalid message structure: {raw_data}")
                        await websocket.send_text(json.dumps({"type": "error", "content": "Invalid message format. 'message' is required."}))
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
                        chat_id=chat_id, # Pass chat_id
                        message=message, # Pass message content
                        websocket=websocket
                    ):
                        # Send the structured response part as a JSON string
                        await websocket.send_text(json.dumps(response_part))

                        # --- Handle Session Resumption Updates --- 
                        # Check for session resumption updates within the response stream
                        if response_part.get('type') == 'session_resumption_update':
                            update_data = response_part.get('content') # Assuming content holds the update details
                            if update_data and isinstance(update_data, dict):
                                is_resumable = update_data.get('resumable')
                                new_handle = update_data.get('new_handle')
                                if is_resumable and new_handle:
                                    # Store the new handle for this user
                                    manager.set_session_handle(user_id, new_handle)
                                    logger.info(f"Received and stored new session handle for user {user_id}.")
                                elif not is_resumable:
                                    # Session became non-resumable, clear the handle
                                    manager.set_session_handle(user_id, None)
                                    logger.warning(f"Session for user {user_id} became non-resumable. Cleared handle.")
                        # -----------------------------------------

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
