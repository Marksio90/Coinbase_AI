"""Execution service with strict risk gate and exchange abstraction."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from common.logger import setup_logging
from common.schemas import ExecutionRequest, ExecutionResponse
from common.utils import async_retry

from .order_builder import build_coinbase_order_payload

logger = setup_logging("execution-engine")


class ExchangeGateway(Protocol):
    async def submit_order(self, payload: dict) -> str:
        """Submit order payload to exchange and return exchange order id."""


@dataclass
class SimulatedCoinbaseGateway:
    """Deterministic fallback gateway for non-production environments."""

    async def submit_order(self, payload: dict) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"sim-{payload['client_order_id'][:8]}-{timestamp}"


class ExecutionService:
    """Risk-aware execution orchestrator."""

    def __init__(self, gateway: ExchangeGateway | None = None) -> None:
        self.gateway = gateway or SimulatedCoinbaseGateway()
        self.allowed_callers = {
            caller.strip() for caller in os.getenv("EXECUTION_ALLOWED_CALLERS", "orchestrator").split(",")
        }

    async def execute(self, request: ExecutionRequest, caller: str) -> ExecutionResponse:
        if caller not in self.allowed_callers:
            logger.warning("execution_rejected_unauthorized_caller", extra={"caller": caller})
            return ExecutionResponse(
                accepted=False,
                status="REJECTED",
                reason="caller is not authorized to submit executable orders",
            )

        if not request.risk_decision.approved:
            logger.warning(
                "execution_rejected_by_risk",
                extra={
                    "intent_id": request.intent.intent_id,
                    "veto_reason": request.risk_decision.veto_reason,
                },
            )
            return ExecutionResponse(
                accepted=False,
                status="REJECTED",
                reason="risk decision denied execution",
            )

        payload = build_coinbase_order_payload(request.intent)

        async def _submit() -> str:
            return await self.gateway.submit_order(payload)

        exchange_order_id = await async_retry(_submit, attempts=3, base_delay=0.25, max_delay=2.0)
        logger.info(
            "execution_accepted",
            extra={
                "intent_id": request.intent.intent_id,
                "exchange_order_id": exchange_order_id,
                "symbol": request.intent.symbol,
            },
        )
        return ExecutionResponse(
            accepted=True,
            status="ACCEPTED",
            exchange_order_id=exchange_order_id,
            reason=None,
        )
