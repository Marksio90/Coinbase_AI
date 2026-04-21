"""Risk engine service enforcing hard veto before execution."""

from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from common.config import get_config
from common.logger import setup_logging
from common.schemas import TradeIntent

from .rules import RiskConfig, RiskRuleEngine

logger = setup_logging("risk-engine")


def _load_config() -> RiskConfig:
    cfg = get_config()
    return RiskConfig(
        allowed_symbols=set(cfg.risk.allowed_symbols),
        max_notional_usd=Decimal(str(cfg.risk.max_notional_usd)),
        max_ai_confidence_for_auto=cfg.risk.max_ai_confidence_auto,
    )


engine = RiskRuleEngine(_load_config())
app = FastAPI(title="risk-engine", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "risk-engine"}


@app.post("/v1/risk/evaluate")
def evaluate_intent(intent: TradeIntent) -> JSONResponse:
    decision = engine.evaluate(intent)
    logger.info(
        "risk_evaluation_completed",
        extra={
            "intent_id": intent.intent_id,
            "symbol": intent.symbol,
            "approved": decision.approved,
            "risk_score": decision.risk_score,
            "veto_reason": decision.veto_reason,
        },
    )
    status_code = 200 if decision.approved else 202
    return JSONResponse(status_code=status_code, content=decision.model_dump(mode="json"))
