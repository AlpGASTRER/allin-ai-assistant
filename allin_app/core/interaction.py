# Placeholder for Core Interaction Logic (Phase 2)
from google import genai
from google.genai import types
from .config import settings  # Use relative import for config
from .logging_config import logger # Use relative import for logger
import asyncio
from pathlib import Path

class InteractionManager:
    def __init__(self):
        """Initializes the Interaction Manager, including the Google AI client and system prompt."""
        logger.info("Initializing InteractionManager...")
        # Change to a model confirmed to support 'generateContent'
        self.live_model_name = 'models/gemini-2.0-flash-001' 
        self.client = None # Initialize client attribute
        self.async_model_client = None # Initialize async client interface attribute
        self.system_prompt = None # Initialize system_prompt attribute
        # Store ChatSession objects keyed by chat_id
        self.chat_histories: dict[str, genai.ChatSession] = {} 

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
        # ------------------------

        # --- Initialize Google AI Client ---
        try:
            # Removed genai.configure()
            # Initialize the client directly with the API key
            self.client = genai.Client(api_key=settings.google_api_key)
            # Get the asynchronous interface for models from the client
            self.async_model_client = self.client.aio.models
            logger.info(f"Google GenAI client initialized successfully.")
            # Optional: Test connection or list models here if needed

        except Exception as e:
            logger.error(f"Failed to initialize Google GenAI client: {e}")
            logger.error("Please ensure GOOGLE_API_KEY is set correctly in the .env file and network is accessible.")
            self.client = None
            self.async_model_client = None

        # TODO: Initialize other components like:
        # - Memory Manager
        # - RAG Handler
        pass

    async def handle_message(self, message: str, chat_id: str, websocket):
        """Processes an incoming message and streams back responses via WebSocket."""
        if not self.async_model_client:
            logger.error("InteractionManager: Google GenAI async client not initialized.")
            await websocket.send_text("Error: AI backend is not configured.")
            return

        logger.info(f"Handling message for chat {chat_id}: {message}")

        try:
            # --- Get or Create Chat Session ---
            if chat_id not in self.chat_histories:
                logger.info(f"Creating new chat session for chat_id: {chat_id}")
                # TODO: Investigate how to pass system_prompt or initial history here if needed
                # Use client.aio.chats directly
                self.chat_histories[chat_id] = self.client.aio.chats.create(
                    model=self.live_model_name
                    # history=[] # Can potentially initialize history here?
                    # system_instruction=self.system_prompt # Can this be passed?
                )
            
            chat_session = self.chat_histories[chat_id]
            # ----------------------------------

            # --- Send message using Chat Session (manages history internally) ---
            logger.debug(f"Sending message to chat session for {chat_id}: {message}")
            # Need to await the call to send_message_stream before iterating
            stream = await chat_session.send_message_stream(message)
            # ------------------------------------------------------------------

            # Accumulate response and stream back to WebSocket client
            full_response = ""
            async for chunk in stream: # Iterate over the awaited async generator
                # TODO: Better error handling for chunks/stream errors
                if chunk.text:
                    await websocket.send_text(chunk.text)
                    full_response += chunk.text
            logger.debug(f"Finished streaming response for {chat_id}.")
 
            # No need to manually append model response, ChatSession handles it.

        except Exception as e:
            logger.error(f"Error handling message for chat {chat_id}: {e}")
            await websocket.send_text(f"Error processing message: {e}")

async def cleanup_interaction(interaction_manager):
    # TODO: Implement cleanup logic here
    pass
