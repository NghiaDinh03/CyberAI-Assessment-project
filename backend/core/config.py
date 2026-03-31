import os
from typing import List


class Settings:
    APP_NAME: str = "CyberAI Assessment API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    LOCALAI_URL: str = os.getenv("LOCALAI_URL", "http://localai:8080")
    # Default to 8B to avoid OOM in LocalAI containers (12–16GB). 70B requires much higher RAM.
    MODEL_NAME: str = os.getenv("MODEL_NAME", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")
    SECURITY_MODEL_NAME: str = os.getenv("SECURITY_MODEL_NAME", os.getenv("MODEL_NAME", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "-1"))
    LOCAL_ONLY_MODE: bool = os.getenv("LOCAL_ONLY_MODE", "false").lower() == "true"
    # Prefer running on LocalAI first to keep data on-prem (cloud as fallback only if needed)
    PREFER_LOCAL: bool = os.getenv("PREFER_LOCAL", "true").lower() == "true"
    REQUIRED_MODEL_IDS: str = os.getenv(
        "REQUIRED_MODEL_IDS",
        "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf,SecurityLLM-7B-Q4_K_M.gguf",
    )

    CLOUD_LLM_API_URL: str = os.getenv("CLOUD_LLM_API_URL", "https://open-claude.com/v1")
    CLOUD_MODEL_NAME: str = os.getenv("CLOUD_MODEL_NAME", "gemini-3-flash-preview")
    CLOUD_API_KEYS: str = os.getenv("CLOUD_API_KEYS", "")

    ISO_DOCS_PATH: str = os.getenv("ISO_DOCS_PATH", "/data/iso_documents")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "/data/vector_store")
    DATA_PATH: str = os.getenv("DATA_PATH", "/data")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    RATE_LIMIT_CHAT: str = os.getenv("RATE_LIMIT_CHAT", "10/minute")
    RATE_LIMIT_ASSESS: str = os.getenv("RATE_LIMIT_ASSESS", "3/minute")
    RATE_LIMIT_BENCHMARK: str = os.getenv("RATE_LIMIT_BENCHMARK", "5/minute")

    INFERENCE_TIMEOUT: int = int(os.getenv("INFERENCE_TIMEOUT", "120"))
    CLOUD_TIMEOUT: int = int(os.getenv("CLOUD_TIMEOUT", "60"))
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def cloud_api_key_list(self) -> List[str]:
        keys = []
        if self.CLOUD_API_KEYS:
            for k in self.CLOUD_API_KEYS.split(","):
                k = k.strip()
                if k and k not in keys and k != "your_open_claude_api_key_here":
                    keys.append(k)
        return keys

    @property
    def required_model_ids(self) -> List[str]:
        return [m.strip() for m in self.REQUIRED_MODEL_IDS.split(",") if m.strip()]

    def validate(self):
        warnings = []
        if not self.cloud_api_key_list:
            warnings.append("No CLOUD_API_KEYS configured — will fallback to LocalAI")
        if self.JWT_SECRET == "change-me-in-production":
            warnings.append("JWT_SECRET not changed — not safe for production")
        if "*" in self.CORS_ORIGINS:
            warnings.append("CORS_ORIGINS='*' — should restrict to specific domains")
        return warnings


settings = Settings()
