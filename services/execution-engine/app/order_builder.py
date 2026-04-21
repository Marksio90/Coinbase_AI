"""Order payload construction for Coinbase Advanced Trade requests."""

from __future__ import annotations

from typing import Any

from common.schemas import TradeIntent


def build_coinbase_order_payload(intent: TradeIntent) -> dict[str, Any]:
    """Build Coinbase-style payload from normalized TradeIntent."""

    payload: dict[str, Any] = {
        "product_id": intent.symbol,
        "side": intent.side.value,
        "client_order_id": intent.intent_id,
    }

    if intent.order_type.value == "MARKET":
        payload["order_configuration"] = {
            "market_market_ioc": {"base_size": str(intent.quantity)}
        }
    else:
        if intent.limit_price is None:
            raise ValueError("limit_price is required for LIMIT order")
        payload["order_configuration"] = {
            "limit_limit_gtc": {
                "base_size": str(intent.quantity),
                "limit_price": str(intent.limit_price),
                "post_only": False,
            }
        }
    return payload
