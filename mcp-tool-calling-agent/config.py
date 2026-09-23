"""
config.py
---------
Centralized configuration loading from environment variables.

Usage:
    from config import settings
    print(settings.llm_provider)
"""

import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """All configuration values loaded from environment."""

    # LLM
    llm_provider: str
    llm_model: str
    openai_api_key: str
    anthropic_api_key: str
    openrouter_api_key: str
    openrouter_base_url: str

    # Mode
    demo_mode: bool

    # Data paths
    data_dir: str
    documents_dir: str

    # MCP server
    mcp_server_host: str
    mcp_server_port: int

    # Logging
    log_level: str


def load_settings() -> Settings:
    """Load and validate settings from environment variables."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "openrouter").lower(),
        llm_model=os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        demo_mode=os.getenv("DEMO_MODE", "true").lower() == "true",
        data_dir=os.getenv("DATA_DIR", "data"),
        documents_dir=os.getenv("DOCUMENTS_DIR", "documents"),
        mcp_server_host=os.getenv("MCP_SERVER_HOST", "localhost"),
        mcp_server_port=int(os.getenv("MCP_SERVER_PORT", "8000")),
        log_level=log_level,
    )


# Module-level singleton
settings = load_settings()
