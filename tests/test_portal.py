"""Customer portal tests — lookup, request flow, policy enforcement, tracking."""
from datetime import datetime, timedelta


def test_portal_home(client):
    r = client.get("/portal")
    assert r.status_code == 200 and "Returns" in r.text


def test_order_lookup_found(client):
    r = client.get("/portal/order?order_id=ORD-98231")
    assert r.status_code == 200
    assert "ORD-98231" in r.text and "AeroSound" in r.text


def test_order_lookup_not_found(client):
    r = client.get("/portal/order?order_id=ORD-NOPE")
    assert r.status_code == 200 and "No order found" in r.text


def test_request_without_proof_needs_proof(client):
    r = client.post("/portal/order/request",
                    data={"order_id": "ORD-98231", "claim_type": "damaged",
                          "customer_claim": "cracked"})
    assert r.status_code == 200
    assert "More information needed" in r.text


def test_request_with_proof_approved_and_ticket_created(client):
    r = client.post(
        "/portal/order/request",
        data={"order_id": "ORD-98231", "claim_type": "damaged", "customer_claim": "cracked on arrival"},
        files={"proof": ("proof.jpg", b"fake-image-bytes", "image/jpeg")})
    assert r.status_code == 200
    # PROD-EAR-001 is in stock -> replacement approved
    assert "REPLACEMENT" in r.text or "Replacement" in r.text
    assert "TCK-" in r.text


def test_track_shows_request(client):
    # raise one, then track
    client.post("/portal/order/request",
                data={"order_id": "ORD-98231", "claim_type": "damaged", "customer_claim": "x"},
                files={"proof": ("p.jpg", b"x", "image/jpeg")})
    r = client.get("/portal/track?order_id=ORD-98231")
    assert r.status_code == 200 and "TCK-" in r.text


def test_track_unknown_order(client):
    r = client.get("/portal/track?order_id=ORD-NOPE")
    assert r.status_code == 200 and "No order found" in r.text


def test_not_delivered_order_cannot_raise(client):
    # ORD-98232 is 'Shipped' (not delivered) -> no request form, guidance shown
    r = client.get("/portal/order?order_id=ORD-98232")
    assert "once this order is marked" in r.text
