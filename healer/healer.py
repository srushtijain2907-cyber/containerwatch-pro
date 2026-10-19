"""ContainerWatch Healer: self-healing engine + live status page.

Every CHECK_INTERVAL seconds it looks at containers labelled
`containerwatch.autoheal=true` and restarts any that are exited or unhealthy.
It also receives alerts from Alertmanager and exposes Prometheus metrics.
"""
import logging
import os
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import docker
from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

LABEL = "containerwatch.autoheal"
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))
COOLDOWN = int(os.getenv("COOLDOWN_SECONDS", "45"))
STATS_INTERVAL = int(os.getenv("STATS_INTERVAL", "15"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = Flask(__name__)

RESTARTS = Counter("healer_restarts_total", "Containers restarted by the healer", ["container", "reason"])
MONITORED = Gauge("healer_containers_monitored", "Containers carrying the autoheal label")
ALERTS = Counter("healer_alerts_received_total", "Alerts received from Alertmanager")

# Per-container resource metrics read straight from the Docker API
CPU = Gauge("cw_container_cpu_percent", "Container CPU usage (100 = one full core)", ["name"])
MEM = Gauge("cw_container_memory_usage_bytes", "Container memory usage in bytes", ["name"])
MEM_LIMIT = Gauge("cw_container_memory_limit_bytes", "Container memory limit in bytes (0 = unlimited)", ["name"])
MEM_PCT = Gauge("cw_container_memory_percent", "Memory usage as % of the container limit", ["name"])
_seen = set()

events = deque(maxlen=60)
last_heal = {}
heal_counts = {}
state = {"enabled": True}
_client = None


def get_client():
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


SHOW_ALL = os.getenv("SHOW_ALL_CONTAINERS", "0") == "1"
_scope = {}


def get_project():
    """Compose project this healer belongs to (None = unknown, so show everything)."""
    if "project" not in _scope:
        try:
            me = get_client().containers.get(os.getenv("HOSTNAME", ""))
            _scope["project"] = me.labels.get("com.docker.compose.project")
        except Exception:  # noqa: BLE001
            return None
    return _scope["project"]


def in_scope(container):
    project = get_project()
    if SHOW_ALL or not project:
        return True
    return (getattr(container, "labels", None) or {}).get("com.docker.compose.project") == project


def add_event(kind, message):
    events.appendleft({"ts": time.time(), "kind": kind, "message": message})
    logging.info("[%s] %s", kind, message)


def heal(container, reason):
    last_heal[container.name] = time.time()
    try:
        if reason == "exited":
            container.start()
        else:
            container.restart(timeout=5)
    except Exception as exc:  # noqa: BLE001
        add_event("error", f"Failed to heal {container.name}: {exc}")
        return
    heal_counts[container.name] = heal_counts.get(container.name, 0) + 1
    RESTARTS.labels(container.name, reason).inc()
    add_event("heal", f"Self-healed {container.name} (reason: {reason})")


def parse_stats(raw):
    """Turn a Docker stats sample into (cpu_percent, memory_bytes)."""
    cpu, pre = raw.get("cpu_stats", {}), raw.get("precpu_stats", {})
    cpu_delta = cpu.get("cpu_usage", {}).get("total_usage", 0) - pre.get("cpu_usage", {}).get("total_usage", 0)
    sys_delta = cpu.get("system_cpu_usage", 0) - pre.get("system_cpu_usage", 0)
    online = cpu.get("online_cpus") or len(cpu.get("cpu_usage", {}).get("percpu_usage") or []) or 1
    pct = cpu_delta / sys_delta * online * 100.0 if sys_delta > 0 and cpu_delta >= 0 else 0.0
    mem = raw.get("memory_stats", {})
    cache = mem.get("stats", {})
    usage = max(mem.get("usage", 0) - cache.get("inactive_file", cache.get("total_inactive_file", 0)), 0)
    return pct, usage


def _collect_one(container):
    try:
        pct, usage = parse_stats(container.stats(stream=False))
        limit = container.attrs.get("HostConfig", {}).get("Memory", 0) or 0
        return container.name, pct, usage, limit
    except Exception as exc:  # noqa: BLE001
        logging.warning("stats failed for %s: %s", getattr(container, "name", "?"), exc)
        return None


def collect_stats():
    running = [c for c in get_client().containers.list() if in_scope(c)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = [r for r in pool.map(_collect_one, running) if r]
    names = set()
    for name, pct, usage, limit in results:
        names.add(name)
        CPU.labels(name).set(round(pct, 2))
        MEM.labels(name).set(usage)
        MEM_LIMIT.labels(name).set(limit)
        if limit > 0:
            MEM_PCT.labels(name).set(round(usage / limit * 100, 2))
        else:
            try:
                MEM_PCT.remove(name)
            except KeyError:
                pass
    for gone in _seen - names:
        for g in (CPU, MEM, MEM_LIMIT, MEM_PCT):
            try:
                g.remove(gone)
            except KeyError:
                pass
    _seen.clear()
    _seen.update(names)


def stats_loop():
    while True:
        try:
            collect_stats()
        except Exception as exc:  # noqa: BLE001
            logging.error("stats collection failed: %s", exc)
        time.sleep(STATS_INTERVAL)


def check_once():
    containers = get_client().containers.list(all=True, filters={"label": f"{LABEL}=true"})
    MONITORED.set(len(containers))
    for c in containers:
        for r in ("exited", "unhealthy"):
            RESTARTS.labels(c.name, r)  # start counters at 0 so increase() sees the first heal
    if not state["enabled"]:
        return
    for c in containers:
        c.reload()
        health = c.attrs.get("State", {}).get("Health", {}).get("Status")
        if c.status in ("exited", "dead"):
            reason = "exited"
        elif health == "unhealthy":
            reason = "unhealthy"
        else:
            continue
        if time.time() - last_heal.get(c.name, 0) >= COOLDOWN:
            heal(c, reason)


def loop():
    add_event("info", f"Healer started (interval {CHECK_INTERVAL}s, cooldown {COOLDOWN}s)")
    while True:
        try:
            check_once()
        except Exception as exc:  # noqa: BLE001
            logging.error("check failed: %s", exc)
        time.sleep(CHECK_INTERVAL)


@app.get("/api/status")
def api_status():
    try:
        items = []
        for c in filter(in_scope, get_client().containers.list(all=True)):
            st = c.attrs.get("State", {})
            items.append({
                "name": c.name,
                "image": c.attrs.get("Config", {}).get("Image", "?"),
                "status": c.status,
                "health": st.get("Health", {}).get("Status", "none"),
                "autoheal": c.labels.get(LABEL) == "true",
                "heals": heal_counts.get(c.name, 0),
            })
        items.sort(key=lambda x: x["name"])
        return jsonify(enabled=state["enabled"], containers=items, events=list(events),
                       scope=(get_project() or "all") if not SHOW_ALL else "all")
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=str(exc)), 500


@app.post("/api/heal/<action>")
def api_toggle(action):
    if action not in ("pause", "resume"):
        return jsonify(error="use pause or resume"), 400
    state["enabled"] = action == "resume"
    add_event("info", f"Auto-healing {'resumed' if state['enabled'] else 'paused'}")
    return jsonify(enabled=state["enabled"])


@app.post("/webhook")
def webhook():
    payload = request.get_json(silent=True) or {}
    for a in payload.get("alerts", []):
        ALERTS.inc()
        labels, notes = a.get("labels", {}), a.get("annotations", {})
        add_event(f"alert-{a.get('status', 'firing')}", f"{labels.get('alertname')}: {notes.get('summary', '')}")
    return jsonify(received=len(payload.get("alerts", [])))


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>ContainerWatch Status</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,sans-serif;color:#e6edf3;
background:radial-gradient(circle at 20% 0,#1b2a4a,#0d1117 60%);min-height:100vh;padding:24px}
h1{margin:0;font-size:28px}.sub{color:#8b98a9;margin:4px 0 20px}
.bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:20px}
.pill{padding:6px 14px;border-radius:999px;background:#1f2a3d;font-size:14px}
button{background:#2f6feb;border:0;color:#fff;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
.card{background:#151b26cc;border:1px solid #263247;border-radius:14px;padding:16px;border-left:5px solid #3fb950}
.card.bad{border-left-color:#f85149}.card.warn{border-left-color:#d29922}
.card h3{margin:0 0 6px;font-size:17px}.meta{color:#8b98a9;font-size:13px;line-height:1.7}
.badge{display:inline-block;padding:2px 9px;border-radius:6px;font-size:12px;background:#1f6f3a}
.bad .badge{background:#8e1b1b}.warn .badge{background:#7a5a00}
h2{margin:28px 0 10px;font-size:19px}.ev{background:#151b26cc;border:1px solid #263247;border-radius:12px;padding:6px 14px}
.ev div{padding:7px 0;border-bottom:1px solid #202a3b;font-size:14px}.ev div:last-child{border:0}
.t{color:#8b98a9;margin-right:10px;font-family:monospace}.heal{color:#3fb950}.alert-firing{color:#f85149}
.alert-resolved{color:#58a6ff}.error{color:#f85149}
</style></head><body>
<h1>🛡️ ContainerWatch</h1><div class="sub">Live container health &amp; self-healing status</div>
<div class="bar"><span class="pill" id="sum">loading…</span><span class="pill" id="heal"></span><span class="pill" id="scope"></span>
<button id="tog">Pause healing</button></div>
<div class="grid" id="grid"></div>
<h2>Event timeline <small style="color:#8b98a9;font-weight:normal">(your local time)</small></h2><div class="ev" id="ev"></div>
<script>
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let enabled=true;
async function load(){
 try{
  const d=await (await fetch('/api/status')).json(); if(d.error) throw new Error(d.error);
  enabled=d.enabled;
  const ok=d.containers.filter(c=>c.status==='running'&&c.health!=='unhealthy').length;
  document.getElementById('sum').textContent=`${ok}/${d.containers.length} containers healthy`;
  document.getElementById('scope').textContent='Project: '+d.scope;
  document.getElementById('heal').textContent=enabled?'Auto-healing: ON':'Auto-healing: PAUSED';
  document.getElementById('tog').textContent=enabled?'Pause healing':'Resume healing';
  document.getElementById('grid').innerHTML=d.containers.map(c=>{
   const bad=c.status!=='running'||c.health==='unhealthy';
   const warn=!bad&&c.health==='starting';
   return `<div class="card ${bad?'bad':warn?'warn':''}"><h3>${esc(c.name)}</h3>
   <span class="badge">${esc(c.status)}${c.health!=='none'?' · '+esc(c.health):''}</span>
   <div class="meta">${esc(c.image)}<br>Auto-heal: ${c.autoheal?'✅ enabled':'—'}<br>Self-heals: ${c.heals}</div></div>`}).join('');
  document.getElementById('ev').innerHTML=d.events.map(e=>`<div><span class="t">${esc(new Date(e.ts*1000).toLocaleTimeString())}</span><span class="${esc(e.kind)}">${esc(e.message)}</span></div>`).join('')||'<div>No events yet</div>';
 }catch(e){document.getElementById('sum').textContent='Error: '+e.message}
}
document.getElementById('tog').onclick=async()=>{await fetch('/api/heal/'+(enabled?'pause':'resume'),{method:'POST'});load()};
load();setInterval(load,4000);
</script></body></html>"""


@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")


if os.getenv("HEALER_AUTOSTART", "1") == "1":
    threading.Thread(target=loop, daemon=True).start()
    threading.Thread(target=stats_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
