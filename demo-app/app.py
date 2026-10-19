import os, signal, threading, time
from flask import Flask, jsonify, request
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
REQUESTS = Counter("demo_app_requests_total", "Total requests", ["endpoint"])
UPTIME = Gauge("demo_app_uptime_seconds", "App uptime")
START = time.time()
state = {"healthy": True}
_memory_hog = []


@app.get("/")
def index():
    REQUESTS.labels("/").inc()
    return jsonify(
        service="ContainerWatch demo app",
        chaos=["/chaos/unhealthy", "/chaos/crash", "/chaos/recover"],
        load=["/load/cpu?seconds=120", "/load/memory?mb=200", "/load/release"],
    )


@app.get("/health")
def health():
    REQUESTS.labels("/health").inc()
    if not state["healthy"]:
        return jsonify(status="broken"), 500
    return jsonify(status="ok", uptime_seconds=round(time.time() - START))


@app.get("/metrics")
def metrics():
    UPTIME.set(time.time() - START)
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


# ---------- chaos engineering ----------
@app.get("/chaos/unhealthy")
def chaos_unhealthy():
    state["healthy"] = False
    return jsonify(message="health endpoint now fails; Docker will mark the container unhealthy")


@app.get("/chaos/recover")
def chaos_recover():
    state["healthy"] = True
    return jsonify(message="health restored")


@app.get("/chaos/crash")
def chaos_crash():
    # stop the gunicorn master (PID 1) so the whole container exits
    threading.Timer(0.5, lambda: os.kill(os.getppid(), signal.SIGTERM)).start()
    return jsonify(message="crashing the container in 0.5s")


# ---------- resource load ----------
def _burn(seconds):
    end = time.time() + seconds
    while time.time() < end:
        pass


@app.get("/load/cpu")
def load_cpu():
    seconds = min(int(request.args.get("seconds", 120)), 600)
    threading.Thread(target=_burn, args=(seconds,), daemon=True).start()
    return jsonify(message=f"burning CPU for {seconds}s")


@app.get("/load/memory")
def load_memory():
    mb = min(int(request.args.get("mb", 200)), 240)
    _memory_hog.append(bytearray(mb * 1024 * 1024))
    return jsonify(message=f"allocated {mb} MB")


@app.get("/load/release")
def release():
    _memory_hog.clear()
    return jsonify(message="memory released")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
