# Placeholder for Core Interaction Logic (Phase 2)
from google import genai
from google.genai import types
from .config import settings  # Use relative import for config
from .logging_config import logger # Use relative import for logger
import asyncio

class InteractionManager:
    def __init__(self):
        """Initializes the Interaction Manager, including the Google AI client."""
        logger.info("Initializing InteractionManager...")
        # Change to a model confirmed to support 'generateContent'
        self.live_model_name = 'models/gemini-2.0-flash-001' 
        self.client = None # Initialize client attribute
        self.async_model_client = None # Initialize async client interface attribute

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
        # - System Prompt Loader
        pass

    async def handle_message(self, message: str, chat_id: str, websocket):
        """Processes an incoming message and streams back responses via WebSocket."""
        if not self.async_model_client:
            logger.error("InteractionManager: Google GenAI async client not initialized.")
            await websocket.send_text("Error: AI backend is not configured.")
            return

        logger.info(f"Handling message for chat {chat_id}: {message}")

        try:
            # TODO: Determine if RAG is needed.
            # TODO: Incorporate chat history/context management (Phase 2 Task 2/3).
            # TODO: Use system prompt.

            # --- Basic Streaming Example --- 
            logger.debug(f"Sending to model '{self.live_model_name}': {message}")
            stream = await self.async_model_client.generate_content_stream(
                model=self.live_model_name,
                contents=[message] 
                # TODO: Add system_instruction, tools=[types.Tool(...)] etc. later
            )

            # Stream response chunks back to the client
            async for chunk in stream:
                if chunk.text:
                    await websocket.send_text(chunk.text)
            logger.debug(f"Finished streaming response for chat {chat_id}")
            # ------------------------------- 

        except Exception as e:
            logger.error(f"Error during model interaction for chat {chat_id}: {e}")
            await websocket.send_text(f"Error processing message: {e}")


# Consider using FastAPI's dependency injection for managing this instance
# This basic instantiation might work for simple cases but isn't ideal for FastAPI
# interaction_manager = InteractionManager()
