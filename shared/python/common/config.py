"""Production-grade typed configuration with lazy singleton loading."""

from __future__ import annotations

from threading import Lock
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    AnyUrl,
    BaseModel,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from .logger import setup_logging

logger = setup_logging("config")


class AppConfig(BaseSettings):
    """Global runtime configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    env: Literal["development", "staging", "production"] = "development"
    deployment_name: str = "coinbase-ai-platform-dev"
    timezone: str = "UTC"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", validation_alias="LOG_LEVEL"
    )

    @field_validator("deployment_name")
    @classmethod
    def deployment_name_not_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("APP_DEPLOYMENT_NAME cannot be empty")
        return cleaned


class CoinbaseConfig(BaseSettings):
    """Coinbase Advanced Trade connectivity settings."""

    model_config = SettingsConfigDict(env_prefix="COINBASE_", extra="ignore")

    api_base_url: AnyHttpUrl = "https://api.coinbase.com"
    ws_url: AnyUrl = "wss://advanced-trade-ws.coinbase.com"
    api_key: SecretStr = Field(default=SecretStr(""))
    api_private_key: SecretStr = Field(default=SecretStr(""))
    portfolio_id: str = ""
    http_timeout_seconds: int = 10

    @field_validator("http_timeout_seconds")
    @classmethod
    def timeout_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("COINBASE_HTTP_TIMEOUT_SECONDS must be > 0")
        return value


class TradingConfig(BaseSettings):
    """Trading policy and feature flag settings."""

    model_config = SettingsConfigDict(env_prefix="TRADING_", extra="ignore")

    mode: Literal["paper", "live"] = Field(default="paper", validation_alias="TRADING_MODE")
    default_quote_currency: str = "USD"
    allowed_symbols: list[str] = Field(default_factory=lambda: ["BTC-USD", "ETH-USD"])
    default_timeframe: str = "1m"
    max_open_positions: int = 5
    enable_ai: bool = Field(default=True, validation_alias="ENABLE_AI")
    enable_trading: bool = Field(default=True, validation_alias="ENABLE_TRADING")
    enable_execution: bool = Field(default=False, validation_alias="ENABLE_EXECUTION")

    @field_validator("allowed_symbols", mode="before")
    @classmethod
    def parse_symbols(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            parsed = [item.strip().upper() for item in value.split(",") if item.strip()]
            if not parsed:
                raise ValueError("TRADING_ALLOWED_SYMBOLS cannot be empty")
            return parsed
        return [symbol.strip().upper() for symbol in value if symbol.strip()]

    @field_validator("max_open_positions")
    @classmethod
    def max_positions_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("TRADING_MAX_OPEN_POSITIONS must be >= 1")
        return value


class RiskConfig(BaseSettings):
    """Risk guardrails and hard limits."""

    model_config = SettingsConfigDict(env_prefix="RISK_", extra="ignore")

    max_notional_usd: float = 1000.0
    daily_max_loss_usd: float = 500.0
    max_drawdown_pct: float = 0.10
    max_ai_confidence_auto: float = 0.92
    allowed_symbols: list[str] = Field(default_factory=lambda: ["BTC-USD", "ETH-USD"])
    check_max_retries: int = 2

    @field_validator("allowed_symbols", mode="before")
    @classmethod
    def parse_symbols(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            parsed = [item.strip().upper() for item in value.split(",") if item.strip()]
        else:
            parsed = [symbol.strip().upper() for symbol in value if symbol.strip()]
        if not parsed:
            raise ValueError("RISK_ALLOWED_SYMBOLS cannot be empty")
        return parsed

    @field_validator("max_notional_usd", "daily_max_loss_usd")
    @classmethod
    def positive_money(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("money limits must be > 0")
        return value

    @field_validator("max_drawdown_pct", "max_ai_confidence_auto")
    @classmethod
    def valid_fraction(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("fraction limits must be in [0, 1]")
        return value


class InfraConfig(BaseSettings):
    """Infrastructure connectivity settings (Redis/Postgres/API)."""

    model_config = SettingsConfigDict(extra="ignore")

    redis_host: str = Field(default="redis", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(default=0, validation_alias="REDIS_DB")
    postgres_host: str = Field(default="postgres", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="coinbase_ai", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(default="coinbase_ai_user", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres_password_example", validation_alias="POSTGRES_PASSWORD")
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8080, validation_alias="API_PORT")

    @field_validator("redis_port", "postgres_port", "api_port")
    @classmethod
    def valid_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("port value must be between 1 and 65535")
        return value

    @field_validator("redis_host", "postgres_host", "postgres_db", "postgres_user", "api_host")
    @classmethod
    def non_empty_host_values(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("infra host/user/db values cannot be empty")
        return cleaned


class OpenAIConfig(BaseSettings):
    """OpenAI model and resilience configuration."""

    model_config = SettingsConfigDict(env_prefix="OPENAI_", extra="ignore")

    base_url: AnyHttpUrl = "https://api.openai.com/v1"
    api_key: SecretStr = Field(default=SecretStr(""))
    model_primary: str = "gpt-5.1"
    model_fallback: str = "gpt-4.1-mini"
    timeout_seconds: int = 30
    max_retries: int = 3

    @field_validator("timeout_seconds", "max_retries")
    @classmethod
    def positive_ints(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("timeout/retry settings must be > 0")
        return value


class PlatformConfig(BaseModel):
    """Strongly-typed aggregate config for all services."""

    app: AppConfig
    coinbase: CoinbaseConfig
    trading: TradingConfig
    risk: RiskConfig
    infra: InfraConfig
    openai: OpenAIConfig

    @model_validator(mode="after")
    def validate_cross_constraints(self) -> "PlatformConfig":
        if self.trading.mode == "live" and not self.trading.enable_execution:
            raise ValueError("live trading requires ENABLE_EXECUTION=true")
        if self.trading.enable_execution and not self.trading.enable_trading:
            raise ValueError("ENABLE_EXECUTION requires ENABLE_TRADING=true")
        if self.trading.mode == "live" and not self.coinbase.api_key.get_secret_value().strip():
            raise ValueError("live trading requires COINBASE_API_KEY")
        if self.trading.enable_ai and not self.openai.api_key.get_secret_value().strip():
            raise ValueError("ENABLE_AI=true requires OPENAI_API_KEY")
        return self


_singleton_lock = Lock()
_singleton_instance: PlatformConfig | None = None


def _build_config() -> PlatformConfig:
    try:
        config = PlatformConfig(
            app=AppConfig(),
            coinbase=CoinbaseConfig(),
            trading=TradingConfig(),
            risk=RiskConfig(),
            infra=InfraConfig(),
            openai=OpenAIConfig(),
        )
        logger.info(
            "config_loaded",
            extra={
                "env": config.app.env,
                "deployment": config.app.deployment_name,
                "trading_mode": config.trading.mode,
                "execution_enabled": config.trading.enable_execution,
            },
        )
        return config
    except ValidationError:
        logger.exception("config_validation_error")
        raise
    except Exception:
        logger.exception("config_unexpected_error")
        raise


def get_config() -> PlatformConfig:
    """Lazy-loaded singleton config accessor for application runtime."""

    global _singleton_instance
    if _singleton_instance is not None:
        return _singleton_instance

    with _singleton_lock:
        if _singleton_instance is None:
            _singleton_instance = _build_config()
    return _singleton_instance


def reset_config_singleton() -> None:
    """Reset singleton cache (used in tests and controlled reload flows)."""

    global _singleton_instance
    with _singleton_lock:
        _singleton_instance = None
