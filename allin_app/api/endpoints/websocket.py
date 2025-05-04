# WebSocket endpoint logic (Phase 2)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...core.interaction import InteractionManager # Adjusted import path
from ...core.logging_config import logger # Adjusted import path

router = APIRouter()

# Instantiate the InteractionManager (global for now, consider DI later)
# Ensure this runs *after* logging and config are set up if they have side effects on import
try:
    interaction_manager = InteractionManager()
except Exception as e:
    logger.critical(f"Failed to initialize InteractionManager: {e}")
    interaction_manager = None # Set to None to prevent usage

@router.websocket("/ws/{chat_id}") # Add chat_id to the path
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    client_host = websocket.client.host
    client_port = websocket.client.port
    logger.info(f"WebSocket connection accepted for chat_id '{chat_id}' from {client_host}:{client_port}")
    await websocket.accept()

    if not interaction_manager:
        logger.error(f"InteractionManager not available. Closing WebSocket for chat_id '{chat_id}'.")
        await websocket.close(code=1011, reason="AI Service Unavailable")
        return

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received via WebSocket from {client_host}:{client_port} for chat '{chat_id}': {data}")
            # Process incoming message using the InteractionManager
            await interaction_manager.handle_message(message=data, chat_id=chat_id, websocket=websocket)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for chat_id '{chat_id}' from {client_host}:{client_port}")
        # TODO: Handle client disconnection (e.g., cleanup resources associated with chat_id)
    except Exception as e:
        logger.error(f"WebSocket error for chat_id '{chat_id}': {e}", exc_info=True)
        # Attempt to close gracefully, but connection might already be dead
        try:
            await websocket.close(code=1011, reason=f"Server error: {e}")
        except RuntimeError:
            pass # Connection likely already closed
