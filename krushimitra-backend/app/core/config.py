"""Application settings, loaded from environment / .env.

One place to read config. Secrets (Anthropic, Bhashini) live here server-side — never in the app.
`use_mocks` is the master switch: when True (or when a provider key is missing) the swappable
services fall back to their mock implementation, so the backend runs end-to-end with zero keys.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "KrushiMitra AI Backend"
    env: str = "dev"

    # --- Database ---
    # SQLite by default so the backend runs with zero setup — a farmer-facing MVP should not
    # require a Postgres install before the first login works. Every model is plain SQLAlchemy,
    # so production switches to Postgres+pgvector by setting DATABASE_URL and nothing else.
    # The one Postgres-only column (KbChunk.embedding) falls back to JSON on SQLite; RAG is not
    # built yet, so nothing depends on vector search today.
    database_url: str = "sqlite:///./data/krushimitra.db"

    # --- Auth ---
    # No SMS provider is wired yet, so OTP is not really sent. In dev any phone + DEV_OTP logs in.
    # `auth_otp_is_real` is surfaced on /health so "is the login real?" is never guessed — same
    # honesty rule as the vision badge. Wire an SMS/WhatsApp provider before launch.
    dev_otp: str = "123456"
    sms_provider: str | None = None
    jwt_secret: str = "dev-secret-change-me"
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30  # 30 days (farmers won't re-login often)

    # --- Object storage ---
    s3_bucket: str = "krushimitra-images"
    s3_region: str = "ap-south-1"
    s3_endpoint_url: str | None = None  # set for MinIO/local

    # --- AI / external providers (all optional; absence => mock) ---
    anthropic_api_key: str | None = None
    # Default per Anthropic guidance; switch to a cheaper model (e.g. claude-haiku-4-5)
    # later if cost/latency matters at scale.
    anthropic_model: str = "claude-opus-5-5"
    bhashini_api_key: str | None = None
    openweather_api_key: str | None = None

    # --- Self-hosted TEXT model for the copilot (OpenAI-compatible) ---
    # Separate from the vision endpoint on purpose: a text-only model (Gemma 3 1B, Llama 3 8B,
    # Qwen 2.5 7B...) can serve the chatbot and CANNOT serve /vision. Keeping them as two
    # settings stops a text endpoint being pointed at image analysis by accident.
    # Opt-in by presence, like everything else.
    llm_base_url: str | None = None             # e.g. http://10.0.0.5:11434/v1
    llm_api_key: str | None = None
    llm_model: str = "gemma-3-1b-it"
    llm_timeout_s: float = 60.0
    llm_verify_ssl: bool = True                 # see vision_verify_ssl
    llm_max_tokens: int = 700

    # --- Self-hosted vision model (OpenAI-compatible: vLLM / SGLang / Ollama / TGI) ---
    # Gemma 3 at 4B/12B/27B is multimodal (shared SigLIP vision encoder). Gemma 3 *1B is
    # text-only* and cannot diagnose an image at all. Qwen2.5-VL, InternVL etc. also work
    # through this same adapter — it only assumes the OpenAI chat-completions shape.
    #
    # Opt-in is by presence: set VISION_BASE_URL and vision goes live, independent of
    # USE_MOCKS (which exists so the backend boots with zero keys). VISION_PROVIDER=mock
    # forces the mock back on for testing. GET /health reports which one is actually serving.
    vision_base_url: str | None = None          # e.g. http://10.0.0.5:8000/v1
    vision_api_key: str | None = None
    vision_model: str = "gemma-3-27b-it"
    vision_timeout_s: float = 90.0
    # Some servers (vLLM, SGLang) honour JSON mode; Ollama and older TGI reject the field.
    # We send it when True and transparently retry without it on a 400.
    vision_json_mode: bool = True
    vision_provider: str = "auto"               # auto | mock | self_hosted | claude
    # Set False ONLY for an internal endpoint with a self-signed certificate (the `curl -k`
    # case). It disables TLS verification, so anyone on the path could read the crop photos
    # going out and alter the diagnosis coming back. Acceptable on a UAT box inside a company
    # network; never acceptable once real farmers' photos travel over it.
    vision_verify_ssl: bool = True

    # --- Weather (OpenWeatherMap free tier: /weather + /forecast) ---
    # Key is server-only. Opt-in by presence, like vision: set OPENWEATHER_API_KEY and forecasts
    # go live. WEATHER_PROVIDER=mock forces sample data back on for testing.
    weather_provider: str = "auto"              # auto | mock | openweather
    weather_timeout_s: float = 12.0

    # --- Mandi prices (data.gov.in / Agmarknet) ---
    # Free key from data.gov.in. Opt-in by presence, like the others.
    # NOTE: that API serves only the CURRENT day — there is no history to query — so every board
    # we fetch is appended to market_history_dir. Trends come from what we have accumulated, and
    # a fresh install honestly reports "trend unknown" rather than guessing a direction.
    datagov_api_key: str | None = None
    market_provider: str = "auto"               # auto | mock | agmarknet
    market_timeout_s: float = 15.0
    market_history_enabled: bool = True
    market_history_dir: str = "data/market"
    # Rupees per quintal per km, used to turn a mandi price into a NET realisation. A ~5 t hired
    # tempo at roughly Rs 30/km works out near this. Farmer-overridable per request.
    transport_rate_per_qtl_km: float = 0.6

    # Below this confidence the endpoint ABSTAINS — it reports "not identified" and gives no
    # treatment, rather than naming a disease it isn't sure about. This is the product promise.
    vision_min_confidence: float = 0.55

    # Every diagnosed photo + its prediction is kept, so the proprietary field dataset starts
    # accumulating from the first farmer. This is the data moat (see docs/DATASET.md).
    capture_enabled: bool = True
    capture_dir: str = "data/captures"

    # Master switch. Even if False, a missing provider key still forces that service to mock.
    use_mocks: bool = True

    @property
    def self_hosted_llm_live(self) -> bool:
        """Presence of LLM_BASE_URL turns the self-hosted copilot on, independent of USE_MOCKS."""
        return bool(self.llm_base_url)

    @property
    def llm_live(self) -> bool:
        return not self.use_mocks and bool(self.anthropic_api_key)

    @property
    def active_copilot_provider(self) -> str:
        if self.self_hosted_llm_live:
            return f"selfhosted:{self.llm_model}"
        if self.llm_live:
            return f"claude:{self.anthropic_model}"
        return "mock"

    @property
    def voice_live(self) -> bool:
        return not self.use_mocks and bool(self.bhashini_api_key)

    @property
    def self_hosted_vision_live(self) -> bool:
        if self.vision_provider in ("mock", "claude"):
            return False
        return bool(self.vision_base_url)

    @property
    def claude_vision_live(self) -> bool:
        if self.vision_provider in ("mock", "self_hosted"):
            return False
        return not self.use_mocks and bool(self.anthropic_api_key)

    @property
    def auth_otp_is_real(self) -> bool:
        return bool(self.sms_provider)

    @property
    def weather_live(self) -> bool:
        if self.weather_provider == "mock":
            return False
        return bool(self.openweather_api_key)

    @property
    def active_weather_provider(self) -> str:
        return "openweather" if self.weather_live else "mock"

    @property
    def market_live(self) -> bool:
        if self.market_provider == "mock":
            return False
        return bool(self.datagov_api_key)

    @property
    def active_market_provider(self) -> str:
        return "agmarknet" if self.market_live else "mock"

    @property
    def active_vision_provider(self) -> str:
        """What is actually serving /vision/diagnose — surfaced on /health so it is never a mystery."""
        if self.self_hosted_vision_live:
            return f"self_hosted:{self.vision_model}"
        if self.claude_vision_live:
            return f"claude:{self.anthropic_model}"
        return "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
