"""Talab HTTP routes. Stub: returns 501 for order intake until month-4 launch."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from jumlaos.core.context import RequestContext
from jumlaos.core.deps import current_context, require_module

router = APIRouter()


@router.get("/order-intakes", status_code=200)
async def list_intakes(
    ctx: RequestContext = Depends(require_module("talab")),
) -> dict[str, object]:
    """Stub — returns empty until the pipeline ships.

    See `docs/plan.md` §7 for the WhatsApp ingestion pipeline.
    """
    return {"items": [], "total": 0, "status": "not_yet_enabled"}


@router.get("/orders", status_code=200)
async def list_orders(ctx: RequestContext = Depends(current_context)) -> dict[str, object]:
    return {"items": [], "total": 0, "status": "not_yet_enabled"}
