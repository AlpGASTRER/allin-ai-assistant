# Manages long-term memory using mem0ai

from mem0 import MemoryClient # Use MemoryClient for cloud service
from ..core.logging_config import logger # Use relative import for logger
from ..core.config import settings # Import settings for API keys

class MemoryManager:
    def __init__(self):
        """Initializes the Memory Manager."""
        logger.info("Initializing MemoryManager with MemoryClient...")
        self.memory_client = None # Rename attribute for clarity
        try:
            # Initialize the MemoryClient
            # Pass MEM0_API_KEY if available, otherwise rely on OPENAI_API_KEY env var or defaults.
            init_args = {}
            # Access the correct snake_case attribute name from the Settings object
            if settings.mem0_api_key:
                init_args['api_key'] = settings.mem0_api_key
                logger.info("Using MEM0_API_KEY from environment for MemoryClient.")
            else:
                # According to docs/errors, API key is required for MemoryClient, either via arg or env var.
                # Throw an error if not provided, rather than letting it fail later.
                raise ValueError("MEM0_API_KEY is required but not found in environment settings for MemoryClient.")

            self.memory_client = MemoryClient(**init_args) # Instantiate MemoryClient
            logger.info("MemoryClient initialized successfully.")
            # Note: Underlying operations within Mem0 might still require OPENAI_API_KEY env var
            # if using default OpenAI models for embedding/summarization.
        except Exception as e:
            logger.error(f"Failed to initialize MemoryClient: {e}", exc_info=True)
            # Keep self.memory_client as None if init fails

    async def add_memory(self, user_id: str, role: str, content: str):
        """Adds a piece of content to the memory for a specific user.
        
        Args:
            user_id: The unique identifier for the user.
            role: The role of the message sender ('user' or 'assistant').
            content: The text content of the message.
        """
        if not self.memory_client:
            logger.error("Mem0 client not available. Cannot add memory.")
            return
        
        try:
            # Format message according to Mem0 documentation
            message_to_add = [{
                "role": role,
                "content": content
            }]
            # TODO: Determine if user_id should map to mem0's user_id or agent_id
            logger.debug(f"Adding memory for user {user_id}: {content[:50]}...")
            # Pass the formatted message list
            response = self.memory_client.add(message_to_add, user_id=user_id)
            logger.info(f"Memory added for user {user_id}. Response: {response}")
        except Exception as e:
            logger.error(f"Failed to add memory for user {user_id}: {e}", exc_info=True)

    async def get_relevant_memory(self, user_id: str, query: str, limit: int = 5) -> list[str]:
        """Retrieves relevant memories for a user based on a query."""
        if not self.memory_client:
            logger.error("Mem0 client not available. Cannot retrieve memory.")
            return []
        
        try:
            logger.debug(f"Searching memory for user {user_id} with query: {query[:50]}...")
            # Use the renamed client attribute
            memories = self.memory_client.search(query=query, user_id=user_id, limit=limit)
            logger.info(f"Found {len(memories)} relevant memories for user {user_id}.")
            # Extract just the text content from the memory objects
            return [memory.get('text', '') for memory in memories if 'text' in memory]
        except Exception as e:
            logger.error(f"Failed to search memory for user {user_id}: {e}", exc_info=True)
            return []

    # TODO: Add other methods as needed (e.g., get_all_memory, delete_memory)

# Example usage (for testing purposes)
# async def main():
#     manager = MemoryManager()
#     if manager.memory_client:
#         await manager.add_memory(user_id="test_user", role="user", content="My favorite color is blue.")
#         relevant = await manager.get_relevant_memory(user_id="test_user", query="What is my favorite color?")
#         print("Relevant memory:", relevant)
# 
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())
