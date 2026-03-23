"""
Dione AI - Configuration Settings
Pydantic-based settings with environment variable support.
"""

from pathlib import Path
from typing import Literal, Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field

# Load .env file early so all sub-settings can read from it
from dotenv import load_dotenv
load_dotenv()


class LLMSettings(BaseSettings):
    """LLM backend configuration."""
    backend: Literal["ollama", "llamacpp", "gemini", "openai", "copilot"] = "copilot"
    model: str = "claude-sonnet-4.6"
    
    # Ollama settings
    ollama_host: str = "http://127.0.0.1:11434"
    
    # llama.cpp settings
    llamacpp_path: Optional[str] = None
    
    # Cloud API settings (Gemini / OpenAI / GitHub Models)
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None  # Custom base URL for OpenAI-compatible APIs
    
    max_tokens: int = 2048
    temperature: float = 0.7

    class Config:
        env_prefix = "DIONE_LLM_"


class KnowledgeSettings(BaseSettings):
    """Knowledge graph configuration."""
    db_path: str = "./data/knowledge/dione.db"
    graph_path: str = "./data/knowledge/graph.json"

    class Config:
        env_prefix = "DIONE_KNOWLEDGE_"


class VectorStoreSettings(BaseSettings):
    """ChromaDB vector store configuration."""
    chroma_path: str = "./data/vectors"
    embedding_model: str = "all-MiniLM-L6-v2"
    collection_name: str = "dione_memory"

    class Config:
        env_prefix = "DIONE_"


class MemorySettings(BaseSettings):
    """Memory system configuration."""
    memory_path: str = "./data/memory"
    max_context_tokens: int = 4096
    summary_threshold: int = 10  # Summarize after N conversation turns

    class Config:
        env_prefix = "DIONE_"


class SentimentSettings(BaseSettings):
    """Sentiment engine configuration."""
    enabled: bool = True
    model: Literal["local", "llm"] = "local"
    urgency_threshold: float = 0.7  # Score above which message is flagged urgent
    batch_low_priority: bool = True  # Batch non-urgent messages

    class Config:
        env_prefix = "DIONE_SENTIMENT_"


class SecuritySettings(BaseSettings):
    """Security configuration."""
    sandbox_enabled: bool = True
    require_confirmation_for: List[str] = ["delete", "send", "execute"]
    max_retries: int = 3
    blocked_patterns: List[str] = [
        "rm -rf",
        "DROP TABLE",
        "FORMAT",
        "del /f /s /q",
    ]

    class Config:
        env_prefix = "DIONE_"


class ServerSettings(BaseSettings):
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8900
    debug: bool = True
    secret_key: str = "change-this-to-a-random-secret-key"
    cors_origins: List[str] = ["*"]

    class Config:
        env_prefix = "DIONE_"


class DioneSettings(BaseSettings):
    """Root configuration combining all sub-settings."""
    
    # Sub-configurations
    llm: LLMSettings = Field(default_factory=LLMSettings)
    knowledge: KnowledgeSettings = Field(default_factory=KnowledgeSettings)
    vectorstore: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    sentiment: SentimentSettings = Field(default_factory=SentimentSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

    # Paths
    base_dir: Path = Path(".")
    plugins_dir: Path = Path("./server/plugins/builtin")
    data_dir: Path = Path("./data")

    class Config:
        env_prefix = "DIONE_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def ensure_directories(self):
        """Create required data directories if they don't exist."""
        dirs = [
            self.data_dir,
            self.data_dir / "knowledge",
            self.data_dir / "vectors",
            self.data_dir / "memory",
            self.data_dir / "logs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


# Singleton settings instance
_settings: Optional[DioneSettings] = None


def get_settings() -> DioneSettings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = DioneSettings()
        _settings.ensure_directories()
    return _settings
