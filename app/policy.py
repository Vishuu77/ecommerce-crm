"""Return & refund policy engine (roadmap section 1).

Rules:
  - Damaged/Defective on arrival (DOA): report within 48-72h (3 days).
  - Standard return window: product.return_window_days (default 7) from delivery.
  - Proof (photo/video) required to proceed.
  - Remedy priority: replacement first; refund only if out of stock / unserviceable.
"""
from __future__ import annotations
from dataclasses import dataclass, field

DOA_DAYS = 3            # 48-72h
CLAIM_TYPES = ["damaged", "defective", "wrong_item", "not_needed", "other"]


@dataclass
class PolicyResult:
    status: str                       # ELIGIBLE | NEEDS_PROOF | NOT_ELIGIBLE
    remedy: str                       # REPLACEMENT | REFUND | NONE
    checks: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def summary(self) -> str:
        return "; ".join(self.checks)


def check_policy(order, claim_type: str, has_proof: bool, product=None) -> PolicyResult:
    """Evaluate a return/replacement request against company policy."""
    checks: list[str] = []
    window = getattr(product, "return_window_days", 7) or 7
    days = order.days_since_delivery if order else None

    # --- Stage 1: automated checks ---
    if order is None:
        return PolicyResult("NOT_ELIGIBLE", "NONE", ["Order not found"], "Order not found.")

    if order.delivery_status != "Delivered":
        return PolicyResult("NOT_ELIGIBLE", "NONE",
                            [f"Order status is '{order.delivery_status}', not Delivered"],
                            "Returns can only be raised after delivery.")

    if days is None:
        return PolicyResult("NOT_ELIGIBLE", "NONE", ["No delivery date on record"],
                            "We have no delivery date for this order.")

    # window check
    if days > window:
        checks.append(f"Delivered {days} days ago — outside the {window}-day return window")
        return PolicyResult("NOT_ELIGIBLE", "NONE", checks,
                            f"Sorry, this is outside the {window}-day return window.")

    checks.append(f"Delivered {days} days ago (<{window}-day window)")

    # DOA specific
    if claim_type in ("damaged", "defective"):
        if days <= DOA_DAYS:
            checks.append(f"Reported within DOA window ({days} days <= {DOA_DAYS})")
        else:
            checks.append(f"Reported at {days} days — outside DOA 48-72h window "
                          f"(still inside standard {window}-day window)")

    # --- Stage 2: proof requirement ---
    if not has_proof:
        return PolicyResult("NEEDS_PROOF", "NONE", checks,
                            "Please upload a photo or short video of the issue "
                            "(product + packaging) to proceed.")

    checks.append("Proof attached")

    # --- Stage 3: remedy priority — replacement first ---
    in_stock = bool(product and getattr(product, "stock_qty", 0) > 0)
    if in_stock:
        remedy = "REPLACEMENT"
        checks.append(f"Replacement available (stock {product.stock_qty})")
    else:
        remedy = "REFUND"
        checks.append("Out of stock — refund to original payment method")
    return PolicyResult("ELIGIBLE", remedy, checks, "Your request is eligible.")
