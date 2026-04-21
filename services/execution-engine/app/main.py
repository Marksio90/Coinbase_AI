"""Execution engine API service."""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException

from common.schemas import ExecutionRequest, ExecutionResponse

from .execution_service import ExecutionService

service = ExecutionService()
app = FastAPI(title="execution-engine", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "execution-engine"}


@app.post("/v1/execution/submit", response_model=ExecutionResponse)
async def submit_execution(
    request: ExecutionRequest,
    x_caller_service: str = Header(default="unknown", convert_underscores=False),
) -> ExecutionResponse:
    if request.intent.proposed_by_ai and x_caller_service == "ai-agent":
        # Critical separation-of-duties control.
        raise HTTPException(
            status_code=403,
            detail="ai-agent is not allowed to submit directly to execution-engine",
        )

    response = await service.execute(request, caller=x_caller_service)
    if not response.accepted:
        raise HTTPException(status_code=409, detail=response.reason)
    return response
