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
        self.live_model_name = 'models/gemini-2.0-flash-live-001' 
        self.client = None # Initialize client attribute
        self.system_prompt = None # Initialize system_prompt attribute
        self.last_session_handle = None # Add state for session resumption

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

    async def process_live_message(self, live_session, message: str, websocket):
        """Processes a message within an active Live API session."""
        if not self.client:
            logger.error("InteractionManager: Google GenAI client not initialized.")
            return

        logger.info(f"Processing live message: {message}")

        try:
            # --- Send message using Live Session ---
            # Structure the message according to Live API 'turns' format
            turn = types.Content(role="user", parts=[types.Part(text=message)])
            logger.debug(f"Sending content to live session: {turn}")
            await live_session.send_client_content(turns=turn, turn_complete=True)
            # ---------------------------------------

            # --- Receive response and handle resumption ---
            logger.debug("Waiting for response from live session...")
            full_response = ""
            async for response in live_session.receive():
                # Check for session resumption updates
                if response.session_resumption_update:
                    update = response.session_resumption_update
                    if update.resumable and update.new_handle:
                        logger.info(f"Received new session resumption handle: {update.new_handle}")
                        self.last_session_handle = update.new_handle # Store the new handle

                # Process text response
                if response.text is not None:
                    text_chunk = response.text
                    await websocket.send_text(text_chunk)
                    full_response += text_chunk
                # TODO: Handle other response types if needed (e.g., audio, tool calls)

            logger.debug(f"Full response received: {full_response}")
            # ----------------------------------------

        except Exception as e:
            logger.error(f"Error processing live message: {e}")
            try:
                await websocket.send_text(f"Error: {e}")
            except Exception as ws_err:
                logger.error(f"Failed to send error via WebSocket: {ws_err}")

async def cleanup_interaction(interaction_manager):
    # TODO: Implement cleanup logic here
    pass
