"""Configuration settings for the Gemini Review MCP server."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


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
    
    # Workflow Configuration
    auto_review: bool = Field(
        default=True,
        env="AUTO_REVIEW",
        description="Automatically review generated code with Gemini"
    )
    auto_improve: bool = Field(
        default=True,
        env="AUTO_IMPROVE", 
        description="Automatically improve code based on review feedback"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Create global settings instance
settings = Settings()