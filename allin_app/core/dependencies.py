# Shared dependencies for the Allin AI Assistant

from allin_app.core.interaction import InteractionManager

# --- Global instances (Centralized) ---
# Initialize InteractionManager once globally
interaction_manager = InteractionManager()

def get_interaction_manager():
    """Dependency function to get the global InteractionManager instance."""
    return interaction_manager
# ---------------------------------------
