"""Policy engine tests — window, DOA, proof, remedy priority."""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.policy import check_policy


def _order(days_ago, status="Delivered"):
    return SimpleNamespace(delivery_status=status,
                           delivery_date=datetime.utcnow() - timedelta(days=days_ago),
                           days_since_delivery=days_ago)


def _product(stock=10, window=7):
    return SimpleNamespace(stock_qty=stock, return_window_days=window)


def test_eligible_replacement_with_proof_in_stock():
    r = check_policy(_order(2), "damaged", True, _product(stock=5))
    assert r.status == "ELIGIBLE" and r.remedy == "REPLACEMENT"


def test_refund_when_out_of_stock():
    r = check_policy(_order(2), "damaged", True, _product(stock=0))
    assert r.status == "ELIGIBLE" and r.remedy == "REFUND"


def test_needs_proof_without_upload():
    r = check_policy(_order(2), "damaged", False, _product())
    assert r.status == "NEEDS_PROOF"


def test_not_eligible_outside_window():
    r = check_policy(_order(10), "damaged", True, _product(window=7))
    assert r.status == "NOT_ELIGIBLE"


def test_not_eligible_if_not_delivered():
    r = check_policy(_order(1, status="Shipped"), "damaged", True, _product())
    assert r.status == "NOT_ELIGIBLE"


def test_not_eligible_unknown_order():
    r = check_policy(None, "damaged", True, None)
    assert r.status == "NOT_ELIGIBLE"


def test_doa_flag_within_72h():
    r = check_policy(_order(2), "defective", True, _product())
    assert any("DOA" in c for c in r.checks)


def test_doa_flag_outside_72h_but_in_window():
    r = check_policy(_order(5), "defective", True, _product(window=7))
    assert r.status == "ELIGIBLE"
    assert any("outside DOA" in c for c in r.checks)


def test_boundary_exactly_at_window():
    r = check_policy(_order(7), "damaged", True, _product(window=7))
    assert r.status == "ELIGIBLE"          # day 7 is still inside
