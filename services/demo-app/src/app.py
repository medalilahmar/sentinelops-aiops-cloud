from flask import Flask, jsonify
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time, threading, os

app = Flask(__name__)

REQUEST_COUNT = Counter('demo_requests_total', 'Total requests', ['endpoint', 'method', 'status'])
REQUEST_LATENCY = Histogram('demo_request_duration_seconds', 'Request latency', ['endpoint'])
MEMORY_USAGE = Gauge('demo_memory_usage_bytes', 'Simulated memory usage')
CPU_SPIKE = Gauge('demo_cpu_spike_active', 'CPU spike active (0 or 1)')

_leak_memory = []
_cpu_spike_active = False

@app.before_request
def start_timer():
    from flask import request, g
    g.start = time.time()

@app.after_request
def record_metrics(response):
    from flask import request, g
    endpoint = request.path
    REQUEST_COUNT.labels(endpoint=endpoint, method=request.method, status=response.status_code).inc()
    if hasattr(g, 'start'):
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.time() - g.start)
    return response

@app.route('/')
def home():
    return jsonify({"status": "ok", "service": "demo-app"})

@app.route('/metrics')
def metrics():
    from prometheus_client import REGISTRY
    return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/chaos/memory')
def chaos_memory():
    _leak_memory.append(bytearray(50 * 1024 * 1024))
    MEMORY_USAGE.set(len(_leak_memory) * 50 * 1024 * 1024)
    return jsonify({"chaos": "memory", "leaked_mb": len(_leak_memory) * 50})

def _cpu_burn():
    global _cpu_spike_active
    _cpu_spike_active = True
    CPU_SPIKE.set(1)
    end = time.time() + 30
    while time.time() < end:
        _ = sum(i * i for i in range(10000))
    _cpu_spike_active = False
    CPU_SPIKE.set(0)

@app.route('/chaos/cpu')
def chaos_cpu():
    threading.Thread(target=_cpu_burn, daemon=True).start()
    return jsonify({"chaos": "cpu", "duration_seconds": 30})

@app.route('/chaos/error')
def chaos_error():
    return jsonify({"error": "simulated failure"}), 500

@app.route('/chaos/latency')
def chaos_latency():
    time.sleep(5)
    return jsonify({"chaos": "latency", "delay_seconds": 5})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
