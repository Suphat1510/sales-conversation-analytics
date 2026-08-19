from src.rules import classify_text

def test_spa_booking_and_price():
    r = classify_text("อยากจองคิว ขอราคาและ demo", "SPA")
    assert "Booking/Appointment" in r["interest"]
    assert "ถามราคา" in r["purchase_signal"]
    assert "ขอ Demo" in r["purchase_signal"]

def test_fnb_stock():
    r = classify_text("ร้านมีหลายสาขา อยากจัดการ stock และครัว", "FNB")
    assert "Stock/Recipe" in r["interest"]
    assert "Kitchen/KDS" in r["interest"]
