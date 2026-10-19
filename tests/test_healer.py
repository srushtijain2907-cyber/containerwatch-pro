import os, sys
os.environ["HEALER_AUTOSTART"] = "0"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "healer"))
import healer


class FakeContainer:
    def __init__(self, name, status, health=None):
        self.name, self.status = name, status
        self.attrs = {"State": {"Health": {"Status": health}} if health else {"State": {}}}
        self.actions = []

    def reload(self): pass
    def restart(self, timeout=5): self.actions.append("restart")
    def start(self): self.actions.append("start")


class FakeClient:
    def __init__(self, items):
        self.containers = self
        self.items = items

    def list(self, **kwargs): return self.items


def setup_function():
    healer.last_heal.clear(); healer.heal_counts.clear(); healer.state["enabled"] = True


def test_restarts_unhealthy(monkeypatch):
    c = FakeContainer("demo-app", "running", "unhealthy")
    monkeypatch.setattr(healer, "get_client", lambda: FakeClient([c]))
    healer.check_once()
    assert c.actions == ["restart"] and healer.heal_counts["demo-app"] == 1


def test_starts_exited(monkeypatch):
    c = FakeContainer("demo-app", "exited")
    monkeypatch.setattr(healer, "get_client", lambda: FakeClient([c]))
    healer.check_once()
    assert c.actions == ["start"]


def test_cooldown_and_pause(monkeypatch):
    c = FakeContainer("demo-app", "exited")
    monkeypatch.setattr(healer, "get_client", lambda: FakeClient([c]))
    healer.check_once(); healer.check_once()
    assert c.actions == ["start"]          # cooldown blocks the 2nd heal
    healer.last_heal.clear(); healer.state["enabled"] = False
    healer.check_once()
    assert c.actions == ["start"]          # paused: nothing happens


def test_healthy_untouched(monkeypatch):
    c = FakeContainer("demo-app", "running", "healthy")
    monkeypatch.setattr(healer, "get_client", lambda: FakeClient([c]))
    healer.check_once()
    assert c.actions == []


def test_page_and_webhook():
    cl = healer.app.test_client()
    assert b"ContainerWatch" in cl.get("/").data
    r = cl.post("/webhook", json={"alerts": [{"status": "firing", "labels": {"alertname": "X"}, "annotations": {"summary": "s"}}]})
    assert r.get_json()["received"] == 1


class StatsContainer:
    name = "demo-app"
    attrs = {"HostConfig": {"Memory": 256 * 1024 * 1024}}

    def stats(self, stream=False):
        return {
            "cpu_stats": {"cpu_usage": {"total_usage": 2_000_000}, "system_cpu_usage": 20_000_000, "online_cpus": 4},
            "precpu_stats": {"cpu_usage": {"total_usage": 1_000_000}, "system_cpu_usage": 10_000_000},
            "memory_stats": {"usage": 200 * 1024 * 1024, "stats": {"inactive_file": 20 * 1024 * 1024}},
        }


def test_parse_stats():
    pct, usage = healer.parse_stats(StatsContainer().stats())
    assert round(pct) == 40                      # 1M/10M * 4 cpus * 100
    assert usage == 180 * 1024 * 1024


def test_collect_stats_sets_metrics(monkeypatch):
    monkeypatch.setattr(healer, "get_client", lambda: FakeClient([StatsContainer()]))
    healer.collect_stats()
    assert round(healer.CPU.labels("demo-app")._value.get()) == 40
    assert round(healer.MEM_PCT.labels("demo-app")._value.get()) == 70   # 180/256


class ScopedContainer:
    def __init__(self, name, project):
        self.name, self.status = name, "running"
        self.labels = {"com.docker.compose.project": project}
        self.attrs = {"State": {}, "Config": {"Image": "x"}}


def test_status_page_only_shows_own_project(monkeypatch):
    items = [ScopedContainer("a", "cw"), ScopedContainer("b", "other")]
    monkeypatch.setattr(healer, "get_client", lambda: FakeClient(items))
    healer._scope["project"] = "cw"
    try:
        data = healer.app.test_client().get("/api/status").get_json()
    finally:
        healer._scope.clear()
    assert [c["name"] for c in data["containers"]] == ["a"] and data["scope"] == "cw"
