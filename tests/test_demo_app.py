import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "demo-app"))
import app as demo


def test_health_ok_then_chaos_then_recover():
    c = demo.app.test_client()
    assert c.get("/health").status_code == 200
    c.get("/chaos/unhealthy")
    assert c.get("/health").status_code == 500
    c.get("/chaos/recover")
    assert c.get("/health").status_code == 200


def test_metrics():
    assert b"demo_app_uptime_seconds" in demo.app.test_client().get("/metrics").data
