import logging
import os
from typing import List, Literal

logger = logging.getLogger(__name__)

_WEAK_JWT_SECRETS = {
    "changeme",
    "change-me-in-production",
    "secret",
    "your-secret-key",
    "your_secret_key",
}
_JWT_MIN_LENGTH = 32

# Read DEBUG early (before Settings class) so _validate_jwt_secret can use it
_IS_DEBUG = os.getenv("DEBUG", "false").lower() == "true"


def _validate_jwt_secret(value: str) -> str:
    """In production (DEBUG=false): raise ValueError for weak/short secrets.
    In development (DEBUG=true): emit a warning but allow startup to continue.
    """
    is_weak = (not value) or (value.lower() in _WEAK_JWT_SECRETS) or (len(value) < _JWT_MIN_LENGTH)
    if not is_weak:
        return value

    msg = (
        f"JWT_SECRET is insecure (value='{value[:8]}...', len={len(value)}). "
        "Set a unique random secret of at least 32 characters via the JWT_SECRET env var."
    )
    if _IS_DEBUG:
        # Dev/test mode: warn and continue
        logger.warning(f"[DEV] {msg} — continuing because DEBUG=true")
        return value
    # Production mode: hard fail
    raise ValueError(msg)


class Settings:
    APP_NAME: str = "CyberAI Assessment API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = _IS_DEBUG

    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemma4:latest")
    SECURITY_MODEL_NAME: str = os.getenv("SECURITY_MODEL_NAME", os.getenv("MODEL_NAME", "gemma4:latest"))
    # Ollama — OpenAI-compatible local inference for Gemma 3/4
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://ollama:11434")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "-1"))
    LOCAL_ONLY_MODE: bool = os.getenv("LOCAL_ONLY_MODE", "false").lower() == "true"
    PREFER_LOCAL: bool = os.getenv("PREFER_LOCAL", "true").lower() == "true"
    REQUIRED_MODEL_IDS: str = os.getenv(
        "REQUIRED_MODEL_IDS",
        "gemma4:latest",
    )

    CLOUD_LLM_API_URL: str = os.getenv("CLOUD_LLM_API_URL", "https://open-claude.com/v1")
    CLOUD_MODEL_NAME: str = os.getenv("CLOUD_MODEL_NAME", "gemini-3.1-pro-preview")
    CLOUD_API_KEYS: str = os.getenv("CLOUD_API_KEYS", "")

    # Google AI Studio (Gemini free-tier) — used as last-resort cloud fallback
    GOOGLE_AI_STUDIO_API_KEY: str = os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")
    GOOGLE_AI_STUDIO_MODEL: str = os.getenv("GOOGLE_AI_STUDIO_MODEL", "gemini-2.0-flash")
    GOOGLE_AI_STUDIO_URL: str = os.getenv(
        "GOOGLE_AI_STUDIO_URL",
        "https://generativelanguage.googleapis.com/v1beta",
    )

    ISO_DOCS_PATH: str = os.getenv("ISO_DOCS_PATH", "/data/iso_documents")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "/data/vector_store")
    DATA_PATH: str = os.getenv("DATA_PATH", "/data")

    # JWT_SECRET: validated at class load time. Weak values raise in prod, warn in dev.
    JWT_SECRET: str = _validate_jwt_secret(
        os.getenv("JWT_SECRET", "change-me-in-production")
    )
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    RATE_LIMIT_CHAT: str = os.getenv("RATE_LIMIT_CHAT", "10/minute")
    RATE_LIMIT_ASSESS: str = os.getenv("RATE_LIMIT_ASSESS", "3/minute")
    RATE_LIMIT_BENCHMARK: str = os.getenv("RATE_LIMIT_BENCHMARK", "5/minute")

    # Local model inference on CPU can take 10-30 minutes for complex prompts
    INFERENCE_TIMEOUT: int = int(os.getenv("INFERENCE_TIMEOUT", "1800"))
    CLOUD_TIMEOUT: int = int(os.getenv("CLOUD_TIMEOUT", "120"))
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))

    # Step 3 — hybrid assessment pipeline.
    # ASSESSMENT_MODE: default mode for /iso27001/assess when the request body
    # does not specify one. "hybrid" = SecurityLM summary → local mid-size draft
    # → cloud narrative; "local" = no cloud calls; "cloud" = legacy cloud-only.
    ASSESSMENT_MODE: Literal["cloud", "local", "hybrid"] = os.getenv(
        "ASSESSMENT_MODE", "hybrid"
    ).lower()  # type: ignore[assignment]
    # Token cap for the SecurityLM evidence-summary step (Step 3).
    EVIDENCE_SUMMARY_TOKENS: int = int(os.getenv("EVIDENCE_SUMMARY_TOKENS", "256"))
    # Step 8 docker RAM guard threshold (GB). Defined here so Step 8 only reads.
    LOCAL_RAM_GUARD_GB: float = float(os.getenv("LOCAL_RAM_GUARD_GB", "20.0"))

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
        if "*" in self.CORS_ORIGINS:
            warnings.append("CORS_ORIGINS='*' — should restrict to specific domains")
        return warnings


settings = Settings()
