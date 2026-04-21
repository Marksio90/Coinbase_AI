"""Canonical cross-service request and response schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class TradeIntent(BaseModel):
    """Intent produced by strategy/orchestrator, never sent directly to exchange."""

    intent_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Field(gt=Decimal("0"))
    limit_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    confidence: float = Field(ge=0.0, le=1.0)
    strategy_name: str
    proposed_by_ai: bool = True

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if "-" not in cleaned:
            raise ValueError("symbol must be product format BASE-QUOTE, e.g. BTC-USD")
        return cleaned


class RiskDecision(BaseModel):
    """Decision from risk-engine; can veto any trade."""

    approved: bool
    veto_reason: str | None = None
    risk_score: float = Field(ge=0.0, le=1.0)
    max_allowed_notional_usd: Decimal = Field(ge=Decimal("0"))
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionRequest(BaseModel):
    """Only execution-engine can transform this into an exchange order."""

    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    intent: TradeIntent
    risk_decision: RiskDecision


class ExecutionResponse(BaseModel):
    """Execution result returned to orchestrator."""

    accepted: bool
    status: str
    exchange_order_id: str | None = None
    reason: str | None = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
