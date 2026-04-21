"""Risk rules and decision logic."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from common.schemas import RiskDecision, TradeIntent


@dataclass(frozen=True)
class RiskConfig:
    allowed_symbols: set[str]
    max_notional_usd: Decimal
    max_ai_confidence_for_auto: float


class RiskRuleEngine:
    """Stateless risk rule evaluator with hard veto semantics."""

    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    def evaluate(self, intent: TradeIntent) -> RiskDecision:
        if intent.symbol not in self._config.allowed_symbols:
            return RiskDecision(
                approved=False,
                veto_reason=f"symbol {intent.symbol} not whitelisted",
                risk_score=1.0,
                max_allowed_notional_usd=self._config.max_notional_usd,
            )

        inferred_notional = intent.quantity * (intent.limit_price or Decimal("0"))
        if intent.order_type.value == "MARKET" and inferred_notional == 0:
            # Safety guard: if no price for market order, route for manual approval.
            return RiskDecision(
                approved=False,
                veto_reason="market order requires pricing context for notional checks",
                risk_score=0.95,
                max_allowed_notional_usd=self._config.max_notional_usd,
            )

        if inferred_notional > self._config.max_notional_usd:
            return RiskDecision(
                approved=False,
                veto_reason=(
                    f"notional {inferred_notional} exceeds max {self._config.max_notional_usd}"
                ),
                risk_score=0.98,
                max_allowed_notional_usd=self._config.max_notional_usd,
            )

        if intent.proposed_by_ai and intent.confidence > self._config.max_ai_confidence_for_auto:
            return RiskDecision(
                approved=False,
                veto_reason=(
                    "ai confidence too high for unattended execution; requires human confirmation"
                ),
                risk_score=0.8,
                max_allowed_notional_usd=self._config.max_notional_usd,
            )

        risk_score = min(float(inferred_notional / self._config.max_notional_usd), 1.0)
        return RiskDecision(
            approved=True,
            veto_reason=None,
            risk_score=risk_score,
            max_allowed_notional_usd=self._config.max_notional_usd,
        )
