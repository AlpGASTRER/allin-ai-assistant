# Placeholder for Core Interaction Logic (Phase 2)
from google import genai
from google.genai import types
from .config import settings  # Use relative import for config
from ..memory.manager import MemoryManager # Import MemoryManager
from .logging_config import logger # Use relative import for logger
import asyncio
from pathlib import Path
from typing import Dict, Optional

class InteractionManager:
    def __init__(self):
        """Initializes the Interaction Manager, including the Google AI client and system prompt."""
        logger.info("Initializing InteractionManager...")
        # Change to a model confirmed to support 'generateContent'
        self.live_model_name = 'models/gemini-2.0-flash-live-001' 
        self.client = None # Initialize client attribute
        self.system_prompt = None # Initialize system_prompt attribute
        self._session_handles: Dict[str, Optional[str]] = {} # Store user_id -> session handle
        self.memory_manager = None # Initialize memory manager attribute

        # --- Load System Prompt ---
        try:
            # Construct path relative to this file's location
            prompt_path = Path(__file__).parent.parent / "system_prompt.txt"
            if prompt_path.is_file():
                self.system_prompt = prompt_path.read_text(encoding='utf-8')
                logger.info("System prompt loaded successfully.")
            else:
                logger.warning(f"System prompt file not found at: {prompt_path}")
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")

        # --- Initialize Memory Manager ---
        try:
            self.memory_manager = MemoryManager()
        except Exception as e:
            logger.error(f"Failed to initialize MemoryManager: {e}", exc_info=True)
            # Allow InteractionManager to continue, but memory features will be disabled
        # ---------------------------------

        # --- Initialize Google Client --- 
        if settings.google_api_key:
            try:
                # Initialize the client directly with the API key
                self.client = genai.Client(api_key=settings.google_api_key)
                logger.info(f"Google GenAI client initialized successfully.")
                # Optional: Test connection or list models here if needed

            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI client: {e}")
                logger.error("Please ensure GOOGLE_API_KEY is set correctly in the .env file and network is accessible.")
                self.client = None

        # TODO: Initialize other components like:
        # - Memory Manager
        # - RAG Handler
        pass

    def get_system_prompt(self) -> str | None:
        """Returns the loaded system prompt text."""
        return self.system_prompt

    def get_session_handle(self, user_id: str) -> Optional[str]:
        """Retrieves the last known session handle for a given user_id."""
        handle = self._session_handles.get(user_id)
        logger.debug(f"Retrieved session handle for user '{user_id}': {'Exists' if handle else 'None'}")
        return handle

    def set_session_handle(self, user_id: str, handle: Optional[str]):
        """Stores the session handle for a given user_id."""
        self._session_handles[user_id] = handle
        logger.info(f"Stored session handle for user '{user_id}': {'Set' if handle else 'Cleared'}")

    async def process_live_message(
        self, 
        live_session, 
        user_id: str, 
        chat_id: str, 
        message: str, 
        websocket
    ):
        """Processes a message within an active Live API session."""
        if not self.client:
            logger.error("Google GenAI client not initialized.")
            await websocket.send_text("Error: AI Service not configured.")
            return

        logger.info(f"Processing live message for user_id '{user_id}': {message[:50]}...")

        # --- Prepare content with Memory --- 
        turns_to_send = []
        if self.memory_manager:
            try:
                # Retrieve relevant memories
                relevant_memories = await self.memory_manager.get_relevant_memory(user_id=user_id, query=message)
                if relevant_memories:
                    # Use more explicit labels for the AI
                    memory_prefix = "CONTEXT FROM PREVIOUS CONVERSATIONS:\n"
                    formatted_memories_text = "\n".join(f"- {mem}" for mem in relevant_memories)
                    # Create a separate turn for the memory context
                    # Using role='user' for context might be okay, or might need refinement based on API behavior
                    context_turn = types.Content(role="user", parts=[types.Part(text=f"{memory_prefix}{formatted_memories_text}")])
                    turns_to_send.append(context_turn)
                    logger.debug(f"Prepended {len(relevant_memories)} memories to message for user {user_id}.")
                else:
                    logger.debug(f"No relevant memories found for user {user_id} query.")

            except Exception as e:
                logger.error(f"Failed to retrieve/format memory for user {user_id}: {e}", exc_info=True)
                # Proceed without memory if retrieval fails

        # Always add the current user message as the final turn
        current_message_turn = types.Content(role="user", parts=[types.Part(text=message)])
        turns_to_send.append(current_message_turn)

        try:
            logger.debug(f"Sending {len(turns_to_send)} turn(s) to live session for user {user_id}: {str(turns_to_send)[:150]}...")
            # Send the list of turns
            await live_session.send_client_content(turns=turns_to_send, turn_complete=True)
            # --------------------------------------- 

            # --- Receive response and handle resumption --- 
            full_response_text = ""
            text_buffer = "" # Buffer for consecutive text parts

            try:
                async for chunk in live_session.receive():
                    # Process structured server content
                    if chunk.server_content:
                        model_turn = chunk.server_content.model_turn
                        if model_turn:
                            for part in model_turn.parts:
                                if part.text is not None:
                                    text_content = part.text
                                    # Append to buffer instead of yielding immediately
                                    text_buffer += text_content
                                elif part.executable_code is not None:
                                    # If buffer has content, yield it first
                                    if text_buffer:
                                        full_response_text += text_buffer 
                                        yield {"type": "text", "content": text_buffer}
                                        text_buffer = "" # Clear buffer
                                    # Process Code Part
                                    # Add a placeholder to memory indicating code was generated
                                    full_response_text += "\n[AI generated code to perform the requested task]\n"
                                    code_content = part.executable_code.code
                                    yield {"type": "code", "content": code_content}
                                elif part.code_execution_result is not None:
                                    # If buffer has content, yield it first
                                    if text_buffer:
                                        full_response_text += text_buffer 
                                        yield {"type": "text", "content": text_buffer}
                                        text_buffer = "" # Clear buffer
                                    # Process Code Result (Check for Errors)
                                    result_output = part.code_execution_result.output
                                    is_error = "Traceback (most recent call last):" in result_output or \
                                               "Error:" in result_output or \
                                               "Exception:" in result_output
                                    if is_error:
                                        logger.warning(f"Code execution error: {result_output[:100]}...")
                                        # Use a clearer placeholder for failed execution in memory
                                        full_response_text += "\n[AI code execution FAILED]\n"
                                        yield {"type": "code_error", "content": result_output}
                                    else:
                                        full_response_text += f"\n--- Code Output ---\n{result_output}\n-------------------\n"
                                        yield {"type": "code_result", "content": result_output}
                                # TODO: Handle other potential parts like inline_data
            except Exception as e:
                logger.error(f"Error during Live API stream processing for user {user_id}: {e}", exc_info=True)
                # Yield a specific error message to the client
                yield {"type": "api_error", 
                       "content": "An error occurred while processing the AI response.", 
                       "details": str(e)}
                # We might want to break or ensure the session closes gracefully depending on the error
                # For now, we'll let it proceed to the 'finally' block equivalent (post-loop yield)
                # Note: The error might mean the 'end_of_response' from the websocket endpoint won't be sent naturally.

            # After the loop (or if an error occurred), yield any remaining text in the buffer
            if text_buffer:
                full_response_text += text_buffer # Add final buffered text to memory
                yield {"type": "text", "content": text_buffer}

            # --- Store AI Response in Memory --- 
            if self.memory_manager and full_response_text:
                try:
                    # Add user message
                    await self.memory_manager.add_memory(user_id=user_id, role="user", content=message, chat_id=chat_id)
                    # Log the content being saved for the assistant
                    logger.debug(f"Saving assistant response to memory for user {user_id}: '{full_response_text}'")                    # Add AI response
                    await self.memory_manager.add_memory(user_id=user_id, role="assistant", content=full_response_text, chat_id=chat_id)
                    logger.debug(f"Added user message and AI response to memory for user {user_id}.")
                except Exception as e:
                    logger.error(f"Failed to add interaction to memory for user {user_id}: {e}", exc_info=True)
            # --------------------------------- 

        except Exception as e:
            logger.error(f"Error processing live message for user {user_id}: {e}", exc_info=True)
            try:
                await websocket.send_text(f"Error processing message: {e}")
            except Exception:
                logger.error(f"Failed to send error via WebSocket: {e}")

async def cleanup_interaction(interaction_manager):
    # TODO: Implement cleanup logic here
    pass
