# Placeholder for Chat REST endpoints (Phase 4)
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

from allin_app.core.interaction import InteractionManager
from allin_app.core.dependencies import get_interaction_manager # Import the dependency getter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat Management"])

# --- Pydantic Models ---
class ChatHistoryListResponse(BaseModel):
    chat_ids: List[str] # Assuming client.users() returns a list of user IDs
# ----------------------

@router.get("/history", response_model=ChatHistoryListResponse)
async def get_chat_history(manager: InteractionManager = Depends(get_interaction_manager)):
    """Retrieve a list of all known chat session IDs (user IDs)."""
    logger.info("Attempting to retrieve chat history list (user IDs).")
    try:
        client = manager.memory_manager.memory_client
        if client:
            try:
                logger.info("Attempting to retrieve user list from memory client.")
                users_response = client.users()
                logger.info(f"Received response from users() method (type: {type(users_response)}): {users_response}")
 
                # --- Updated Parsing Logic --- 
                # Check if the response is a dictionary and has the 'results' key
                if isinstance(users_response, dict) and 'results' in users_response:
                    results_list = users_response.get('results', [])
                    if isinstance(results_list, list):
                        # Extract the 'name' (user_id) from each user object in the list
                        chat_ids = [user.get('name') for user in results_list if isinstance(user, dict) and 'name' in user]
                        logger.info(f"Successfully extracted chat IDs (user IDs): {chat_ids}")
                    else:
                        logger.warning(f"'results' key in users_response is not a list: {results_list}")
                else:
                    logger.warning(f"Unexpected response structure from memory_client.users(): {users_response}. Expected dict with 'results' key.")
                # -----------------------------
 
            except Exception as e:
                logger.error(f"Error retrieving chat history from memory client: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve chat history."
                )
        return {"chat_ids": chat_ids}

    except Exception as e:
        logger.error(f"Error retrieving chat history from mem0ai: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history."
        )

# Example endpoints (to be implemented):
# /start
# /end
# /config
# /history/{chat_id}
# /history/{chat_id}/resume
# /search
