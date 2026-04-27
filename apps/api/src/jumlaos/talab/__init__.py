"""Talab (طلب) — WhatsApp order intake, orders, deliveries.

Status: **stub**. The full pipeline ships at month 4 (see docs/plan.md §7).
The data model below is finalized so Mali can already reference orders.
"""

from jumlaos.talab.routes import router

__all__ = ["router"]
