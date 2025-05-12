# Placeholder for Chat REST endpoints (Phase 4)
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from allin_app.core.interaction import InteractionManager
from allin_app.core.dependencies import get_interaction_manager # Import the dependency getter
from allin_app.core.logging_config import logger

# Remove prefix here, it's added in main.py
router = APIRouter(tags=["Chat Management"])

# --- Pydantic Models ---
class ChatHistoryListResponse(BaseModel):
    chat_ids: List[str] # Assuming client.users() returns a list of user IDs

class UserChatsListResponse(BaseModel):
    user_id: str
    chat_ids: List[str]

# --- Models for Detailed History --- 
class MemoryItem(BaseModel):
    id: str
    memory: str
    created_at: Optional[str] = None # Make timestamp optional just in case
    # Add other fields if needed, like metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatHistoryDetailResponse(BaseModel):
    user_id: str
    chat_id: str # Added chat_id
    memories: List[MemoryItem]
# ---------------------------------

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
                    detail="Failed to retrieve chat history list."
                )
        return {"chat_ids": chat_ids}

    except Exception as e:
        logger.error(f"Error retrieving chat history from mem0ai: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history."
        )

@router.get("/history/{user_id}/{chat_id}", response_model=ChatHistoryDetailResponse)
async def get_user_chat_history(
    user_id: str, 
    chat_id: str, # Added chat_id
    manager: InteractionManager = Depends(get_interaction_manager)
):
    """Retrieve all memories for a specific user ID and chat ID."""
    logger.info(f"Attempting to retrieve memory history for user_id: {user_id}, chat_id: {chat_id}")
    memories_data = []
    client = manager.memory_manager.memory_client
    if client:
        try:
            # Construct filter for chat_id metadata according to mem0 docs (needs AND/OR wrapper)
            filters = {
                "AND": [
                    {"metadata": {"chat_id": chat_id}}
                ]
            }
            logger.info(f"Calling memory_client.get_all for user: {user_id} with filter: {filters}")
            # Passing user_id directly and chat_id via filters
            raw_memories = client.get_all(user_id=user_id, filters=filters) 
            logger.info(f"Received response from get_all() for {user_id}/{chat_id} (type: {type(raw_memories)}): {raw_memories}")
            # --- Add detailed logging for debugging filter --- 
            logger.debug(f"RAW MEMORIES structure for {user_id}/{chat_id} with filter {filters}: {raw_memories}")
            # --- End detailed logging --- 
 
            # Basic validation/parsing - adjust based on actual return type!
            if isinstance(raw_memories, list):
                memories_data = raw_memories # Assume list of dicts matching MemoryItem
            elif isinstance(raw_memories, dict) and 'results' in raw_memories:
                 # Handle potential pagination structure like users() had
                 results_list = raw_memories.get('results', [])
                 if isinstance(results_list, list):
                    memories_data = results_list
                 else:
                    logger.warning(f"'results' key in get_all response is not a list: {results_list}")
            else:
                 logger.warning(f"Unexpected response structure from memory_client.get_all(): {raw_memories}")

        except AttributeError:
             # This might occur if get_all doesn't exist or filters aren't supported as expected
             logger.error(f"MemoryClient method error (likely get_all or filters). User: {user_id}, Chat: {chat_id}", exc_info=True)
             raise HTTPException(status_code=501, detail="Memory retrieval method/filter not implemented correctly.")
        except Exception as e:
            logger.error(f"Error retrieving memory history for user {user_id}, chat {chat_id}: {e}", exc_info=True)
            # Consider specific exceptions if mem0 raises them (e.g., UserNotFound)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve memory history for user {user_id}, chat {chat_id}."
            )
    else:
        logger.warning("Memory client not available.")
        raise HTTPException(status_code=503, detail="Memory service unavailable.")

    # Validate and structure the response using Pydantic models
    # This will raise validation errors if the data doesn't match MemoryItem structure
    try:
        validated_memories = [MemoryItem(**mem) for mem in memories_data]
        logger.info(f"Successfully retrieved and validated {len(validated_memories)} memories for user {user_id}, chat {chat_id}.")
        return ChatHistoryDetailResponse(user_id=user_id, chat_id=chat_id, memories=validated_memories)
    except Exception as pydantic_e: # Catch potential Pydantic validation errors
        logger.error(f"Failed to validate memory data for user {user_id}, chat {chat_id}: {pydantic_e}", exc_info=True)
        logger.error(f"Raw data causing validation error: {memories_data}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory data format error for user {user_id}, chat {chat_id}."
        )

@router.get("/chats/{user_id}", response_model=UserChatsListResponse)
async def list_user_chats(user_id: str, manager: InteractionManager = Depends(get_interaction_manager)):
    """Lists unique chat IDs associated with a given user ID based on memory metadata."""
    logger.info(f"Attempting to list chat IDs for user_id: {user_id}")
    chat_ids = set()
    client = manager.memory_manager.memory_client

    if client:
        try:
            # Retrieve all memories for the user, we'll filter chat_ids locally
            logger.info(f"Calling memory_client.get_all for user: {user_id} to extract chat IDs.")
            # Note: This could be inefficient if a user has a vast number of memories.
            # Consider pagination or if mem0 offers metadata aggregation in the future.
            all_memories = client.get_all(user_id=user_id)
            logger.debug(f"Received raw memories for user {user_id}: {all_memories}")

            # Process the response to extract chat_ids from metadata
            memories_list = []
            if isinstance(all_memories, list):
                memories_list = all_memories
            elif isinstance(all_memories, dict) and 'results' in all_memories:
                results = all_memories.get('results', [])
                if isinstance(results, list):
                    memories_list = results

            # Extract chat_id from metadata
            for memory in memories_list:
                if isinstance(memory, dict):
                    metadata = memory.get('metadata')
                    if isinstance(metadata, dict):
                        chat_id = metadata.get('chat_id')
                        if chat_id and isinstance(chat_id, str):
                            chat_ids.add(chat_id)
            
            logger.info(f"Found {len(chat_ids)} unique chat IDs for user {user_id}: {chat_ids}")

        except AttributeError:
             logger.error(f"MemoryClient method error (likely get_all). User: {user_id}", exc_info=True)
             raise HTTPException(status_code=501, detail="Memory retrieval method not implemented correctly.")
        except Exception as e:
            logger.error(f"Error retrieving memories to list chats for user {user_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve data to list chats for user {user_id}."
            )
    else:
        logger.warning("Memory client not available.")
        raise HTTPException(status_code=503, detail="Memory service unavailable.")

    return UserChatsListResponse(user_id=user_id, chat_ids=list(chat_ids))

# Example endpoints (to be implemented):
# /start
# /end
# /config
# /history/{chat_id}
# /history/{chat_id}/resume
# /search
