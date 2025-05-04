import os
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional

# Determine the project root directory dynamically
# __file__ is the path to the current file (config.py)
# os.path.dirname gets the directory ('core')
# Repeat os.path.dirname to go up levels ('allin_app', then project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')

# Load .env file from the determined project root
load_dotenv(dotenv_path=ENV_PATH)

class Settings(BaseSettings):
    # Use Field(..., env=...) for required fields read from environment
    google_api_key: Optional[str] = Field(None, validation_alias="GOOGLE_API_KEY")
    mem0_api_key: Optional[str] = Field(None, validation_alias="MEM0_API_KEY")
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    # Add other settings as needed
    # Example: database_url: str = Field(None, validation_alias="DATABASE_URL")

    class Config:
        env_file = ENV_PATH
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from environment
        # If using validation_alias, need to allow population by field name too
        allow_population_by_field_name = True

# Create a single instance of the settings
settings = Settings()

# Example usage (within other modules):
# from allin_app.core.config import settings
# api_key = settings.google_api_key
# print(f"Loaded Google API Key: {api_key[:5]}...{api_key[-4:]}")
# print(f"Log Level: {settings.log_level}")
