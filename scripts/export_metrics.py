
"""Export Prometheus metrics to CSV for SentinelOps ML training."""
import argparse, csv, time, urllib.parse, urllib.request, json
from datetime import datetime, timezone

PROM_URL = "http://localhost:9090"

QUERIES = {
    "demo_requests_rate":   'sum(rate(demo_requests_total{job="kubernetes-pods"}[1m]))',
    "demo_errors_rate":     'sum(rate(demo_requests_total{job="kubernetes-pods",status=~"5.."}[1m]))',
    "demo_memory_bytes":    'demo_memory_usage_bytes{job="kubernetes-pods"}',
    "demo_cpu_spike":       'demo_cpu_spike_active{job="kubernetes-pods"}',
    "container_cpu_rate":   'sum(rate(container_cpu_usage_seconds_total{pod=~"demo-app.*"}[1m]))',
    "container_mem_bytes":  'sum(container_memory_working_set_bytes{pod=~"demo-app.*"})',
    "container_net_rx":     'sum(rate(container_network_receive_bytes_total{pod=~"demo-app.*"}[1m]))',
    "container_net_tx":     'sum(rate(container_network_transmit_bytes_total{pod=~"demo-app.*"}[1m]))',
}

def query_range(prom_url, query, start, end, step=15):
    params = urllib.parse.urlencode({"query": query, "start": start, "end": end, "step": step})
    url = f"{prom_url}/api/v1/query_range?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    if data["status"] != "success":
        raise RuntimeError(f"Prometheus error: {data}")
    if not data["data"]["result"]:
        return []
    return [(float(ts), float(val)) for ts, val in data["data"]["result"][0]["values"]]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True, choices=["normal", "anomaly"])
    p.add_argument("--duration", type=int, default=300)
    p.add_argument("--step", type=int, default=15)
    p.add_argument("--prom-url", default=PROM_URL)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    end = time.time(); start = end - args.duration
    print(f"Export {args.label} de {args.duration}s")
    series_by_name = {}
    for name, q in QUERIES.items():
        print(f"  - {name} ...", end=" ", flush=True)
        try:
            s = query_range(args.prom_url, q, start, end, args.step)
            series_by_name[name] = dict(s)
            print(f"{len(s)} points")
        except Exception as e:
            print(f"ERREUR: {e}")
            series_by_name[name] = {}

    all_ts = sorted({ts for d in series_by_name.values() for ts in d})
    print(f"{len(all_ts)} timestamps uniques")

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "iso_time"] + list(QUERIES.keys()) + ["label"])
        for ts in all_ts:
            row = [int(ts), datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()]
            for name in QUERIES:
                row.append(series_by_name[name].get(ts, ""))
            row.append(args.label)
            w.writerow(row)
    print(f"✅ CSV écrit: {args.out}")

if __name__ == "__main__":
    main()
