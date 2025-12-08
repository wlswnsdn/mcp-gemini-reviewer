"""Configuration settings for the Gemini Review MCP server."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    dotenv_path = project_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
        print(f"Loaded .env from: {dotenv_path}")
    else:
        print(f"No .env file found at: {dotenv_path}")
except ImportError:
    print("python-dotenv not available, using system environment variables only")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")

    # Model Configuration
    gemini_model: str = Field(
        default="gemini-2.0-flash-001",
        env="GEMINI_MODEL"
    )
    gemini_model_fallback: str = Field(
        default="gemini-2.0-flash-001",
        env="GEMINI_MODEL_FALLBACK"
    )

    # Server Configuration
    mcp_server_name: str = Field(
        default="gemini-review",
        env="MCP_SERVER_NAME"
    )
    mcp_server_version: str = Field(
        default="0.1.0",
        env="MCP_SERVER_VERSION"
    )

    # Request Configuration
    max_tokens: int = Field(default=4096, env="MAX_TOKENS")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Create global settings instance
try:
    settings = Settings()
    # Validate critical settings
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not set or is using default placeholder value")
    print(f"Settings loaded successfully - Gemini model: {settings.gemini_model}")
except Exception as e:
    print(f"Error loading settings: {e}")
    raise